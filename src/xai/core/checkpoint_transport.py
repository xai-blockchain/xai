"""
Checkpoint transport stub.

Responsible for fetching checkpoint payloads from P2P or other sources.
Currently a placeholder returning None; to be implemented with actual fetch logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .checkpoint_payload import CheckpointPayload


class CheckpointTransport:
    """Placeholder transport that will retrieve checkpoint payloads."""

    def __init__(self, p2p_manager: Optional[Any] = None):
        self.p2p_manager = p2p_manager

    def fetch_payload(self, meta: Dict[str, Any]) -> Optional[CheckpointPayload]:
        """
        Fetch checkpoint payload given metadata. Returns None until implemented.
        """
        _ = meta
        return None
