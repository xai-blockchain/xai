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
        self.min_peer_diversity = int(getattr(getattr(blockchain, "config", None), "CHECKPOINT_MIN_PEERS", 2))
        self.rate_limit_seconds = int(getattr(getattr(blockchain, "config", None), "CHECKPOINT_REQUEST_RATE_SECONDS", 30))
        self._last_request_ts: float = 0.0
        self._provenance_log: list[dict] = []

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
        payload = None
        if meta:
            payload = self.fetch_payload(meta)
        # Fallback: use local checkpoint manager if metadata is local and no URL present
        if not payload and meta and meta.get("source") == "local" and self.checkpoint_manager:
            try:
                payload = self.checkpoint_manager.load_latest_checkpoint()
            except (OSError, IOError, ValueError, TypeError, KeyError, AttributeError) as e:
                import logging
                logging.getLogger(__name__).debug(
                    "Failed to load local checkpoint",
                    extra={"error_type": type(e).__name__, "error": str(e)}
                )
                payload = None
        # Fallback: request from peers if nothing was obtained
        if not payload:
            payload = self.request_checkpoint_from_peers()
        if not payload:
            return False
        if not self._validate_payload_signature(payload.to_dict()):
            return False
        if not self._validate_work(payload.to_dict()):
            return False
        self._log_provenance(payload, payload.to_dict(), source=meta.get("source") if meta else "unknown")
        return self.apply_payload(payload, self.blockchain)

    def request_checkpoint_from_peers(self) -> Optional[CheckpointPayload]:
        """
        Ask P2P manager to request checkpoint payloads and return the first valid payload.
        """
        if not self.p2p_manager or not hasattr(self.p2p_manager, "broadcast"):
            return None
        import time
        now = time.time()
        if now - self._last_request_ts < self.rate_limit_seconds:
            return None
        self._last_request_ts = now
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
        except (RuntimeError, AttributeError, ValueError) as e:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to broadcast checkpoint request",
                extra={"error_type": type(e).__name__, "error": str(e)}
            )
            return None

        # Inspect cached peer features for received payload hints with quorum logic
        features = getattr(self.p2p_manager, "peer_features", {}) or {}
        candidates: Dict[str, Dict[str, Any]] = {}
        for peer_id, info in features.items():
            payload_data = info.get("checkpoint_payload") if isinstance(info, dict) else None
            if not payload_data:
                continue
            try:
                height = int(payload_data["height"])
                block_hash = str(payload_data["block_hash"])
                state_hash = str(payload_data["state_hash"])
                entry = candidates.setdefault(
                    block_hash,
                    {
                        "count": 0,
                        "payload": payload_data,
                        "height": height,
                        "state_hash": state_hash,
                        "peers": set(),
                    },
                )
                entry["count"] += 1
                entry["peers"].add(peer_id)
            except (KeyError, ValueError, TypeError):
                continue

        # Choose the highest-height candidate that meets quorum
        quorum_candidates = [
            data
            for data in candidates.values()
            if data.get("count", 0) >= self.required_quorum and len(data.get("peers", set())) >= self.min_peer_diversity
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
        if not self._validate_work(payload_data):
            return None
        self._log_provenance(payload, payload_data, source="p2p")
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

    def _validate_work(self, payload_data: Dict[str, Any]) -> bool:
        """
        Validate that advertised cumulative work meets a minimum threshold and is non-decreasing.
        """
        advertised_work = payload_data.get("work") or payload_data.get("cumulative_work")
        if advertised_work is None:
            return True  # tolerate missing for now
        try:
            work_val = int(advertised_work)
        except (TypeError, ValueError):
            return False
        if work_val <= 0:
            return False
        last_work = getattr(self.checkpoint_manager, "latest_checkpoint_work", None)
        if last_work is not None and work_val < last_work:
            return False
        return True

    def _log_provenance(self, payload: CheckpointPayload, raw: Dict[str, Any], source: str) -> None:
        entry = {
            "height": payload.height,
            "block_hash": payload.block_hash,
            "state_hash": payload.state_hash,
            "source": source,
            "work": raw.get("work"),
            "timestamp": raw.get("timestamp"),
        }
        self._provenance_log.append(entry)
        try:
            import logging

            logging.getLogger(__name__).info(
                "Checkpoint accepted",
                extra={"event": "checkpoint.accepted", "checkpoint": entry},
            )
            self._record_metrics(entry)
        except (OSError, RuntimeError, ValueError) as e:
            # best-effort logging; ignore failures
            import logging
            logging.getLogger(__name__).debug(
                "Failed to log checkpoint acceptance",
                extra={"error_type": type(e).__name__, "error": str(e)}
            )

    def get_provenance(self) -> list[dict]:
        """Return checkpoint provenance log."""
        return list(self._provenance_log)

    def _record_metrics(self, entry: dict) -> None:
        try:
            from xai.core.monitoring import MetricsCollector

            collector = MetricsCollector.instance()
            g_height = collector.get_metric("xai_checkpoint_height")
            if g_height:
                g_height.set(entry.get("height") or 0)
            g_work = collector.get_metric("xai_checkpoint_work")
            if g_work and entry.get("work") is not None:
                g_work.set(entry["work"])
            c_accepts = collector.get_metric("xai_checkpoint_accepted_total")
            if c_accepts:
                c_accepts.inc()
        except (ImportError, RuntimeError, ValueError, AttributeError, KeyError) as e:
            # metrics optional - log but continue
            import logging
            logging.getLogger(__name__).debug(
                "Failed to record checkpoint metrics",
                extra={"error_type": type(e).__name__, "error": str(e)}
            )
            return

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
                work=data.get("work"),
                signature=data.get("signature"),
                pubkey=data.get("pubkey"),
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
                    work=data.get("work"),
                    signature=data.get("signature"),
                    pubkey=data.get("pubkey"),
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
