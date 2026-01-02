"""
Concentrated Liquidity Pool Implementation (Uniswap V3 Style).

Provides capital-efficient liquidity provision through:
- Price range positions
- Tick-based price representation
- Concentrated liquidity with higher capital efficiency
- NFT-based LP position tracking
- Fee tier selection

Security features:
- Tick spacing validation
- Position bounds checking
- Reentrancy protection
- Precision handling for sqrt prices
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ..vm.exceptions import VMExecutionError
from .safe_math import (
    MAX_UINT256,
)
from .safe_math import Q96 as SAFE_Q96
from .safe_math import Q128 as SAFE_Q128
from .safe_math import (
    RAY,
    WAD,
    SafeMath,
)

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)

# Constants
MIN_TICK = -887272
MAX_TICK = 887272
MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

# Q96 fixed point (2^96) for sqrt price representation
Q96 = SAFE_Q96
Q128 = SAFE_Q128

# Precision for liquidity calculations
LIQUIDITY_PRECISION = 10**18

# ==================== Fixed-Point Arithmetic (Using SafeMath) ====================

# Import SafeMath functions for compatibility with existing code
safe_mul = SafeMath.safe_mul
wad_mul = SafeMath.wad_mul
wad_div = SafeMath.wad_div
ray_mul = SafeMath.ray_mul
ray_div = SafeMath.ray_div

def mul_div(a: int, b: int, denominator: int, round_up: bool = False) -> int:
    """
    Calculate (a * b) / denominator with full precision and controlled rounding.

    This is critical for preventing precision loss in financial calculations.

    Args:
        a: First multiplicand
        b: Second multiplicand
        denominator: Divisor
        round_up: If True, round up (for charging users)
                  If False, round down (for paying users)

    Returns:
        Result of (a * b) / denominator

    Raises:
        ValueError: If denominator is zero
        OverflowError: If calculation overflows
    """
    if denominator == 0:
        raise ValueError("Division by zero")

    result = safe_mul(a, b)

    if round_up:
        return (result + denominator - 1) // denominator
    return result // denominator

def calculate_fee_amount(amount: int, fee_bps: int) -> int:
    """
    Calculate fee amount from basis points, always rounding UP.

    This ensures the protocol never loses fees due to rounding.

    Args:
        amount: Input amount
        fee_bps: Fee in basis points (e.g., 3000 = 0.30%)

    Returns:
        Fee amount (rounded up)
    """
    # fee = amount * fee_bps / 10000, rounded up
    return mul_div(amount, fee_bps, 10000, round_up=True)

class FeeTier(Enum):
    """Available fee tiers with corresponding tick spacing."""
    LOW = (100, 1)      # 0.01% fee, 1 tick spacing
    MEDIUM = (500, 10)   # 0.05% fee, 10 tick spacing
    STANDARD = (3000, 60)  # 0.30% fee, 60 tick spacing
    HIGH = (10000, 200)   # 1.00% fee, 200 tick spacing

    def __init__(self, fee: int, tick_spacing: int):
        self.fee = fee  # In basis points (10000 = 100%)
        self.tick_spacing = tick_spacing

@dataclass
class TickInfo:
    """Information stored for each initialized tick."""
    liquidity_gross: int = 0  # Total liquidity referencing this tick
    liquidity_net: int = 0    # Net liquidity change when crossing tick
    fee_growth_outside_0: int = 0  # Fee growth outside range (token 0)
    fee_growth_outside_1: int = 0  # Fee growth outside range (token 1)
    initialized: bool = False

@dataclass
class Position:
    """
    Liquidity position within a price range.

    Represents LP's share of liquidity between two ticks.
    """

    id: int = 0
    owner: str = ""

    # Range (in ticks)
    tick_lower: int = 0
    tick_upper: int = 0

    # Liquidity amount
    liquidity: int = 0

    # Fee tracking
    fee_growth_inside_0_last: int = 0
    fee_growth_inside_1_last: int = 0
    tokens_owed_0: int = 0
    tokens_owed_1: int = 0

    # Timestamps
    created_at: float = field(default_factory=time.time)

    def is_in_range(self, current_tick: int) -> bool:
        """Check if current price is within position's range."""
        return self.tick_lower <= current_tick < self.tick_upper

@dataclass
class ConcentratedLiquidityPool:
    """
    Uniswap V3-style concentrated liquidity pool.

    Key features:
    - LPs provide liquidity in specific price ranges
    - Capital efficiency increases within range
    - Swap fees accumulate only while in range
    - Multiple fee tiers available

    Price representation:
    - Uses sqrt price (Q64.96 format) for precision
    - Ticks represent discretized price points
    - tick = log1.0001(price)
    """

    address: str = ""
    token0: str = ""
    token1: str = ""
    fee_tier: FeeTier = FeeTier.STANDARD

    # Current state
    sqrt_price: int = 0  # Q64.96 format
    tick: int = 0
    liquidity: int = 0  # Active liquidity

    # Fee tracking
    fee_growth_global_0: int = 0  # Q128.128
    fee_growth_global_1: int = 0
    protocol_fees_0: int = 0
    protocol_fees_1: int = 0

    # Tick data
    ticks: dict[int, TickInfo] = field(default_factory=dict)
    tick_bitmap: dict[int, int] = field(default_factory=dict)

    # Positions
    positions: dict[int, Position] = field(default_factory=dict)
    next_position_id: int = 1

    # Reserves (for reference, actual amounts calculated from positions)
    reserve0: int = 0
    reserve1: int = 0

    # Reentrancy guard
    _locked: bool = False

    def __post_init__(self) -> None:
        """Initialize pool."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"clp:{self.token0}:{self.token1}:{self.fee_tier.fee}:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Price Utilities ====================

    @staticmethod
    def tick_to_sqrt_price(tick: int) -> int:
        """
        Convert tick to sqrt price in Q64.96 format.

        sqrt_price = 1.0001^(tick/2) * 2^96
        """
        abs_tick = abs(tick)

        # Use precomputed powers for efficiency
        ratio = Q96

        if abs_tick & 0x1:
            ratio = (ratio * 340265354078544963557816517032075149313) >> 128
        if abs_tick & 0x2:
            ratio = (ratio * 340248342086729790484326174814286782778) >> 128
        if abs_tick & 0x4:
            ratio = (ratio * 340214320654664324051920982716015181260) >> 128
        if abs_tick & 0x8:
            ratio = (ratio * 340146287995602323631171512101879684304) >> 128
        if abs_tick & 0x10:
            ratio = (ratio * 340010263488231146823593991679159461444) >> 128
        if abs_tick & 0x20:
            ratio = (ratio * 339738377640345403697157401104375502016) >> 128
        if abs_tick & 0x40:
            ratio = (ratio * 339195258003219555707034227454543997025) >> 128
        if abs_tick & 0x80:
            ratio = (ratio * 338111622100601834656805679988414885971) >> 128
        if abs_tick & 0x100:
            ratio = (ratio * 335954724994790223023589805789778977700) >> 128
        if abs_tick & 0x200:
            ratio = (ratio * 331682121138379247127172139078559817300) >> 128
        if abs_tick & 0x400:
            ratio = (ratio * 323299236684853023288211250268160618739) >> 128
        if abs_tick & 0x800:
            ratio = (ratio * 307163716377032989948697243942600083929) >> 128
        if abs_tick & 0x1000:
            ratio = (ratio * 277268403626896220162999269216087595045) >> 128
        if abs_tick & 0x2000:
            ratio = (ratio * 225923453940442621947126027127485391333) >> 128
        if abs_tick & 0x4000:
            ratio = (ratio * 149997214084966997727330242082538205943) >> 128
        if abs_tick & 0x8000:
            ratio = (ratio * 66119101136024775622716233608466517926) >> 128
        if abs_tick & 0x10000:
            ratio = (ratio * 12847376061809297530290974190478138313) >> 128

        if tick > 0:
            # Invert ratio for positive ticks
            # This is a special case where we need exact Uniswap V3 behavior
            # Using standard division here matches the reference implementation
            ratio = (2**256 - 1) // ratio

        return ratio

    @staticmethod
    def sqrt_price_to_tick(sqrt_price: int) -> int:
        """
        Convert sqrt price to tick.

        tick = floor(log_1.0001(sqrt_price^2))
        """
        if sqrt_price < MIN_SQRT_RATIO or sqrt_price > MAX_SQRT_RATIO:
            raise VMExecutionError("Sqrt price out of range")

        # Approximate using binary search
        low, high = MIN_TICK, MAX_TICK

        while low < high:
            mid = (low + high + 1) // 2
            mid_sqrt = ConcentratedLiquidityPool.tick_to_sqrt_price(mid)

            if mid_sqrt <= sqrt_price:
                low = mid
            else:
                high = mid - 1

        return low

    @staticmethod
    def tick_to_price(tick: int) -> float:
        """Convert tick to actual price (for display)."""
        return 1.0001 ** tick

    @staticmethod
    def price_to_tick(price: float) -> int:
        """Convert price to nearest tick."""
        if price <= 0:
            raise VMExecutionError("Price must be positive")
        return int(math.log(price) / math.log(1.0001))

    # ==================== Position Management ====================

    def mint(
        self,
        caller: str,
        tick_lower: int,
        tick_upper: int,
        amount: int,
    ) -> tuple[int, int, int]:
        """
        Mint a new liquidity position.

        Args:
            caller: Position owner
            tick_lower: Lower tick of range
            tick_upper: Upper tick of range
            amount: Liquidity amount

        Returns:
            (position_id, amount0, amount1) - tokens required
        """
        self._require_not_locked()

        try:
            self._locked = True

            # Validate ticks
            self._validate_ticks(tick_lower, tick_upper)

            # Calculate amounts needed
            amount0, amount1 = self._calculate_amounts_for_liquidity(
                tick_lower, tick_upper, amount, add=True
            )

            # Create position
            position_id = self.next_position_id
            self.next_position_id += 1

            position = Position(
                id=position_id,
                owner=caller,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                liquidity=amount,
                fee_growth_inside_0_last=self._get_fee_growth_inside(tick_lower, tick_upper, 0),
                fee_growth_inside_1_last=self._get_fee_growth_inside(tick_lower, tick_upper, 1),
            )
            self.positions[position_id] = position

            # Update tick state
            self._update_tick(tick_lower, amount, True)
            self._update_tick(tick_upper, amount, False)

            # Update pool liquidity if in range
            if tick_lower <= self.tick < tick_upper:
                self.liquidity += amount

            # Update reserves
            self.reserve0 += amount0
            self.reserve1 += amount1

            logger.info(
                "Position minted",
                extra={
                    "event": "clp.mint",
                    "pool": self.address[:10],
                    "position_id": position_id,
                    "range": f"[{tick_lower}, {tick_upper}]",
                    "liquidity": amount,
                }
            )

            return position_id, amount0, amount1

        finally:
            self._locked = False

    def burn(
        self,
        caller: str,
        position_id: int,
        amount: int | None = None,
    ) -> tuple[int, int]:
        """
        Burn liquidity from a position.

        Args:
            caller: Must be position owner
            position_id: Position to burn from
            amount: Amount to burn (default: all)

        Returns:
            (amount0, amount1) - tokens returned
        """
        self._require_not_locked()

        try:
            self._locked = True

            position = self.positions.get(position_id)
            if not position:
                raise VMExecutionError(f"Position {position_id} not found")

            if position.owner.lower() != caller.lower():
                raise VMExecutionError("Not position owner")

            burn_amount = min(amount or position.liquidity, position.liquidity)

            # Calculate amounts to return
            amount0, amount1 = self._calculate_amounts_for_liquidity(
                position.tick_lower, position.tick_upper, burn_amount, add=False
            )

            # Collect accumulated fees
            fee0, fee1 = self._collect_fees(position)
            amount0 += fee0
            amount1 += fee1

            # Update position
            position.liquidity -= burn_amount

            # Update tick state
            self._update_tick(position.tick_lower, -burn_amount, True)
            self._update_tick(position.tick_upper, -burn_amount, False)

            # Update pool liquidity if in range
            if position.tick_lower <= self.tick < position.tick_upper:
                self.liquidity -= burn_amount

            # Update reserves
            self.reserve0 -= amount0
            self.reserve1 -= amount1

            # Remove position if empty
            if position.liquidity == 0:
                del self.positions[position_id]

            logger.info(
                "Position burned",
                extra={
                    "event": "clp.burn",
                    "pool": self.address[:10],
                    "position_id": position_id,
                    "amount": burn_amount,
                }
            )

            return amount0, amount1

        finally:
            self._locked = False

    def collect(
        self,
        caller: str,
        position_id: int,
    ) -> tuple[int, int]:
        """
        Collect accumulated fees from a position.

        Args:
            caller: Must be position owner
            position_id: Position to collect from

        Returns:
            (amount0, amount1) - fees collected
        """
        position = self.positions.get(position_id)
        if not position:
            raise VMExecutionError(f"Position {position_id} not found")

        if position.owner.lower() != caller.lower():
            raise VMExecutionError("Not position owner")

        return self._collect_fees(position)

    def _collect_fees(self, position: Position) -> tuple[int, int]:
        """
        Collect fees for a position.

        Fees are always rounded DOWN when paying users to prevent dust drain attacks.
        """
        fee_growth_inside_0 = self._get_fee_growth_inside(
            position.tick_lower, position.tick_upper, 0
        )
        fee_growth_inside_1 = self._get_fee_growth_inside(
            position.tick_lower, position.tick_upper, 1
        )

        # Calculate owed fees - round DOWN when paying users
        # This prevents users from draining dust through rounding
        fees_owed_0 = mul_div(
            (fee_growth_inside_0 - position.fee_growth_inside_0_last),
            position.liquidity,
            Q128,
            round_up=False  # Round down when paying users
        )
        fees_owed_1 = mul_div(
            (fee_growth_inside_1 - position.fee_growth_inside_1_last),
            position.liquidity,
            Q128,
            round_up=False  # Round down when paying users
        )

        # Add previously owed
        amount0 = position.tokens_owed_0 + fees_owed_0
        amount1 = position.tokens_owed_1 + fees_owed_1

        # Update position
        position.fee_growth_inside_0_last = fee_growth_inside_0
        position.fee_growth_inside_1_last = fee_growth_inside_1
        position.tokens_owed_0 = 0
        position.tokens_owed_1 = 0

        return amount0, amount1

    # ==================== Swapping ====================

    def swap(
        self,
        caller: str,
        zero_for_one: bool,
        amount_specified: int,
        sqrt_price_limit: int | None = None,
    ) -> tuple[int, int]:
        """
        Execute a swap through the pool.

        Args:
            caller: Swap initiator
            zero_for_one: True for token0->token1, False for token1->token0
            amount_specified: Positive for exact input, negative for exact output
            sqrt_price_limit: Price limit for the swap

        Returns:
            (amount0, amount1) - amounts swapped (negative = out)
        """
        self._require_not_locked()

        try:
            self._locked = True

            if amount_specified == 0:
                raise VMExecutionError("Amount must be non-zero")

            # Set price limit if not provided
            if sqrt_price_limit is None:
                sqrt_price_limit = (
                    MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
                )

            # Validate price limit
            if zero_for_one:
                if sqrt_price_limit >= self.sqrt_price:
                    raise VMExecutionError("Price limit too high")
                if sqrt_price_limit < MIN_SQRT_RATIO:
                    raise VMExecutionError("Price limit too low")
            else:
                if sqrt_price_limit <= self.sqrt_price:
                    raise VMExecutionError("Price limit too low")
                if sqrt_price_limit > MAX_SQRT_RATIO:
                    raise VMExecutionError("Price limit too high")

            exact_input = amount_specified > 0
            amount_remaining = abs(amount_specified)
            amount_calculated = 0

            state_sqrt_price = self.sqrt_price
            state_tick = self.tick
            state_liquidity = self.liquidity
            fee_growth_global = self.fee_growth_global_0 if zero_for_one else self.fee_growth_global_1

            # Loop through ticks until amount is fulfilled or price limit reached
            while amount_remaining > 0 and state_sqrt_price != sqrt_price_limit:
                # Find next initialized tick
                next_tick = self._next_initialized_tick(state_tick, zero_for_one)

                # Compute sqrt price at next tick
                sqrt_price_next = self.tick_to_sqrt_price(next_tick)

                # Cap at price limit
                if zero_for_one:
                    sqrt_price_target = max(sqrt_price_next, sqrt_price_limit)
                else:
                    sqrt_price_target = min(sqrt_price_next, sqrt_price_limit)

                # Compute swap step
                (
                    state_sqrt_price,
                    amount_in,
                    amount_out,
                    fee_amount,
                ) = self._compute_swap_step(
                    state_sqrt_price,
                    sqrt_price_target,
                    state_liquidity,
                    amount_remaining,
                    self.fee_tier.fee,
                    zero_for_one,
                    exact_input,
                )

                if exact_input:
                    amount_remaining -= amount_in + fee_amount
                    amount_calculated += amount_out
                else:
                    amount_remaining -= amount_out
                    amount_calculated += amount_in + fee_amount

                # Update fee growth - use full precision, no rounding for global accounting
                if state_liquidity > 0:
                    fee_growth_global += mul_div(fee_amount, Q128, state_liquidity, round_up=False)

                # Cross tick if reached
                if state_sqrt_price == sqrt_price_next:
                    # Cross tick
                    if next_tick in self.ticks:
                        tick_info = self.ticks[next_tick]
                        if zero_for_one:
                            state_liquidity -= tick_info.liquidity_net
                        else:
                            state_liquidity += tick_info.liquidity_net

                    state_tick = next_tick - 1 if zero_for_one else next_tick
                else:
                    state_tick = self.sqrt_price_to_tick(state_sqrt_price)

            # Update state
            self.sqrt_price = state_sqrt_price
            self.tick = state_tick
            self.liquidity = state_liquidity

            if zero_for_one:
                self.fee_growth_global_0 = fee_growth_global
            else:
                self.fee_growth_global_1 = fee_growth_global

            # Calculate final amounts
            if zero_for_one:
                if exact_input:
                    amount0 = amount_specified
                    amount1 = -amount_calculated
                else:
                    amount0 = amount_calculated
                    amount1 = -amount_specified
            else:
                if exact_input:
                    amount0 = -amount_calculated
                    amount1 = amount_specified
                else:
                    amount0 = -amount_specified
                    amount1 = amount_calculated

            # Update reserves
            self.reserve0 += amount0
            self.reserve1 += amount1

            logger.info(
                "Swap executed",
                extra={
                    "event": "clp.swap",
                    "pool": self.address[:10],
                    "direction": "0->1" if zero_for_one else "1->0",
                    "amount0": amount0,
                    "amount1": amount1,
                }
            )

            return amount0, amount1

        finally:
            self._locked = False

    def _compute_swap_step(
        self,
        sqrt_price_current: int,
        sqrt_price_target: int,
        liquidity: int,
        amount_remaining: int,
        fee: int,
        zero_for_one: bool,
        exact_input: bool,
    ) -> tuple[int, int, int, int]:
        """
        Compute a single swap step.

        Returns:
            (sqrt_price_next, amount_in, amount_out, fee_amount)
        """
        if liquidity == 0:
            return sqrt_price_target, 0, 0, 0

        # Calculate maximum swap in this step
        if zero_for_one:
            amount_in_max = self._get_amount0_delta(
                sqrt_price_target, sqrt_price_current, liquidity, True
            )
            amount_out_max = self._get_amount1_delta(
                sqrt_price_target, sqrt_price_current, liquidity, False
            )
        else:
            amount_in_max = self._get_amount1_delta(
                sqrt_price_current, sqrt_price_target, liquidity, True
            )
            amount_out_max = self._get_amount0_delta(
                sqrt_price_current, sqrt_price_target, liquidity, False
            )

        # Calculate fee - round UP when charging users
        fee_max = calculate_fee_amount(amount_in_max, fee)

        if exact_input:
            if amount_remaining >= amount_in_max + fee_max:
                # Use full step
                return sqrt_price_target, amount_in_max, amount_out_max, fee_max
            else:
                # Partial step - calculate amount_in from total including fee
                # amount_remaining = amount_in + fee_amount
                # amount_remaining = amount_in + (amount_in * fee / 10000)
                # amount_remaining = amount_in * (10000 + fee) / 10000
                # amount_in = amount_remaining * 10000 / (10000 + fee)
                amount_in = mul_div(amount_remaining, 10000, 10000 + fee, round_up=False)
                fee_amount = amount_remaining - amount_in

                # Calculate new sqrt price
                if zero_for_one:
                    sqrt_price_next = self._get_next_sqrt_price_from_input(
                        sqrt_price_current, liquidity, amount_in, zero_for_one
                    )
                    amount_out = self._get_amount1_delta(
                        sqrt_price_next, sqrt_price_current, liquidity, False
                    )
                else:
                    sqrt_price_next = self._get_next_sqrt_price_from_input(
                        sqrt_price_current, liquidity, amount_in, zero_for_one
                    )
                    amount_out = self._get_amount0_delta(
                        sqrt_price_current, sqrt_price_next, liquidity, False
                    )

                return sqrt_price_next, amount_in, amount_out, fee_amount
        else:
            if amount_remaining >= amount_out_max:
                # Use full step
                return sqrt_price_target, amount_in_max, amount_out_max, fee_max
            else:
                # Partial step
                if zero_for_one:
                    sqrt_price_next = self._get_next_sqrt_price_from_output(
                        sqrt_price_current, liquidity, amount_remaining, zero_for_one
                    )
                    amount_in = self._get_amount0_delta(
                        sqrt_price_next, sqrt_price_current, liquidity, True
                    )
                else:
                    sqrt_price_next = self._get_next_sqrt_price_from_output(
                        sqrt_price_current, liquidity, amount_remaining, zero_for_one
                    )
                    amount_in = self._get_amount1_delta(
                        sqrt_price_current, sqrt_price_next, liquidity, True
                    )

                # Calculate fee - round UP when charging users
                fee_amount = calculate_fee_amount(amount_in, fee)
                return sqrt_price_next, amount_in, amount_remaining, fee_amount

    # ==================== Internal Math ====================

    def _get_amount0_delta(
        self,
        sqrt_price_a: int,
        sqrt_price_b: int,
        liquidity: int,
        round_up: bool,
    ) -> int:
        """Calculate token0 amount for liquidity in price range."""
        if sqrt_price_a > sqrt_price_b:
            sqrt_price_a, sqrt_price_b = sqrt_price_b, sqrt_price_a

        numerator = liquidity * Q96 * (sqrt_price_b - sqrt_price_a)
        denominator = sqrt_price_b * sqrt_price_a

        if round_up:
            return (numerator + denominator - 1) // denominator
        return numerator // denominator

    def _get_amount1_delta(
        self,
        sqrt_price_a: int,
        sqrt_price_b: int,
        liquidity: int,
        round_up: bool,
    ) -> int:
        """Calculate token1 amount for liquidity in price range."""
        if sqrt_price_a > sqrt_price_b:
            sqrt_price_a, sqrt_price_b = sqrt_price_b, sqrt_price_a

        numerator = liquidity * (sqrt_price_b - sqrt_price_a)

        if round_up:
            return (numerator + Q96 - 1) // Q96
        return numerator // Q96

    def _get_next_sqrt_price_from_input(
        self,
        sqrt_price: int,
        liquidity: int,
        amount_in: int,
        zero_for_one: bool,
    ) -> int:
        """Calculate new sqrt price after input."""
        if zero_for_one:
            # Price decreases (more token0 = lower price)
            return liquidity * Q96 * sqrt_price // (
                liquidity * Q96 + amount_in * sqrt_price
            )
        else:
            # Price increases (more token1 = higher price)
            return sqrt_price + (amount_in * Q96 // liquidity)

    def _get_next_sqrt_price_from_output(
        self,
        sqrt_price: int,
        liquidity: int,
        amount_out: int,
        zero_for_one: bool,
    ) -> int:
        """Calculate new sqrt price after output."""
        if zero_for_one:
            # Taking out token1
            return sqrt_price - (amount_out * Q96 // liquidity)
        else:
            # Taking out token0
            numerator = liquidity * Q96 * sqrt_price
            denominator = liquidity * Q96 - amount_out * sqrt_price
            return numerator // denominator

    def _calculate_amounts_for_liquidity(
        self,
        tick_lower: int,
        tick_upper: int,
        liquidity: int,
        add: bool,
    ) -> tuple[int, int]:
        """Calculate token amounts needed for liquidity position."""
        sqrt_price_lower = self.tick_to_sqrt_price(tick_lower)
        sqrt_price_upper = self.tick_to_sqrt_price(tick_upper)

        if self.tick < tick_lower:
            # Below range - need only token0
            amount0 = self._get_amount0_delta(
                sqrt_price_lower, sqrt_price_upper, liquidity, add
            )
            amount1 = 0
        elif self.tick >= tick_upper:
            # Above range - need only token1
            amount0 = 0
            amount1 = self._get_amount1_delta(
                sqrt_price_lower, sqrt_price_upper, liquidity, add
            )
        else:
            # In range - need both
            amount0 = self._get_amount0_delta(
                self.sqrt_price, sqrt_price_upper, liquidity, add
            )
            amount1 = self._get_amount1_delta(
                sqrt_price_lower, self.sqrt_price, liquidity, add
            )

        return amount0, amount1

    # ==================== Tick Management ====================

    def _validate_ticks(self, tick_lower: int, tick_upper: int) -> None:
        """Validate tick range."""
        if tick_lower >= tick_upper:
            raise VMExecutionError("tick_lower must be less than tick_upper")

        if tick_lower < MIN_TICK or tick_upper > MAX_TICK:
            raise VMExecutionError("Ticks out of range")

        spacing = self.fee_tier.tick_spacing
        if tick_lower % spacing != 0 or tick_upper % spacing != 0:
            raise VMExecutionError(f"Ticks must be multiples of {spacing}")

    def _update_tick(self, tick: int, liquidity_delta: int, is_lower: bool) -> None:
        """Update tick liquidity."""
        if tick not in self.ticks:
            self.ticks[tick] = TickInfo()

        info = self.ticks[tick]
        info.liquidity_gross += abs(liquidity_delta)

        if is_lower:
            info.liquidity_net += liquidity_delta
        else:
            info.liquidity_net -= liquidity_delta

        if info.liquidity_gross > 0:
            info.initialized = True
            self._flip_tick(tick)
        elif info.liquidity_gross == 0:
            info.initialized = False

    def _flip_tick(self, tick: int) -> None:
        """Flip tick in bitmap."""
        word_pos = tick >> 8
        bit_pos = tick & 0xFF

        if word_pos not in self.tick_bitmap:
            self.tick_bitmap[word_pos] = 0

        self.tick_bitmap[word_pos] ^= (1 << bit_pos)

    def _next_initialized_tick(self, tick: int, zero_for_one: bool) -> int:
        """Find next initialized tick."""
        spacing = self.fee_tier.tick_spacing

        # Align to spacing
        compressed = tick // spacing
        if tick < 0 and tick % spacing != 0:
            compressed -= 1

        if zero_for_one:
            # Search downward
            for t in range(compressed * spacing, MIN_TICK, -spacing):
                if t in self.ticks and self.ticks[t].initialized:
                    return t
            return MIN_TICK
        else:
            # Search upward
            for t in range((compressed + 1) * spacing, MAX_TICK, spacing):
                if t in self.ticks and self.ticks[t].initialized:
                    return t
            return MAX_TICK

    def _get_fee_growth_inside(
        self,
        tick_lower: int,
        tick_upper: int,
        token: int,
    ) -> int:
        """Calculate fee growth inside a tick range."""
        fee_growth_global = (
            self.fee_growth_global_0 if token == 0 else self.fee_growth_global_1
        )

        lower_info = self.ticks.get(tick_lower, TickInfo())
        upper_info = self.ticks.get(tick_upper, TickInfo())

        fee_outside_lower = (
            lower_info.fee_growth_outside_0 if token == 0
            else lower_info.fee_growth_outside_1
        )
        fee_outside_upper = (
            upper_info.fee_growth_outside_0 if token == 0
            else upper_info.fee_growth_outside_1
        )

        if self.tick >= tick_lower:
            fee_below = fee_outside_lower
        else:
            fee_below = fee_growth_global - fee_outside_lower

        if self.tick < tick_upper:
            fee_above = fee_outside_upper
        else:
            fee_above = fee_growth_global - fee_outside_upper

        return fee_growth_global - fee_below - fee_above

    # ==================== View Functions ====================

    def get_position(self, position_id: int) -> dict | None:
        """Get position details."""
        position = self.positions.get(position_id)
        if not position:
            return None

        amount0, amount1 = self._calculate_amounts_for_liquidity(
            position.tick_lower, position.tick_upper,
            position.liquidity, False
        )

        fees0, fees1 = self._collect_fees_preview(position)

        return {
            "id": position.id,
            "owner": position.owner,
            "tick_lower": position.tick_lower,
            "tick_upper": position.tick_upper,
            "price_lower": self.tick_to_price(position.tick_lower),
            "price_upper": self.tick_to_price(position.tick_upper),
            "liquidity": position.liquidity,
            "amount0": amount0,
            "amount1": amount1,
            "uncollected_fees_0": fees0,
            "uncollected_fees_1": fees1,
            "in_range": position.is_in_range(self.tick),
        }

    def _collect_fees_preview(self, position: Position) -> tuple[int, int]:
        """
        Preview fees without modifying state.

        Fees are always rounded DOWN when paying users.
        """
        fee_growth_inside_0 = self._get_fee_growth_inside(
            position.tick_lower, position.tick_upper, 0
        )
        fee_growth_inside_1 = self._get_fee_growth_inside(
            position.tick_lower, position.tick_upper, 1
        )

        # Round DOWN when paying users
        fees_0 = mul_div(
            (fee_growth_inside_0 - position.fee_growth_inside_0_last),
            position.liquidity,
            Q128,
            round_up=False
        ) + position.tokens_owed_0

        fees_1 = mul_div(
            (fee_growth_inside_1 - position.fee_growth_inside_1_last),
            position.liquidity,
            Q128,
            round_up=False
        ) + position.tokens_owed_1

        return fees_0, fees_1

    def get_pool_state(self) -> dict:
        """Get current pool state."""
        return {
            "address": self.address,
            "token0": self.token0,
            "token1": self.token1,
            "fee_tier": self.fee_tier.fee,
            "tick_spacing": self.fee_tier.tick_spacing,
            "sqrt_price": self.sqrt_price,
            "tick": self.tick,
            "price": self.tick_to_price(self.tick),
            "liquidity": self.liquidity,
            "reserve0": self.reserve0,
            "reserve1": self.reserve1,
            "positions_count": len(self.positions),
            "initialized_ticks": len([t for t in self.ticks.values() if t.initialized]),
        }

    def quote(
        self,
        zero_for_one: bool,
        amount_in: int,
    ) -> tuple[int, int]:
        """
        Get quote for a swap without executing.

        Args:
            zero_for_one: Swap direction
            amount_in: Input amount

        Returns:
            (amount_out, price_impact_bps)
        """
        # Simulate swap on copy of state
        original_sqrt_price = self.sqrt_price

        try:
            # Approximate by computing with current liquidity
            if self.liquidity == 0:
                return 0, 0

            if zero_for_one:
                # Selling token0 for token1
                new_sqrt_price = self._get_next_sqrt_price_from_input(
                    self.sqrt_price, self.liquidity, amount_in, True
                )
                amount_out = self._get_amount1_delta(
                    new_sqrt_price, self.sqrt_price, self.liquidity, False
                )
            else:
                # Selling token1 for token0
                new_sqrt_price = self._get_next_sqrt_price_from_input(
                    self.sqrt_price, self.liquidity, amount_in, False
                )
                amount_out = self._get_amount0_delta(
                    self.sqrt_price, new_sqrt_price, self.liquidity, False
                )

            # Apply fee - round UP when charging users, round DOWN when paying
            fee = calculate_fee_amount(amount_in, self.fee_tier.fee)
            # Reduce output by fee percentage - round DOWN when paying users
            amount_out = mul_div(
                amount_out,
                (10000 - self.fee_tier.fee),
                10000,
                round_up=False
            )

            # Calculate price impact in basis points
            if self.sqrt_price > 0:
                price_impact = mul_div(
                    abs(new_sqrt_price - self.sqrt_price),
                    10000,
                    self.sqrt_price,
                    round_up=False
                )
            else:
                price_impact = 0

            return max(0, amount_out), price_impact

        except (ValueError, TypeError, ZeroDivisionError, OverflowError, ArithmeticError) as e:
            logger.warning(
                "Failed to calculate swap quote: %s - %s",
                type(e).__name__,
                str(e),
                extra={
                    "pool_id": self.pool_id,
                    "zero_for_one": zero_for_one,
                    "amount_in": amount_in,
                    "error_type": type(e).__name__,
                    "event": "concentrated_liquidity.quote_failed"
                }
            )
            return 0, 0

    # ==================== Helpers ====================

    def _require_not_locked(self) -> None:
        if self._locked:
            raise VMExecutionError("Pool is locked")

@dataclass
class ConcentratedLiquidityFactory:
    """Factory for deploying concentrated liquidity pools."""

    address: str = ""
    owner: str = ""

    # Deployed pools
    pools: dict[str, ConcentratedLiquidityPool] = field(default_factory=dict)

    # Pool lookup by pair
    pool_by_pair: dict[str, dict[int, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize factory."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"clp_factory:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def create_pool(
        self,
        caller: str,
        token0: str,
        token1: str,
        fee_tier: FeeTier,
        initial_sqrt_price: int,
    ) -> ConcentratedLiquidityPool:
        """
        Create a new concentrated liquidity pool.

        Args:
            caller: Pool creator
            token0: First token (alphabetically)
            token1: Second token
            fee_tier: Fee tier configuration
            initial_sqrt_price: Initial sqrt price (Q64.96)

        Returns:
            Created pool
        """
        # Sort tokens
        if token0 > token1:
            token0, token1 = token1, token0
            # Invert sqrt price with full precision
            initial_sqrt_price = mul_div(Q96, Q96, initial_sqrt_price, round_up=False)

        pair_key = f"{token0}:{token1}"

        # Check if pool exists for this pair and fee
        if pair_key in self.pool_by_pair:
            if fee_tier.fee in self.pool_by_pair[pair_key]:
                raise VMExecutionError(
                    f"Pool already exists for {pair_key} at {fee_tier.fee} fee"
                )

        pool = ConcentratedLiquidityPool(
            token0=token0,
            token1=token1,
            fee_tier=fee_tier,
            sqrt_price=initial_sqrt_price,
            tick=ConcentratedLiquidityPool.sqrt_price_to_tick(initial_sqrt_price),
        )

        self.pools[pool.address] = pool

        if pair_key not in self.pool_by_pair:
            self.pool_by_pair[pair_key] = {}
        self.pool_by_pair[pair_key][fee_tier.fee] = pool.address

        logger.info(
            "Concentrated liquidity pool created",
            extra={
                "event": "factory.pool_created",
                "pool": pool.address[:10],
                "pair": pair_key,
                "fee": fee_tier.fee,
            }
        )

        return pool

    def get_pool(
        self,
        token0: str,
        token1: str,
        fee: int,
    ) -> ConcentratedLiquidityPool | None:
        """Get pool by token pair and fee."""
        if token0 > token1:
            token0, token1 = token1, token0

        pair_key = f"{token0}:{token1}"

        if pair_key not in self.pool_by_pair:
            return None

        pool_address = self.pool_by_pair[pair_key].get(fee)
        if not pool_address:
            return None

        return self.pools.get(pool_address)

    def get_all_pools_for_pair(
        self,
        token0: str,
        token1: str,
    ) -> list[ConcentratedLiquidityPool]:
        """Get all pools for a token pair (all fee tiers)."""
        if token0 > token1:
            token0, token1 = token1, token0

        pair_key = f"{token0}:{token1}"

        if pair_key not in self.pool_by_pair:
            return []

        return [
            self.pools[addr]
            for addr in self.pool_by_pair[pair_key].values()
            if addr in self.pools
        ]
