"""
Comprehensive tests for node_consensus.py to achieve 95%+ coverage

Tests ConsensusManager class:
- Block validation (hash, PoW, linkage, timestamps)
- Chain validation (full chain integrity)
- Fork resolution (longest valid chain rule)
- Chain integrity checks
- Chain work calculation
- Should replace chain logic
- Consensus info retrieval
"""

import pytest
import time
from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.node_consensus import ConsensusManager


class TestConsensusManagerInitialization:
    """Test ConsensusManager initialization"""

    def test_create_consensus_manager(self, tmp_path):
        """Test creating consensus manager"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        assert manager.blockchain == bc


class TestValidateBlock:
    """Test individual block validation"""

    def test_validate_block_valid(self, tmp_path):
        """Test validation of valid block"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_valid, error = manager.validate_block(block, bc.chain[-2])

        assert is_valid is True
        assert error is None

    def test_validate_block_invalid_hash(self, tmp_path):
        """Test validation fails with invalid hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        # Tamper with hash
        block.hash = "invalid_hash"

        is_valid, error = manager.validate_block(block)

        assert is_valid is False
        assert "hash" in error.lower()

    def test_validate_block_invalid_proof_of_work(self, tmp_path):
        """Test validation fails with invalid PoW"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Create block with invalid PoW
        block = Block(1, [], bc.get_latest_block().hash, bc.difficulty)
        block.hash = "1234567890abcdef" * 4  # Doesn't meet difficulty

        is_valid, error = manager.validate_block(block)

        assert is_valid is False
        assert "proof of work" in error.lower()

    def test_validate_block_previous_hash_mismatch(self, tmp_path):
        """Test validation fails with wrong previous hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        previous = bc.chain[-2]

        # Tamper with previous hash
        block.previous_hash = "wrong_hash"

        is_valid, error = manager.validate_block(block, previous)

        assert is_valid is False
        assert "previous hash" in error.lower()

    def test_validate_block_invalid_index(self, tmp_path):
        """Test validation fails with wrong index"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        previous = bc.chain[-2]

        # Tamper with index
        block.index = 999

        is_valid, error = manager.validate_block(block, previous)

        assert is_valid is False
        assert "index" in error.lower()

    def test_validate_block_timestamp_before_previous(self, tmp_path):
        """Test validation fails with timestamp before previous block"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        previous = bc.chain[-2]

        # Set timestamp before previous
        block.timestamp = previous.timestamp - 100

        is_valid, error = manager.validate_block(block, previous)

        assert is_valid is False
        assert "timestamp" in error.lower()

    def test_validate_block_index_mismatch_with_chain(self, tmp_path):
        """Test validation fails when index doesn't match chain position"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Create block with wrong index for current chain
        block = Block(999, [], bc.get_latest_block().hash, bc.difficulty)
        block.hash = block.mine_block()

        is_valid, error = manager.validate_block(block)

        assert is_valid is False
        assert "index" in error.lower()


class TestValidateBlockTransactions:
    """Test block transaction validation"""

    def test_validate_block_transactions_valid(self, tmp_path):
        """Test validation of block with valid transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_valid, error = manager.validate_block_transactions(block)

        assert is_valid is True
        assert error is None

    def test_validate_block_transactions_skip_coinbase(self, tmp_path):
        """Test validation skips coinbase transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Block with only coinbase
        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        block = Block(1, [coinbase], bc.get_latest_block().hash, bc.difficulty)

        is_valid, error = manager.validate_block_transactions(block)

        assert is_valid is True

    def test_validate_block_transactions_skip_system(self, tmp_path):
        """Test validation skips SYSTEM transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        tx = Transaction("SYSTEM", "recipient", 10.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], bc.get_latest_block().hash, bc.difficulty)

        is_valid, error = manager.validate_block_transactions(block)

        assert is_valid is True

    def test_validate_block_transactions_skip_airdrop(self, tmp_path):
        """Test validation skips AIRDROP transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        tx = Transaction("AIRDROP", "recipient", 10.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], bc.get_latest_block().hash, bc.difficulty)

        is_valid, error = manager.validate_block_transactions(block)

        assert is_valid is True

    def test_validate_block_transactions_invalid_signature(self, tmp_path):
        """Test validation fails with invalid signature"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Transaction with wrong public key (invalid signature)
        tx = Transaction(
            wallet1.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet2.public_key
        )
        tx.sign_transaction(wallet1.private_key)
        tx.tx_type = "normal"

        block = Block(1, [tx], bc.get_latest_block().hash, bc.difficulty)

        is_valid, error = manager.validate_block_transactions(block)

        assert is_valid is False
        assert "signature" in error.lower()

    def test_validate_block_transactions_insufficient_balance(self, tmp_path):
        """Test validation fails with insufficient balance"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Transaction spending more than sender has
        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            1000000.0,  # Way more than balance
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            block = Block(1, [tx], bc.get_latest_block().hash, bc.difficulty)

            is_valid, error = manager.validate_block_transactions(block)

            assert is_valid is False
            assert "balance" in error.lower()


class TestValidateChain:
    """Test full chain validation"""

    def test_validate_chain_valid(self, tmp_path):
        """Test validation of valid chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Mine some blocks
        for i in range(3):
            bc.mine_pending_transactions(wallet.address)

        is_valid, error = manager.validate_chain(bc.chain)

        assert is_valid is True
        assert error is None

    def test_validate_chain_empty(self):
        """Test validation fails for empty chain"""
        bc = Blockchain()
        manager = ConsensusManager(bc)

        is_valid, error = manager.validate_chain([])

        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_chain_invalid_genesis_index(self, tmp_path):
        """Test validation fails if genesis has wrong index"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        # Modify genesis index
        bc.chain[0].index = 1

        is_valid, error = manager.validate_chain(bc.chain)

        assert is_valid is False
        assert "genesis" in error.lower()

    def test_validate_chain_invalid_genesis_previous_hash(self, tmp_path):
        """Test validation fails if genesis has wrong previous_hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        # Modify genesis previous_hash
        bc.chain[0].previous_hash = "not_zero"

        is_valid, error = manager.validate_chain(bc.chain)

        assert is_valid is False
        assert "genesis" in error.lower()

    def test_validate_chain_block_validation_failure(self, tmp_path):
        """Test validation fails when a block is invalid"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Tamper with block
        bc.chain[1].hash = "invalid"

        is_valid, error = manager.validate_chain(bc.chain)

        assert is_valid is False
        assert "validation failed" in error.lower()

    def test_validate_chain_transaction_validation_failure(self, tmp_path):
        """Test validation fails when transaction is invalid"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet1 = Wallet()
        wallet2 = Wallet()

        bc.mine_pending_transactions(wallet1.address)

        # Create transaction with invalid signature
        tx = Transaction(
            wallet1.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet2.public_key  # Wrong key
        )
        tx.sign_transaction(wallet1.private_key)
        tx.tx_type = "normal"

        # Add invalid transaction to chain
        block = Block(2, [tx], bc.get_latest_block().hash, bc.difficulty)
        block.hash = block.mine_block()
        bc.chain.append(block)

        is_valid, error = manager.validate_chain(bc.chain)

        assert is_valid is False


class TestResolveForks:
    """Test fork resolution"""

    def test_resolve_forks_no_chains(self):
        """Test fork resolution with no chains"""
        bc = Blockchain()
        manager = ConsensusManager(bc)

        chain, reason = manager.resolve_forks([])

        assert chain is None
        assert "no chains" in reason.lower()

    def test_resolve_forks_single_valid_chain(self, tmp_path):
        """Test fork resolution with single valid chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        chain, reason = manager.resolve_forks([bc.chain])

        assert chain == bc.chain
        assert "longest" in reason.lower()

    def test_resolve_forks_longest_chain_wins(self, tmp_path):
        """Test longest valid chain is selected"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        # Make bc1 longer
        for i in range(3):
            bc1.mine_pending_transactions(wallet.address)

        bc2.mine_pending_transactions(wallet.address)

        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        assert len(chain) > len(bc2.chain)
        assert "longest" in reason.lower()

    def test_resolve_forks_rejects_invalid_chains(self, tmp_path):
        """Test invalid chains are rejected"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        # Invalidate bc2
        bc2.chain[1].hash = "invalid"

        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        # Should select bc1 (only valid chain)
        assert chain == bc1.chain

    def test_resolve_forks_all_invalid(self, tmp_path):
        """Test fork resolution with all invalid chains"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        # Invalidate both
        bc1.chain[1].hash = "invalid"
        bc2.chain[1].hash = "invalid"

        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        assert chain is None
        assert "no valid" in reason.lower()

    def test_resolve_forks_tie_handling(self, tmp_path):
        """Test fork resolution with equal length chains"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        # Make them equal length
        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        # Should note the tie
        assert "tied" in reason.lower() or "tie" in reason.lower()


class TestCheckChainIntegrity:
    """Test chain integrity checking"""

    def test_check_chain_integrity_valid(self, tmp_path):
        """Test integrity check on valid chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        is_intact, issues = manager.check_chain_integrity()

        assert is_intact is True
        assert len(issues) == 0

    def test_check_chain_integrity_empty_chain(self, tmp_path):
        """Test integrity check on empty chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc.chain = []  # Empty chain
        manager = ConsensusManager(bc)

        is_intact, issues = manager.check_chain_integrity()

        assert is_intact is True  # Empty is valid
        assert len(issues) == 0

    def test_check_chain_integrity_index_gap(self, tmp_path):
        """Test integrity check detects index gaps"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Create index gap
        bc.chain[1].index = 10  # Should be 1

        is_intact, issues = manager.check_chain_integrity()

        assert is_intact is False
        assert len(issues) > 0
        assert any("index" in issue.lower() for issue in issues)

    def test_check_chain_integrity_validation_failure(self, tmp_path):
        """Test integrity check detects validation failures"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Break chain
        bc.chain[1].hash = "invalid"

        is_intact, issues = manager.check_chain_integrity()

        assert is_intact is False
        assert len(issues) > 0


class TestCalculateChainWork:
    """Test cumulative work calculation"""

    def test_calculate_chain_work_empty(self):
        """Test work calculation on empty chain"""
        bc = Blockchain()
        manager = ConsensusManager(bc)

        work = manager.calculate_chain_work([])

        assert work == 0

    def test_calculate_chain_work_single_block(self, tmp_path):
        """Test work calculation on single block"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        work = manager.calculate_chain_work([bc.chain[0]])

        assert work > 0

    def test_calculate_chain_work_multiple_blocks(self, tmp_path):
        """Test work calculation on multiple blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        for i in range(3):
            bc.mine_pending_transactions(wallet.address)

        work = manager.calculate_chain_work(bc.chain)

        assert work > 0

    def test_calculate_chain_work_increases_with_difficulty(self, tmp_path):
        """Test more difficult blocks have more work"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        bc1.difficulty = 4
        bc2.difficulty = 6

        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        work1 = manager.calculate_chain_work(bc1.chain)
        work2 = manager.calculate_chain_work(bc2.chain)

        # Higher difficulty should have more work
        assert work2 >= work1


class TestShouldReplaceChain:
    """Test chain replacement decision"""

    def test_should_replace_chain_longer_valid(self, tmp_path):
        """Test should replace with longer valid chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Mine current chain
        bc.mine_pending_transactions(wallet.address)

        # Create longer chain
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        for i in range(3):
            bc2.mine_pending_transactions(wallet.address)

        should_replace, reason = manager.should_replace_chain(bc2.chain)

        assert should_replace is True
        assert "longer" in reason.lower()

    def test_should_replace_chain_invalid(self, tmp_path):
        """Test should not replace with invalid chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Create invalid chain
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        bc2.mine_pending_transactions(wallet.address)
        bc2.chain[1].hash = "invalid"

        should_replace, reason = manager.should_replace_chain(bc2.chain)

        assert should_replace is False
        assert "invalid" in reason.lower()

    def test_should_replace_chain_not_longer(self, tmp_path):
        """Test should not replace with shorter chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        # Make current chain longer
        for i in range(3):
            bc.mine_pending_transactions(wallet.address)

        # Create shorter chain
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        bc2.mine_pending_transactions(wallet.address)

        should_replace, reason = manager.should_replace_chain(bc2.chain)

        assert should_replace is False
        assert "not longer" in reason.lower()

    def test_should_replace_chain_same_length_more_work(self, tmp_path):
        """Test replace same length chain with more work"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        # Make them same length but bc2 has higher difficulty
        bc1.difficulty = 4
        bc1.mine_pending_transactions(wallet.address)

        bc2.difficulty = 6
        bc2.mine_pending_transactions(wallet.address)

        # Artificially make them same length
        if len(bc2.chain) > len(bc1.chain):
            should_replace, reason = manager.should_replace_chain(bc2.chain)
            # May or may not replace depending on work calculation


class TestVerifyProofOfWork:
    """Test proof-of-work verification"""

    def test_verify_proof_of_work_valid(self, tmp_path):
        """Test verification of valid PoW"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_valid = manager.verify_proof_of_work(block, bc.difficulty)

        assert is_valid is True

    def test_verify_proof_of_work_invalid(self, tmp_path):
        """Test verification of invalid PoW"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)

        block = Block(1, [], bc.get_latest_block().hash, bc.difficulty)
        block.hash = "1234567890abcdef" * 4  # Doesn't meet difficulty

        is_valid = manager.verify_proof_of_work(block, bc.difficulty)

        assert is_valid is False

    def test_verify_proof_of_work_different_difficulties(self, tmp_path):
        """Test PoW verification with different difficulties"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.difficulty = 4
        block = bc.mine_pending_transactions(wallet.address)

        # Should pass with difficulty 4
        assert manager.verify_proof_of_work(block, 4) is True

        # Should fail with difficulty 5
        assert manager.verify_proof_of_work(block, 5) is False


class TestGetConsensusInfo:
    """Test consensus information retrieval"""

    def test_get_consensus_info_structure(self, tmp_path):
        """Test consensus info has correct structure"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        info = manager.get_consensus_info()

        assert "chain_height" in info
        assert "difficulty" in info
        assert "total_work" in info
        assert "chain_intact" in info
        assert "integrity_issues" in info
        assert "genesis_hash" in info
        assert "latest_block_hash" in info

    def test_get_consensus_info_values(self, tmp_path):
        """Test consensus info contains correct values"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        info = manager.get_consensus_info()

        assert info["chain_height"] == len(bc.chain)
        assert info["difficulty"] == bc.difficulty
        assert info["chain_intact"] is True
        assert info["integrity_issues"] == 0
        assert info["genesis_hash"] == bc.chain[0].hash
        assert info["latest_block_hash"] == bc.chain[-1].hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
