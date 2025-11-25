"""API authentication helper for protecting sensitive endpoints with rotation support."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from typing import Dict, Optional, Tuple, Any, List

from flask import Request

from xai.core.config import Config
from xai.core.security_validation import log_security_event


class APIKeyStore:
    """Persistent API key storage with auditing metadata."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._audit_path = f"{path}.log"
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        self._keys = data
                    else:
                        self._keys = {}
            except (OSError, json.JSONDecodeError):
                self._keys = {}

    def _persist(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._keys, handle, indent=2)
        os.replace(tmp_path, self.path)

    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._keys)

    @property
    def audit_log_path(self) -> str:
        return self._audit_path

    def issue_key(self, label: str = "", scope: str = "user", plaintext: Optional[str] = None) -> Tuple[str, str]:
        new_key = plaintext or secrets.token_hex(32)
        key_id = self._hash_key(new_key)
        self._keys[key_id] = {"label": label, "created": time.time(), "scope": scope}
        self._persist()
        self._log_event("issue", key_id, {"label": label, "scope": scope})
        return new_key, key_id

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            self._persist()
            self._log_event("revoke", key_id)
            return True
        return False

    def _log_event(self, action: str, key_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "timestamp": time.time(),
            "action": action,
            "key_id": key_id,
        }
        if extra:
            event.update(extra)
        directory = os.path.dirname(self._audit_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        self._emit_security_log(event)

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not os.path.exists(self._audit_path):
            return []
        events: List[Dict[str, Any]] = []
        with open(self._audit_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events[-limit:]

    def _emit_security_log(self, event: Dict[str, Any]) -> None:
        try:
            payload = {
                "action": event.get("action"),
                "key_id": event.get("key_id"),
                "scope": event.get("scope", "unknown"),
                "label": event.get("label", ""),
                "timestamp": event.get("timestamp"),
            }
            severity = "WARNING" if event.get("action") == "revoke" else "INFO"
            log_security_event("api_key_audit", payload, severity=severity)
        except Exception:
            # Never let logging issues break key management
            return


class APIAuthManager:
    """API key authentication + rotation helper."""

    def __init__(
        self,
        required: bool = False,
        allowed_keys: Optional[List[str]] = None,
        store: Optional[APIKeyStore] = None,
        admin_keys: Optional[List[str]] = None,
    ) -> None:
        manual_users = [key.strip() for key in (allowed_keys or []) if key.strip()]
        manual_admins = [key.strip() for key in (admin_keys or []) if key.strip()]
        self._manual_admin_hashes = {self._hash_key(key) for key in manual_admins}
        self._manual_hashes = {self._hash_key(key) for key in manual_users} | self._manual_admin_hashes
        self._store = store
        self._store_metadata: Dict[str, Dict[str, Any]] = store.list_keys() if store else {}
        self._store_hash_set = set(self._store_metadata.keys()) if store else set()
        self._store_admin_hashes = {
            key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
        }
        self._required = required

    @classmethod
    def from_config(cls, store: Optional[APIKeyStore] = None) -> "APIAuthManager":
        return cls(
            required=getattr(Config, "API_AUTH_REQUIRED", False),
            allowed_keys=list(getattr(Config, "API_AUTH_KEYS", [])),
            admin_keys=list(getattr(Config, "API_ADMIN_KEYS", [])),
            store=store,
        )

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_enabled(self) -> bool:
        return self._required

    def _extract_key(self, request: Request) -> Optional[str]:
        header_key = request.headers.get("X-API-Key")
        if header_key:
            return header_key.strip()

        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()

        arg_key = request.args.get("api_key")
        if arg_key:
            return arg_key.strip()

        return None

    def authorize(self, request: Request) -> Tuple[bool, Optional[str]]:
        if not self.is_enabled():
            return True, None

        key = self._extract_key(request)
        if not key:
            return False, "API key missing or invalid"

        hashed = self._hash_key(key)
        if hashed in self._manual_hashes or hashed in self._store_hash_set:
            return True, None
        return False, "API key missing or invalid"

    def authorize_admin(self, request: Request) -> Tuple[bool, Optional[str]]:
        key = self._extract_admin_token(request)
        if not key:
            return False, "Admin token missing"
        hashed = self._hash_key(key)
        if hashed in self._manual_admin_hashes or hashed in self._store_admin_hashes:
            return True, None
        return False, "Admin token invalid"

    def refresh_from_store(self) -> None:
        if self._store:
            self._store_metadata = self._store.list_keys()
            self._store_hash_set = set(self._store_metadata.keys())
            self._store_admin_hashes = {
                key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
            }

    def list_key_metadata(self) -> Dict[str, Any]:
        return {
            "manual_keys": len(self._manual_hashes),
            "manual_admin_keys": len(self._manual_admin_hashes),
            "store": self._store_metadata if self._store else {},
        }

    def issue_key(self, label: str = "", scope: str = "user") -> Tuple[str, str]:
        if not self._store:
            raise ValueError("API key store not configured")
        plaintext, key_id = self._store.issue_key(label=label, scope=scope)
        self.refresh_from_store()
        return plaintext, key_id

    def revoke_key(self, key_id: str) -> bool:
        if not self._store:
            raise ValueError("API key store not configured")
        removed = self._store.revoke_key(key_id)
        self.refresh_from_store()
        return removed

    def _extract_admin_token(self, request: Request) -> Optional[str]:
        token = request.headers.get("X-Admin-Token")
        if token:
            return token.strip()
        auth = request.headers.get("Authorization", "").strip()
        if auth.lower().startswith("admin "):
            return auth.split(" ", 1)[1].strip()
        return None
