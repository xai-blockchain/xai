"""
Checkpoint-based partial sync helper.

Provides a thin coordination layer to source checkpoint metadata from the
local checkpoint manager and P2P network manager, picking the best available
candidate to accelerate sync without full chain download.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


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

        Preference is given to P2P metadata if present, otherwise falls back
        to the latest local checkpoint.
        """
        p2p_meta = self._p2p_checkpoint_metadata()
        if p2p_meta:
            return p2p_meta
        return self._local_checkpoint_metadata()

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
