"""
Comprehensive tests for Merkle proof generation and verification

Tests merkle tree construction, proof generation, and verification
with various transaction counts and edge cases.
"""

import pytest
import hashlib
from unittest.mock import Mock, patch

from xai.core.blockchain import Block, Transaction, Blockchain
from xai.core.wallet import Wallet


class TestMerkleProofGeneration:
    """Tests for merkle proof generation"""

    def _create_test_transactions(self, count: int):
        """Helper to create test transactions"""
        transactions = []
        for i in range(count):
            wallet1 = Wallet()
            wallet2 = Wallet()
            tx = Transaction(wallet1.address, wallet2.address, float(i+1), 0.1)
            tx.public_key = wallet1.public_key
            tx.sign_transaction(wallet1.private_key)
            transactions.append(tx)
        return transactions

    def test_merkle_proof_single_transaction(self, tmp_path):
        """Test merkle proof with single transaction"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine a block with single transaction
        bc.mine_pending_transactions(wallet.address)

        block = bc.chain[-1]
        assert len(block.transactions) > 0

        # Merkle root should exist
        assert block.merkle_root is not None
        assert len(block.merkle_root) == 64  # SHA-256 hex string

    def test_merkle_proof_two_transactions(self, tmp_path):
        """Test merkle proof with exactly 2 transactions"""
        transactions = self._create_test_transactions(2)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        # Calculate merkle root
        merkle_root = block.calculate_merkle_root()
        assert merkle_root is not None
        assert len(merkle_root) == 64

        # Merkle root should be hash of both transaction hashes
        tx_hashes = [tx.calculate_hash() for tx in transactions]
        combined = tx_hashes[0] + tx_hashes[1]
        expected_root = hashlib.sha256(combined.encode()).hexdigest()
        assert merkle_root == expected_root

    @pytest.mark.parametrize("tx_count", [3, 4, 5, 7, 10])
    def test_merkle_proof_various_counts(self, tx_count, tmp_path):
        """Test merkle proof with 3, 4, 5, 7, 10 transactions"""
        transactions = self._create_test_transactions(tx_count)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()
        assert merkle_root is not None
        assert len(merkle_root) == 64

        # Merkle root should be consistent
        merkle_root2 = block.calculate_merkle_root()
        assert merkle_root == merkle_root2

    def test_merkle_proof_100_transactions(self, tmp_path):
        """Test merkle proof with 100 transactions (stress test)"""
        transactions = self._create_test_transactions(100)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()
        assert merkle_root is not None
        assert len(merkle_root) == 64

    def test_merkle_proof_power_of_two_transactions(self, tmp_path):
        """Test merkle proof with power of 2 transactions (optimal case)"""
        for power in [1, 2, 3, 4, 5]:  # 2, 4, 8, 16, 32 transactions
            tx_count = 2 ** power
            transactions = self._create_test_transactions(tx_count)

            block = Block(
                index=1,
                transactions=transactions,
                previous_hash="0" * 64,
                difficulty=1
            )

            merkle_root = block.calculate_merkle_root()
            assert merkle_root is not None
            assert len(merkle_root) == 64


class TestMerkleProofVerification:
    """Tests for merkle proof verification"""

    def _create_test_transactions(self, count: int):
        """Helper to create test transactions"""
        transactions = []
        for i in range(count):
            wallet1 = Wallet()
            wallet2 = Wallet()
            tx = Transaction(wallet1.address, wallet2.address, float(i+1), 0.1)
            tx.public_key = wallet1.public_key
            tx.sign_transaction(wallet1.private_key)
            transactions.append(tx)
        return transactions

    def _generate_merkle_proof(self, transactions, tx_index):
        """
        Generate merkle proof for transaction at tx_index.
        Returns proof path as list of hashes.
        """
        if not transactions:
            return []

        # Get transaction hashes
        tx_hashes = [tx.calculate_hash() for tx in transactions]

        # Build merkle tree
        tree_levels = [tx_hashes]
        current_level = tx_hashes

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = current_level[i] + current_level[i + 1]
                    next_level.append(hashlib.sha256(combined.encode()).hexdigest())
                else:
                    # Odd number: duplicate the last hash
                    combined = current_level[i] + current_level[i]
                    next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            tree_levels.append(next_level)
            current_level = next_level

        # Generate proof path
        proof = []
        index = tx_index

        for level in tree_levels[:-1]:  # All levels except root
            is_right = index % 2 == 1
            sibling_index = index - 1 if is_right else index + 1

            if sibling_index < len(level):
                proof.append((level[sibling_index], "left" if is_right else "right"))
            else:
                # If no sibling, use same hash (for odd-length levels)
                proof.append((level[index], "right"))

            index = index // 2

        return proof

    def _verify_merkle_proof(self, tx_hash, proof, merkle_root):
        """Verify merkle proof"""
        current_hash = tx_hash

        for sibling_hash, position in proof:
            if position == "left":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == merkle_root

    def test_merkle_proof_verification_simple(self, tmp_path):
        """Test basic merkle proof verification"""
        transactions = self._create_test_transactions(4)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()

        # Generate and verify proof for first transaction
        proof = self._generate_merkle_proof(transactions, 0)
        tx_hash = transactions[0].calculate_hash()

        is_valid = self._verify_merkle_proof(tx_hash, proof, merkle_root)
        assert is_valid is True

    def test_invalid_proof_wrong_transaction(self, tmp_path):
        """Test merkle proof fails for wrong transaction"""
        transactions = self._create_test_transactions(4)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()

        # Generate proof for transaction 0 but try to verify with transaction 1
        proof = self._generate_merkle_proof(transactions, 0)
        wrong_tx_hash = transactions[1].calculate_hash()

        is_valid = self._verify_merkle_proof(wrong_tx_hash, proof, merkle_root)
        assert is_valid is False

    def test_invalid_proof_modified_path(self, tmp_path):
        """Test merkle proof fails with tampered proof"""
        transactions = self._create_test_transactions(4)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()

        # Generate proof and tamper with it
        proof = self._generate_merkle_proof(transactions, 0)
        if proof:
            # Modify the first proof element
            proof[0] = ("0" * 64, proof[0][1])

        tx_hash = transactions[0].calculate_hash()
        is_valid = self._verify_merkle_proof(tx_hash, proof, merkle_root)
        assert is_valid is False

    def test_merkle_proof_all_transactions(self, tmp_path):
        """Test merkle proof verification for all transactions in block"""
        tx_count = 8
        transactions = self._create_test_transactions(tx_count)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        merkle_root = block.calculate_merkle_root()

        # Verify proof for each transaction
        for i in range(tx_count):
            proof = self._generate_merkle_proof(transactions, i)
            tx_hash = transactions[i].calculate_hash()
            is_valid = self._verify_merkle_proof(tx_hash, proof, merkle_root)
            assert is_valid is True, f"Proof failed for transaction {i}"

    def test_merkle_proof_consistency(self, tmp_path):
        """Test that merkle root is consistent across recalculations"""
        transactions = self._create_test_transactions(5)

        block = Block(
            index=1,
            transactions=transactions,
            previous_hash="0" * 64,
            difficulty=1
        )

        # Calculate merkle root multiple times
        roots = [block.calculate_merkle_root() for _ in range(5)]

        # All should be identical
        assert all(root == roots[0] for root in roots)

    def test_merkle_empty_transaction_list(self, tmp_path):
        """Test merkle root with empty transaction list"""
        block = Block(
            index=1,
            transactions=[],
            previous_hash="0" * 64,
            difficulty=1
        )

        # Should handle empty list gracefully
        merkle_root = block.calculate_merkle_root()
        # Empty merkle root should be hash of empty string
        expected = hashlib.sha256("".encode()).hexdigest()
        assert merkle_root == expected
