"""
Compact Block Relay - BIP 152-style compact blocks for bandwidth reduction.

This module implements compact block relay to reduce bandwidth usage during
block propagation. Instead of transmitting full blocks (~500KB for 2000tx),
compact blocks transmit:
- Block header (~80 bytes)
- Short transaction IDs (6 bytes each via SipHash)
- Prefilled transactions (coinbase, typically)

Recipients reconstruct full blocks by matching short txids against their mempool,
only requesting missing transactions.

Bandwidth savings: 80-97% depending on mempool overlap.

Based on BIP 152: https://github.com/bitcoin/bips/blob/master/bip-0152.mediawiki
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from xai.core.api.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain_components.block import Block
    from xai.core.transaction import Transaction

logger = get_structured_logger()


def _siphash_short_txid(txid: str, nonce: int) -> bytes:
    """
    Compute a 6-byte short transaction ID using SipHash-2-4.

    The short txid is computed as:
        SipHash-2-4(k, txid)[:6]
    where k is derived from block header hash and nonce.

    For simplicity, we use SHA256 truncated to 6 bytes as a portable
    approximation that maintains collision resistance for our use case.

    Args:
        txid: Full 64-character transaction ID (hex)
        nonce: Random nonce for this compact block

    Returns:
        6-byte short transaction ID
    """
    # Combine txid with nonce for key derivation
    key_material = f"{txid}:{nonce}".encode()
    digest = hashlib.sha256(key_material).digest()
    return digest[:6]


@dataclass
class PrefilledTransaction:
    """Transaction included directly in compact block (e.g., coinbase)."""

    index: int  # Index in block's transaction list
    tx_data: dict[str, Any]  # Serialized transaction


@dataclass
class CompactBlock:
    """
    Compact block representation for efficient relay.

    Contains:
    - Block header data
    - Random nonce for short txid computation
    - List of short (6-byte) transaction IDs
    - Prefilled transactions (coinbase always included)
    """

    # Header fields
    header_hash: str
    previous_hash: str
    merkle_root: str
    timestamp: float
    difficulty: int
    nonce: int
    block_index: int
    block_nonce: int  # Block's PoW nonce

    # Compact block specific
    short_txid_nonce: int  # Nonce for short txid computation
    short_txids: list[bytes] = field(default_factory=list)
    prefilled_txns: list[PrefilledTransaction] = field(default_factory=list)

    # Optional fields for reconstruction
    miner_pubkey: str | None = None
    signature: str | None = None
    version: int = 1

    @classmethod
    def from_block(cls, block: "Block", include_coinbase: bool = True) -> "CompactBlock":
        """
        Create a compact block from a full block.

        Args:
            block: The full block to compact
            include_coinbase: Whether to prefill the coinbase transaction

        Returns:
            CompactBlock representation of the block
        """
        import secrets

        # Generate random nonce for short txid computation (cryptographically secure)
        short_txid_nonce = secrets.randbits(64)

        # Compute short txids for all transactions
        short_txids: list[bytes] = []
        prefilled_txns: list[PrefilledTransaction] = []

        for idx, tx in enumerate(block.transactions):
            txid = tx.txid if tx.txid else tx.calculate_hash()

            # Prefill coinbase (index 0) to avoid mempool lookup
            if include_coinbase and idx == 0:
                prefilled_txns.append(
                    PrefilledTransaction(index=idx, tx_data=tx.to_dict())
                )
            else:
                short_txids.append(_siphash_short_txid(txid, short_txid_nonce))

        return cls(
            header_hash=block.header.hash,
            previous_hash=block.header.previous_hash,
            merkle_root=block.header.merkle_root,
            timestamp=block.header.timestamp,
            difficulty=block.header.difficulty,
            nonce=short_txid_nonce,
            block_index=block.header.index,
            block_nonce=block.header.nonce,
            short_txid_nonce=short_txid_nonce,
            short_txids=short_txids,
            prefilled_txns=prefilled_txns,
            miner_pubkey=block.header.miner_pubkey,
            signature=block.header.signature,
            version=block.header.version,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize compact block for network transmission."""
        return {
            "type": "compact_block",
            "header_hash": self.header_hash,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "block_index": self.block_index,
            "block_nonce": self.block_nonce,
            "short_txid_nonce": self.short_txid_nonce,
            "short_txids": [stxid.hex() for stxid in self.short_txids],
            "prefilled_txns": [
                {"index": pt.index, "tx_data": pt.tx_data}
                for pt in self.prefilled_txns
            ],
            "miner_pubkey": self.miner_pubkey,
            "signature": self.signature,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompactBlock":
        """Deserialize compact block from network message."""
        prefilled = [
            PrefilledTransaction(index=pt["index"], tx_data=pt["tx_data"])
            for pt in data.get("prefilled_txns", [])
        ]

        return cls(
            header_hash=data["header_hash"],
            previous_hash=data["previous_hash"],
            merkle_root=data["merkle_root"],
            timestamp=data["timestamp"],
            difficulty=data["difficulty"],
            nonce=data["short_txid_nonce"],
            block_index=data["block_index"],
            block_nonce=data["block_nonce"],
            short_txid_nonce=data["short_txid_nonce"],
            short_txids=[bytes.fromhex(s) for s in data.get("short_txids", [])],
            prefilled_txns=prefilled,
            miner_pubkey=data.get("miner_pubkey"),
            signature=data.get("signature"),
            version=data.get("version", 1),
        )

    def size_bytes(self) -> int:
        """Estimate serialized size in bytes."""
        # Header fields: ~150 bytes
        # Short txids: 6 bytes each
        # Prefilled: varies, estimate ~200 bytes per tx
        header_size = 150
        short_txid_size = len(self.short_txids) * 6
        prefilled_size = len(self.prefilled_txns) * 200
        return header_size + short_txid_size + prefilled_size


@dataclass
class BlockTransactionsRequest:
    """Request for missing transactions to complete compact block reconstruction."""

    block_hash: str
    indexes: list[int]  # Indexes of missing transactions

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "getblocktxn",
            "block_hash": self.block_hash,
            "indexes": self.indexes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlockTransactionsRequest":
        return cls(
            block_hash=data["block_hash"],
            indexes=data["indexes"],
        )


@dataclass
class BlockTransactionsResponse:
    """Response with missing transactions for compact block reconstruction."""

    block_hash: str
    transactions: list[dict[str, Any]]  # Serialized transactions

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "blocktxn",
            "block_hash": self.block_hash,
            "transactions": self.transactions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlockTransactionsResponse":
        return cls(
            block_hash=data["block_hash"],
            transactions=data["transactions"],
        )


class CompactBlockReconstructor:
    """
    Reconstructs full blocks from compact blocks using mempool transactions.
    """

    def __init__(self, mempool: list["Transaction"]) -> None:
        """
        Initialize with reference to mempool transactions.

        Args:
            mempool: List of pending transactions in mempool
        """
        self._mempool = mempool
        self._mempool_index: dict[bytes, "Transaction"] = {}

    def _build_mempool_index(self, nonce: int) -> None:
        """Build short txid -> transaction index for fast lookup."""
        self._mempool_index.clear()
        for tx in self._mempool:
            txid = tx.txid if tx.txid else tx.calculate_hash()
            short_txid = _siphash_short_txid(txid, nonce)
            self._mempool_index[short_txid] = tx

    def find_missing_transactions(
        self, compact_block: CompactBlock
    ) -> tuple[list["Transaction"], list[int]]:
        """
        Attempt to reconstruct block from compact block and mempool.

        Args:
            compact_block: The compact block to reconstruct

        Returns:
            Tuple of (found_transactions, missing_indexes)
            - found_transactions: Transactions found in mempool, in order
            - missing_indexes: Indexes of transactions not in mempool
        """
        self._build_mempool_index(compact_block.short_txid_nonce)

        found: list["Transaction"] = []
        missing: list[int] = []

        # Start with prefilled transactions
        prefilled_indexes = {pt.index for pt in compact_block.prefilled_txns}

        # Track current index in short_txids list
        stxid_idx = 0

        # Total transactions = prefilled + short_txids
        total_txns = len(compact_block.short_txids) + len(compact_block.prefilled_txns)

        for tx_idx in range(total_txns):
            if tx_idx in prefilled_indexes:
                # Skip prefilled transactions for now - will be added during reconstruction
                continue

            if stxid_idx >= len(compact_block.short_txids):
                break

            short_txid = compact_block.short_txids[stxid_idx]
            stxid_idx += 1

            if short_txid in self._mempool_index:
                found.append(self._mempool_index[short_txid])
            else:
                missing.append(tx_idx)

        logger.debug(
            "Compact block reconstruction",
            found=len(found),
            missing=len(missing),
            total=total_txns,
        )

        return found, missing

    def can_reconstruct(self, compact_block: CompactBlock) -> bool:
        """Check if block can be fully reconstructed from mempool."""
        _, missing = self.find_missing_transactions(compact_block)
        return len(missing) == 0

    def reconstruct(
        self,
        compact_block: CompactBlock,
        missing_txns: list["Transaction"] | None = None,
    ) -> "Block":
        """
        Reconstruct full block from compact block.

        Args:
            compact_block: The compact block
            missing_txns: Transactions that weren't in mempool (optional)

        Returns:
            Full Block object

        Raises:
            ValueError: If reconstruction fails due to missing transactions
        """
        from xai.core.chain.block_header import BlockHeader
        from xai.core.blockchain_components.block import Block
        from xai.core.transaction import Transaction

        # Build transaction list
        found_txns, missing_indexes = self.find_missing_transactions(compact_block)

        if missing_indexes and not missing_txns:
            raise ValueError(
                f"Cannot reconstruct block: missing {len(missing_indexes)} transactions"
            )

        # Create full transaction list
        transactions: list[Transaction] = []

        # First add prefilled transactions (coinbase is always index 0)
        prefilled_by_idx = {pt.index: pt for pt in compact_block.prefilled_txns}

        # Track which found/missing transactions we've used
        found_idx = 0
        missing_idx = 0
        total_txns = len(compact_block.short_txids) + len(compact_block.prefilled_txns)

        for tx_idx in range(total_txns):
            if tx_idx in prefilled_by_idx:
                # Reconstruct transaction from prefilled data
                tx = Transaction.from_dict(prefilled_by_idx[tx_idx].tx_data)
                transactions.append(tx)
            elif tx_idx in missing_indexes:
                # Use provided missing transaction
                if missing_txns and missing_idx < len(missing_txns):
                    transactions.append(missing_txns[missing_idx])
                    missing_idx += 1
                else:
                    raise ValueError(f"Missing transaction at index {tx_idx}")
            else:
                # Use transaction found in mempool
                if found_idx < len(found_txns):
                    transactions.append(found_txns[found_idx])
                    found_idx += 1

        # Reconstruct block header
        header = BlockHeader(
            index=compact_block.block_index,
            previous_hash=compact_block.previous_hash,
            merkle_root=compact_block.merkle_root,
            timestamp=compact_block.timestamp,
            difficulty=compact_block.difficulty,
            nonce=compact_block.block_nonce,
            signature=compact_block.signature,
            miner_pubkey=compact_block.miner_pubkey,
            version=compact_block.version,
        )

        return Block(header=header, transactions=transactions)


def calculate_bandwidth_savings(
    full_block_bytes: int,
    compact_block_bytes: int,
) -> float:
    """Calculate percentage bandwidth savings."""
    if full_block_bytes == 0:
        return 0.0
    return ((full_block_bytes - compact_block_bytes) / full_block_bytes) * 100


__all__ = [
    "CompactBlock",
    "CompactBlockReconstructor",
    "BlockTransactionsRequest",
    "BlockTransactionsResponse",
    "PrefilledTransaction",
    "calculate_bandwidth_savings",
]
