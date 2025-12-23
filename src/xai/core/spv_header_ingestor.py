"""
SPV header ingestion helper.

Provides an ingest pipeline that validates linkage and proof-of-work before
storing headers via SPVHeaderStore.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from .spv_header_store import Header, SPVHeaderStore

class SPVHeaderIngestor:
    """Validate linkage and ingest headers into SPVHeaderStore."""

    def __init__(self, store: SPVHeaderStore | None = None):
        self.store = store or SPVHeaderStore()

    def ingest(self, headers: Iterable[dict[str, Any]]) -> tuple[int, list[str]]:
        """
        Ingest a batch of headers. Returns count added and list of rejected hashes.

        Headers must be provided in height order and include: height, block_hash, prev_hash, bits.
        """
        added = 0
        rejected: list[str] = []
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

            if self.store.add_header(header):
                added += 1
            else:
                rejected.append(header.block_hash)

        return added, rejected

    def ingest_from_rpc(
        self,
        rpc_url: str,
        rpc_user: str,
        rpc_password: str,
        start_height: int,
        end_height: int,
    ) -> tuple[int, list[str]]:
        """
        Ingest headers from a Bitcoin-compatible JSON-RPC endpoint (e.g., regtest).
        """
        added = 0
        rejected: list[str] = []
        session = requests.Session()
        headers = []

        def rpc_call(method: str, params: list[Any] | None = None) -> Any:
            resp = session.post(
                rpc_url,
                auth=(rpc_user, rpc_password),
                json={"jsonrpc": "1.0", "id": "spv", "method": method, "params": params or []},
                timeout=5,
            )
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("error"):
                raise RuntimeError(payload["error"])
            return payload["result"]

        for height in range(start_height, end_height + 1):
            block_hash = rpc_call("getblockhash", [height])
            header_json = rpc_call("getblockheader", [block_hash])
            headers.append(
                {
                    "height": height,
                    "block_hash": block_hash,
                    "prev_hash": header_json["previousblockhash"] if height > 0 else "",
                    "bits": int(header_json["bits"], 16),
                }
            )

        return self.ingest(headers)
