"""
Partial sync bootstrapper.

Uses CheckpointSyncManager to fetch/apply a checkpoint when the local chain is
empty or explicitly requested, wiring in SPV-backed checkpoint validation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .checkpoint_sync import CheckpointSyncManager

logger = logging.getLogger(__name__)


class PartialSyncCoordinator:
    """Orchestrates checkpoint-based partial sync prior to full block download."""

    def __init__(self, blockchain: Any, p2p_manager: Optional[Any] = None):
        self.blockchain = blockchain
        self.p2p_manager = p2p_manager
        self.sync_manager = CheckpointSyncManager(blockchain, p2p_manager=p2p_manager)

    def _current_height(self) -> int:
        """Best-effort current height getter across different blockchain APIs."""
        for attr in ("height", "block_height", "current_height", "latest_height"):
            if hasattr(self.blockchain, attr):
                try:
                    return int(getattr(self.blockchain, attr))
                except (AttributeError, TypeError, ValueError):
                    continue
        getter_candidates = (
            "get_latest_height",
            "get_height",
            "get_block_height",
        )
        for name in getter_candidates:
            fn = getattr(self.blockchain, name, None)
            if callable(fn):
                try:
                    return int(fn())
                except (AttributeError, TypeError, ValueError, RuntimeError):
                    continue
        return 0

    def bootstrap_if_empty(self, force: bool = False) -> bool:
        """
        Apply the best available checkpoint when the node has no blocks yet (or when forced).

        Returns True if a checkpoint was applied, False otherwise.
        """
        current_height = self._current_height()
        if current_height > 0 and not force:
            return False

        try:
            applied = self.sync_manager.fetch_validate_apply()
            if applied:
                logger.info("Partial sync applied checkpoint")
            return bool(applied)
        except Exception as exc:
            logger.warning("Partial sync failed: %s", exc, extra={"event": "partial_sync_failed"})
            return False
