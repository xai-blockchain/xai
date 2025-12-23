"""
Lightweight SPV header store skeleton for UTXO chains.

Tracks headers, cumulative work, and best tip selection to support SPV verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


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

    @staticmethod
    def compact_to_target(bits: int) -> int:
        """Convert Bitcoin-style compact bits to target integer."""
        exponent = bits >> 24
        mantissa = bits & 0xFFFFFF
        if exponent <= 3:
            target = mantissa >> (8 * (3 - exponent))
        else:
            target = mantissa << (8 * (exponent - 3))
        return target

    def is_valid_pow(self) -> bool:
        target = self.compact_to_target(self.bits)
        try:
            h = int(self.block_hash, 16)
        except ValueError:
            return False
        return h < target

class SPVHeaderStore:
    """Minimal header store to track best chain by cumulative work."""

    def __init__(self):
        self.headers: dict[str, Header] = {}
        self.best_tip: Header | None = None
        self.heights: dict[int, str] = {}

    def add_header(self, header: Header) -> bool:
        """Add a header if it links to an existing chain (or is genesis)."""
        if not header.is_valid_pow():
            return False

        if header.height > 0:
            parent = self.headers.get(header.prev_hash)
            if not parent:
                return False
            header.cumulative_work = parent.cumulative_work + header.work()
        else:
            header.cumulative_work = header.work()

        self.headers[header.block_hash] = header
        self.heights[header.height] = header.block_hash
        if not self.best_tip or header.cumulative_work > self.best_tip.cumulative_work:
            self.best_tip = header
        return True

    def get_best_tip(self) -> Header | None:
        return self.best_tip

    def get_header(self, block_hash: str) -> Header | None:
        return self.headers.get(block_hash)

    def has_height(self, height: int) -> bool:
        return height in self.heights

    def save(self, path: str) -> None:
        """Persist headers to disk."""
        payload = {
            "headers": [
                {
                    "height": h.height,
                    "block_hash": h.block_hash,
                    "prev_hash": h.prev_hash,
                    "bits": h.bits,
                    "cumulative_work": h.cumulative_work,
                }
                for h in self.headers.values()
            ],
            "best_tip": self.best_tip.block_hash if self.best_tip else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

    @classmethod
    def load(cls, path: str) -> "SPVHeaderStore":
        """Load headers from disk."""
        store = cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for h in data.get("headers", []):
                header = Header(
                    height=int(h["height"]),
                    block_hash=str(h["block_hash"]),
                    prev_hash=str(h["prev_hash"]),
                    bits=int(h["bits"]),
                    cumulative_work=int(h.get("cumulative_work", 0)),
                )
                # Skip PoW validation on load; assume trusted file
                store.headers[header.block_hash] = header
                store.heights[header.height] = header.block_hash
            best_hash = data.get("best_tip")
            store.best_tip = store.headers.get(best_hash) if best_hash else None
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            return cls()
        return store
