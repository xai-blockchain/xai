"""
Tests for lending pool interest accrual dust loss fix.

These tests verify that the accumulator pattern prevents small depositors
from losing interest due to integer division rounding.
"""

import pytest
import time
from xai.core.defi.lending import (
    LendingPool,
    AssetConfig,
    InterestRateModel,
)


class TestLendingDustLossFix:
    """Test suite for dust loss prevention using accumulator pattern."""

    @pytest.fixture
    def pool(self):
        """Create a lending pool with test assets."""
        pool = LendingPool(name="Test Pool", owner="owner_address")

        # Add XAI asset with 5% APY base rate
        config = AssetConfig(
            symbol="XAI",
            address="0xXAI",
            ltv=8000,  # 80%
            liquidation_threshold=8500,  # 85%
            liquidation_bonus=500,  # 5%
            base_rate=500,  # 5% APY
            slope1=400,
            slope2=7500,
            optimal_utilization=8000,
            reserve_factor=1000,  # 10%
        )
        pool.add_asset("owner_address", config)

        return pool

    def test_small_deposit_accrues_interest(self, pool):
        """
        Test that small deposits accrue interest over time when there's utilization.

        Before fix: 100 tokens at 5% APY daily = 0 interest (dust loss)
        After fix: 100 tokens at 5% APY daily > 0 interest (preserved)
        """
        # User 1 makes small deposit
        deposit_amount = 100 * 10**18  # 100 tokens
        pool.supply("user1", "XAI", deposit_amount)

        # User 2 supplies collateral and borrows to create utilization
        pool.supply("user2", "XAI", 10000 * 10**18)
        pool.borrow("user2", "XAI", 50 * 10**18, InterestRateModel.VARIABLE)

        # Initial balance
        position = pool._get_position("user1")
        initial_balance = pool._get_user_supply_balance(position, "XAI")
        assert initial_balance == deposit_amount

        # Simulate 1 day passing
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400  # 1 day ago

        # Update indices to accrue interest
        pool._update_indices("XAI")

        # Check balance after interest accrual
        final_balance = pool._get_user_supply_balance(position, "XAI")

        # Should have earned interest
        # Even for small amounts, should be > 0 due to RAY precision
        assert final_balance > initial_balance, "Small deposit should accrue interest"

        # Calculate expected interest (approximately)
        # With RAY precision, even small amounts should accrue correctly
        interest_earned = final_balance - initial_balance
        assert interest_earned > 0, "Interest should be greater than zero"

    def test_small_borrow_accrues_interest(self, pool):
        """
        Test that small borrows accrue interest correctly.

        This is critical for preventing users from avoiding interest
        by borrowing small amounts.
        """
        # Setup: User supplies collateral
        collateral = 1000 * 10**18  # 1000 tokens
        pool.supply("user1", "XAI", collateral)

        # Borrow small amount
        borrow_amount = 100 * 10**18  # 100 tokens
        pool.borrow("user1", "XAI", borrow_amount, InterestRateModel.VARIABLE)

        # Initial debt
        position = pool._get_position("user1")
        initial_debt = pool._get_user_borrow_balance(position, "XAI")
        assert initial_debt == borrow_amount

        # Simulate 1 day passing
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400  # 1 day ago

        # Update indices
        pool._update_indices("XAI")

        # Check debt after interest accrual
        final_debt = pool._get_user_borrow_balance(position, "XAI")

        # Debt should increase
        assert final_debt > initial_debt, "Small borrow should accrue interest"

        interest_accrued = final_debt - initial_debt
        assert interest_accrued > 0, "Interest should be greater than zero"

    def test_interest_accumulates_over_many_periods(self, pool):
        """
        Test that interest accumulates correctly over many periods.

        This ensures indices don't drift or lose precision over time.
        """
        deposit_amount = 1000 * 10**18

        # User 1 supplies
        pool.supply("user1", "XAI", deposit_amount)

        # User 2 creates utilization
        pool.supply("user2", "XAI", 10000 * 10**18)
        pool.borrow("user2", "XAI", 5000 * 10**18, InterestRateModel.VARIABLE)

        position = pool._get_position("user1")

        # Simulate 365 days of daily updates
        for day in range(365):
            state = pool.pool_states["XAI"]
            state.last_update = time.time() - 86400  # 1 day ago
            pool._update_indices("XAI")

        # After 1 year with ~50% utilization and 5% base rate
        # Should have earned some interest
        final_balance = pool._get_user_supply_balance(position, "XAI")

        # Should have earned at least some interest (conservative check)
        assert final_balance > deposit_amount, f"Balance {final_balance} should be > {deposit_amount}"

    def test_index_never_decreases(self, pool):
        """
        Test that indices only increase, never decrease.

        This is a critical invariant for the accumulator pattern.
        """
        state = pool.pool_states["XAI"]
        initial_supply_index = state.supply_index
        initial_borrow_index = state.borrow_index

        # Update multiple times
        for _ in range(10):
            state.last_update = time.time() - 3600  # 1 hour ago
            pool._update_indices("XAI")

            # Indices should never decrease
            assert state.supply_index >= initial_supply_index
            assert state.borrow_index >= initial_borrow_index

            # Update for next iteration
            initial_supply_index = state.supply_index
            initial_borrow_index = state.borrow_index

    def test_rounding_favors_protocol_on_withdrawals(self, pool):
        """
        Test that rounding on withdrawals favors the protocol.

        When calculating user balances, we should round DOWN.
        """
        deposit_amount = 1000 * 10**18
        pool.supply("user1", "XAI", deposit_amount)

        # Simulate time passing
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        position = pool._get_position("user1")

        # Get balance (should round down)
        balance = pool._get_user_supply_balance(position, "XAI")

        # Withdraw all
        withdrawn = pool.withdraw("user1", "XAI", 2**256 - 1)

        # Should have withdrawn the rounded-down amount
        assert withdrawn == balance

    def test_rounding_favors_protocol_on_debt_calculation(self, pool):
        """
        Test that debt calculation rounds UP to favor the protocol.
        """
        # Setup
        collateral = 10000 * 10**18
        pool.supply("user1", "XAI", collateral)

        # Borrow
        borrow_amount = 1000 * 10**18
        pool.borrow("user1", "XAI", borrow_amount, InterestRateModel.VARIABLE)

        # Simulate time passing
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        position = pool._get_position("user1")
        debt = pool._get_user_borrow_balance(position, "XAI")

        # Debt should be greater than principal (interest accrued)
        assert debt > borrow_amount

        # Try to repay exact principal (should not fully repay due to interest)
        repaid = pool.repay("user1", "XAI", borrow_amount)

        # Should have repaid the requested amount
        assert repaid == borrow_amount

        # Should still have remaining debt (the accrued interest)
        position_after = pool._get_position("user1")
        remaining_debt = pool._get_user_borrow_balance(position_after, "XAI")
        assert remaining_debt > 0, "Should have remaining debt from accrued interest"

    def test_multiple_users_independent_interest(self, pool):
        """
        Test that multiple users accrue interest independently.

        Each user should earn interest based on their own deposit timing.
        """
        # User 1 deposits
        pool.supply("user1", "XAI", 1000 * 10**18)

        # Create utilization
        pool.supply("user3", "XAI", 10000 * 10**18)
        pool.borrow("user3", "XAI", 5000 * 10**18, InterestRateModel.VARIABLE)

        # Simulate 1 day
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        # User 2 deposits (at higher index)
        pool.supply("user2", "XAI", 1000 * 10**18)

        # Simulate another day
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        # User 1 should have more balance (deposited earlier)
        pos1 = pool._get_position("user1")
        pos2 = pool._get_position("user2")

        balance1 = pool._get_user_supply_balance(pos1, "XAI")
        balance2 = pool._get_user_supply_balance(pos2, "XAI")

        assert balance1 > balance2, "Earlier depositor should have more due to compound interest"

    def test_repay_updates_principal_correctly(self, pool):
        """
        Test that partial repayments update the principal correctly.
        """
        # Setup
        pool.supply("user1", "XAI", 10000 * 10**18)
        pool.borrow("user1", "XAI", 1000 * 10**18, InterestRateModel.VARIABLE)

        # Accrue interest
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        position = pool._get_position("user1")
        debt_before = pool._get_user_borrow_balance(position, "XAI")

        # Partial repayment
        repay_amount = 500 * 10**18
        pool.repay("user1", "XAI", repay_amount)

        # Check remaining debt
        position_after = pool._get_position("user1")
        debt_after = pool._get_user_borrow_balance(position_after, "XAI")

        assert debt_after == debt_before - repay_amount

    def test_very_small_amounts_no_overflow(self, pool):
        """
        Test that very small amounts don't cause overflow or underflow.
        """
        # Very small deposit (1 wei)
        tiny_amount = 1

        pool.supply("user1", "XAI", tiny_amount)

        # Should not crash
        position = pool._get_position("user1")
        balance = pool._get_user_supply_balance(position, "XAI")

        assert balance >= 0  # Should not underflow

    def test_very_large_amounts_no_overflow(self, pool):
        """
        Test that very large amounts don't overflow.
        """
        # Large deposit within collateral bounds
        large_amount = 100_000 * 10**18

        pool.supply("user1", "XAI", large_amount)

        # Create utilization
        pool.supply("user2", "XAI", large_amount)
        pool.borrow("user2", "XAI", large_amount // 2, InterestRateModel.VARIABLE)

        # Accrue interest over many periods
        for _ in range(100):
            state = pool.pool_states["XAI"]
            state.last_update = time.time() - 86400
            pool._update_indices("XAI")

        # Should not overflow
        position = pool._get_position("user1")
        balance = pool._get_user_supply_balance(position, "XAI")

        assert balance > large_amount  # Should have earned interest
        assert balance < large_amount * 2  # But not unreasonably large

    def test_borrow_index_snapshot_stored(self, pool):
        """
        Test that borrow index is stored when borrowing.
        """
        pool.supply("user1", "XAI", 10000 * 10**18)
        pool.borrow("user1", "XAI", 1000 * 10**18, InterestRateModel.VARIABLE)

        position = pool._get_position("user1")

        # Should have borrow index snapshot
        assert "XAI" in position.borrow_index
        assert position.borrow_index["XAI"] > 0

        # Should match current index at time of borrow
        state = pool.pool_states["XAI"]
        assert position.borrow_index["XAI"] == state.borrow_index

    def test_supply_index_used_for_atoken_conversion(self, pool):
        """
        Test that supply index is used correctly for aToken conversion.
        """
        deposit_amount = 1000 * 10**18

        pool.supply("user1", "XAI", deposit_amount)

        position = pool._get_position("user1")
        state = pool.pool_states["XAI"]

        # aTokens should be scaled by index
        a_tokens = position.supplied["XAI"]

        # At initial index (1 RAY), aTokens ≈ deposit amount / RAY
        # But slightly less due to rounding
        expected_a_tokens = deposit_amount * pool.RAY // state.supply_index

        assert abs(a_tokens - expected_a_tokens) <= 1  # Allow 1 wei rounding

    def test_interest_accrual_with_utilization_changes(self, pool):
        """
        Test that interest accrues correctly as utilization changes.
        """
        # User 1 supplies
        pool.supply("user1", "XAI", 10000 * 10**18)

        # User 2 borrows (increases utilization)
        pool.supply("user2", "XAI", 10000 * 10**18)
        pool.borrow("user2", "XAI", 5000 * 10**18, InterestRateModel.VARIABLE)

        # Accrue interest at high utilization
        state = pool.pool_states["XAI"]
        state.last_update = time.time() - 86400
        pool._update_indices("XAI")

        pos1 = pool._get_position("user1")
        pos2 = pool._get_position("user2")

        # User 1 should have earned supply interest
        balance1 = pool._get_user_supply_balance(pos1, "XAI")
        assert balance1 > 10000 * 10**18

        # User 2 should have accrued borrow interest
        debt2 = pool._get_user_borrow_balance(pos2, "XAI")
        assert debt2 > 5000 * 10**18

    def test_zero_time_elapsed_no_interest(self, pool):
        """
        Test that no interest accrues if no time has passed.
        """
        pool.supply("user1", "XAI", 1000 * 10**18)

        state = pool.pool_states["XAI"]
        initial_index = state.supply_index

        # Update with same timestamp
        pool._update_indices("XAI")

        # Index should not change
        assert state.supply_index == initial_index

    def test_negative_time_no_update(self, pool):
        """
        Test that negative time elapsed doesn't break the system.
        """
        pool.supply("user1", "XAI", 1000 * 10**18)

        state = pool.pool_states["XAI"]

        # Set future timestamp (would be negative time elapsed)
        state.last_update = time.time() + 3600

        initial_index = state.supply_index

        # Update should not change index
        pool._update_indices("XAI")

        assert state.supply_index == initial_index
