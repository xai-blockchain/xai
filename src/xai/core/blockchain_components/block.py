"""
Block class for XAI Blockchain

Extracted from blockchain.py as part of god class refactoring.
Contains the Block class which represents individual blocks in the blockchain.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from xai.core.block_header import BlockHeader, canonical_json
from xai.core.config import Config
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex
from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.transaction import Transaction


class Block:
    """Blockchain block with real proof-of-work"""

    def __init__(
        self,
        header: Union[BlockHeader, int],
        transactions: List["Transaction"],
        previous_hash: Optional[str] = None,
        difficulty: Optional[int] = None,
        timestamp: Optional[float] = None,
        nonce: int = 0,
        merkle_root: Optional[str] = None,
        signature: Optional[str] = None,
        miner_pubkey: Optional[str] = None,
    ) -> None:
        """
        Accept either a fully constructed BlockHeader or legacy positional fields
        (index, transactions, previous_hash, difficulty, ...). The legacy path
        keeps backward compatibility with tests/utilities that still instantiate
        blocks directly from primitives.
        """
        import time

        if isinstance(header, BlockHeader):
            block_header = header
        else:
            if previous_hash is None or difficulty is None:
                raise ValueError(
                    "previous_hash and difficulty are required for legacy block construction"
                )
            block_header = BlockHeader(
                index=int(header),
                previous_hash=previous_hash,
                merkle_root=merkle_root
                or self._calculate_merkle_root_static(transactions),
                timestamp=timestamp or time.time(),
                difficulty=int(difficulty),
                nonce=nonce,
                signature=signature,
                miner_pubkey=miner_pubkey,
                version=Config.BLOCK_HEADER_VERSION,
            )

        self.header = block_header
        self.transactions = transactions
        self._miner: Optional[str] = None
        self.logger = get_structured_logger()
        # Optional ancestry window for fast reorg sync; never persisted
        self.lineage: Optional[List["Block"]] = None

    @staticmethod
    def _calculate_merkle_root_static(transactions: List["Transaction"]) -> str:
        """Calculate a merkle root from raw transactions without needing a Blockchain instance."""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        tx_hashes: List[str] = []
        for tx in transactions:
            if tx.txid is None:
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            tx_hashes = [
                hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(tx_hashes), 2)
            ]

        return tx_hashes[0]

    @property
    def index(self) -> int:
        return self.header.index

    @index.setter
    def index(self, value: int) -> None:
        self.header.index = value

    @property
    def hash(self) -> str:
        return self.header.hash

    @hash.setter
    def hash(self, value: str) -> None:
        self.header.hash = value

    @property
    def version(self) -> int:
        return getattr(
            self.header, "version", getattr(Config, "BLOCK_HEADER_VERSION", 1)
        )

    @property
    def previous_hash(self) -> str:
        return self.header.previous_hash

    @previous_hash.setter
    def previous_hash(self, value: str) -> None:
        # Allow controlled updates (used in reorg/orphan handling paths and tests)
        self.header.previous_hash = value

    @property
    def timestamp(self) -> float:
        return self.header.timestamp

    @timestamp.setter
    def timestamp(self, value: float) -> None:
        self.header.timestamp = value
        self.header.hash = self.header.calculate_hash()

    @property
    def difficulty(self) -> int:
        return self.header.difficulty

    @difficulty.setter
    def difficulty(self, value: int) -> None:
        self.header.difficulty = int(value)
        self.header.hash = self.header.calculate_hash()

    @property
    def nonce(self) -> int:
        return self.header.nonce

    @nonce.setter
    def nonce(self, value: int) -> None:
        self.header.nonce = int(value)
        self.header.hash = self.header.calculate_hash()

    @property
    def merkle_root(self) -> str:
        return self.header.merkle_root

    @property
    def signature(self) -> Optional[str]:
        return self.header.signature

    @property
    def miner_pubkey(self) -> Optional[str]:
        return self.header.miner_pubkey

    @property
    def miner(self) -> Optional[str]:
        return self._miner or self.header.miner_pubkey

    @miner.setter
    def miner(self, value: str) -> None:
        self._miner = value

    def calculate_hash(self) -> str:
        return self.header.calculate_hash()

    def sign_block(self, private_key: str) -> None:
        self.header.signature = sign_message_hex(
            private_key, self.header.hash.encode()
        )

    def verify_signature(self, public_key: str) -> bool:
        if self.header.signature is None or self.header.miner_pubkey is None:
            return False
        return verify_signature_hex(
            public_key, self.header.hash.encode(), self.header.signature
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "miner": self.miner,
        }

    def estimate_size_bytes(self) -> int:
        """
        Estimate the serialized size of the block for strict resource enforcement.

        The estimation uses deterministic JSON serialization for the header and
        transactions, falling back to structural approximations if a transaction
        is missing helpers (should never happen in production).
        """
        header_bytes = len(canonical_json(self.header.to_dict()).encode("utf-8"))

        tx_bytes = 0
        for tx in self.transactions:
            if tx is None:
                continue
            try:
                tx_bytes += tx.get_size()
            except AttributeError:
                try:
                    tx_bytes += len(canonical_json(tx.to_dict()).encode("utf-8"))
                except Exception as e:
                    self.logger.warning(
                        "Failed to calculate transaction size, using 0",
                        tx_type=type(tx).__name__,
                        error=str(e),
                    )
                    tx_bytes += 0

        miner_bytes = len((self.miner or "").encode("utf-8"))
        structure_overhead = 8 + len(self.transactions) * 4
        return header_bytes + tx_bytes + miner_bytes + structure_overhead

    def calculate_merkle_root(self) -> str:
        """Calculate merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b"").hexdigest()

        # Get transaction hashes, ensuring all txids are set
        tx_hashes = []
        for tx in self.transactions:
            if tx.txid is None:
                # Calculate hash for transactions without txid
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def generate_merkle_proof(self, txid: str) -> List[Tuple[str, bool]]:
        """
        Generate a merkle proof for a transaction in this block.

        This allows light clients to verify a transaction is in a block without
        downloading all transactions. The proof is a list of sibling hashes
        needed to reconstruct the merkle root.

        Args:
            txid: Transaction ID to generate proof for

        Returns:
            List of (sibling_hash, is_right) tuples where:
            - sibling_hash: The hash of the sibling node in the merkle tree
            - is_right: True if sibling is on the right, False if on the left

        Raises:
            ValueError: If transaction is not found in block
        """
        if not self.transactions:
            raise ValueError("Block has no transactions")

        # Build transaction hash list
        tx_hashes = []
        tx_index = -1
        for idx, tx in enumerate(self.transactions):
            if tx.txid is None:
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)
            if tx.txid == txid:
                tx_index = idx

        if tx_index == -1:
            raise ValueError(f"Transaction {txid} not found in block")

        # Build merkle tree proof
        proof: List[Tuple[str, bool]] = []
        current_index = tx_index
        current_level = tx_hashes.copy()

        # Build proof by traversing up the tree
        while len(current_level) > 1:
            # Handle odd number of elements (duplicate last)
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])

            # Find sibling for current index
            if current_index % 2 == 0:
                # Current node is left child, sibling is right
                sibling_index = current_index + 1
                is_right = True
            else:
                # Current node is right child, sibling is left
                sibling_index = current_index - 1
                is_right = False

            # Add sibling to proof
            sibling_hash = current_level[sibling_index]
            proof.append((sibling_hash, is_right))

            # Build next level
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            # Update for next iteration
            current_level = next_level
            current_index = current_index // 2

        return proof

    @staticmethod
    def verify_merkle_proof(
        txid: str, merkle_root: str, proof: List[Tuple[str, bool]]
    ) -> bool:
        """
        Verify a merkle proof for a transaction.

        Args:
            txid: Transaction ID to verify
            merkle_root: Expected merkle root
            proof: Merkle proof from generate_merkle_proof

        Returns:
            True if the proof is valid
        """
        current_hash = txid

        for sibling_hash, is_right in proof:
            if is_right:
                combined = current_hash + sibling_hash
            else:
                combined = sibling_hash + current_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == merkle_root

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, hash={self.hash[:8]}..., "
            f"txs={len(self.transactions)}, difficulty={self.difficulty})"
        )
