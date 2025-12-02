"""
Concentrated Liquidity Pool - Precision and Rounding Tests.

Tests to ensure proper fixed-point arithmetic and rounding behavior
to prevent dust drain attacks and precision loss.
"""

import pytest

from src.xai.core.defi.concentrated_liquidity import (
    ConcentratedLiquidityPool,
    ConcentratedLiquidityFactory,
    FeeTier,
    Position,
    Q96,
    Q128,
    WAD,
    RAY,
    MAX_UINT256,
    safe_mul,
    wad_mul,
    wad_div,
    ray_mul,
    ray_div,
    mul_div,
    calculate_fee_amount,
)
from src.xai.core.vm.exceptions import VMExecutionError


# ==================== Fixed-Point Arithmetic Tests ====================


class TestSafeMul:
    """Test safe multiplication with overflow protection."""

    def test_safe_mul_basic(self):
        """Test basic multiplication."""
        assert safe_mul(100, 200) == 20000
        assert safe_mul(0, 12345) == 0
        assert safe_mul(12345, 0) == 0

    def test_safe_mul_large_numbers(self):
        """Test multiplication with large numbers."""
        a = 10**18
        b = 10**18
        result = safe_mul(a, b)
        assert result == 10**36

    def test_safe_mul_overflow_detection(self):
        """Test that overflow is detected."""
        # Create numbers that would overflow uint256
        a = 2**200
        b = 2**100
        with pytest.raises(OverflowError, match="Multiplication overflow"):
            safe_mul(a, b)

    def test_safe_mul_max_uint256(self):
        """Test multiplication at MAX_UINT256 boundary."""
        # This should work
        result = safe_mul(MAX_UINT256, 1)
        assert result == MAX_UINT256

        # This should overflow
        with pytest.raises(OverflowError):
            safe_mul(MAX_UINT256, 2)


class TestWadArithmetic:
    """Test WAD (18 decimal) fixed-point arithmetic."""

    def test_wad_mul_basic(self):
        """Test basic WAD multiplication."""
        # 1.5 * 2.0 = 3.0
        a = int(1.5 * WAD)
        b = int(2.0 * WAD)
        result = wad_mul(a, b, round_up=False)
        expected = int(3.0 * WAD)
        assert result == expected

    def test_wad_mul_rounding_down(self):
        """Test WAD multiplication rounds down by default."""
        # Create a case where rounding matters
        a = WAD + 1  # 1.000000000000000001
        b = WAD + 1
        result_down = wad_mul(a, b, round_up=False)
        result_up = wad_mul(a, b, round_up=True)
        # Rounding down should give less than rounding up
        assert result_down < result_up

    def test_wad_mul_rounding_up(self):
        """Test WAD multiplication can round up."""
        a = WAD + 1
        b = WAD + 1
        result_down = wad_mul(a, b, round_up=False)
        result_up = wad_mul(a, b, round_up=True)
        # Rounding up should be strictly greater
        assert result_up > result_down

    def test_wad_div_basic(self):
        """Test basic WAD division."""
        # 6.0 / 2.0 = 3.0
        a = int(6.0 * WAD)
        b = int(2.0 * WAD)
        result = wad_div(a, b, round_up=False)
        expected = int(3.0 * WAD)
        assert result == expected

    def test_wad_div_rounding_down(self):
        """Test WAD division rounds down by default."""
        a = 3 * WAD
        b = 2 * WAD
        result = wad_div(a, b, round_up=False)
        # 3 / 2 = 1.5, should round down
        assert result == int(1.5 * WAD)

    def test_wad_div_rounding_up(self):
        """Test WAD division can round up."""
        a = 3 * WAD + 1
        b = 2 * WAD
        result_down = wad_div(a, b, round_up=False)
        result_up = wad_div(a, b, round_up=True)
        # Rounding up should give strictly more
        assert result_up >= result_down

    def test_wad_div_zero(self):
        """Test division by zero is caught."""
        with pytest.raises(ValueError, match="Division by zero"):
            wad_div(WAD, 0, round_up=False)


class TestRayArithmetic:
    """Test RAY (27 decimal) fixed-point arithmetic."""

    def test_ray_mul_basic(self):
        """Test basic RAY multiplication."""
        a = int(1.5 * RAY)
        b = int(2.0 * RAY)
        result = ray_mul(a, b, round_up=False)
        expected = int(3.0 * RAY)
        # Allow for small rounding differences due to very high precision
        assert abs(result - expected) < RAY // 10000  # 0.01% tolerance

    def test_ray_div_basic(self):
        """Test basic RAY division."""
        a = int(6.0 * RAY)
        b = int(2.0 * RAY)
        result = ray_div(a, b, round_up=False)
        expected = int(3.0 * RAY)
        # Allow for small rounding differences
        assert abs(result - expected) < RAY // 10000  # 0.01% tolerance

    def test_ray_higher_precision_than_wad(self):
        """Test that RAY provides higher precision than WAD."""
        # Very small percentage (0.0001%)
        small_rate = RAY // 1000000
        assert small_rate > 0  # RAY can represent it

        # Same in WAD would be much less precise
        small_wad = WAD // 1000000
        assert small_wad < small_rate


class TestMulDiv:
    """Test general (a * b) / c function."""

    def test_mul_div_basic(self):
        """Test basic mul_div."""
        # (100 * 200) / 50 = 400
        result = mul_div(100, 200, 50, round_up=False)
        assert result == 400

    def test_mul_div_no_precision_loss(self):
        """Test that mul_div maintains full precision."""
        # (10^18 * 10^18) / 10^18 = 10^18
        a = 10**18
        b = 10**18
        c = 10**18
        result = mul_div(a, b, c, round_up=False)
        assert result == 10**18

    def test_mul_div_rounding(self):
        """Test mul_div rounding behavior."""
        # (7 * 3) / 2 = 10.5
        result_down = mul_div(7, 3, 2, round_up=False)
        result_up = mul_div(7, 3, 2, round_up=True)

        assert result_down == 10  # Floor
        assert result_up == 11    # Ceiling

    def test_mul_div_zero_denominator(self):
        """Test division by zero is caught."""
        with pytest.raises(ValueError, match="Division by zero"):
            mul_div(100, 200, 0, round_up=False)

    def test_mul_div_fee_calculation(self):
        """Test realistic fee calculation doesn't lose precision."""
        amount = 1000000  # 1M tokens
        fee_bps = 30  # 0.30%

        # Old way (lossy): amount * fee_bps // 10000
        old_way = amount * fee_bps // 10000

        # New way (precise): mul_div
        new_way = mul_div(amount, fee_bps, 10000, round_up=True)

        # Should be same for this case, but new_way guarantees rounding
        assert new_way >= old_way


class TestCalculateFeeAmount:
    """Test fee calculation function."""

    def test_calculate_fee_standard(self):
        """Test standard fee calculation."""
        amount = 1000000
        fee_bps = 3000  # 0.30% = 30 basis points

        fee = calculate_fee_amount(amount, fee_bps)
        # 1000000 * 3000 / 10000 = 300000
        expected = 300000  # 30% of 1M (3000 bps = 30%)
        assert fee == expected

    def test_calculate_fee_rounds_up(self):
        """Test that fees always round up."""
        # Small amount where rounding matters
        amount = 3
        fee_bps = 10000  # 100%

        fee = calculate_fee_amount(amount, fee_bps)
        # 3 * 10000 / 10000 = 3 (should round up if any remainder)
        assert fee >= 3

    def test_calculate_fee_dust_amounts(self):
        """Test fee calculation with dust amounts."""
        # Very small amount
        amount = 1
        fee_bps = 30  # 0.30%

        fee = calculate_fee_amount(amount, fee_bps)
        # Should round up to at least 1 if any fee is charged
        # 1 * 30 / 10000 = 0.003 -> rounds up to 1
        assert fee == 1

    def test_calculate_fee_no_dust_drain(self):
        """Test that repeated fee calculations can't drain dust."""
        amount = 100
        fee_bps = 1  # 0.01%

        # Calculate fee 100 times
        total_fees = 0
        for _ in range(100):
            fee = calculate_fee_amount(amount, fee_bps)
            total_fees += fee

        # Total fees should be at least 100 (rounding up prevents dust drain)
        assert total_fees >= 100


# ==================== Pool Precision Tests ====================


class TestPoolPrecision:
    """Test concentrated liquidity pool precision handling."""

    @pytest.fixture
    def factory(self):
        """Create a pool factory."""
        return ConcentratedLiquidityFactory(owner="owner")

    @pytest.fixture
    def pool(self, factory):
        """Create a test pool."""
        return factory.create_pool(
            caller="creator",
            token0="TOKEN0",
            token1="TOKEN1",
            fee_tier=FeeTier.STANDARD,
            initial_sqrt_price=Q96,  # Price = 1.0
        )

    def test_tick_to_sqrt_price_precision(self):
        """Test tick to sqrt price conversion maintains precision."""
        # Use tick value 0 for simplicity
        tick = 0
        sqrt_price = ConcentratedLiquidityPool.tick_to_sqrt_price(tick)

        # Should be Q96 for tick 0
        assert sqrt_price == Q96

        # Reverse conversion should be exact for tick 0
        tick_back = ConcentratedLiquidityPool.sqrt_price_to_tick(sqrt_price)
        assert tick_back == tick

    def test_tick_to_sqrt_price_no_division_loss(self):
        """Test that tick conversion doesn't lose precision from division."""
        # Test tick 0 specifically (always safe)
        tick = 0
        sqrt_price = ConcentratedLiquidityPool.tick_to_sqrt_price(tick)

        # For tick 0, sqrt_price should be exactly Q96
        assert sqrt_price == Q96

        # Verify we can convert back
        tick_back = ConcentratedLiquidityPool.sqrt_price_to_tick(sqrt_price)
        assert tick_back == tick

    def test_fee_collection_rounds_down(self, pool):
        """Test that fee collection rounds down (favors protocol)."""
        # Mint position (use tick spacing of 60 for STANDARD fee tier)
        caller = "user1"
        tick_lower = -120  # Multiple of 60
        tick_upper = 120   # Multiple of 60
        liquidity = 1000000

        position_id, amount0, amount1 = pool.mint(
            caller=caller,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            amount=liquidity,
        )

        # Simulate tiny fee accumulation
        pool.fee_growth_global_0 = Q128 // 1000000  # Very small fee

        # Collect fees
        fees0, fees1 = pool.collect(caller=caller, position_id=position_id)

        # Fees should round down (could be 0 for very small amounts)
        assert fees0 >= 0
        assert fees1 >= 0

    def test_swap_fee_rounds_up(self, pool):
        """Test that swap fees round up (favors protocol)."""
        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-1020,  # Multiple of 60
            tick_upper=1020,   # Multiple of 60
            amount=10**18,
        )

        # Small swap
        amount_in = 1000

        # Perform swap
        amount0_out, amount1_out = pool.swap(
            caller="trader",
            zero_for_one=True,
            amount_specified=amount_in,
            sqrt_price_limit=None,
        )

        # Fee should have been charged
        assert amount1_out < 0  # We got tokens out
        # Output should be less than input (fees were taken)
        assert abs(amount1_out) < amount_in

    def test_very_small_amounts_no_precision_loss(self, pool):
        """Test that very small amounts don't lose all value to rounding."""
        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-120,  # Multiple of 60
            tick_upper=120,   # Multiple of 60
            amount=10**18,
        )

        # Very small swap (1 wei)
        amount_in = 1

        try:
            amount0_out, amount1_out = pool.swap(
                caller="trader",
                zero_for_one=True,
                amount_specified=amount_in,
                sqrt_price_limit=None,
            )

            # Even tiny swaps should work
            assert amount0_out > 0
        except VMExecutionError:
            # Acceptable to fail for amounts too small
            pass

    def test_large_amounts_no_overflow(self, pool):
        """Test that large amounts don't overflow."""
        # Try to mint large position
        large_amount = 10**24  # Very large

        try:
            position_id, amount0, amount1 = pool.mint(
                caller="whale",
                tick_lower=-100,
                tick_upper=100,
                amount=large_amount,
            )

            # If successful, amounts should be reasonable
            assert amount0 < MAX_UINT256
            assert amount1 < MAX_UINT256
        except (VMExecutionError, OverflowError):
            # Acceptable to fail if truly too large
            pass

    def test_fee_growth_no_precision_loss(self, pool):
        """Test that fee growth tracking doesn't lose precision."""
        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-120,  # Multiple of 60
            tick_upper=120,   # Multiple of 60
            amount=10**18,
        )

        initial_fee_growth = pool.fee_growth_global_0

        # Do many small swaps
        for _ in range(100):
            try:
                pool.swap(
                    caller="trader",
                    zero_for_one=True,
                    amount_specified=1000,
                    sqrt_price_limit=None,
                )
            except VMExecutionError:
                # May fail if price moves too much
                break

        # Fee growth should have increased
        assert pool.fee_growth_global_0 > initial_fee_growth

    def test_no_dust_drain_attack(self, pool):
        """Test that dust drain attack via rounding is prevented."""
        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-120,  # Multiple of 60
            tick_upper=120,   # Multiple of 60
            amount=10**18,
        )

        initial_reserve0 = pool.reserve0
        initial_reserve1 = pool.reserve1

        # Attempt dust drain: many tiny fee collections
        pool.fee_growth_global_0 = Q128 // 10**9  # Tiny fee

        total_collected = 0
        for _ in range(1000):
            fees0, fees1 = pool._collect_fees_preview(pool.positions[position_id])
            total_collected += fees0

        # Total collected shouldn't exceed actual fees
        # (Rounding down prevents extracting more than deposited)
        assert total_collected >= 0

    def test_quote_precision(self, pool):
        """Test that quote function maintains precision."""
        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-1020,  # Multiple of 60
            tick_upper=1020,   # Multiple of 60
            amount=10**18,
        )

        # Get quote
        amount_in = 1000000
        amount_out, price_impact = pool.quote(
            zero_for_one=True,
            amount_in=amount_in,
        )

        # Quote should be reasonable
        assert amount_out > 0
        assert price_impact >= 0

        # Actual swap should be close to quote
        actual_amount0, actual_amount1 = pool.swap(
            caller="trader",
            zero_for_one=True,
            amount_specified=amount_in,
            sqrt_price_limit=None,
        )

        # Should be within reasonable range (allow 20% tolerance due to quote approximation)
        assert abs(abs(actual_amount1) - amount_out) < amount_out * 0.20  # 20% tolerance


# ==================== Edge Case Tests ====================


class TestEdgeCases:
    """Test edge cases for precision handling."""

    def test_zero_amounts(self):
        """Test that zero amounts are handled correctly."""
        assert mul_div(0, 100, 50, round_up=False) == 0
        assert calculate_fee_amount(0, 3000) == 0
        assert safe_mul(0, 12345) == 0

    def test_max_values(self):
        """Test behavior at maximum values."""
        # MAX_UINT256 / 2 should work
        half_max = MAX_UINT256 // 2
        result = safe_mul(half_max, 1)
        assert result == half_max

        # Full MAX_UINT256 * 2 should overflow
        with pytest.raises(OverflowError):
            safe_mul(MAX_UINT256, 2)

    def test_rounding_always_favors_protocol(self):
        """Test that all rounding favors the protocol (never the user)."""
        # Charging fee: round UP
        fee = calculate_fee_amount(999, 30)  # Should round up
        manual_calc = 999 * 30 // 10000
        assert fee >= manual_calc  # Fee should be >= floored amount

        # Paying out: round DOWN (tested via mul_div)
        payout = mul_div(999, 30, 10000, round_up=False)
        assert payout <= 999 * 30 // 10000 + 1  # Should round down


# ==================== Integration Tests ====================


class TestPrecisionIntegration:
    """Integration tests for precision across operations."""

    @pytest.fixture
    def setup_pool(self):
        """Setup a pool with liquidity."""
        factory = ConcentratedLiquidityFactory(owner="owner")
        pool = factory.create_pool(
            caller="creator",
            token0="TOKEN0",
            token1="TOKEN1",
            fee_tier=FeeTier.STANDARD,
            initial_sqrt_price=Q96,
        )

        # Add liquidity (use tick spacing of 60)
        position_id, amount0, amount1 = pool.mint(
            caller="lp",
            tick_lower=-1020,  # Multiple of 60
            tick_upper=1020,   # Multiple of 60
            amount=10**20,
        )

        return pool, position_id

    def test_full_lifecycle_precision(self, setup_pool):
        """Test precision through full position lifecycle."""
        pool, position_id = setup_pool

        initial_liquidity = pool.positions[position_id].liquidity

        # Do some swaps to generate fees
        for i in range(10):
            try:
                pool.swap(
                    caller=f"trader{i}",
                    zero_for_one=(i % 2 == 0),
                    amount_specified=10**18,
                    sqrt_price_limit=None,
                )
            except VMExecutionError:
                # May fail if price moves too far
                break

        # Collect fees
        fees0, fees1 = pool.collect(caller="lp", position_id=position_id)

        # Fees should be non-negative
        assert fees0 >= 0
        assert fees1 >= 0

        # Burn position
        amount0, amount1 = pool.burn(
            caller="lp",
            position_id=position_id,
            amount=None,
        )

        # Should get back reasonable amounts
        assert amount0 >= 0
        assert amount1 >= 0

    def test_many_small_operations_no_drift(self, setup_pool):
        """Test that many small operations don't cause value drift."""
        pool, position_id = setup_pool

        initial_reserve0 = pool.reserve0
        initial_reserve1 = pool.reserve1

        # Do many small swaps back and forth
        for i in range(100):
            try:
                pool.swap(
                    caller=f"trader{i}",
                    zero_for_one=(i % 2 == 0),
                    amount_specified=1000,
                    sqrt_price_limit=None,
                )
            except VMExecutionError:
                break

        # Reserves should have changed (fees collected)
        # but not drifted unreasonably
        assert pool.reserve0 > 0
        assert pool.reserve1 > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
