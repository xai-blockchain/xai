from typing import Dict, Any


class LiquidityPool:
    def __init__(
        self,
        token_x_reserve: float,
        token_y_reserve: float,
        pool_slippage_limit_percentage: float = 0.5,
        max_trade_size: float = float("inf"),
        price_impact_rejection_threshold_percentage: float = 2.0,
    ):  # Default 2%
        if not isinstance(token_x_reserve, (int, float)) or token_x_reserve <= 0:
            raise ValueError("Token X reserve must be a positive number.")
        if not isinstance(token_y_reserve, (int, float)) or token_y_reserve <= 0:
            raise ValueError("Token Y reserve must be a positive number.")
        if not isinstance(pool_slippage_limit_percentage, (int, float)) or not (
            0 <= pool_slippage_limit_percentage < 100
        ):
            raise ValueError(
                "Pool slippage limit percentage must be between 0 and 100 (exclusive of 100)."
            )
        if not isinstance(max_trade_size, (int, float)) or max_trade_size <= 0:
            raise ValueError("Max trade size must be a positive number.")
        if not isinstance(price_impact_rejection_threshold_percentage, (int, float)) or not (
            0 <= price_impact_rejection_threshold_percentage < 100
        ):
            raise ValueError(
                "Price impact rejection threshold must be between 0 and 100 (exclusive of 100)."
            )

        self.reserve_x = token_x_reserve
        self.reserve_y = token_y_reserve
        self.k = self.reserve_x * self.reserve_y  # Constant product
        self.pool_slippage_limit_percentage = pool_slippage_limit_percentage
        self.max_trade_size = max_trade_size
        self.price_impact_rejection_threshold_percentage = (
            price_impact_rejection_threshold_percentage
        )

    def get_expected_output(self, amount_in: float, token_in: str) -> float:
        """
        Calculates the expected output amount for a swap based on the constant product formula.
        """
        if amount_in <= 0:
            raise ValueError("Amount in must be positive.")

        if token_in == "X":
            new_reserve_x = self.reserve_x + amount_in
            expected_output = self.reserve_y - (self.k / new_reserve_x)
        elif token_in == "Y":
            new_reserve_y = self.reserve_y + amount_in
            expected_output = self.reserve_x - (self.k / new_reserve_y)
        else:
            raise ValueError("Invalid token_in. Must be 'X' or 'Y'.")

        return expected_output

    def calculate_price_impact(self, amount_in: float, token_in: str) -> float:
        """
        Calculates the estimated price impact of a trade.
        Returns the price impact as a percentage.
        """
        if amount_in <= 0:
            return 0.0

        initial_price = (
            self.reserve_y / self.reserve_x if token_in == "X" else self.reserve_x / self.reserve_y
        )

        # Simulate the trade to find the new price
        if token_in == "X":
            new_reserve_x = self.reserve_x + amount_in
            new_reserve_y = self.k / new_reserve_x
            final_price = new_reserve_y / new_reserve_x
        else:  # token_in == "Y"
            new_reserve_y = self.reserve_y + amount_in
            new_reserve_x = self.k / new_reserve_y
            final_price = new_reserve_x / new_reserve_y

        price_impact_percentage = abs((final_price - initial_price) / initial_price) * 100
        return price_impact_percentage

    def swap(self, amount_in: float, token_in: str, min_amount_out: float = 0.0) -> float:
        """
        Executes a swap, enforcing pool-specific and user-defined slippage limits,
        maximum trade size caps, and price impact rejection thresholds.
        Returns the actual amount out.
        """
        if amount_in <= 0:
            raise ValueError("Amount in must be positive.")
        if min_amount_out < 0:
            raise ValueError("Minimum amount out cannot be negative.")

        # Check maximum trade size cap
        if amount_in > self.max_trade_size:
            raise ValueError(
                f"Swap failed: Amount in {amount_in:.4f} exceeds maximum allowed trade size of {self.max_trade_size:.4f}."
            )

        # New: Check price impact rejection threshold
        price_impact = self.calculate_price_impact(amount_in, token_in)
        if price_impact > self.price_impact_rejection_threshold_percentage:
            raise ValueError(
                f"Swap failed: Price impact {price_impact:.2f}% exceeds rejection threshold of {self.price_impact_rejection_threshold_percentage:.2f}%."
            )

        expected_output = self.get_expected_output(amount_in, token_in)

        # Calculate actual output after simulating a small price movement or fee
        # For simplicity, let's assume a small fixed fee or impact for actual output
        actual_output_raw = expected_output * 0.999  # Simulate 0.1% fee/impact

        # Check user-defined slippage limit (min_amount_out)
        if actual_output_raw < min_amount_out:
            raise ValueError(
                f"Swap failed: Actual output {actual_output_raw:.4f} is less than user's minimum acceptable output {min_amount_out:.4f}."
            )

        # Check pool-specific slippage limit
        slippage_percentage = ((expected_output - actual_output_raw) / expected_output) * 100
        if slippage_percentage > self.pool_slippage_limit_percentage:
            raise ValueError(
                f"Swap failed: Slippage {slippage_percentage:.2f}% exceeds pool's limit of {self.pool_slippage_limit_percentage:.2f}%."
            )

        # Simulate updating reserves
        if token_in == "X":
            self.reserve_x += amount_in
            self.reserve_y -= actual_output_raw
        else:  # token_in == "Y"
            self.reserve_y += amount_in
            self.reserve_x -= actual_output_raw

        self.k = self.reserve_x * self.reserve_y  # Update k (should remain constant in ideal AMM)
        print(
            f"Swap successful: {amount_in:.4f} {token_in} for {actual_output_raw:.4f} {('Y' if token_in == 'X' else 'X')}. "
            f"Slippage: {slippage_percentage:.2f}%. New reserves: X={self.reserve_x:.4f}, Y={self.reserve_y:.4f}"
        )
        return actual_output_raw


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Create a liquidity pool with 1000 ETH and 1,000,000 USDC
    pool = LiquidityPool(
        token_x_reserve=1000.0,
        token_y_reserve=1000000.0,
        pool_slippage_limit_percentage=1.0,
        max_trade_size=100.0,
        price_impact_rejection_threshold_percentage=1.5,
    )  # 1.5% price impact limit

    print("--- Initial Pool State ---")
    print(f"Reserves: X={pool.reserve_x}, Y={pool.reserve_y}, K={pool.k}")
    print(f"Pool Slippage Limit: {pool.pool_slippage_limit_percentage}%")
    print(f"Max Trade Size: {pool.max_trade_size}")
    print(f"Price Impact Rejection Threshold: {pool.price_impact_rejection_threshold_percentage}%")

    print("\n--- Scenario 1: Small Swap (within limits) ---")
    try:
        # User wants to swap 1 ETH for at least 990 USDC (0.1% user slippage tolerance)
        pool.swap(amount_in=1.0, token_in="X", min_amount_out=990.0)
    except ValueError as e:
        print(f"Error: {e}")
    print(f"Current Reserves: X={pool.reserve_x:.4f}, Y={pool.reserve_y:.4f}")

    print("\n--- Scenario 2: Swap exceeding user's min_amount_out ---")
    try:
        # User wants to swap 1 ETH for at least 1000 USDC (too high expectation)
        pool.swap(amount_in=1.0, token_in="X", min_amount_out=1000.0)
    except ValueError as e:
        print(f"Error: {e}")
    print(f"Current Reserves: X={pool.reserve_x:.4f}, Y={pool.reserve_y:.4f}")

    print("\n--- Scenario 3: Large Swap exceeding pool's slippage limit ---")
    try:
        # Simulate a very large swap that would cause high slippage
        # Reset pool for this test
        pool_large_swap_test = LiquidityPool(
            token_x_reserve=1000.0,
            token_y_reserve=1000000.0,
            pool_slippage_limit_percentage=0.5,
            max_trade_size=100.0,
            price_impact_rejection_threshold_percentage=1.5,
        )
        pool_large_swap_test.swap(amount_in=50.0, token_in="X", min_amount_out=0.0)  # Swap 50 ETH
    except ValueError as e:
        print(f"Error: {e}")
    print(
        f"Current Reserves (large swap test): X={pool_large_swap_test.reserve_x:.4f}, Y={pool_large_swap_test.reserve_y:.4f}"
    )

    print("\n--- Scenario 4: Swap exceeding maximum trade size ---")
    try:
        pool.swap(
            amount_in=150.0, token_in="X", min_amount_out=0.0
        )  # Try to swap 150 ETH (max is 100)
    except ValueError as e:
        print(f"Error: {e}")
    print(f"Current Reserves: X={pool.reserve_x:.4f}, Y={pool.reserve_y:.4f}")

    print("\n--- Scenario 5: Swap exceeding price impact rejection threshold ---")
    try:
        # Reset pool for this test
        pool_price_impact_test = LiquidityPool(
            token_x_reserve=1000.0,
            token_y_reserve=1000000.0,
            pool_slippage_limit_percentage=1.0,
            max_trade_size=100.0,
            price_impact_rejection_threshold_percentage=0.1,
        )  # Very low threshold
        pool_price_impact_test.swap(
            amount_in=50.0, token_in="X", min_amount_out=0.0
        )  # This should exceed 0.1% impact
    except ValueError as e:
        print(f"Error: {e}")
    print(
        f"Current Reserves (price impact test): X={pool_price_impact_test.reserve_x:.4f}, Y={pool_price_impact_test.reserve_y:.4f}"
    )
