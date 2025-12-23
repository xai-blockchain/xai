"""
Light Client SPV (Simplified Payment Verification) Implementation
Task 177: Complete light client SPV proof verification

This module provides SPV functionality allowing light clients to verify
transactions without downloading the entire blockchain.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

@dataclass
class BlockHeader:
    """Lightweight block header for SPV clients"""
    index: int
    timestamp: float
    previous_hash: str
    merkle_root: str
    difficulty: int
    nonce: int
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BlockHeader:
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            previous_hash=data["previous_hash"],
            merkle_root=data["merkle_root"],
            difficulty=data["difficulty"],
            nonce=data["nonce"],
            hash=data["hash"]
        )

    @classmethod
    def from_block(cls, block: Any) -> BlockHeader:
        """Create header from full block"""
        return cls(
            index=block.index,
            timestamp=block.timestamp,
            previous_hash=block.previous_hash,
            merkle_root=block.merkle_root,
            difficulty=block.difficulty,
            nonce=block.nonce,
            hash=block.hash
        )

class MerkleProofGenerator:
    """Generate and verify Merkle proofs for SPV"""

    @staticmethod
    def calculate_merkle_root(tx_hashes: list[str]) -> str:
        """Calculate merkle root from transaction hashes"""
        if not tx_hashes:
            return hashlib.sha256(b"").hexdigest()

        hashes = tx_hashes.copy()

        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])

            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            hashes = new_hashes

        return hashes[0]

    @staticmethod
    def generate_merkle_proof(tx_hashes: list[str], txid: str) -> list[tuple[str, bool]]:
        """
        Generate a merkle proof for a transaction

        Returns:
            List of (sibling_hash, is_right) tuples
        """
        if not tx_hashes:
            raise ValueError("No transactions")

        try:
            tx_index = tx_hashes.index(txid)
        except ValueError:
            raise ValueError(f"Transaction {txid} not found")

        proof: list[tuple[str, bool]] = []
        current_index = tx_index
        current_level = tx_hashes.copy()

        while len(current_level) > 1:
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])

            if current_index % 2 == 0:
                sibling_index = current_index + 1
                is_right = True
            else:
                sibling_index = current_index - 1
                is_right = False

            sibling_hash = current_level[sibling_index]
            proof.append((sibling_hash, is_right))

            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            current_level = next_level
            current_index = current_index // 2

        return proof

    @staticmethod
    def verify_merkle_proof(txid: str, merkle_proof: list[tuple[str, bool]], merkle_root: str) -> bool:
        """
        Verify a transaction is in a block using a merkle proof

        Args:
            txid: Transaction ID to verify
            merkle_proof: List of (sibling_hash, is_right) tuples
            merkle_root: Expected merkle root

        Returns:
            True if proof is valid
        """
        if not merkle_proof and txid == merkle_root:
            return True

        if not merkle_proof:
            return False

        current_hash = txid

        for sibling_hash, is_right in merkle_proof:
            if is_right:
                combined = current_hash + sibling_hash
            else:
                combined = sibling_hash + current_hash

            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == merkle_root

@dataclass
class SPVProof:
    """Complete SPV proof for transaction verification"""
    txid: str
    block_header: BlockHeader
    merkle_proof: list[tuple[str, bool]]
    transaction_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "txid": self.txid,
            "block_header": self.block_header.to_dict(),
            "merkle_proof": [(h, r) for h, r in self.merkle_proof],
            "transaction_data": self.transaction_data
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SPVProof:
        return cls(
            txid=data["txid"],
            block_header=BlockHeader.from_dict(data["block_header"]),
            merkle_proof=[(h, r) for h, r in data["merkle_proof"]],
            transaction_data=data.get("transaction_data")
        )

class LightClient:
    """
    Light client implementation using SPV

    Light clients only download block headers and verify transactions
    using Merkle proofs, significantly reducing bandwidth and storage.
    """

    def __init__(self):
        self.headers: list[BlockHeader] = []
        self.verified_transactions: dict[str, SPVProof] = {}

    def add_header(self, header: BlockHeader) -> bool:
        """Add and validate a block header"""
        # Validate chain continuity
        if self.headers:
            last_header = self.headers[-1]
            if header.previous_hash != last_header.hash:
                return False
            if header.index != last_header.index + 1:
                return False

        # Validate proof of work
        if not self._validate_pow(header):
            return False

        self.headers.append(header)
        return True

    def _validate_pow(self, header: BlockHeader) -> bool:
        """
        Validate proof of work for header using proper target comparison.

        The hash must be numerically less than the target value where:
        target = 2^256 / difficulty

        This is the correct Bitcoin-style PoW validation that compares
        the hash as an integer against the target, not just leading zeros.

        Args:
            header: Block header to validate

        Returns:
            True if hash meets difficulty requirement

        Security:
            Using integer comparison instead of string prefix is critical.
            String prefix only checks leading zeros but doesn't verify
            the actual numeric value of the hash is below target.
        """
        if not header.hash:
            return False

        if header.difficulty <= 0:
            return False

        try:
            # Convert hash to integer for comparison
            hash_int = int(header.hash, 16)

            # Calculate target: 2^256 / difficulty
            # Lower difficulty = higher target = easier to mine
            # Higher difficulty = lower target = harder to mine
            target = (2**256) // header.difficulty

            return hash_int < target

        except (ValueError, ZeroDivisionError):
            # Invalid hash format or zero difficulty
            return False

    def verify_transaction(self, spv_proof: SPVProof) -> bool:
        """
        Verify a transaction using SPV proof

        Args:
            spv_proof: SPV proof containing transaction, header, and merkle proof

        Returns:
            True if transaction is verified
        """
        # Check if we have the block header
        header = self._get_header(spv_proof.block_header.index)
        if not header:
            return False

        # Verify header matches
        if header.hash != spv_proof.block_header.hash:
            return False

        # Verify merkle proof
        is_valid = MerkleProofGenerator.verify_merkle_proof(
            spv_proof.txid,
            spv_proof.merkle_proof,
            header.merkle_root
        )

        if is_valid:
            self.verified_transactions[spv_proof.txid] = spv_proof

        return is_valid

    def _get_header(self, index: int) -> BlockHeader | None:
        """Get header by index"""
        for header in self.headers:
            if header.index == index:
                return header
        return None

    def get_confirmations(self, txid: str) -> int:
        """Get number of confirmations for a verified transaction"""
        proof = self.verified_transactions.get(txid)
        if not proof:
            return 0

        if not self.headers:
            return 0

        block_index = proof.block_header.index
        latest_index = self.headers[-1].index

        return max(0, latest_index - block_index + 1)

    def is_transaction_confirmed(self, txid: str, min_confirmations: int = 6) -> bool:
        """Check if transaction has minimum confirmations"""
        return self.get_confirmations(txid) >= min_confirmations

    def get_chain_height(self) -> int:
        """Get current chain height"""
        return len(self.headers)

    def get_latest_header(self) -> BlockHeader | None:
        """Get the latest header"""
        return self.headers[-1] if self.headers else None

    def sync_headers(self, headers: list[BlockHeader]) -> int:
        """
        Sync multiple headers at once

        Returns:
            Number of headers successfully added
        """
        added = 0
        for header in headers:
            if self.add_header(header):
                added += 1
            else:
                break  # Stop on first invalid header
        return added

    def export_headers(self) -> list[dict[str, Any]]:
        """Export headers for storage"""
        return [h.to_dict() for h in self.headers]

    def import_headers(self, headers_data: list[dict[str, Any]]) -> None:
        """Import headers from storage"""
        self.headers = [BlockHeader.from_dict(h) for h in headers_data]

class SPVServerInterface:
    """
    Interface for full nodes to serve SPV clients

    Full nodes can generate SPV proofs for light clients
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def get_headers(self, start_height: int = 0, count: int = 2000) -> list[BlockHeader]:
        """Get block headers for light client sync"""
        headers = []
        for i in range(start_height, min(start_height + count, len(self.blockchain.chain))):
            block = self.blockchain.chain[i]
            headers.append(BlockHeader.from_block(block))
        return headers

    def get_spv_proof(self, txid: str) -> SPVProof | None:
        """
        Generate SPV proof for a transaction

        Args:
            txid: Transaction ID

        Returns:
            SPVProof if transaction found, None otherwise
        """
        # Find transaction in blockchain
        for block in self.blockchain.chain:
            tx_hashes = [tx.txid for tx in block.transactions]
            if txid in tx_hashes:
                # Generate merkle proof
                merkle_proof = MerkleProofGenerator.generate_merkle_proof(tx_hashes, txid)

                # Get transaction data
                tx_data = None
                for tx in block.transactions:
                    if tx.txid == txid:
                        tx_data = tx.to_dict()
                        break

                return SPVProof(
                    txid=txid,
                    block_header=BlockHeader.from_block(block),
                    merkle_proof=merkle_proof,
                    transaction_data=tx_data
                )

        return None

    def get_header_by_height(self, height: int) -> BlockHeader | None:
        """Get header at specific height"""
        if 0 <= height < len(self.blockchain.chain):
            return BlockHeader.from_block(self.blockchain.chain[height])
        return None

    def get_latest_headers(self, count: int = 10) -> list[BlockHeader]:
        """Get the latest N headers"""
        start = max(0, len(self.blockchain.chain) - count)
        return self.get_headers(start, count)
