"""
Checkpoint payload container and integrity helper.

Intended to wrap streamed checkpoint data (e.g., state snapshot + header) and
verify integrity before application.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class CheckpointPayload:
    height: int
    block_hash: str
    state_hash: str
    data: Dict[str, Any]

    def verify_integrity(self) -> bool:
        """Verify state hash against serialized data."""
        serialized = str(self.data).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return digest == self.state_hash
