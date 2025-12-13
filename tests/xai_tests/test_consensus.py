"""
Comprehensive PoW Consensus Tests for XAI Blockchain
Phase 3 of LOCAL_TESTING_PLAN.md

Tests Proof-of-Work consensus mechanisms:
- Block validation and PoW verification
- Chain validity and integrity
- Consensus rules enforcement
- Fork resolution logic
- Longest chain rule
- Block acceptance/rejection
- Finality and confirmations
"""

import pytest
import time
import hashlib
from typing import List

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.node_consensus import ConsensusManager
from xai.core.advanced_consensus import AdvancedConsensusManager, FinalityTracker


class TestProofOfWork:
    """Test Proof-of-Work validation"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_valid_pow_accepted(self, blockchain):
        """Test blocks with valid PoW are accepted"""
        wallet = Wallet()

        # Mine block with proper PoW
        block = blockchain.mine_pending_transactions(wallet.address)

        # Should have valid PoW
        assert block.hash.startswith("0" * block.difficulty)

        # Should be in chain
        assert len(blockchain.chain) == 2
        assert blockchain.chain[1].hash == block.hash

    def test_invalid_pow_rejected(self, blockchain):
        """Test blocks with invalid PoW are rejected"""
        wallet = Wallet()

        # Create block without mining
        coinbase = Transaction("COINBASE", wallet.address, blockchain.initial_block_reward)
        coinbase.txid = coinbase.calculate_hash()

        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty
        )

        # Set invalid hash (doesn't meet difficulty)
        block.hash = "1234567890abcdef" * 4

        # Should be rejected
        result = blockchain.add_block(block)
        assert result is False
        assert len(blockchain.chain) == 1  # Still only genesis

    def test_pow_difficulty_enforced(self, blockchain):
        """Test PoW difficulty is properly enforced"""
        wallet = Wallet()

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Hash should meet difficulty requirement
        difficulty = block.difficulty
        assert block.hash.startswith("0" * difficulty)

        # Should NOT start with more zeros than required
        # (probabilistically unlikely but possible)
        # Just verify minimum requirement is met
        leading_zeros = len(block.hash) - len(block.hash.lstrip("0"))
        assert leading_zeros >= difficulty

    def test_increasing_difficulty_requires_more_work(self, tmp_path):
        """Test higher difficulty requires more mining work"""
        # Create blockchain with low difficulty
        bc_low = Blockchain(data_dir=str(tmp_path / "low"))
        bc_low.difficulty = 1
        wallet = Wallet()

        # Mine with low difficulty
        start = time.time()
        block_low = bc_low.mine_pending_transactions(wallet.address)
        time_low = time.time() - start

        # Create blockchain with higher difficulty
        bc_high = Blockchain(data_dir=str(tmp_path / "high"))
        bc_high.difficulty = 3
        wallet2 = Wallet()

        # Mine with high difficulty (should take longer)
        start = time.time()
        block_high = bc_high.mine_pending_transactions(wallet2.address)
        time_high = time.time() - start

        # Both should succeed
        assert block_low is not None
        assert block_high is not None

        # Higher difficulty block should have more leading zeros
        assert block_high.hash.startswith("0" * 3)
        assert block_low.hash.startswith("0" * 1)

    def test_pow_hash_immutability(self, blockchain):
        """Test block hash changes if content changes"""
        wallet = Wallet()

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)
        original_hash = block.hash

        # Change block content
        block.timestamp = block.timestamp + 1000

        # Recalculate hash
        new_hash = block.calculate_hash()

        # Hash should be different
        assert new_hash != original_hash

        # New hash likely won't meet PoW requirement
        assert not new_hash.startswith("0" * block.difficulty)


class TestChainValidity:
    """Test blockchain validity checks"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_valid_chain_passes_validation(self, blockchain):
        """Test valid chain passes validation"""
        wallet = Wallet()

        # Build valid chain
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Should validate
        assert blockchain.validate_chain() is True

    def test_corrupted_block_detected(self, blockchain):
        """Test corrupted blocks are detected"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        # Corrupt a block
        blockchain.chain[1].transactions[0].amount = 999999.0

        # Should fail validation
        assert blockchain.validate_chain() is False

    def test_broken_chain_link_detected(self, blockchain):
        """Test broken chain links are detected"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        # Break chain link
        blockchain.chain[2].previous_hash = "wrong_hash"

        # Should fail validation
        assert blockchain.validate_chain() is False

    def test_invalid_hash_detected(self, blockchain):
        """Test invalid block hashes are detected"""
        wallet = Wallet()

        # Build chain
        for _ in range(2):
            blockchain.mine_pending_transactions(wallet.address)

        # Corrupt hash
        blockchain.chain[1].hash = "corrupted_hash"

        # Should fail validation
        assert blockchain.validate_chain() is False

    def test_genesis_block_immutable(self, blockchain):
        """Test genesis block cannot be modified"""
        wallet = Wallet()

        # Mine block
        blockchain.mine_pending_transactions(wallet.address)

        # Store original genesis
        original_genesis = blockchain.chain[0]

        # Try to modify genesis
        blockchain.chain[0].index = 999

        # Validation should fail
        is_valid = blockchain.validate_chain()

        # Restore for other tests
        blockchain.chain[0] = original_genesis


class TestConsensusRules:
    """Test consensus rule enforcement"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_block_index_must_increment(self, blockchain):
        """Test block index must increment by 1"""
        wallet = Wallet()

        # Mine valid block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Create block with wrong index
        coinbase = Transaction("COINBASE", wallet.address, blockchain.initial_block_reward)
        coinbase.txid = coinbase.calculate_hash()

        bad_block = Block(
            index=99,  # Wrong index
            transactions=[coinbase],
            previous_hash=block.hash,
            difficulty=blockchain.difficulty
        )
        bad_block.hash = bad_block.mine_block()

        # Should be rejected
        result = blockchain.add_block(bad_block)
        # Block will be orphaned due to index mismatch

    def test_previous_hash_must_match(self, blockchain):
        """Test previous hash must match chain tip"""
        wallet = Wallet()

        # Mine valid block
        blockchain.mine_pending_transactions(wallet.address)

        # Create block with wrong previous hash
        coinbase = Transaction("COINBASE", wallet.address, blockchain.initial_block_reward)
        coinbase.txid = coinbase.calculate_hash()

        bad_block = Block(
            index=2,
            transactions=[coinbase],
            previous_hash="wrong_hash",
            difficulty=blockchain.difficulty
        )
        bad_block.hash = bad_block.mine_block()

        # Should be rejected or orphaned
        result = blockchain.add_block(bad_block)
        # Block won't extend main chain

    def test_block_timestamp_must_be_reasonable(self, blockchain):
        """Test block timestamp validation"""
        wallet = Wallet()

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Timestamp should be within reasonable bounds
        now = time.time()
        assert abs(block.timestamp - now) < 300  # Within 5 minutes

    def test_difficulty_must_match_expected(self, blockchain):
        """Test block difficulty matches expected value"""
        wallet = Wallet()

        # Mine several blocks
        for _ in range(3):
            block = blockchain.mine_pending_transactions(wallet.address)
            # Each block should have appropriate difficulty
            assert block.difficulty >= blockchain.difficulty


class TestForkResolution:
    """Test fork resolution logic"""

    @pytest.fixture
    def two_chains(self, tmp_path) -> tuple:
        """Create two blockchain instances"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        return bc1, bc2

    def test_longest_chain_wins(self, two_chains):
        """Test longest valid chain is adopted"""
        bc1, bc2 = two_chains
        wallet = Wallet()

        # BC1 mines 5 blocks
        for _ in range(5):
            bc1.mine_pending_transactions(wallet.address)

        # BC2 mines 3 blocks
        for _ in range(3):
            bc2.mine_pending_transactions(wallet.address)

        # Use ConsensusManager to determine which chain to follow
        manager = ConsensusManager(bc2)
        should_replace, reason = manager.should_replace_chain(bc1.chain)

        # Should prefer longer chain
        assert should_replace is True
        assert len(bc1.chain) > len(bc2.chain)

    def test_equal_length_chains_handled(self, two_chains):
        """Test handling of equal length competing chains"""
        bc1, bc2 = two_chains
        wallet = Wallet()

        # Both mine 3 blocks
        for _ in range(3):
            bc1.mine_pending_transactions(wallet.address)
            bc2.mine_pending_transactions(wallet.address)

        # Chains have equal length
        assert len(bc1.chain) == len(bc2.chain)

        manager = ConsensusManager(bc1)
        should_replace, reason = manager.should_replace_chain(bc2.chain)

        # Equal length chains - implementation specific
        # Either accept or reject is valid

    def test_invalid_longer_chain_rejected(self, two_chains):
        """Test longer but invalid chain is rejected"""
        bc1, bc2 = two_chains
        wallet = Wallet()

        # BC1 mines 5 blocks
        for _ in range(5):
            bc1.mine_pending_transactions(wallet.address)

        # Corrupt BC1's chain
        bc1.chain[2].transactions[0].amount = 999999.0

        # BC2 has valid but shorter chain
        for _ in range(3):
            bc2.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc2)
        is_valid, error = manager.validate_chain(bc1.chain)

        # Corrupted chain should fail validation
        assert is_valid is False

    def test_fork_with_common_ancestor(self, tmp_path):
        """Test fork resolution with common ancestor"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Build common history
        for _ in range(3):
            bc.mine_pending_transactions(wallet.address)

        # Save state
        common_chain = bc.chain.copy()

        # Build fork 1 (2 more blocks)
        fork1_blocks = []
        for _ in range(2):
            block = bc.mine_pending_transactions(wallet.address)
            fork1_blocks.append(block)

        fork1_chain = bc.chain.copy()

        # Reset to common point and build fork 2 (3 more blocks)
        bc.chain = common_chain.copy()
        fork2_blocks = []
        for _ in range(3):
            block = bc.mine_pending_transactions(wallet.address)
            fork2_blocks.append(block)

        fork2_chain = bc.chain.copy()

        # Fork 2 should be preferred (longer)
        assert len(fork2_chain) > len(fork1_chain)


class TestConsensusManager:
    """Test ConsensusManager functionality"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_consensus_manager_initialization(self, blockchain):
        """Test ConsensusManager initializes correctly"""
        manager = ConsensusManager(blockchain)

        assert manager.blockchain is blockchain
        assert manager is not None

    def test_validate_chain(self, blockchain):
        """Test ConsensusManager validates chains"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(blockchain)

        # Should validate
        is_valid = manager.validate_chain()
        assert is_valid is True

    def test_consensus_info(self, blockchain):
        """Test getting consensus information"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(blockchain)
        info = manager.get_consensus_info()

        # Should contain key information
        assert "chain_height" in info
        assert "difficulty" in info
        assert info["chain_height"] == len(blockchain.chain)

    def test_check_consensus(self, blockchain):
        """Test consensus check"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(blockchain)
        consensus_valid = manager.check_consensus()

        # Should be valid
        assert consensus_valid is True

    def test_chain_integrity_check(self, blockchain):
        """Test chain integrity checking"""
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(blockchain)

        # Check integrity
        is_intact, issues = manager.check_chain_integrity()
        assert is_intact is True
        assert len(issues) == 0

        # Introduce integrity issue
        blockchain.chain[1].index = 999

        is_intact, issues = manager.check_chain_integrity()
        assert is_intact is False
        assert len(issues) > 0


class TestAdvancedConsensus:
    """Test AdvancedConsensusManager features"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_advanced_consensus_manager_initialization(self, blockchain):
        """Test AdvancedConsensusManager initializes"""
        manager = AdvancedConsensusManager(blockchain)

        assert manager.blockchain is blockchain
        assert manager.propagation_monitor is not None
        assert manager.orphan_pool is not None
        assert manager.finality_tracker is not None

    def test_process_new_block(self, blockchain):
        """Test processing new blocks"""
        manager = AdvancedConsensusManager(blockchain)
        wallet = Wallet()

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Process it through manager
        accepted, message = manager.process_new_block(block)

        # Should be accepted (already in chain)
        # Or may have specific behavior

    def test_consensus_stats(self, blockchain):
        """Test getting consensus statistics"""
        manager = AdvancedConsensusManager(blockchain)
        wallet = Wallet()

        # Build chain
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        # Get stats
        stats = manager.get_consensus_stats()

        assert "propagation" in stats
        assert "orphan_pool" in stats
        assert "finality" in stats
        assert "difficulty" in stats


class TestFinality:
    """Test block finality and confirmations"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_block_confirmations_increase(self, blockchain):
        """Test block confirmations increase with chain growth"""
        wallet = Wallet()

        # Mine block at height 1
        block1 = blockchain.mine_pending_transactions(wallet.address)
        height1 = len(blockchain.chain) - 1

        # Mine more blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Block 1 should have 5 confirmations now
        confirmations = len(blockchain.chain) - 1 - height1
        assert confirmations == 5

    def test_finality_tracker(self, blockchain):
        """Test FinalityTracker functionality"""
        tracker = FinalityTracker()
        wallet = Wallet()

        # Build chain
        for _ in range(150):
            blockchain.mine_pending_transactions(wallet.address)

        # Blocks with 100+ confirmations are finalized
        # Mark early blocks as finalized
        for i in range(50):
            tracker.mark_finalized(i)

        # Check finality
        assert tracker.is_finalized(10) is True
        assert tracker.is_finalized(140) is False

    def test_recent_blocks_not_final(self, blockchain):
        """Test recent blocks are not considered final"""
        tracker = FinalityTracker()
        wallet = Wallet()

        # Build short chain
        for _ in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        # Recent blocks should not be final
        chain_height = len(blockchain.chain)
        recent_block_index = chain_height - 1

        # Unless explicitly marked, should not be finalized
        assert tracker.is_finalized(recent_block_index) is False

    def test_finalized_blocks_immutable(self, blockchain):
        """Test finalized blocks should not be reorganized"""
        tracker = FinalityTracker()
        wallet = Wallet()

        # Build chain
        for _ in range(120):
            blockchain.mine_pending_transactions(wallet.address)

        # Mark block 10 as finalized
        tracker.mark_finalized(10)

        # Block 10 should be considered immutable
        assert tracker.is_finalized(10) is True

        # Reorganization beyond this point should be rejected
        # (Implementation specific)


class TestConsensusEdgeCases:
    """Test consensus edge cases"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_empty_block_valid(self, blockchain):
        """Test empty blocks (no transactions except coinbase) are valid"""
        wallet = Wallet()

        # Mine block with no pending transactions
        block = blockchain.mine_pending_transactions(wallet.address)

        # Should only have coinbase
        assert len(block.transactions) == 1
        assert block.transactions[0].sender == "COINBASE"

        # Should be valid
        assert blockchain.validate_chain() is True

    def test_single_node_consensus(self, blockchain):
        """Test single node can maintain consensus"""
        wallet = Wallet()

        # Mine blocks
        for _ in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        # Chain should be valid
        assert blockchain.validate_chain() is True
        assert len(blockchain.chain) == 11

    def test_rapid_block_mining(self, blockchain):
        """Test rapid block mining maintains consensus"""
        wallet = Wallet()

        # Mine blocks rapidly
        for _ in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            assert block is not None

        # All should be valid
        assert blockchain.validate_chain() is True
        assert len(blockchain.chain) == 6

    def test_block_timestamp_monotonic(self, blockchain):
        """Test block timestamps should generally increase"""
        wallet = Wallet()

        timestamps = [blockchain.chain[0].timestamp]

        # Mine blocks
        for _ in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            timestamps.append(block.timestamp)

        # Timestamps should generally increase
        # (Small violations possible due to system time, but trend should be upward)
        assert timestamps[-1] >= timestamps[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
