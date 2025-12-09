"""
Checkpoint-based partial sync helper.

Provides a thin coordination layer to source checkpoint metadata from the
local checkpoint manager and P2P network manager, picking the best available
candidate to accelerate sync without full chain download.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, Optional

import requests
from ecdsa import SECP256k1, VerifyingKey, BadSignatureError
import hashlib

from .checkpoint_payload import CheckpointPayload

@dataclass
class CheckpointMetadata:
    """Simple typed container for checkpoint metadata."""

    height: int
    block_hash: str
    timestamp: Optional[float] = None
    source: str = "unknown"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointMetadata":
        return cls(
            height=int(data["height"]),
            block_hash=str(data["block_hash"]),
            timestamp=data.get("timestamp"),
            source=data.get("source", "unknown"),
        )


class CheckpointSyncManager:
    """Coordinate checkpoint discovery and selection for partial sync."""

    def __init__(self, blockchain: Any, p2p_manager: Optional[Any] = None):
        self.blockchain = blockchain
        self.p2p_manager = p2p_manager
        self.checkpoint_manager = getattr(blockchain, "checkpoint_manager", None)
        self.required_quorum = int(getattr(getattr(blockchain, "config", None), "CHECKPOINT_QUORUM", 3))
        self.trusted_pubkeys = set(
            getattr(getattr(blockchain, "config", None), "TRUSTED_CHECKPOINT_PUBKEYS", []) or []
        )

    def _local_checkpoint_metadata(self) -> Optional[Dict[str, Any]]:
        """Return latest local checkpoint metadata if available."""
        cm = self.checkpoint_manager
        if not cm:
            return None
        if not hasattr(cm, "load_latest_checkpoint"):
            return None
        checkpoint = cm.load_latest_checkpoint()
        if not checkpoint:
            height = getattr(cm, "latest_checkpoint_height", None)
            if height is None:
                return None
            if hasattr(cm, "load_checkpoint"):
                checkpoint = cm.load_checkpoint(height)
        if not checkpoint:
            return None
        return {
            "height": getattr(checkpoint, "height", None),
            "block_hash": getattr(checkpoint, "block_hash", None),
            "timestamp": getattr(checkpoint, "timestamp", None),
            "source": "local",
        }

    def _p2p_checkpoint_metadata(self) -> Optional[Dict[str, Any]]:
        """Return checkpoint metadata reported by peers, if available."""
        mgr = self.p2p_manager
        if not mgr or not hasattr(mgr, "_get_checkpoint_metadata"):
            return None
        meta = mgr._get_checkpoint_metadata()  # noqa: SLF001 - deliberate internal hook
        if not meta:
            return None
        meta["source"] = "p2p"
        return meta

    def get_best_checkpoint_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Pick a checkpoint candidate from P2P (preferred) or local store.

        Preference is given to P2P metadata if present and complete, otherwise
        falls back to the latest local checkpoint. If both are available, the
        newer height wins.
        """
        p2p_meta = self._p2p_checkpoint_metadata()
        local_meta = self._local_checkpoint_metadata()
        chosen = self.choose_newer_metadata(p2p_meta, local_meta)
        if chosen:
            try:
                meta_obj = CheckpointMetadata.from_dict(chosen)
                # Preserve auxiliary fields like URL
                enriched = {**chosen, **meta_obj.__dict__}
                return enriched
            except (KeyError, ValueError, TypeError):
                return chosen
        return None

    def apply_local_checkpoint(self, height: Optional[int] = None) -> Optional[Any]:
        """
        Attempt to load a checkpoint and return it to the caller for application.

        This does not mutate chain state; callers should validate and apply the
        checkpoint contents before trusting it.
        """
        cm = self.checkpoint_manager
        if not cm:
            return None
        if height is not None:
            return cm.load_checkpoint(height)
        return cm.load_latest_checkpoint()

    @staticmethod
    def validate_payload(payload: CheckpointPayload) -> bool:
        """Validate payload integrity before application."""
        return payload.verify_integrity()

    def apply_payload(self, payload: CheckpointPayload, applier: Any) -> bool:
        """
        Validate and apply a checkpoint payload using provided applier.

        Args:
            payload: CheckpointPayload with state snapshot info
            applier: Callable or object with `.apply_checkpoint(payload)` to mutate state

        Returns:
            True if applied, False otherwise
        """
        if not self.validate_payload(payload):
            return False
        # Prefer direct blockchain application if supported
        if self._apply_to_blockchain(payload):
            return True
        if hasattr(applier, "apply_checkpoint"):
            applier.apply_checkpoint(payload)
            return True
        if callable(applier):
            applier(payload)
            return True
        return False

    def fetch_validate_apply(self) -> bool:
        """
        End-to-end helper: pick best checkpoint metadata, fetch payload, validate, and apply.
        """
        meta = self.get_best_checkpoint_metadata()
        if not meta:
            return False
        payload = self.fetch_payload(meta)
        # Fallback: use local checkpoint manager if metadata is local and no URL present
        if not payload and meta.get("source") == "local" and self.checkpoint_manager:
            try:
                payload = self.checkpoint_manager.load_latest_checkpoint()
            except Exception:
                payload = None
        if not payload:
            return False
        return self.apply_payload(payload, self.blockchain)

    def request_checkpoint_from_peers(self) -> Optional[CheckpointPayload]:
        """
        Ask P2P manager to request checkpoint payloads and return the first valid payload.
        """
        if not self.p2p_manager or not hasattr(self.p2p_manager, "broadcast"):
            return None
        # Broadcast a checkpoint request
        try:
            coro = self.p2p_manager.broadcast({"type": "checkpoint_request", "payload": {"want_payload": True}})
            if coro:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(coro)
                else:
                    loop.run_until_complete(coro)
        except Exception:
            return None

        # Inspect cached peer features for received payload hints with quorum logic
        features = getattr(self.p2p_manager, "peer_features", {}) or {}
        candidates: Dict[str, Dict[str, Any]] = {}
        for info in features.values():
            payload_data = info.get("checkpoint_payload") if isinstance(info, dict) else None
            if not payload_data:
                continue
            try:
                height = int(payload_data["height"])
                block_hash = str(payload_data["block_hash"])
                state_hash = str(payload_data["state_hash"])
                candidates.setdefault(block_hash, {"count": 0, "payload": payload_data})
                candidates[block_hash]["count"] += 1
                candidates[block_hash]["height"] = height
                candidates[block_hash]["state_hash"] = state_hash
            except (KeyError, ValueError, TypeError):
                continue

        # Choose the highest-height candidate that meets quorum
        quorum_candidates = [
            data for data in candidates.values() if data.get("count", 0) >= self.required_quorum
        ]
        if not quorum_candidates:
            return None
        chosen = max(quorum_candidates, key=lambda c: c.get("height", -1))
        payload_data = chosen["payload"]
        payload = self._build_payload(payload_data)
        if not payload:
            return None
        if not self._validate_payload_signature(payload_data):
            return None
        return payload

    def _build_payload(self, payload_data: Dict[str, Any]) -> Optional[CheckpointPayload]:
        try:
            payload = CheckpointPayload(
                height=int(payload_data["height"]),
                block_hash=str(payload_data["block_hash"]),
                state_hash=str(payload_data["state_hash"]),
                data=payload_data.get("data", {}),
            )
        except (KeyError, ValueError, TypeError):
            return None
        if not payload.verify_integrity():
            return None
        return payload

    def _validate_payload_signature(self, payload_data: Dict[str, Any]) -> bool:
        """
        Validate optional signature using trusted checkpoint signers.
        If no trusted pubkeys are configured, accept unsigned payloads (test/dev).
        """
        if not self.trusted_pubkeys:
            return True
        signature_hex = payload_data.get("signature")
        pubkey_hex = payload_data.get("pubkey")
        if not signature_hex or not pubkey_hex or pubkey_hex not in self.trusted_pubkeys:
            return False
        try:
            digest = self._checkpoint_digest(payload_data)
            vk = VerifyingKey.from_string(bytes.fromhex(pubkey_hex), curve=SECP256k1)
            vk.verify_digest(bytes.fromhex(signature_hex), digest)
            return True
        except (BadSignatureError, ValueError, TypeError):
            return False

    @staticmethod
    def _checkpoint_digest(payload_data: Dict[str, Any]) -> bytes:
        """
        Compute deterministic digest of critical checkpoint fields for signing.
        """
        import json
        material = {
            "height": int(payload_data["height"]),
            "block_hash": str(payload_data["block_hash"]),
            "state_hash": str(payload_data["state_hash"]),
        }
        blob = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).digest()

    def _apply_to_blockchain(self, payload: CheckpointPayload) -> bool:
        """
        Apply checkpoint payload directly to blockchain components when supported.

        Supports restoring UTXO snapshot and updating checkpoint metadata.
        """
        bc = getattr(self, "blockchain", None)
        if not bc:
            return False

        applied = False
        utxo_snapshot = payload.data.get("utxo_snapshot")
        if utxo_snapshot and hasattr(bc, "utxo_manager"):
            bc.utxo_manager.restore(utxo_snapshot)
            applied = True

        cm = getattr(bc, "checkpoint_manager", None)
        if cm and payload.height is not None:
            cm.latest_checkpoint_height = payload.height
            applied = True

        return applied

    @staticmethod
    def load_payload_from_file(path: str) -> Optional[CheckpointPayload]:
        """
        Load a checkpoint payload from a JSON file.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CheckpointPayload(
                height=int(data["height"]),
                block_hash=str(data["block_hash"]),
                state_hash=str(data["state_hash"]),
                data=data.get("data", {}),
            )
        except (FileNotFoundError, KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def fetch_payload(self, meta: Dict[str, Any]) -> Optional[CheckpointPayload]:
        """
        Fetch a checkpoint payload using metadata hints.

        Supports:
        - Local file path via `meta["url"]` pointing to a file.
        - HTTP(S) URL fetch with JSON payload.
        """
        url = meta.get("url")
        if not url:
            return None

        # Local file path
        if os.path.exists(url):
            payload = self.load_payload_from_file(url)
            return payload

        # HTTP(S)
        if url.startswith("http://") or url.startswith("https://"):
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                return CheckpointPayload(
                    height=int(data["height"]),
                    block_hash=str(data["block_hash"]),
                    state_hash=str(data["state_hash"]),
                    data=data.get("data", {}),
                )
            except (requests.RequestException, KeyError, ValueError, TypeError, json.JSONDecodeError):
                return None

        return None


    @staticmethod
    def choose_newer_metadata(*candidates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Choose the highest-height valid checkpoint metadata from provided candidates.
        """
        valid = [c for c in candidates if c and CheckpointSyncManager._is_metadata_complete(c)]
        if not valid:
            return None
        return max(valid, key=lambda m: m.get("height", -1))

    @staticmethod
    def _is_metadata_complete(meta: Dict[str, Any]) -> bool:
        return bool(meta.get("height") is not None and meta.get("block_hash"))
