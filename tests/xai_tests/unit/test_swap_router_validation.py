"""
Comprehensive tests for SwapRouter input validation and safe math.

Tests cover:
- Input validation for swap functions
- Token and amount validation
- Integer overflow protection
- Safe math operations
- Limit order validation
"""

import pytest
import time
from xai.core.defi.swap_router import (
    SwapRouter,
    PoolInfo,
    LimitOrder,
    OrderStatus,
)
from xai.core.vm.exceptions import VMExecutionError


class TestSwapRouterInputValidation:
    """Tests for swap router input validation."""

    @pytest.fixture
    def router(self):
        """Create a router with test pools."""
        router = SwapRouter(
            owner="0xowner123",
            chain_id=1,
        )
        # Register test pools
        router.register_pool("pool1", "ETH", "USDC", fee=30)
        router.update_pool_reserves("pool1", 1000000, 2000000000)  # ETH/USDC

        router.register_pool("pool2", "USDC", "DAI", fee=10)
        router.update_pool_reserves("pool2", 1000000000, 1000000000)  # USDC/DAI

        return router

    def test_swap_validates_empty_caller(self, router):
        """Test that empty caller address is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Invalid caller"):
            router.swap_exact_input(
                caller="",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_whitespace_caller(self, router):
        """Test that whitespace-only caller is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Invalid caller"):
            router.swap_exact_input(
                caller="   ",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_empty_token_in(self, router):
        """Test that empty input token is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Invalid input token"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_empty_token_out(self, router):
        """Test that empty output token is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Invalid output token"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_same_token(self, router):
        """Test that swapping token to itself is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Cannot swap token to itself"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="ETH",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_zero_amount(self, router):
        """Test that zero input amount is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="must be positive"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=0,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_negative_amount(self, router):
        """Test that negative input amount is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="must be positive"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=-1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_max_amount(self, router):
        """Test that amount exceeding maximum is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="exceeds maximum"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=2**200,  # Way over max
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_validates_negative_min_output(self, router):
        """Test that negative minimum output is rejected."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="cannot be negative"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=-100,
                deadline=deadline,
            )

    def test_swap_validates_expired_deadline(self, router):
        """Test that expired deadline is rejected."""
        deadline = time.time() - 3600  # In the past

        with pytest.raises(VMExecutionError, match="expired"):
            router.swap_exact_input(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=0,
                deadline=deadline,
            )

    def test_swap_exact_output_validation(self, router):
        """Test validation for swap_exact_output."""
        deadline = time.time() + 3600

        with pytest.raises(VMExecutionError, match="Invalid caller"):
            router.swap_exact_output(
                caller="",
                token_in="ETH",
                token_out="USDC",
                amount_out=1000,
                max_amount_in=10000,
                deadline=deadline,
            )


class TestLimitOrderValidation:
    """Tests for limit order input validation."""

    @pytest.fixture
    def router(self):
        """Create a router."""
        return SwapRouter(owner="0xowner123", chain_id=1)

    def test_limit_order_validates_empty_caller(self, router):
        """Test that empty caller is rejected."""
        future_expiry = int(time.time()) + 3600

        with pytest.raises(VMExecutionError, match="Invalid caller"):
            router.create_limit_order(
                caller="",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=2000,
                expiry=future_expiry,
                signature=b"x" * 64,
            )

    def test_limit_order_validates_zero_min_output(self, router):
        """Test that zero minimum output is rejected for limit orders."""
        future_expiry = int(time.time()) + 3600

        with pytest.raises(VMExecutionError, match="positive minimum output"):
            router.create_limit_order(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=0,
                expiry=future_expiry,
                signature=b"x" * 64,
            )

    def test_limit_order_validates_past_expiry(self, router):
        """Test that past expiry is rejected."""
        past_expiry = int(time.time()) - 3600

        with pytest.raises(VMExecutionError, match="must be in the future"):
            router.create_limit_order(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=2000,
                expiry=past_expiry,
                signature=b"x" * 64,
            )

    def test_limit_order_validates_far_future_expiry(self, router):
        """Test that expiry too far in future is rejected."""
        # More than 1 year in the future
        far_expiry = int(time.time()) + (400 * 24 * 60 * 60)

        with pytest.raises(VMExecutionError, match="too far in the future"):
            router.create_limit_order(
                caller="0xcaller",
                token_in="ETH",
                token_out="USDC",
                amount_in=1000,
                min_amount_out=2000,
                expiry=far_expiry,
                signature=b"x" * 64,
            )


class TestFillLimitOrderValidation:
    """Tests for limit order fill validation and safe math."""

    @pytest.fixture
    def router_with_order(self):
        """Create router with a valid order for filling."""
        router = SwapRouter(owner="0xowner123", chain_id=1)

        # Manually create an order to bypass signature verification
        order = LimitOrder(
            id="order123",
            maker="0xmaker",
            token_in="ETH",
            token_out="USDC",
            amount_in=1000,
            min_amount_out=2000,
            expiry=int(time.time()) + 3600,
            nonce=0,
            signature=b"x" * 64,
            status=OrderStatus.OPEN,
        )
        router.orders[order.id] = order

        return router, order.id

    def test_fill_validates_empty_caller(self, router_with_order):
        """Test that empty caller is rejected for fill."""
        router, order_id = router_with_order

        with pytest.raises(VMExecutionError, match="Invalid caller"):
            router.fill_limit_order(caller="", order_id=order_id)

    def test_fill_validates_nonexistent_order(self, router_with_order):
        """Test that nonexistent order is rejected."""
        router, _ = router_with_order

        with pytest.raises(VMExecutionError, match="not found"):
            router.fill_limit_order(caller="0xfiller", order_id="nonexistent")

    def test_fill_validates_zero_amount(self, router_with_order):
        """Test that zero fill amount is rejected."""
        router, order_id = router_with_order

        with pytest.raises(VMExecutionError, match="must be positive"):
            router.fill_limit_order(
                caller="0xfiller",
                order_id=order_id,
                amount_to_fill=0,
            )

    def test_fill_validates_negative_amount(self, router_with_order):
        """Test that negative fill amount is rejected."""
        router, order_id = router_with_order

        with pytest.raises(VMExecutionError, match="must be positive"):
            router.fill_limit_order(
                caller="0xfiller",
                order_id=order_id,
                amount_to_fill=-100,
            )

    def test_fill_validates_excessive_amount(self, router_with_order):
        """Test that fill amount exceeding max is rejected."""
        router, order_id = router_with_order

        with pytest.raises(VMExecutionError, match="exceeds maximum"):
            router.fill_limit_order(
                caller="0xfiller",
                order_id=order_id,
                amount_to_fill=2**200,
            )

    def test_fill_expired_order(self, router_with_order):
        """Test that filling expired order is rejected."""
        router, order_id = router_with_order

        # Manually expire the order
        router.orders[order_id].expiry = int(time.time()) - 100

        with pytest.raises(VMExecutionError, match="expired"):
            router.fill_limit_order(caller="0xfiller", order_id=order_id)


class TestSafeMath:
    """Tests for safe math operations."""

    @pytest.fixture
    def router(self):
        """Create router for safe math testing."""
        return SwapRouter()

    def test_safe_add_normal(self, router):
        """Test safe add with normal values."""
        assert router._safe_add(100, 200) == 300

    def test_safe_add_overflow(self, router):
        """Test safe add detects overflow."""
        with pytest.raises(VMExecutionError, match="overflow"):
            router._safe_add(2**128, 2**128)

    def test_safe_sub_normal(self, router):
        """Test safe sub with normal values."""
        assert router._safe_sub(300, 100) == 200

    def test_safe_sub_underflow(self, router):
        """Test safe sub detects underflow."""
        with pytest.raises(VMExecutionError, match="underflow"):
            router._safe_sub(100, 200)

    def test_safe_mul_normal(self, router):
        """Test safe mul with normal values."""
        assert router._safe_mul(100, 200) == 20000

    def test_safe_mul_zero(self, router):
        """Test safe mul with zero."""
        assert router._safe_mul(0, 1000000) == 0
        assert router._safe_mul(1000000, 0) == 0

    def test_safe_mul_overflow(self, router):
        """Test safe mul detects overflow."""
        with pytest.raises(VMExecutionError, match="overflow"):
            router._safe_mul(2**128, 2)

    def test_safe_mul_div_normal(self, router):
        """Test safe mul_div with normal values."""
        # (100 * 200) / 50 = 400
        assert router._safe_mul_div(100, 200, 50) == 400

    def test_safe_mul_div_division_by_zero(self, router):
        """Test safe mul_div rejects division by zero."""
        with pytest.raises(VMExecutionError, match="Division by zero"):
            router._safe_mul_div(100, 200, 0)

    def test_safe_mul_div_zero_operand(self, router):
        """Test safe mul_div with zero operand."""
        assert router._safe_mul_div(0, 200, 50) == 0
        assert router._safe_mul_div(100, 0, 50) == 0

    def test_safe_mul_div_large_values(self, router):
        """Test safe mul_div handles large intermediate values."""
        # (10^20 * 10^20) / 10^20 = 10^20
        large = 10**20
        result = router._safe_mul_div(large, large, large)
        assert result == large

    def test_safe_mul_div_precision(self, router):
        """Test safe mul_div maintains precision."""
        # This is a typical DeFi calculation
        # (amount * price) / scale
        amount = 1_000_000_000_000  # 1 trillion wei
        price = 2_000_000_000_000  # 2 trillion
        scale = 1_000_000_000_000  # 1 trillion scale

        result = router._safe_mul_div(amount, price, scale)
        assert result == 2_000_000_000_000


class TestLimitOrderSafeMath:
    """Tests for safe math in limit order filling."""

    @pytest.fixture
    def router_with_large_order(self):
        """Create router with order using large values."""
        router = SwapRouter(owner="0xowner123", chain_id=1)

        # Create order with large but valid values
        order = LimitOrder(
            id="large_order",
            maker="0xmaker",
            token_in="ETH",
            token_out="USDC",
            amount_in=10**18,  # 1 ETH in wei
            min_amount_out=2 * 10**18,  # 2000 USDC in wei (1:2 ratio)
            expiry=int(time.time()) + 3600,
            nonce=0,
            signature=b"x" * 64,
            status=OrderStatus.OPEN,
        )
        router.orders[order.id] = order

        return router, order.id

    def test_fill_large_order_calculates_output_correctly(self, router_with_large_order):
        """Test that output is calculated correctly for large orders."""
        router, order_id = router_with_large_order

        # Fill half the order
        fill_amount = 5 * 10**17  # 0.5 ETH
        amount_filled, amount_out = router.fill_limit_order(
            caller="0xfiller",
            order_id=order_id,
            amount_to_fill=fill_amount,
        )

        # At 1:2 ratio, 0.5 ETH should give 1 USDC worth
        expected_output = 10**18  # (0.5 * 2) = 1
        assert amount_out == expected_output
        assert amount_filled == fill_amount

    def test_fill_order_with_precise_ratio(self, router_with_large_order):
        """Test precise ratio calculation doesn't overflow."""
        router, _ = router_with_large_order

        # Create an order with a precise ratio
        order = LimitOrder(
            id="precise_order",
            maker="0xmaker",
            token_in="TOKEN_A",
            token_out="TOKEN_B",
            amount_in=3 * 10**18,  # 3 tokens
            min_amount_out=7 * 10**18,  # 7 tokens (3:7 ratio)
            expiry=int(time.time()) + 3600,
            nonce=1,
            signature=b"x" * 64,
            status=OrderStatus.OPEN,
        )
        router.orders[order.id] = order

        # Fill 1.5 tokens
        fill_amount = 15 * 10**17
        amount_filled, amount_out = router.fill_limit_order(
            caller="0xfiller",
            order_id=order.id,
            amount_to_fill=fill_amount,
        )

        # (1.5 * 7) / 3 = 3.5 tokens
        expected_output = 35 * 10**17
        assert amount_out == expected_output


class TestSuccessfulSwap:
    """Tests for successful swaps with valid inputs."""

    @pytest.fixture
    def router(self):
        """Create router with liquidity."""
        router = SwapRouter(owner="0xowner123", chain_id=1)
        router.register_pool("pool1", "ETH", "USDC", fee=30)
        router.update_pool_reserves("pool1", 1_000_000, 2_000_000_000)
        return router

    def test_successful_swap_with_valid_inputs(self, router):
        """Test a successful swap with all valid inputs."""
        deadline = time.time() + 3600

        output = router.swap_exact_input(
            caller="0xcaller123",
            token_in="ETH",
            token_out="USDC",
            amount_in=1000,
            min_amount_out=0,
            deadline=deadline,
        )

        assert output > 0
        assert router.total_swaps == 1
