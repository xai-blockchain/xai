"""
SPV header ingestion helper.

Provides a minimal ingest pipeline that validates linkage and stores headers
via SPVHeaderStore. Proof-of-work validation is intentionally stubbed for
future integration.
"""

from __future__ import annotations

from typing import Iterable, Dict, Any, List, Tuple

from .spv_header_store import SPVHeaderStore, Header


class SPVHeaderIngestor:
    """Validate linkage and ingest headers into SPVHeaderStore."""

    def __init__(self, store: SPVHeaderStore | None = None):
        self.store = store or SPVHeaderStore()

    def ingest(self, headers: Iterable[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Ingest a batch of headers. Returns count added and list of rejected hashes.

        Headers must be provided in height order and include: height, block_hash, prev_hash, bits.
        """
        added = 0
        rejected: List[str] = []
        for h in headers:
            try:
                header = Header(
                    height=int(h["height"]),
                    block_hash=str(h["block_hash"]),
                    prev_hash=str(h["prev_hash"]),
                    bits=int(h["bits"]),
                )
            except (KeyError, ValueError, TypeError):
                rejected.append(str(h.get("block_hash", "unknown")))
                continue

            # Placeholder PoW check: ensure bits is positive
            if header.bits <= 0:
                rejected.append(header.block_hash)
                continue

            if self.store.add_header(header):
                added += 1
            else:
                rejected.append(header.block_hash)

        return added, rejected
