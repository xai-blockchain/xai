"""
Lightweight SPV header store skeleton for UTXO chains.

Tracks headers, cumulative work, and best tip selection to support SPV verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Header:
    height: int
    block_hash: str
    prev_hash: str
    bits: int  # compact difficulty representation
    cumulative_work: int = field(default=0)

    def work(self) -> int:
        # Simplified placeholder work metric (higher bits => harder)
        return max(1, self.bits)


class SPVHeaderStore:
    """Minimal header store to track best chain by cumulative work."""

    def __init__(self):
        self.headers: Dict[str, Header] = {}
        self.best_tip: Optional[Header] = None

    def add_header(self, header: Header) -> bool:
        """Add a header if it links to an existing chain (or is genesis)."""
        if header.height > 0:
            parent = self.headers.get(header.prev_hash)
            if not parent:
                return False
            header.cumulative_work = parent.cumulative_work + header.work()
        else:
            header.cumulative_work = header.work()

        self.headers[header.block_hash] = header
        if not self.best_tip or header.cumulative_work > self.best_tip.cumulative_work:
            self.best_tip = header
        return True

    def get_best_tip(self) -> Optional[Header]:
        return self.best_tip

    def get_header(self, block_hash: str) -> Optional[Header]:
        return self.headers.get(block_hash)
