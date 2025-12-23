"""
Checkpoint payload container and integrity helper.

Intended to wrap streamed checkpoint data (e.g., state snapshot + header) and
verify integrity before application.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckpointPayload:
    height: int
    block_hash: str
    state_hash: str
    data: dict[str, Any]
    work: int | None = None
    signature: str | None = None
    pubkey: str | None = None

    def verify_integrity(self) -> bool:
        """Verify state hash against serialized data."""
        import json

        serialized = json.dumps(self.data, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return digest == self.state_hash

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "height": self.height,
            "block_hash": self.block_hash,
            "state_hash": self.state_hash,
            "data": self.data,
        }
        if self.work is not None:
            payload["work"] = self.work
        if self.signature:
            payload["signature"] = self.signature
        if self.pubkey:
            payload["pubkey"] = self.pubkey
        return payload
