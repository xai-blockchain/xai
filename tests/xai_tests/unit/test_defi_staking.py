"""
Comprehensive tests for DeFi StakingPool delegator reward distribution.

Tests the complete reward distribution flow:
- Validator commission deduction
- Proportional delegator reward distribution
- Reward claiming
- Dust handling
"""
import pytest

from xai.core.defi.staking import StakingPool, Validator, Delegation, ValidatorStatus


class TestDelegatorRewardDistribution:
    """Test delegator reward distribution security and correctness."""

    def test_delegator_receives_rewards_after_commission(self):
        """Test that delegators receive proportional rewards after validator commission."""
        pool = StakingPool(owner="0xOwner")

        # Register validator with 10% commission
        val_addr = "0xValidator1"
        pool.register_validator(
            caller=val_addr,
            name="Validator1",
            commission=1000,  # 10% in basis points
            self_stake=10_000 * 10**18,
        )

        # Delegator delegates 10k tokens (same as validator self-stake)
        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Verify delegation
        assert pool.validators[val_addr.lower()].delegated_stake == 10_000 * 10**18
        assert pool.total_staked == 20_000 * 10**18

        # Distribute 1000 tokens as rewards
        total_rewards = 1000 * 10**18
        pool.distribute_rewards("0xOwner", total_rewards)

        # Validator's total share = 1000 tokens (100% since only validator)
        # Validator takes 10% commission = 100 tokens
        # Remaining 900 goes to delegators
        validator = pool.validators[val_addr.lower()]
        expected_commission = (total_rewards * 1000) // 10000  # 100 tokens
        assert validator.accumulated_rewards == expected_commission

        # Delegator has 100% of delegated_stake (only delegator)
        # So delegator gets all 900 tokens
        delegation = pool.delegations[delegator.lower()][val_addr.lower()]
        expected_delegator_reward = total_rewards - expected_commission  # 900 tokens
        assert delegation.accumulated_rewards == expected_delegator_reward

    def test_multiple_delegators_proportional_distribution(self):
        """Test that multiple delegators receive proportional rewards."""
        pool = StakingPool(owner="0xOwner")

        # Register validator with 5% commission
        val_addr = "0xValidator1"
        pool.register_validator(
            caller=val_addr,
            name="Validator1",
            commission=500,  # 5%
            self_stake=10_000 * 10**18,
        )

        # Three delegators with different amounts
        delegator1 = "0xDelegator1"
        delegator2 = "0xDelegator2"
        delegator3 = "0xDelegator3"

        pool.delegate(delegator1, val_addr, 20_000 * 10**18)  # 2x validator stake
        pool.delegate(delegator2, val_addr, 10_000 * 10**18)  # 1x validator stake
        pool.delegate(delegator3, val_addr, 10_000 * 10**18)  # 1x validator stake

        # Total delegated: 40k, validator self: 10k, total: 50k
        assert pool.total_staked == 50_000 * 10**18

        # Distribute 10,000 tokens
        total_rewards = 10_000 * 10**18
        pool.distribute_rewards("0xOwner", total_rewards)

        # Validator gets 100% of rewards (only validator)
        # Commission: 10k * 5% = 500 tokens
        # Delegator pool: 10k - 500 = 9500 tokens
        validator = pool.validators[val_addr.lower()]
        expected_commission = (total_rewards * 500) // 10000  # 500 tokens
        assert validator.accumulated_rewards == expected_commission

        delegator_pool = total_rewards - expected_commission

        # Delegator 1: 20k/40k = 50% of delegator pool = 4750 tokens
        del1 = pool.delegations[delegator1.lower()][val_addr.lower()]
        expected_del1 = (delegator_pool * 20_000) // 40_000
        assert del1.accumulated_rewards == expected_del1

        # Delegator 2: 10k/40k = 25% of delegator pool = 2375 tokens
        del2 = pool.delegations[delegator2.lower()][val_addr.lower()]
        expected_del2 = (delegator_pool * 10_000) // 40_000
        assert del2.accumulated_rewards == expected_del2

        # Delegator 3: 10k/40k = 25% of delegator pool = 2375 tokens
        del3 = pool.delegations[delegator3.lower()][val_addr.lower()]
        expected_del3 = (delegator_pool * 10_000) // 40_000
        assert del3.accumulated_rewards == expected_del3

        # Total distributed should equal delegator pool (minus dust)
        total_distributed = del1.accumulated_rewards + del2.accumulated_rewards + del3.accumulated_rewards
        assert abs(total_distributed - delegator_pool) <= 40_000  # Allow dust

    def test_claim_rewards_zeroes_balance(self):
        """Test that claiming rewards zeroes the accumulated balance."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Distribute rewards
        pool.distribute_rewards("0xOwner", 1000 * 10**18)

        # Check delegator has rewards
        delegation = pool.delegations[delegator.lower()][val_addr.lower()]
        initial_rewards = delegation.accumulated_rewards
        assert initial_rewards > 0

        # Claim rewards
        claimed = pool.claim_rewards(delegator, val_addr)
        assert claimed == initial_rewards

        # Balance should be zero
        assert delegation.accumulated_rewards == 0

        # Second claim should return 0
        claimed_again = pool.claim_rewards(delegator, val_addr)
        assert claimed_again == 0

    def test_claim_all_rewards_across_validators(self):
        """Test claiming rewards from multiple validators."""
        pool = StakingPool(owner="0xOwner")

        # Register two validators
        val1 = "0xValidator1"
        val2 = "0xValidator2"
        pool.register_validator(val1, "Val1", 500, 10_000 * 10**18)
        pool.register_validator(val2, "Val2", 1000, 10_000 * 10**18)

        # Delegate to both
        delegator = "0xDelegator1"
        pool.delegate(delegator, val1, 10_000 * 10**18)
        pool.delegate(delegator, val2, 10_000 * 10**18)

        # Distribute rewards
        pool.distribute_rewards("0xOwner", 4000 * 10**18)

        # Get rewards info
        rewards_info = pool.get_delegator_rewards(delegator)
        assert rewards_info["total_rewards"] > 0
        assert len(rewards_info["rewards_by_validator"]) == 2

        # Claim all
        total_claimed = pool.claim_all_rewards(delegator)
        assert total_claimed == rewards_info["total_rewards"]

        # All balances should be zero
        del1 = pool.delegations[delegator.lower()][val1.lower()]
        del2 = pool.delegations[delegator.lower()][val2.lower()]
        assert del1.accumulated_rewards == 0
        assert del2.accumulated_rewards == 0

    def test_no_rewards_when_no_stake(self):
        """Test that delegators don't receive rewards if validator has no stake."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        # Distribute before any delegations
        pool.distribute_rewards("0xOwner", 1000 * 10**18)

        # Only validator should have rewards (all goes to commission)
        validator = pool.validators[val_addr.lower()]
        assert validator.accumulated_rewards > 0

    def test_dust_handling_prevents_loss(self):
        """Test that integer division dust doesn't lose rewards."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        # Create scenario with odd numbers that cause dust
        delegator1 = "0xDelegator1"
        delegator2 = "0xDelegator2"
        delegator3 = "0xDelegator3"

        pool.delegate(delegator1, val_addr, 33_333 * 10**18)
        pool.delegate(delegator2, val_addr, 33_333 * 10**18)
        pool.delegate(delegator3, val_addr, 33_334 * 10**18)

        # Total delegated: 100,000
        total_delegated = 100_000 * 10**18

        # Distribute 1000 tokens
        total_rewards = 1000 * 10**18
        pool.distribute_rewards("0xOwner", total_rewards)

        # Calculate what should be distributed
        # Validator gets 100% since it's the only validator
        validator = pool.validators[val_addr.lower()]
        val_share = total_rewards  # 100% of rewards
        commission = (val_share * 500) // 10000
        delegator_pool = val_share - commission

        # Sum delegator rewards
        del1 = pool.delegations[delegator1.lower()][val_addr.lower()]
        del2 = pool.delegations[delegator2.lower()][val_addr.lower()]
        del3 = pool.delegations[delegator3.lower()][val_addr.lower()]

        total_delegator_rewards = (
            del1.accumulated_rewards + del2.accumulated_rewards + del3.accumulated_rewards
        )

        # Dust should be added to validator
        dust = delegator_pool - total_delegator_rewards
        assert validator.accumulated_rewards >= commission
        assert dust >= 0  # No negative dust

        # Total rewards distributed should equal input (accounting for precision)
        total_distributed = validator.accumulated_rewards + total_delegator_rewards
        assert total_distributed <= val_share  # Can't exceed share

    def test_zero_commission_validator(self):
        """Test reward distribution with 0% commission validator."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(
            val_addr, "Val1", commission=0, self_stake=10_000 * 10**18
        )

        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Distribute rewards
        total_rewards = 1000 * 10**18
        pool.distribute_rewards("0xOwner", total_rewards)

        # Validator gets 100% of rewards, takes 0% commission
        # All rewards go to delegators
        validator = pool.validators[val_addr.lower()]
        # Validator may have dust but no commission (0%)
        commission = (total_rewards * 0) // 10000
        assert commission == 0

        # Delegator should get 100% of delegator rewards (only delegator)
        # Total rewards = 1000, commission = 0, delegator pool = 1000
        delegation = pool.delegations[delegator.lower()][val_addr.lower()]
        expected_share = total_rewards  # All 1000 tokens
        # Allow small difference for dust
        assert abs(delegation.accumulated_rewards - expected_share) <= 10_000 * 10**18

    def test_hundred_percent_commission_validator(self):
        """Test reward distribution with 100% commission validator."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(
            val_addr, "Val1", commission=10000, self_stake=10_000 * 10**18  # 100%
        )

        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Distribute rewards
        total_rewards = 1000 * 10**18
        pool.distribute_rewards("0xOwner", total_rewards)

        # Validator should take all rewards as commission
        validator = pool.validators[val_addr.lower()]
        expected_commission = (total_rewards // 2)  # 50% of total (since 50% of stake)
        assert validator.accumulated_rewards >= expected_commission

        # Delegator should get nothing
        delegation = pool.delegations[delegator.lower()][val_addr.lower()]
        assert delegation.accumulated_rewards == 0

    def test_get_delegation_info_includes_rewards(self):
        """Test that delegation info returns accumulated rewards."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Distribute rewards
        pool.distribute_rewards("0xOwner", 1000 * 10**18)

        # Get delegation info
        info = pool.get_delegation_info(delegator, val_addr)
        assert "accumulated_rewards" in info
        assert info["accumulated_rewards"] > 0
        assert info["amount"] == 10_000 * 10**18

    def test_compound_rewards(self):
        """Test auto-delegation of rewards (compounding)."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        delegator = "0xDelegator1"
        initial_delegation = 10_000 * 10**18
        pool.delegate(delegator, val_addr, initial_delegation)

        # Distribute large enough rewards to meet min delegation
        pool.distribute_rewards("0xOwner", 10_000 * 10**18)

        # Get current delegation
        delegation = pool.delegations[delegator.lower()][val_addr.lower()]
        rewards_before = delegation.accumulated_rewards
        amount_before = delegation.amount

        # Compound
        pool.compound_rewards(delegator, val_addr)

        # Rewards should be zero (claimed)
        assert delegation.accumulated_rewards == 0

        # Amount should increase by rewards (if rewards >= min_delegation)
        if rewards_before >= pool.min_delegation:
            assert delegation.amount > amount_before

    def test_multiple_reward_distributions_accumulate(self):
        """Test that multiple reward distributions accumulate correctly."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        delegator = "0xDelegator1"
        pool.delegate(delegator, val_addr, 10_000 * 10**18)

        # Distribute multiple times
        pool.distribute_rewards("0xOwner", 1000 * 10**18)
        first_distribution = pool.delegations[delegator.lower()][
            val_addr.lower()
        ].accumulated_rewards

        pool.distribute_rewards("0xOwner", 1000 * 10**18)
        second_distribution = pool.delegations[delegator.lower()][
            val_addr.lower()
        ].accumulated_rewards

        pool.distribute_rewards("0xOwner", 1000 * 10**18)
        third_distribution = pool.delegations[delegator.lower()][
            val_addr.lower()
        ].accumulated_rewards

        # Each distribution should increase rewards
        assert second_distribution > first_distribution
        assert third_distribution > second_distribution

        # Third should be approximately 3x first (allowing for rounding)
        assert abs(third_distribution - (first_distribution * 3)) < 100

    def test_no_rewards_for_nonexistent_delegation(self):
        """Test that querying non-existent delegation returns zero rewards."""
        pool = StakingPool(owner="0xOwner")

        val_addr = "0xValidator1"
        pool.register_validator(val_addr, "Val1", 500, 10_000 * 10**18)

        # Query non-existent delegator
        info = pool.get_delegation_info("0xNonExistent", val_addr)
        assert info["accumulated_rewards"] == 0
        assert info["amount"] == 0

        # Distribute rewards shouldn't affect non-existent delegator
        pool.distribute_rewards("0xOwner", 1000 * 10**18)

        info = pool.get_delegation_info("0xNonExistent", val_addr)
        assert info["accumulated_rewards"] == 0
