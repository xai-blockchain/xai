"""
Comprehensive tests for Merkle Proof Verification functionality.
Tests the security-critical ability for light clients to verify transactions.
"""

import pytest
from xai.core.blockchain import Block, Transaction


def _addr(index: int) -> str:
    return f"TXAI{index:040x}"


def _txid(index: int) -> str:
    return f"{index:064x}"


class TestMerkleProofVerification:
    """Test suite for Merkle proof generation and verification"""

    def test_single_transaction_block(self):
        """Test merkle proof for a block with only one transaction"""
        # Create a simple coinbase transaction
        tx = Transaction("COINBASE", _addr(1), 12.0)
        tx.txid = tx.calculate_hash()

        # Create block with single transaction
        block = Block(0, [tx], "0" * 64, difficulty=1)

        # Generate proof
        proof = block.generate_merkle_proof(tx.txid)

        # Single transaction should have empty proof (txid is the merkle root)
        assert proof == []

        # Verify proof
        assert Block.verify_merkle_proof(tx.txid, block.merkle_root, proof)

    def test_two_transactions(self):
        """Test merkle proof for a block with two transactions"""
        tx1 = Transaction("COINBASE", _addr(2), 12.0)
        tx1.txid = tx1.calculate_hash()

        tx2 = Transaction(_addr(3), _addr(4), 5.0, 0.1)
        tx2.txid = tx2.calculate_hash()

        block = Block(0, [tx1, tx2], "0" * 64, difficulty=1)

        # Generate proof for first transaction
        proof1 = block.generate_merkle_proof(tx1.txid)
        assert len(proof1) == 1
        assert proof1[0][0] == tx2.txid  # Sibling is tx2
        assert proof1[0][1] == True  # Sibling is on the right

        # Verify proof
        assert Block.verify_merkle_proof(tx1.txid, block.merkle_root, proof1)

        # Generate proof for second transaction
        proof2 = block.generate_merkle_proof(tx2.txid)
        assert len(proof2) == 1
        assert proof2[0][0] == tx1.txid  # Sibling is tx1
        assert proof2[0][1] == False  # Sibling is on the left

        # Verify proof
        assert Block.verify_merkle_proof(tx2.txid, block.merkle_root, proof2)

    def test_four_transactions(self):
        """Test merkle proof for a block with four transactions (complete binary tree)"""
        transactions = []
        for i in range(4):
            tx = Transaction(_addr(i + 10), _addr(i + 20), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Test proof for each transaction
        for i, tx in enumerate(transactions):
            proof = block.generate_merkle_proof(tx.txid)

            # With 4 transactions, we should have 2 levels in the tree
            # So proof should have 2 elements
            assert len(proof) == 2

            # Verify the proof
            assert Block.verify_merkle_proof(tx.txid, block.merkle_root, proof)

    def test_odd_number_transactions(self):
        """Test merkle proof with odd number of transactions (requires duplication)"""
        transactions = []
        for i in range(5):
            tx = Transaction(_addr(i + 30), _addr(i + 40), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Test proof for each transaction
        for tx in transactions:
            proof = block.generate_merkle_proof(tx.txid)

            # Verify the proof
            assert Block.verify_merkle_proof(tx.txid, block.merkle_root, proof)

    def test_large_block(self):
        """Test merkle proof with a large number of transactions"""
        transactions = []
        for i in range(100):
            tx = Transaction(_addr(i + 100), _addr(i + 200), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Test proof for random transactions
        for i in [0, 25, 50, 75, 99]:
            tx = transactions[i]
            proof = block.generate_merkle_proof(tx.txid)

            # With 100 transactions, tree depth should be ceil(log2(100)) = 7
            assert len(proof) <= 7

            # Verify the proof
            assert Block.verify_merkle_proof(tx.txid, block.merkle_root, proof)

    def test_invalid_txid(self):
        """Test that proof generation fails for non-existent transaction"""
        tx = Transaction("COINBASE", _addr(300), 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(0, [tx], "0" * 64, difficulty=1)

        # Try to generate proof for non-existent transaction
        with pytest.raises(ValueError, match="not found in block"):
            block.generate_merkle_proof(_txid(123))

    def test_empty_block(self):
        """Test that proof generation fails for empty block"""
        block = Block(0, [], "0" * 64, difficulty=1)

        with pytest.raises(ValueError, match="no transactions"):
            block.generate_merkle_proof("any_txid")

    def test_tampered_proof_detection(self):
        """Test that verification fails with tampered proof"""
        transactions = []
        for i in range(4):
            tx = Transaction(_addr(i + 400), _addr(i + 500), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Generate valid proof
        proof = block.generate_merkle_proof(transactions[0].txid)

        # Tamper with the proof by changing a sibling hash
        tampered_proof = [(proof[0][0] + "abc", proof[0][1])] + proof[1:]

        # Verification should fail
        assert not Block.verify_merkle_proof(transactions[0].txid, block.merkle_root, tampered_proof)

    def test_wrong_merkle_root(self):
        """Test that verification fails with wrong merkle root"""
        tx = Transaction("COINBASE", _addr(600), 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(0, [tx], "0" * 64, difficulty=1)
        proof = block.generate_merkle_proof(tx.txid)

        # Verify with wrong merkle root
        wrong_root = "0" * 64
        assert not Block.verify_merkle_proof(tx.txid, wrong_root, proof)

    def test_wrong_transaction_id(self):
        """Test that verification fails with wrong transaction ID"""
        transactions = []
        for i in range(4):
            tx = Transaction(_addr(i + 700), _addr(i + 800), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Generate proof for one transaction
        proof = block.generate_merkle_proof(transactions[0].txid)

        # Try to verify with a different transaction ID
        assert not Block.verify_merkle_proof(transactions[1].txid, block.merkle_root, proof)

    def test_proof_size_logarithmic(self):
        """Test that proof size grows logarithmically with number of transactions"""
        import math

        for num_txs in [1, 2, 4, 8, 16, 32, 64, 128]:
            transactions = []
            for i in range(num_txs):
                tx = Transaction(_addr(i + 9000), _addr(i + 10000), float(i + 1), 0.1)
                tx.txid = tx.calculate_hash()
                transactions.append(tx)

            block = Block(0, transactions, "0" * 64, difficulty=1)
            proof = block.generate_merkle_proof(transactions[0].txid)

            # Proof size should be at most ceil(log2(num_txs))
            expected_max_size = math.ceil(math.log2(num_txs)) if num_txs > 1 else 0
            assert len(proof) <= expected_max_size

    def test_light_client_simulation(self):
        """
        Simulate a light client scenario where a client verifies a transaction
        without downloading the full block.
        """
        # Miner creates a block with many transactions
        transactions = []
        for i in range(50):
            tx = Transaction(_addr(i + 12000), _addr(i + 13000), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Target transaction that light client wants to verify
        target_tx = transactions[25]

        # Full node generates proof
        proof = block.generate_merkle_proof(target_tx.txid)

        # Light client only needs: txid, proof, and merkle_root (from block header)
        # Light client does NOT need to download all 50 transactions
        light_client_verified = Block.verify_merkle_proof(
            target_tx.txid, block.merkle_root, proof
        )

        assert light_client_verified

        # Verify proof size is much smaller than downloading all transactions
        # Proof should be ~6 hashes (log2(50) ≈ 5.6)
        assert len(proof) < 10  # Much smaller than 50 transactions

    def test_deterministic_proof(self):
        """Test that proof generation is deterministic"""
        transactions = []
        for i in range(10):
            tx = Transaction(_addr(i + 14000), _addr(i + 15000), float(i + 1), 0.1)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        block = Block(0, transactions, "0" * 64, difficulty=1)

        # Generate proof multiple times
        proof1 = block.generate_merkle_proof(transactions[5].txid)
        proof2 = block.generate_merkle_proof(transactions[5].txid)
        proof3 = block.generate_merkle_proof(transactions[5].txid)

        # All proofs should be identical
        assert proof1 == proof2 == proof3
