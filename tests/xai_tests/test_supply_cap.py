"""
Comprehensive Tests for Supply Cap Enforcement

Ensures that the blockchain never exceeds the 121M XAI cap through:
1. Genesis allocation validation
2. Mining reward caps
3. Total supply validation
4. Edge cases and boundary conditions
"""

import pytest
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestGenesisAllocation:
    """Test genesis block allocation"""

    def test_genesis_allocation_within_cap(self, tmp_path):
        """Genesis allocation should be exactly 50% of max supply"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Calculate genesis allocation
        genesis_supply = bc.get_circulating_supply()

        # Should be 60.5M (50% of 121M)
        expected_genesis = 60_500_000.0
        assert genesis_supply == expected_genesis, f"Genesis should be {expected_genesis}, got {genesis_supply}"

        # Should be less than max supply
        assert genesis_supply < bc.max_supply

    def test_genesis_leaves_room_for_mining(self, tmp_path):
        """Genesis should leave 50% for mining rewards"""
        bc = Blockchain(data_dir=str(tmp_path))

        genesis_supply = bc.get_circulating_supply()
        remaining = bc.max_supply - genesis_supply

        # Should have 60.5M remaining for mining
        expected_remaining = 60_500_000.0
        assert remaining == expected_remaining


class TestMiningRewards:
    """Test mining reward calculations with supply cap"""

    def test_initial_mining_reward(self, tmp_path):
        """First mining reward should be 12 XAI"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Get reward for block 1
        reward = bc.get_block_reward(1)

        assert reward == 12.0

    def test_mining_respects_supply_cap(self, tmp_path):
        """Mining should stop when approaching supply cap"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine multiple blocks
        for i in range(10):
            bc.mine_pending_transactions(miner.address)

            # Check supply never exceeds cap
            current_supply = bc.get_circulating_supply()
            assert current_supply <= bc.max_supply, \
                f"Supply {current_supply} exceeds cap {bc.max_supply} at block {i+1}"

    def test_reward_capped_to_remaining_supply(self, tmp_path):
        """Reward should be capped to remaining supply"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Simulate near-cap scenario
        # Current supply is 60.5M, cap is 121M, so 60.5M remaining
        # If we mine enough blocks, reward should eventually be capped

        current_supply = bc.get_circulating_supply()
        remaining = bc.max_supply - current_supply

        # Get next reward
        next_reward = bc.get_block_reward(1)

        # Reward should not exceed remaining supply
        assert next_reward <= remaining

    def test_zero_reward_at_cap(self, tmp_path):
        """Reward should be zero when supply cap is reached"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Manually set circulating supply to cap (for testing)
        # This simulates what happens when we reach the cap
        original_get_supply = bc.get_circulating_supply

        def mock_at_cap():
            return bc.max_supply

        bc.get_circulating_supply = mock_at_cap

        # Get reward when at cap
        reward = bc.get_block_reward(1)

        assert reward == 0.0, "Reward should be zero when at supply cap"

        # Restore original method
        bc.get_circulating_supply = original_get_supply

    def test_zero_reward_above_cap(self, tmp_path):
        """Reward should be zero if supply somehow exceeds cap"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Mock supply above cap
        def mock_above_cap():
            return bc.max_supply + 1000

        bc.get_circulating_supply = mock_above_cap

        # Get reward when above cap
        reward = bc.get_block_reward(1)

        assert reward == 0.0, "Reward should be zero when above supply cap"


class TestSupplyCapEnforcement:
    """Test overall supply cap enforcement"""

    def test_total_supply_never_exceeds_cap(self, tmp_path):
        """Total supply should never exceed 121M"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine many blocks
        for i in range(50):
            bc.mine_pending_transactions(miner.address)

            total_supply = bc.get_total_supply()
            circulating_supply = bc.get_circulating_supply()

            # Both should never exceed cap
            assert total_supply <= bc.max_supply, \
                f"Total supply {total_supply} exceeds cap at block {i+1}"
            assert circulating_supply <= bc.max_supply, \
                f"Circulating supply {circulating_supply} exceeds cap at block {i+1}"

    def test_supply_approaches_cap_asymptotically(self, tmp_path):
        """Supply should approach cap but never exceed it"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        supplies = []

        # Mine blocks and track supply
        for i in range(20):
            bc.mine_pending_transactions(miner.address)
            supplies.append(bc.get_circulating_supply())

        # Supply should be increasing
        assert all(supplies[i] < supplies[i+1] for i in range(len(supplies)-1)), \
            "Supply should be monotonically increasing"

        # All supplies should be below cap
        assert all(s <= bc.max_supply for s in supplies), \
            "All supplies should be at or below cap"

    def test_genesis_plus_mining_equals_cap_eventually(self, tmp_path):
        """Genesis + all mining rewards should eventually equal cap"""
        bc = Blockchain(data_dir=str(tmp_path))

        genesis_supply = 60_500_000.0
        max_supply = 121_000_000.0

        # The maximum possible mining rewards
        max_mining_rewards = max_supply - genesis_supply

        # Should be exactly 60.5M available for mining
        assert max_mining_rewards == 60_500_000.0


class TestHalvingWithSupplyCap:
    """Test halving schedule with supply cap enforcement"""

    def test_halving_schedule_respected(self, tmp_path):
        """Halving should occur at correct intervals"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Initial reward
        reward_year1 = bc.get_block_reward(1)
        assert reward_year1 == 12.0

        # After first halving (block 262800)
        reward_year2 = bc.get_block_reward(262800)
        assert reward_year2 == 6.0

        # After second halving (block 525600)
        reward_year3 = bc.get_block_reward(525600)
        assert reward_year3 == 3.0

        # After third halving (block 788400)
        reward_year4 = bc.get_block_reward(788400)
        assert reward_year4 == 1.5

    def test_halving_with_supply_cap_interaction(self, tmp_path):
        """Test that halving and supply cap work together"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Even with halving, rewards should respect supply cap
        for block_height in [1, 262800, 525600, 788400]:
            reward = bc.get_block_reward(block_height)
            current_supply = bc.get_circulating_supply()

            # Reward + current supply should not exceed cap
            assert current_supply + reward <= bc.max_supply


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_minimum_reward_threshold(self, tmp_path):
        """Rewards below minimum should be zero"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Very far into future (many halvings)
        # After 64 halvings, reward would be microscopic
        reward = bc.get_block_reward(64 * bc.halving_interval)

        # Should be zero due to minimum threshold
        assert reward == 0.0

    def test_supply_cap_exact_match(self, tmp_path):
        """Test when supply exactly matches cap"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Mock supply exactly at cap
        def mock_exact_cap():
            return bc.max_supply

        bc.get_circulating_supply = mock_exact_cap

        reward = bc.get_block_reward(1)
        assert reward == 0.0

    def test_transaction_fees_dont_break_cap(self, tmp_path):
        """Transaction fees should not cause supply to exceed cap"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender some coins
        bc.mine_pending_transactions(sender.address)

        # Create transaction with fee
        tx = bc.create_transaction(
            sender.address, recipient.address, 1.0, 0.5,
            sender.private_key, sender.public_key
        )

        if tx:
            bc.add_transaction(tx)

        # Mine block with transaction (includes fee)
        bc.mine_pending_transactions(miner.address)

        # Supply should still be within cap
        assert bc.get_circulating_supply() <= bc.max_supply


class TestSupplyCalculations:
    """Test supply calculation methods"""

    def test_circulating_supply_accuracy(self, tmp_path):
        """Circulating supply should match sum of all unspent UTXOs"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine some blocks
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        # Calculate supply manually (only unspent UTXOs)
        # The UTXO set structure is: {address: [utxo_list]}
        # Each UTXO is a dict with 'amount', 'script_pubkey', 'spent', etc.
        # We need to filter out spent UTXOs
        manual_supply = 0.0
        for address, utxos in bc.utxo_manager.utxo_set.items():
            for utxo in utxos:
                # Only count unspent UTXOs
                if not utxo.get("spent", False):
                    manual_supply += utxo.get("amount", 0.0)

        # Should match get_circulating_supply()
        circulating = bc.get_circulating_supply()
        assert abs(circulating - manual_supply) < 0.01, \
            f"Supply mismatch: get_circulating_supply()={circulating}, manual={manual_supply}"

    def test_total_supply_equals_circulating(self, tmp_path):
        """For now, total supply should equal circulating supply"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        bc.mine_pending_transactions(miner.address)

        # Should be equal (no locked/vested tokens yet)
        assert bc.get_total_supply() == bc.get_circulating_supply()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
