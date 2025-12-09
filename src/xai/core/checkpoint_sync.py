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

    def _local_checkpoint_metadata(self) -> Optional[Dict[str, Any]]:
        """Return latest local checkpoint metadata if available."""
        cm = self.checkpoint_manager
        if not cm:
            return None
        checkpoint = cm.load_latest_checkpoint()
        if not checkpoint:
            height = getattr(cm, "latest_checkpoint_height", None)
            if height is None:
                return None
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
        if not payload:
            return False
        return self.apply_payload(payload, self.blockchain)

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
