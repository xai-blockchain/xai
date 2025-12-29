"""
Property-based tests for AMM (Automated Market Maker) invariants.

These tests verify that the constant product formula (x * y = k) is
preserved across all operations on liquidity pools. The invariant
k = reserve_x * reserve_y must be non-decreasing after swaps
(increases due to fees).

Uses Hypothesis for property-based testing with random inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase

from xai.core.transactions.liquidity_pools import LiquidityPool, PoolPair
from xai.blockchain.slippage_limits import LiquidityPool as SlippageLimitPool


class TestCoreLiquidityPoolInvariants:
    """Property tests for core liquidity pool AMM invariants."""

    @given(
        xai_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=1000.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_swap_xai_for_other_preserves_k(self, xai_reserve, other_reserve, swap_amount):
        """Swapping XAI for other should preserve or increase k (due to fees)."""
        # Skip if swap amount is too large relative to reserves (would cause excessive slippage)
        assume(swap_amount < xai_reserve * 0.5)

        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0  # Arbitrary LP tokens

        k_before = pool.xai_reserve * pool.other_reserve

        result = pool.swap_xai_for_other(swap_amount, max_slippage_pct=50.0)

        if result["success"]:
            k_after = pool.xai_reserve * pool.other_reserve

            # k should be non-decreasing (fees make it slightly increase)
            assert k_after >= k_before * 0.9999, (
                f"Invariant violated: k decreased from {k_before} to {k_after}"
            )

    @given(
        xai_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=1000.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_swap_other_for_xai_preserves_k(self, xai_reserve, other_reserve, swap_amount):
        """Swapping other for XAI should preserve or increase k (due to fees)."""
        assume(swap_amount < other_reserve * 0.5)

        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0

        k_before = pool.xai_reserve * pool.other_reserve

        result = pool.swap_other_for_xai(swap_amount, max_slippage_pct=50.0)

        if result["success"]:
            k_after = pool.xai_reserve * pool.other_reserve
            assert k_after >= k_before * 0.9999, (
                f"Invariant violated: k decreased from {k_before} to {k_after}"
            )

    @given(
        xai_reserve=st.floats(min_value=1000.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=1000.0, max_value=1_000_000.0),
        xai_add=st.floats(min_value=1.0, max_value=10000.0),
        other_add=st.floats(min_value=1.0, max_value=10000.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_add_liquidity_preserves_ratio(self, xai_reserve, other_reserve, xai_add, other_add):
        """Adding liquidity should preserve the price ratio (for non-initial providers)."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0

        ratio_before = pool.other_reserve / pool.xai_reserve

        result = pool.add_liquidity("test_provider", xai_add, other_add)

        if result["success"]:
            ratio_after = pool.other_reserve / pool.xai_reserve

            # Ratio should be preserved within floating point tolerance
            assert abs(ratio_after - ratio_before) / ratio_before < 0.0001, (
                f"Ratio changed from {ratio_before} to {ratio_after}"
            )

    @given(
        xai_reserve=st.floats(min_value=1000.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=1000.0, max_value=1_000_000.0),
        withdrawal_pct=st.floats(min_value=0.01, max_value=0.99),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_remove_liquidity_preserves_ratio(self, xai_reserve, other_reserve, withdrawal_pct):
        """Removing liquidity should preserve the price ratio."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0
        pool.liquidity_providers["test_provider"] = 1000.0

        ratio_before = pool.other_reserve / pool.xai_reserve
        lp_to_remove = withdrawal_pct * pool.total_liquidity_tokens

        result = pool.remove_liquidity("test_provider", lp_to_remove)

        if result["success"] and pool.xai_reserve > 0:
            ratio_after = pool.other_reserve / pool.xai_reserve

            assert abs(ratio_after - ratio_before) / ratio_before < 0.0001, (
                f"Ratio changed from {ratio_before} to {ratio_after}"
            )

    @given(
        xai_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
    )
    @settings(max_examples=50, phases=[Phase.generate, Phase.target])
    def test_roundtrip_swap_loses_to_fees(self, xai_reserve, other_reserve):
        """Swapping XAI → other → XAI should result in less XAI due to fees."""
        assume(xai_reserve > 1000 and other_reserve > 1000)

        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0

        initial_xai = 10.0  # Small amount to minimize slippage effects

        # Swap XAI → other
        result1 = pool.swap_xai_for_other(initial_xai, max_slippage_pct=50.0)
        if not result1["success"]:
            return  # Skip if swap fails

        other_received = result1["output_other"]

        # Swap other → XAI
        result2 = pool.swap_other_for_xai(other_received, max_slippage_pct=50.0)
        if not result2["success"]:
            return  # Skip if swap fails

        final_xai = result2["output_xai"]

        # Should lose to fees (approximately 0.7% total for 0.35% each way)
        assert final_xai < initial_xai, (
            f"Roundtrip should lose to fees: started with {initial_xai}, got {final_xai}"
        )


class TestSlippageLimitPoolInvariants:
    """Property tests for slippage-limited liquidity pool."""

    @given(
        reserve_x=st.floats(min_value=1000.0, max_value=1_000_000.0),
        reserve_y=st.floats(min_value=100000.0, max_value=100_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_slippage_pool_swap_preserves_k(self, reserve_x, reserve_y, swap_amount):
        """Swaps should preserve or increase k in slippage-limited pool."""
        assume(swap_amount < reserve_x * 0.1)  # Keep swap small relative to reserves

        pool = SlippageLimitPool(
            token_x_reserve=reserve_x,
            token_y_reserve=reserve_y,
            pool_slippage_limit_percentage=10.0,  # Allow more slippage for testing
            max_trade_size=1000.0,
            price_impact_rejection_threshold_percentage=20.0,
        )

        k_before = pool.reserve_x * pool.reserve_y

        try:
            pool.swap(amount_in=swap_amount, token_in="X", min_amount_out=0.0)
            k_after = pool.reserve_x * pool.reserve_y

            # k should be preserved (no fees in this implementation)
            assert abs(k_after - k_before) / k_before < 0.0001, (
                f"Invariant violated: k changed from {k_before} to {k_after}"
            )
        except ValueError:
            # Expected for trades that exceed limits
            pass

    @given(
        reserve_x=st.floats(min_value=1000.0, max_value=1_000_000.0),
        reserve_y=st.floats(min_value=100000.0, max_value=100_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_slippage_pool_price_impact_bounded(self, reserve_x, reserve_y, swap_amount):
        """Price impact should be bounded by the configured threshold."""
        assume(swap_amount < reserve_x * 0.05)

        threshold = 5.0  # 5% max price impact

        pool = SlippageLimitPool(
            token_x_reserve=reserve_x,
            token_y_reserve=reserve_y,
            pool_slippage_limit_percentage=10.0,
            max_trade_size=1000.0,
            price_impact_rejection_threshold_percentage=threshold,
        )

        price_before = reserve_y / reserve_x

        try:
            pool.swap(amount_in=swap_amount, token_in="X", min_amount_out=0.0)
            price_after = pool.reserve_y / pool.reserve_x

            price_impact = abs(price_after - price_before) / price_before * 100

            # If swap succeeded, price impact should be below threshold
            assert price_impact <= threshold + 0.1, (
                f"Price impact {price_impact}% exceeds threshold {threshold}%"
            )
        except ValueError:
            # Expected for trades that exceed limits
            pass


class TestAMMOutputBounds:
    """Test that AMM outputs are always bounded correctly."""

    @given(
        xai_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=10000.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_output_never_exceeds_reserve(self, xai_reserve, other_reserve, swap_amount):
        """Output of a swap should never exceed the output reserve."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0

        result = pool.swap_xai_for_other(swap_amount, max_slippage_pct=100.0)

        if result["success"]:
            output = result["output_other"]
            # Output should never exceed original reserve
            assert output < other_reserve, (
                f"Output {output} >= original reserve {other_reserve}"
            )

    @given(
        xai_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        other_reserve=st.floats(min_value=100.0, max_value=1_000_000.0),
        swap_amount=st.floats(min_value=0.1, max_value=10000.0),
    )
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_reserves_always_positive(self, xai_reserve, other_reserve, swap_amount):
        """Reserves should always remain positive after operations."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)
        pool.xai_reserve = xai_reserve
        pool.other_reserve = other_reserve
        pool.total_liquidity_tokens = 1000.0

        pool.swap_xai_for_other(swap_amount, max_slippage_pct=100.0)

        assert pool.xai_reserve > 0, "XAI reserve went non-positive"
        assert pool.other_reserve > 0, "Other reserve went non-positive"


class TestLPTokenInvariants:
    """Test LP token supply invariants."""

    @given(
        initial_xai=st.floats(min_value=100.0, max_value=100000.0),
        initial_other=st.floats(min_value=100.0, max_value=100000.0),
    )
    @settings(max_examples=50, phases=[Phase.generate, Phase.target])
    def test_initial_lp_tokens_geometric_mean(self, initial_xai, initial_other):
        """Initial LP tokens should equal geometric mean of deposits."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)

        result = pool.add_liquidity("provider1", initial_xai, initial_other)

        assert result["success"]
        expected_lp = (initial_xai * initial_other) ** 0.5
        actual_lp = result["lp_tokens"]

        assert abs(actual_lp - expected_lp) / expected_lp < 0.0001, (
            f"LP tokens {actual_lp} != geometric mean {expected_lp}"
        )

    @given(
        initial_xai=st.floats(min_value=1000.0, max_value=100000.0),
        initial_other=st.floats(min_value=1000.0, max_value=100000.0),
    )
    @settings(max_examples=50, phases=[Phase.generate, Phase.target])
    def test_lp_tokens_conserved_on_withdrawal(self, initial_xai, initial_other):
        """LP tokens burned should equal LP tokens held before full withdrawal."""
        pool = LiquidityPool(PoolPair.XAI_USDT, fee_percentage=0.003)

        add_result = pool.add_liquidity("provider1", initial_xai, initial_other)
        assert add_result["success"]

        lp_tokens = add_result["lp_tokens"]

        remove_result = pool.remove_liquidity("provider1", lp_tokens)

        assert remove_result["success"]
        assert remove_result["lp_tokens_burned"] == lp_tokens
        assert pool.total_liquidity_tokens == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
