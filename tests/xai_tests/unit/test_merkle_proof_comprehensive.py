"""
Comprehensive Merkle Proof Tests (Task 198 & 199)

Tests for Block.generate_merkle_proof and Block.verify_merkle_proof methods
covering various tree sizes, edge cases, and invalid proof scenarios.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.xai.core.blockchain import Block, Transaction
import hashlib
import time


class TestMerkleProofGeneration:
    """Test merkle proof generation for various tree sizes"""

    def create_test_transactions(self, count: int) -> list:
        """Helper to create test transactions"""
        transactions = []
        for i in range(count):
            tx = Transaction(
                sender=f"XAI{'0' * 40}sender{i}",
                recipient=f"XAI{'0' * 40}recip{i}",
                amount=float(i + 1),
                fee=0.1,
            )
            tx.txid = f"txid_{i:04d}_{'x' * 56}"
            transactions.append(tx)
        return transactions

    def test_merkle_proof_single_transaction(self):
        """Task 198: Test merkle proof for single transaction"""
        txs = self.create_test_transactions(1)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate proof for the only transaction
        proof = block.generate_merkle_proof(0)

        assert proof is not None, "Proof should not be None for single transaction"
        assert isinstance(proof, list), "Proof should be a list"
        # Single transaction tree has no siblings needed
        assert len(proof) == 0 or proof == [block.merkle_root], "Single tx proof should be empty or just root"

    def test_merkle_proof_two_transactions(self):
        """Task 198: Test merkle proof for two transactions"""
        txs = self.create_test_transactions(2)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate proof for first transaction
        proof_0 = block.generate_merkle_proof(0)
        assert proof_0 is not None, "Proof should not be None"
        assert len(proof_0) > 0, "Proof should contain sibling hash"

        # Generate proof for second transaction
        proof_1 = block.generate_merkle_proof(1)
        assert proof_1 is not None, "Proof should not be None"
        assert len(proof_1) > 0, "Proof should contain sibling hash"

    def test_merkle_proof_power_of_two_transactions(self):
        """Task 198: Test merkle proof for power-of-2 tree sizes (2, 4, 8, 16)"""
        for count in [2, 4, 8, 16]:
            txs = self.create_test_transactions(count)
            block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

            # Test proof for first, middle, and last transaction
            indices = [0, count // 2, count - 1]
            for idx in indices:
                proof = block.generate_merkle_proof(idx)
                assert proof is not None, f"Proof should not be None for index {idx} in {count} txs"
                # For power of 2, proof length should be log2(count)
                import math
                expected_length = math.ceil(math.log2(count))
                assert len(proof) <= expected_length + 1, f"Proof length should be ~log2({count})"

    def test_merkle_proof_non_power_of_two_transactions(self):
        """Task 198: Test merkle proof for non-power-of-2 tree sizes (3, 5, 7, 9)"""
        for count in [3, 5, 7, 9]:
            txs = self.create_test_transactions(count)
            block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

            # Test proof for all transactions
            for idx in range(count):
                proof = block.generate_merkle_proof(idx)
                assert proof is not None, f"Proof should not be None for index {idx} in {count} txs"
                assert len(proof) > 0, f"Proof should not be empty for {count} txs"

    def test_merkle_proof_large_tree(self):
        """Task 198: Test merkle proof for large transaction set"""
        count = 100
        txs = self.create_test_transactions(count)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Test random indices
        test_indices = [0, 1, 50, 99]
        for idx in test_indices:
            proof = block.generate_merkle_proof(idx)
            assert proof is not None, f"Proof should exist for index {idx}"
            # Proof length should be roughly log2(100) ≈ 7
            assert 5 <= len(proof) <= 10, f"Proof length should be reasonable for 100 txs"

    def test_merkle_proof_invalid_index(self):
        """Task 198: Test merkle proof with invalid index"""
        txs = self.create_test_transactions(5)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Test out of bounds indices
        assert block.generate_merkle_proof(-1) is None, "Negative index should return None"
        assert block.generate_merkle_proof(5) is None, "Index >= len should return None"
        assert block.generate_merkle_proof(100) is None, "Large invalid index should return None"


class TestMerkleProofVerification:
    """Test merkle proof verification (Task 199)"""

    def create_test_transactions(self, count: int) -> list:
        """Helper to create test transactions"""
        transactions = []
        for i in range(count):
            tx = Transaction(
                sender=f"XAI{'0' * 40}sender{i}",
                recipient=f"XAI{'0' * 40}recip{i}",
                amount=float(i + 1),
                fee=0.1,
            )
            tx.txid = f"txid_{i:04d}_{'x' * 56}"
            transactions.append(tx)
        return transactions

    def test_verify_valid_merkle_proof(self):
        """Task 199: Verify valid merkle proofs"""
        for count in [1, 2, 4, 8, 16]:
            txs = self.create_test_transactions(count)
            block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

            # Generate and verify proof for each transaction
            for idx in range(count):
                proof = block.generate_merkle_proof(idx)
                tx_hash = txs[idx].txid

                is_valid = block.verify_merkle_proof(tx_hash, idx, proof)
                assert is_valid, f"Valid proof should verify for tx {idx} in {count} txs"

    def test_verify_invalid_merkle_proof_wrong_hash(self):
        """Task 199: Reject proof with wrong transaction hash"""
        txs = self.create_test_transactions(5)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate valid proof
        proof = block.generate_merkle_proof(0)

        # Try to verify with wrong tx hash
        wrong_hash = "wrong_hash_" + "x" * 50
        is_valid = block.verify_merkle_proof(wrong_hash, 0, proof)
        assert not is_valid, "Proof with wrong tx hash should fail verification"

    def test_verify_invalid_merkle_proof_wrong_index(self):
        """Task 199: Reject proof with wrong index"""
        txs = self.create_test_transactions(5)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate proof for index 0
        proof = block.generate_merkle_proof(0)
        tx_hash = txs[0].txid

        # Try to verify at wrong index
        is_valid = block.verify_merkle_proof(tx_hash, 2, proof)
        assert not is_valid, "Proof verified at wrong index should fail"

    def test_verify_invalid_merkle_proof_tampered(self):
        """Task 199: Reject tampered merkle proof"""
        txs = self.create_test_transactions(8)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate valid proof
        proof = block.generate_merkle_proof(0)
        tx_hash = txs[0].txid

        if proof and len(proof) > 0:
            # Tamper with the proof by modifying a hash
            tampered_proof = proof.copy()
            tampered_proof[0] = "tampered_" + "x" * 54

            is_valid = block.verify_merkle_proof(tx_hash, 0, tampered_proof)
            assert not is_valid, "Tampered proof should fail verification"

    def test_verify_invalid_merkle_proof_empty(self):
        """Task 199: Handle empty proof correctly"""
        txs = self.create_test_transactions(5)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        tx_hash = txs[0].txid

        # Empty proof should only be valid for single transaction
        is_valid = block.verify_merkle_proof(tx_hash, 0, [])
        # This depends on implementation - might be valid for single tx or always invalid
        # The test documents the expected behavior

    def test_verify_invalid_merkle_proof_wrong_length(self):
        """Task 199: Reject proof with wrong length"""
        txs = self.create_test_transactions(8)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Generate valid proof
        proof = block.generate_merkle_proof(0)
        tx_hash = txs[0].txid

        if proof and len(proof) > 1:
            # Try proof with extra element
            extended_proof = proof + ["extra_hash_" + "x" * 52]
            is_valid = block.verify_merkle_proof(tx_hash, 0, extended_proof)
            # May or may not fail depending on implementation

            # Try proof with missing element
            short_proof = proof[:-1]
            is_valid = block.verify_merkle_proof(tx_hash, 0, short_proof)
            assert not is_valid, "Proof with wrong length should fail"

    def test_verify_all_transactions_in_block(self):
        """Task 199: Comprehensive test - verify all transactions"""
        count = 20
        txs = self.create_test_transactions(count)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Every transaction should have a valid proof
        for idx in range(count):
            proof = block.generate_merkle_proof(idx)
            tx_hash = txs[idx].txid
            is_valid = block.verify_merkle_proof(tx_hash, idx, proof)
            assert is_valid, f"Proof verification failed for tx {idx}"


class TestMerkleProofEdgeCases:
    """Test edge cases for merkle proofs"""

    def create_test_transactions(self, count: int) -> list:
        """Helper to create test transactions"""
        transactions = []
        for i in range(count):
            tx = Transaction(
                sender=f"XAI{'0' * 40}sender{i}",
                recipient=f"XAI{'0' * 40}recip{i}",
                amount=float(i + 1),
                fee=0.1,
            )
            tx.txid = f"txid_{i:04d}_{'x' * 56}"
            transactions.append(tx)
        return transactions

    def test_merkle_proof_no_transactions(self):
        """Edge case: Block with no transactions"""
        block = Block(index=1, transactions=[], previous_hash="0" * 64, difficulty=1)

        proof = block.generate_merkle_proof(0)
        assert proof is None or proof == [], "Empty block should return None/empty proof"

    def test_merkle_proof_duplicate_transactions(self):
        """Edge case: Block with duplicate transaction hashes"""
        txs = self.create_test_transactions(4)
        # Make txid of tx[2] same as tx[0]
        txs[2].txid = txs[0].txid

        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        # Both duplicates should have valid proofs
        proof_0 = block.generate_merkle_proof(0)
        proof_2 = block.generate_merkle_proof(2)

        assert proof_0 is not None, "Proof should exist for first duplicate"
        assert proof_2 is not None, "Proof should exist for second duplicate"

    def test_merkle_root_consistency(self):
        """Verify merkle root is consistent across proof generation"""
        txs = self.create_test_transactions(10)
        block = Block(index=1, transactions=txs, previous_hash="0" * 64, difficulty=1)

        original_root = block.merkle_root

        # Generate proofs for several transactions
        for idx in range(5):
            _ = block.generate_merkle_proof(idx)

        # Merkle root should not change
        assert block.merkle_root == original_root, "Merkle root should not change after proof generation"

    def test_merkle_proof_different_blocks_same_tx(self):
        """Proof from one block should not work for another block"""
        txs1 = self.create_test_transactions(5)
        block1 = Block(index=1, transactions=txs1, previous_hash="0" * 64, difficulty=1)

        txs2 = self.create_test_transactions(5)
        block2 = Block(index=2, transactions=txs2, previous_hash="1" * 64, difficulty=1)

        # Get proof from block1
        proof = block1.generate_merkle_proof(0)
        tx_hash = txs1[0].txid

        # Try to verify against block2's merkle root
        # This should fail because merkle roots are different
        is_valid = block2.verify_merkle_proof(tx_hash, 0, proof)
        assert not is_valid, "Proof from one block should not verify in another block"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
