"""
Unit tests for XAI Blockchain core functionality

Tests blockchain creation, validation, mining, and supply management
"""

import pytest
import sys
import os
import time
from decimal import Decimal

# Add core directory to path

from aixn.core.blockchain import Blockchain, Transaction, Block
from aixn.core.wallet import Wallet


class TestBlockchainInitialization:
    """Test blockchain initialization and configuration"""

    def test_blockchain_creation(self):
        """Test blockchain initializes with genesis block"""
        bc = Blockchain()

        assert len(bc.chain) == 1
        assert bc.chain[0].index == 0
        assert bc.chain[0].previous_hash == "0"

    def test_genesis_block_structure(self):
        """Test genesis block has correct structure"""
        bc = Blockchain()
        genesis = bc.chain[0]

        assert genesis.hash is not None
        assert genesis.timestamp > 0
        assert len(genesis.transactions) > 0
        assert genesis.nonce >= 0

    def test_supply_cap_configuration(self):
        """Test 121M supply cap is correctly set"""
        bc = Blockchain()

        assert bc.max_supply == 121000000.0

    def test_difficulty_configuration(self):
        """Test mining difficulty is set"""
        bc = Blockchain()

        assert bc.difficulty > 0
        assert bc.difficulty <= 6  # Reasonable difficulty range

    def test_initial_state(self):
        """Test blockchain starts in valid state"""
        bc = Blockchain()

        assert bc.validate_chain()
        assert bc.pending_transactions == []
        assert isinstance(bc.utxo_set, dict)


class TestBlockMining:
    """Test block mining functionality"""

    def test_mine_block_basic(self):
        """Test basic block mining"""
        bc = Blockchain()
        wallet = Wallet()

        initial_height = len(bc.chain)
        block = bc.mine_pending_transactions(wallet.address)

        assert len(bc.chain) == initial_height + 1
        assert block.index == initial_height
        assert block.miner == wallet.address

    def test_mining_difficulty_enforcement(self):
        """Test mined blocks meet difficulty requirement"""
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        # Hash should start with required zeros
        required_prefix = "0" * bc.difficulty
        assert block.hash.startswith(required_prefix)

    def test_block_hash_uniqueness(self):
        """Test each block has unique hash"""
        bc = Blockchain()
        wallet = Wallet()

        block1 = bc.mine_pending_transactions(wallet.address)
        block2 = bc.mine_pending_transactions(wallet.address)

        assert block1.hash != block2.hash

    def test_block_linking(self):
        """Test blocks are properly linked"""
        bc = Blockchain()
        wallet = Wallet()

        block1 = bc.mine_pending_transactions(wallet.address)
        block2 = bc.mine_pending_transactions(wallet.address)

        assert block2.previous_hash == block1.hash

    def test_mining_reward(self):
        """Test mining produces correct reward"""
        bc = Blockchain()
        wallet = Wallet()

        initial_balance = bc.get_balance(wallet.address)
        bc.mine_pending_transactions(wallet.address)
        new_balance = bc.get_balance(wallet.address)

        assert new_balance > initial_balance
        assert new_balance - initial_balance == bc.get_block_reward(1)


class TestBlockReward:
    """Test block reward calculation and halving"""

    def test_initial_reward(self):
        """Test initial block reward is 12 XAI"""
        bc = Blockchain()

        reward = bc.get_block_reward(0)
        assert reward == 12.0

    def test_first_halving(self):
        """Test reward after first halving (262,800 blocks)"""
        bc = Blockchain()

        reward = bc.get_block_reward(262800)
        assert reward == 6.0

    def test_second_halving(self):
        """Test reward after second halving"""
        bc = Blockchain()

        reward = bc.get_block_reward(525600)
        assert reward == 3.0

    def test_third_halving(self):
        """Test reward after third halving"""
        bc = Blockchain()

        reward = bc.get_block_reward(788400)
        assert reward == 1.5

    def test_final_reward(self):
        """Test reward never goes below minimum"""
        bc = Blockchain()

        # Very large block number
        reward = bc.get_block_reward(10000000)
        assert reward > 0  # Should never reach zero

    def test_halving_schedule_consistency(self):
        """Test halving schedule is consistent"""
        bc = Blockchain()

        # Each halving should cut reward in half
        r1 = bc.get_block_reward(0)
        r2 = bc.get_block_reward(262800)
        r3 = bc.get_block_reward(525600)

        assert r2 == r1 / 2
        assert r3 == r2 / 2


class TestChainValidation:
    """Test blockchain validation"""

    def test_validate_valid_chain(self):
        """Test validation of valid blockchain"""
        bc = Blockchain()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        assert bc.validate_chain()

    def test_detect_tampered_transaction(self):
        """Test detection of tampered transactions"""
        bc = Blockchain()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Tamper with transaction
        if len(bc.chain[1].transactions) > 0:
            bc.chain[1].transactions[0].amount = 999999

            # Chain should now be invalid
            assert not bc.validate_chain()

    def test_detect_invalid_hash(self):
        """Test detection of invalid block hash"""
        bc = Blockchain()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Tamper with hash
        bc.chain[1].hash = "0" * 64

        assert not bc.validate_chain()

    def test_detect_broken_chain(self):
        """Test detection of broken chain link"""
        bc = Blockchain()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        # Break chain link
        bc.chain[2].previous_hash = "invalid_hash"

        assert not bc.validate_chain()


class TestSupplyManagement:
    """Test supply cap enforcement and tracking"""

    def test_supply_cap_constant(self):
        """Test supply cap is correctly defined"""
        bc = Blockchain()

        assert bc.max_supply == 121_000_000.0

    def test_circulating_supply_tracking(self):
        """Test circulating supply increases with mining"""
        bc = Blockchain()
        wallet = Wallet()

        initial_supply = bc.get_circulating_supply()
        bc.mine_pending_transactions(wallet.address)
        new_supply = bc.get_circulating_supply()

        assert new_supply > initial_supply

    def test_supply_never_exceeds_cap(self):
        """Test supply cannot exceed cap"""
        bc = Blockchain()
        wallet = Wallet()

        # Mine multiple blocks
        for _ in range(5):
            bc.mine_pending_transactions(wallet.address)

        supply = bc.get_circulating_supply()
        assert supply <= bc.max_supply

    def test_reward_calculation_respects_cap(self):
        """Test block rewards don't cause supply overflow"""
        bc = Blockchain()

        # Test at various block heights
        for block_height in [0, 100000, 500000, 1000000]:
            reward = bc.get_block_reward(block_height)
            assert reward > 0
            assert reward < bc.max_supply


class TestBlockTimestamps:
    """Test block timestamp handling"""

    def test_timestamp_format(self):
        """Test timestamps are Unix timestamps"""
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        # Should be reasonable Unix timestamp
        assert block.timestamp > 1700000000
        assert block.timestamp < time.time() + 100

    def test_timestamp_ordering(self):
        """Test blocks have increasing timestamps"""
        bc = Blockchain()
        wallet = Wallet()

        block1 = bc.mine_pending_transactions(wallet.address)
        time.sleep(0.1)  # Small delay
        block2 = bc.mine_pending_transactions(wallet.address)

        assert block2.timestamp >= block1.timestamp

    def test_genesis_timestamp(self):
        """Test genesis block has valid timestamp"""
        bc = Blockchain()
        genesis = bc.chain[0]

        assert genesis.timestamp > 0
        assert genesis.timestamp < time.time() + 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
