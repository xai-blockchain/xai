"""
Checkpoint payload container and integrity helper.

Intended to wrap streamed checkpoint data (e.g., state snapshot + header) and
verify integrity before application.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CheckpointPayload:
    height: int
    block_hash: str
    state_hash: str
    data: Dict[str, Any]

    def verify_integrity(self) -> bool:
        """Verify state hash against serialized data."""
        import json

        serialized = json.dumps(self.data, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return digest == self.state_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "block_hash": self.block_hash,
            "state_hash": self.state_hash,
            "data": self.data,
        }
