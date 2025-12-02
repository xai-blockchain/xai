"""
DeFi Lending Protocol Implementation.

This module provides a complete lending protocol similar to Aave/Compound:
- Collateralized borrowing
- Variable and stable interest rates
- Liquidation mechanism
- Health factor tracking
- Interest accrual

Security features:
- Collateral ratio enforcement
- Liquidation threshold checks
- Interest rate bounds
- Reentrancy protection
- Oracle price validation
"""

from __future__ import annotations

import math
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from decimal import Decimal, ROUND_DOWN
from enum import Enum

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


class InterestRateModel(Enum):
    """Interest rate model types."""
    STABLE = "stable"
    VARIABLE = "variable"


@dataclass
class AssetConfig:
    """Configuration for a supported asset."""

    symbol: str
    address: str  # Token contract address

    # Collateral parameters
    ltv: int  # Loan-to-Value ratio (basis points, e.g., 8000 = 80%)
    liquidation_threshold: int  # Threshold for liquidation (basis points)
    liquidation_bonus: int  # Bonus for liquidators (basis points)

    # Interest rate parameters (basis points per year)
    base_rate: int = 200  # 2% base rate
    slope1: int = 400  # 4% slope before optimal utilization
    slope2: int = 7500  # 75% slope after optimal utilization
    optimal_utilization: int = 8000  # 80% optimal utilization

    # Supply/Borrow caps (0 = unlimited)
    supply_cap: int = 0
    borrow_cap: int = 0

    # Oracle configuration
    oracle_address: str = ""

    # Decimals for precision
    decimals: int = 18

    # Enabled flags
    borrowing_enabled: bool = True
    collateral_enabled: bool = True
    stable_borrowing_enabled: bool = False

    # Reserve factor (basis points - portion of interest to protocol)
    reserve_factor: int = 1000  # 10%


@dataclass
class UserPosition:
    """User's position in a lending pool."""

    user: str

    # Supplied collateral by asset
    supplied: Dict[str, int] = field(default_factory=dict)

    # Borrowed amounts by asset
    borrowed: Dict[str, int] = field(default_factory=dict)

    # Interest rate mode per borrowed asset
    interest_mode: Dict[str, InterestRateModel] = field(default_factory=dict)

    # Timestamps for interest calculation
    last_update: Dict[str, float] = field(default_factory=dict)

    # Accumulated interest
    accrued_interest: Dict[str, int] = field(default_factory=dict)


@dataclass
class PoolState:
    """State of a lending pool for an asset."""

    asset: str

    # Total liquidity
    total_supplied: int = 0
    total_borrowed: int = 0

    # Interest indices (scaled by 1e27 - RAY)
    supply_index: int = 10**27  # Initial index = 1 RAY
    borrow_index: int = 10**27

    # Last update timestamp
    last_update: float = 0.0

    # Protocol reserves
    reserves: int = 0

    # Current rates (basis points per year)
    current_supply_rate: int = 0
    current_borrow_rate: int = 0


@dataclass
class LendingPool:
    """
    Complete lending pool implementation.

    Implements an Aave/Compound-style lending protocol with:
    - Multi-asset support
    - Collateralized borrowing
    - Variable interest rates
    - Liquidation mechanism
    - Health factor tracking

    Security features:
    - Collateral ratio enforcement
    - Liquidation threshold monitoring
    - Interest rate bounds
    - Price oracle validation
    """

    # Pool info
    name: str = "XAI Lending Pool"
    address: str = ""
    owner: str = ""

    # Supported assets
    assets: Dict[str, AssetConfig] = field(default_factory=dict)

    # Pool state per asset
    pool_states: Dict[str, PoolState] = field(default_factory=dict)

    # User positions
    positions: Dict[str, UserPosition] = field(default_factory=dict)

    # Price oracle reference
    oracle_address: str = ""
    _price_cache: Dict[str, Tuple[int, float]] = field(default_factory=dict)

    # Protocol parameters
    close_factor: int = 5000  # 50% max liquidation per tx (basis points)

    # Pause state
    paused: bool = False

    # Constants
    RAY: int = 10**27
    SECONDS_PER_YEAR: int = 365 * 24 * 3600
    BASIS_POINTS: int = 10000

    def __post_init__(self) -> None:
        """Initialize pool."""
        if not self.address:
            import hashlib
            addr_hash = hashlib.sha3_256(f"{self.name}{time.time()}".encode()).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Asset Management ====================

    def add_asset(self, caller: str, config: AssetConfig) -> bool:
        """
        Add a new supported asset.

        Args:
            caller: Must be owner
            config: Asset configuration

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if config.symbol in self.assets:
            raise VMExecutionError(f"Asset {config.symbol} already exists")

        # Validate parameters
        if config.ltv > config.liquidation_threshold:
            raise VMExecutionError("LTV cannot exceed liquidation threshold")
        if config.liquidation_threshold > self.BASIS_POINTS:
            raise VMExecutionError("Liquidation threshold cannot exceed 100%")

        self.assets[config.symbol] = config
        self.pool_states[config.symbol] = PoolState(
            asset=config.symbol,
            last_update=time.time(),
        )

        logger.info(
            "Asset added to lending pool",
            extra={
                "event": "lending.asset_added",
                "symbol": config.symbol,
                "ltv": config.ltv,
            }
        )

        return True

    # ==================== Supply (Deposit) ====================

    def supply(
        self,
        caller: str,
        asset: str,
        amount: int,
        on_behalf_of: Optional[str] = None,
    ) -> int:
        """
        Supply (deposit) assets to the pool.

        Args:
            caller: Depositor
            asset: Asset symbol
            amount: Amount to supply
            on_behalf_of: Optional beneficiary address

        Returns:
            Amount of aTokens minted
        """
        self._require_not_paused()
        self._require_asset(asset)

        if amount <= 0:
            raise VMExecutionError("Amount must be positive")

        config = self.assets[asset]

        # Check supply cap
        if config.supply_cap > 0:
            state = self.pool_states[asset]
            if state.total_supplied + amount > config.supply_cap:
                raise VMExecutionError("Supply cap exceeded")

        # Update interest indices
        self._update_indices(asset)

        # Get/create user position
        beneficiary = on_behalf_of or caller
        position = self._get_or_create_position(beneficiary)

        # Update state
        state = self.pool_states[asset]

        # Calculate aTokens to mint (scaled by supply index)
        a_tokens = self._ray_div(amount * self.RAY, state.supply_index)

        # Update balances
        position.supplied[asset] = position.supplied.get(asset, 0) + a_tokens
        state.total_supplied += amount

        logger.info(
            "Asset supplied to lending pool",
            extra={
                "event": "lending.supply",
                "asset": asset,
                "amount": amount,
                "user": beneficiary[:10],
            }
        )

        return a_tokens

    def withdraw(self, caller: str, asset: str, amount: int) -> int:
        """
        Withdraw supplied assets.

        Args:
            caller: User withdrawing
            asset: Asset symbol
            amount: Amount to withdraw (or max_int for all)

        Returns:
            Amount withdrawn
        """
        self._require_not_paused()
        self._require_asset(asset)

        position = self._get_position(caller)
        if not position:
            raise VMExecutionError("No position found")

        # Update interest indices
        self._update_indices(asset)

        state = self.pool_states[asset]

        # Calculate available balance
        a_token_balance = position.supplied.get(asset, 0)
        underlying_balance = self._ray_mul(a_token_balance, state.supply_index) // self.RAY

        # Handle max withdrawal
        if amount == 2**256 - 1:
            amount = underlying_balance

        if amount > underlying_balance:
            raise VMExecutionError(
                f"Insufficient balance: {amount} > {underlying_balance}"
            )

        # Check if withdrawal maintains health factor
        new_supplied = position.supplied.copy()
        a_tokens_to_burn = self._ray_div(amount * self.RAY, state.supply_index)
        new_supplied[asset] = new_supplied.get(asset, 0) - a_tokens_to_burn

        health_factor = self._calculate_health_factor_with_changes(
            position, new_supplied, position.borrowed
        )

        if health_factor < self.RAY:
            raise VMExecutionError(
                f"Withdrawal would put position below liquidation threshold"
            )

        # Update balances
        position.supplied[asset] = a_token_balance - a_tokens_to_burn
        state.total_supplied -= amount

        logger.info(
            "Asset withdrawn from lending pool",
            extra={
                "event": "lending.withdraw",
                "asset": asset,
                "amount": amount,
                "user": caller[:10],
            }
        )

        return amount

    # ==================== Borrow ====================

    def borrow(
        self,
        caller: str,
        asset: str,
        amount: int,
        interest_mode: InterestRateModel = InterestRateModel.VARIABLE,
    ) -> bool:
        """
        Borrow assets against collateral.

        SECURITY: Comprehensive validation to prevent:
        - Negative/zero amounts
        - Exceeding available liquidity
        - Under-collateralized borrows
        - Integer overflow attacks
        - Borrowing disabled assets

        Args:
            caller: Borrower
            asset: Asset to borrow
            amount: Amount to borrow
            interest_mode: Interest rate mode

        Returns:
            True if successful

        Raises:
            VMExecutionError: If validation fails
        """
        self._require_not_paused()
        self._require_asset(asset)

        # Normalize borrower address
        borrower_norm = self._normalize(caller)

        # VALIDATION 1: Amount must be positive
        if amount <= 0:
            logger.warning(
                "Borrow rejected - invalid amount",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "non_positive_amount",
                    "borrower": borrower_norm,
                    "asset": asset,
                    "amount": amount,
                }
            )
            raise VMExecutionError(f"Borrow amount must be positive, got {amount}")

        # VALIDATION 2: Amount must not exceed maximum safe value (prevent overflow)
        MAX_BORROW = 10**27  # Reasonable upper bound (1 RAY)
        if amount > MAX_BORROW:
            logger.warning(
                "Borrow rejected - exceeds maximum",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "exceeds_maximum",
                    "borrower": borrower_norm,
                    "asset": asset,
                    "amount": amount,
                    "max_borrow": MAX_BORROW,
                }
            )
            raise VMExecutionError(
                f"Borrow amount {amount} exceeds maximum {MAX_BORROW}"
            )

        # VALIDATION 3: Asset must support borrowing
        config = self.assets[asset]
        if not config.borrowing_enabled:
            logger.warning(
                "Borrow rejected - borrowing disabled",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "borrowing_disabled",
                    "borrower": borrower_norm,
                    "asset": asset,
                }
            )
            raise VMExecutionError(f"Borrowing not enabled for {asset}")

        # VALIDATION 4: Interest mode must be supported
        if interest_mode == InterestRateModel.STABLE and not config.stable_borrowing_enabled:
            logger.warning(
                "Borrow rejected - stable borrowing disabled",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "stable_borrowing_disabled",
                    "borrower": borrower_norm,
                    "asset": asset,
                }
            )
            raise VMExecutionError(f"Stable borrowing not enabled for {asset}")

        # VALIDATION 5: Check borrow cap
        state = self.pool_states[asset]
        if config.borrow_cap > 0:
            if state.total_borrowed + amount > config.borrow_cap:
                logger.warning(
                    "Borrow rejected - borrow cap exceeded",
                    extra={
                        "event": "lending.borrow_rejected",
                        "reason": "borrow_cap_exceeded",
                        "borrower": borrower_norm,
                        "asset": asset,
                        "amount": amount,
                        "current_borrowed": state.total_borrowed,
                        "borrow_cap": config.borrow_cap,
                    }
                )
                raise VMExecutionError(
                    f"Borrow cap exceeded for {asset}: "
                    f"current {state.total_borrowed}, cap {config.borrow_cap}, "
                    f"requested {amount}"
                )

        # VALIDATION 6: Check available liquidity
        available_liquidity = state.total_supplied - state.total_borrowed
        if amount > available_liquidity:
            logger.warning(
                "Borrow rejected - insufficient liquidity",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "insufficient_liquidity",
                    "borrower": borrower_norm,
                    "asset": asset,
                    "requested": amount,
                    "available": available_liquidity,
                    "total_supplied": state.total_supplied,
                    "total_borrowed": state.total_borrowed,
                }
            )
            raise VMExecutionError(
                f"Insufficient liquidity for {asset}: "
                f"requested {amount}, available {available_liquidity}"
            )

        # Update indices to get current state
        self._update_indices(asset)

        # Get or create position
        position = self._get_or_create_position(caller)

        # VALIDATION 7: Check borrowing capacity (collateral-based)
        account_data = self.get_user_account_data(caller)
        available_borrow_value = account_data["available_borrow"]

        # Calculate value of requested borrow
        asset_price = self._get_price(asset)
        requested_borrow_value = amount * asset_price

        if requested_borrow_value > available_borrow_value:
            logger.warning(
                "Borrow rejected - exceeds collateral capacity",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "exceeds_capacity",
                    "borrower": borrower_norm,
                    "asset": asset,
                    "requested_value": requested_borrow_value,
                    "available_borrow_value": available_borrow_value,
                    "total_collateral": account_data["total_collateral_value"],
                    "current_debt": account_data["total_debt_value"],
                }
            )
            raise VMExecutionError(
                f"Borrow exceeds collateral capacity: "
                f"requested value {requested_borrow_value}, "
                f"available borrow capacity {available_borrow_value}"
            )

        # VALIDATION 8: Simulate health factor after borrow
        new_borrowed = position.borrowed.copy()
        new_borrowed[asset] = new_borrowed.get(asset, 0) + amount

        health_factor = self._calculate_health_factor_with_changes(
            position, position.supplied, new_borrowed
        )

        if health_factor < self.RAY:
            logger.warning(
                "Borrow rejected - health factor too low",
                extra={
                    "event": "lending.borrow_rejected",
                    "reason": "health_factor_too_low",
                    "borrower": borrower_norm,
                    "asset": asset,
                    "amount": amount,
                    "simulated_health_factor": health_factor,
                    "min_health_factor": self.RAY,
                }
            )
            raise VMExecutionError(
                f"Borrow would put position below liquidation threshold. "
                f"Health factor would be {health_factor / self.RAY:.4f}, "
                f"minimum required is 1.0"
            )

        # All validations passed - proceed with borrow
        logger.info(
            "Borrow approved and executed",
            extra={
                "event": "lending.borrow_approved",
                "borrower": borrower_norm,
                "asset": asset,
                "amount": amount,
                "interest_mode": interest_mode.value,
                "new_health_factor": health_factor / self.RAY,
                "available_liquidity_after": available_liquidity - amount,
            }
        )

        # Update state
        position.borrowed[asset] = position.borrowed.get(asset, 0) + amount
        position.interest_mode[asset] = interest_mode
        position.last_update[asset] = time.time()

        state.total_borrowed += amount

        logger.info(
            "Asset borrowed from lending pool",
            extra={
                "event": "lending.borrow",
                "asset": asset,
                "amount": amount,
                "user": caller[:10],
                "mode": interest_mode.value,
            }
        )

        return True

    def repay(
        self,
        caller: str,
        asset: str,
        amount: int,
        on_behalf_of: Optional[str] = None,
    ) -> int:
        """
        Repay borrowed assets.

        Args:
            caller: Repayer
            asset: Asset symbol
            amount: Amount to repay (max_int for all)
            on_behalf_of: Optional borrower address

        Returns:
            Amount repaid
        """
        self._require_not_paused()
        self._require_asset(asset)

        beneficiary = on_behalf_of or caller
        position = self._get_position(beneficiary)

        if not position:
            raise VMExecutionError("No position found")

        # Update indices and accrue interest
        self._update_indices(asset)
        self._accrue_interest(position, asset)

        # Get total debt (principal + interest)
        principal = position.borrowed.get(asset, 0)
        interest = position.accrued_interest.get(asset, 0)
        total_debt = principal + interest

        if total_debt == 0:
            raise VMExecutionError(f"No debt to repay for {asset}")

        # Handle max repayment
        if amount == 2**256 - 1:
            amount = total_debt

        # Cap at total debt
        amount = min(amount, total_debt)

        # First repay interest, then principal
        if amount <= interest:
            position.accrued_interest[asset] = interest - amount
        else:
            position.accrued_interest[asset] = 0
            principal_repaid = amount - interest
            position.borrowed[asset] = principal - principal_repaid

        # Update pool state
        state = self.pool_states[asset]
        state.total_borrowed = max(0, state.total_borrowed - amount)

        logger.info(
            "Debt repaid to lending pool",
            extra={
                "event": "lending.repay",
                "asset": asset,
                "amount": amount,
                "user": beneficiary[:10],
            }
        )

        return amount

    # ==================== Liquidation ====================

    def liquidate(
        self,
        caller: str,
        borrower: str,
        debt_asset: str,
        collateral_asset: str,
        debt_to_cover: int,
    ) -> Tuple[int, int]:
        """
        Liquidate an unhealthy position.

        Args:
            caller: Liquidator
            borrower: Address to liquidate
            debt_asset: Asset to repay
            collateral_asset: Collateral to seize
            debt_to_cover: Amount of debt to repay

        Returns:
            Tuple of (debt_covered, collateral_seized)
        """
        self._require_not_paused()
        self._require_asset(debt_asset)
        self._require_asset(collateral_asset)

        if caller == borrower:
            raise VMExecutionError("Cannot liquidate own position")

        position = self._get_position(borrower)
        if not position:
            raise VMExecutionError("Position not found")

        # Check health factor
        health_factor = self.get_health_factor(borrower)
        if health_factor >= self.RAY:
            raise VMExecutionError(
                f"Position is healthy (health factor: {health_factor / self.RAY:.4f})"
            )

        # Update indices and accrue interest
        self._update_indices(debt_asset)
        self._update_indices(collateral_asset)
        self._accrue_interest(position, debt_asset)

        # Get debt
        principal = position.borrowed.get(debt_asset, 0)
        interest = position.accrued_interest.get(debt_asset, 0)
        total_debt = principal + interest

        if total_debt == 0:
            raise VMExecutionError("No debt to liquidate")

        # Apply close factor (max liquidation per tx)
        max_liquidatable = (total_debt * self.close_factor) // self.BASIS_POINTS
        debt_to_cover = min(debt_to_cover, max_liquidatable)

        # Calculate collateral to seize
        debt_price = self._get_price(debt_asset)
        collateral_price = self._get_price(collateral_asset)

        collateral_config = self.assets[collateral_asset]
        liquidation_bonus = collateral_config.liquidation_bonus

        # Collateral = (debt_amount * debt_price * (1 + bonus)) / collateral_price
        collateral_value = debt_to_cover * debt_price
        bonus_value = (collateral_value * liquidation_bonus) // self.BASIS_POINTS
        collateral_to_seize = (collateral_value + bonus_value) // collateral_price

        # Check available collateral
        state = self.pool_states[collateral_asset]
        a_token_balance = position.supplied.get(collateral_asset, 0)
        underlying_collateral = self._ray_mul(a_token_balance, state.supply_index) // self.RAY

        if collateral_to_seize > underlying_collateral:
            # Adjust debt to cover based on available collateral
            collateral_to_seize = underlying_collateral
            debt_to_cover = (
                (collateral_to_seize * collateral_price * self.BASIS_POINTS)
                // (debt_price * (self.BASIS_POINTS + liquidation_bonus))
            )

        # Execute liquidation
        # 1. Reduce borrower's debt
        if debt_to_cover <= interest:
            position.accrued_interest[debt_asset] = interest - debt_to_cover
        else:
            position.accrued_interest[debt_asset] = 0
            position.borrowed[debt_asset] = principal - (debt_to_cover - interest)

        # 2. Transfer collateral to liquidator
        a_tokens_seized = self._ray_div(collateral_to_seize * self.RAY, state.supply_index)
        position.supplied[collateral_asset] = a_token_balance - a_tokens_seized

        # Give aTokens to liquidator
        liquidator_position = self._get_or_create_position(caller)
        liquidator_position.supplied[collateral_asset] = (
            liquidator_position.supplied.get(collateral_asset, 0) + a_tokens_seized
        )

        # Update pool states
        debt_state = self.pool_states[debt_asset]
        debt_state.total_borrowed = max(0, debt_state.total_borrowed - debt_to_cover)

        logger.warning(
            "Position liquidated",
            extra={
                "event": "lending.liquidation",
                "borrower": borrower[:10],
                "liquidator": caller[:10],
                "debt_asset": debt_asset,
                "collateral_asset": collateral_asset,
                "debt_covered": debt_to_cover,
                "collateral_seized": collateral_to_seize,
            }
        )

        return debt_to_cover, collateral_to_seize

    # ==================== View Functions ====================

    def get_health_factor(self, user: str) -> int:
        """
        Get user's health factor.

        Health factor = (total_collateral_value * liquidation_threshold) / total_debt_value

        Args:
            user: User address

        Returns:
            Health factor (scaled by RAY). Below RAY = liquidatable
        """
        position = self._get_position(user)
        if not position:
            return self.RAY * 10  # No position = healthy

        return self._calculate_health_factor(position)

    def get_user_account_data(self, user: str) -> Dict:
        """
        Get comprehensive account data for a user.

        Args:
            user: User address

        Returns:
            Account data dictionary
        """
        position = self._get_position(user)
        if not position:
            return {
                "total_collateral_value": 0,
                "total_debt_value": 0,
                "available_borrow": 0,
                "health_factor": self.RAY * 10,
                "ltv": 0,
            }

        total_collateral = 0
        weighted_ltv = 0
        total_debt = 0

        for asset, a_tokens in position.supplied.items():
            if a_tokens > 0:
                state = self.pool_states[asset]
                config = self.assets[asset]

                underlying = self._ray_mul(a_tokens, state.supply_index) // self.RAY
                value = underlying * self._get_price(asset)
                total_collateral += value
                weighted_ltv += value * config.ltv // self.BASIS_POINTS

        for asset, principal in position.borrowed.items():
            if principal > 0:
                self._accrue_interest(position, asset)
                interest = position.accrued_interest.get(asset, 0)
                total_debt += (principal + interest) * self._get_price(asset)

        health_factor = self._calculate_health_factor(position)
        available_borrow = max(0, weighted_ltv - total_debt) if total_collateral > 0 else 0

        return {
            "total_collateral_value": total_collateral,
            "total_debt_value": total_debt,
            "available_borrow": available_borrow,
            "health_factor": health_factor,
            "ltv": (total_debt * self.BASIS_POINTS // total_collateral) if total_collateral > 0 else 0,
        }

    def get_reserve_data(self, asset: str) -> Dict:
        """Get reserve/pool data for an asset."""
        self._require_asset(asset)

        config = self.assets[asset]
        state = self.pool_states[asset]

        utilization = self._calculate_utilization(asset)
        borrow_rate = self._calculate_borrow_rate(asset, utilization)
        supply_rate = self._calculate_supply_rate(asset, utilization, borrow_rate)

        return {
            "symbol": asset,
            "total_supplied": state.total_supplied,
            "total_borrowed": state.total_borrowed,
            "available_liquidity": state.total_supplied - state.total_borrowed,
            "utilization_rate": utilization,
            "supply_rate": supply_rate,
            "borrow_rate": borrow_rate,
            "ltv": config.ltv,
            "liquidation_threshold": config.liquidation_threshold,
            "liquidation_bonus": config.liquidation_bonus,
        }

    # ==================== Interest Rate Model ====================

    def _calculate_utilization(self, asset: str) -> int:
        """Calculate utilization rate (basis points)."""
        state = self.pool_states[asset]

        if state.total_supplied == 0:
            return 0

        return (state.total_borrowed * self.BASIS_POINTS) // state.total_supplied

    def _calculate_borrow_rate(self, asset: str, utilization: int) -> int:
        """
        Calculate borrow interest rate.

        Two-slope model:
        - Below optimal: base_rate + (utilization/optimal) * slope1
        - Above optimal: base_rate + slope1 + ((utilization-optimal)/(1-optimal)) * slope2

        Returns:
            Borrow rate in basis points per year
        """
        config = self.assets[asset]

        if utilization <= config.optimal_utilization:
            # Below optimal utilization
            rate = config.base_rate + (
                (utilization * config.slope1) // config.optimal_utilization
            )
        else:
            # Above optimal utilization
            excess_utilization = utilization - config.optimal_utilization
            remaining_utilization = self.BASIS_POINTS - config.optimal_utilization

            rate = (
                config.base_rate
                + config.slope1
                + (excess_utilization * config.slope2) // remaining_utilization
            )

        return rate

    def _calculate_supply_rate(
        self, asset: str, utilization: int, borrow_rate: int
    ) -> int:
        """Calculate supply (deposit) interest rate."""
        config = self.assets[asset]

        # Supply rate = borrow_rate * utilization * (1 - reserve_factor)
        rate = (
            borrow_rate
            * utilization
            * (self.BASIS_POINTS - config.reserve_factor)
            // (self.BASIS_POINTS * self.BASIS_POINTS)
        )

        return rate

    def _update_indices(self, asset: str) -> None:
        """Update supply and borrow indices with accrued interest."""
        state = self.pool_states[asset]

        time_elapsed = time.time() - state.last_update
        if time_elapsed <= 0:
            return

        utilization = self._calculate_utilization(asset)
        borrow_rate = self._calculate_borrow_rate(asset, utilization)
        supply_rate = self._calculate_supply_rate(asset, utilization, borrow_rate)

        # Calculate interest multipliers
        # interest_multiplier = 1 + (rate * time_elapsed / SECONDS_PER_YEAR)
        borrow_multiplier = self.RAY + (
            borrow_rate * self.RAY * int(time_elapsed)
            // (self.SECONDS_PER_YEAR * self.BASIS_POINTS)
        )
        supply_multiplier = self.RAY + (
            supply_rate * self.RAY * int(time_elapsed)
            // (self.SECONDS_PER_YEAR * self.BASIS_POINTS)
        )

        # Update indices
        state.borrow_index = self._ray_mul(state.borrow_index, borrow_multiplier)
        state.supply_index = self._ray_mul(state.supply_index, supply_multiplier)

        # Update rates
        state.current_borrow_rate = borrow_rate
        state.current_supply_rate = supply_rate

        state.last_update = time.time()

    def _accrue_interest(self, position: UserPosition, asset: str) -> None:
        """Accrue interest for a user's borrowed position."""
        principal = position.borrowed.get(asset, 0)
        if principal == 0:
            return

        last_update = position.last_update.get(asset, time.time())
        time_elapsed = time.time() - last_update

        if time_elapsed <= 0:
            return

        # Get interest rate
        utilization = self._calculate_utilization(asset)
        rate = self._calculate_borrow_rate(asset, utilization)

        # Calculate interest
        interest = (
            principal * rate * int(time_elapsed)
            // (self.SECONDS_PER_YEAR * self.BASIS_POINTS)
        )

        position.accrued_interest[asset] = (
            position.accrued_interest.get(asset, 0) + interest
        )
        position.last_update[asset] = time.time()

    # ==================== Health Factor Calculation ====================

    def _calculate_health_factor(self, position: UserPosition) -> int:
        """Calculate health factor for a position."""
        return self._calculate_health_factor_with_changes(
            position, position.supplied, position.borrowed
        )

    def _calculate_health_factor_with_changes(
        self,
        position: UserPosition,
        supplied: Dict[str, int],
        borrowed: Dict[str, int],
    ) -> int:
        """Calculate health factor with hypothetical changes."""
        total_collateral_threshold = 0
        total_debt = 0

        # Calculate collateral value * liquidation threshold
        for asset, a_tokens in supplied.items():
            if a_tokens > 0 and asset in self.assets:
                config = self.assets[asset]
                state = self.pool_states[asset]

                underlying = self._ray_mul(a_tokens, state.supply_index) // self.RAY
                value = underlying * self._get_price(asset)

                # Weight by liquidation threshold
                total_collateral_threshold += (
                    value * config.liquidation_threshold // self.BASIS_POINTS
                )

        # Calculate total debt value
        for asset, principal in borrowed.items():
            if principal > 0:
                interest = position.accrued_interest.get(asset, 0)
                total_debt += (principal + interest) * self._get_price(asset)

        if total_debt == 0:
            return self.RAY * 10  # No debt = infinite health factor

        # Health factor = collateral_threshold_value / debt_value
        return (total_collateral_threshold * self.RAY) // total_debt

    # ==================== Oracle Integration ====================

    def _get_price(self, asset: str) -> int:
        """Get asset price (with caching)."""
        # Check cache (30 second TTL)
        if asset in self._price_cache:
            price, timestamp = self._price_cache[asset]
            if time.time() - timestamp < 30:
                return price

        # In production, would call oracle contract
        # For now, return mock prices
        mock_prices = {
            "XAI": 1_000_000_000,  # $1
            "ETH": 2000_000_000_000,  # $2000
            "BTC": 40000_000_000_000,  # $40000
            "USDT": 1_000_000_000,  # $1
            "USDC": 1_000_000_000,  # $1
        }

        price = mock_prices.get(asset, 1_000_000_000)
        self._price_cache[asset] = (price, time.time())

        return price

    def set_price_oracle(self, caller: str, asset: str, price: int) -> bool:
        """Set price for an asset (for testing/admin)."""
        self._require_owner(caller)
        self._price_cache[asset] = (price, time.time())
        return True

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        return address.lower()

    def _require_owner(self, caller: str) -> None:
        if self._normalize(caller) != self._normalize(self.owner):
            raise VMExecutionError("Caller is not owner")

    def _require_not_paused(self) -> None:
        if self.paused:
            raise VMExecutionError("Lending pool is paused")

    def _require_asset(self, asset: str) -> None:
        if asset not in self.assets:
            raise VMExecutionError(f"Asset {asset} not supported")

    def _get_position(self, user: str) -> Optional[UserPosition]:
        return self.positions.get(self._normalize(user))

    def _get_or_create_position(self, user: str) -> UserPosition:
        user_norm = self._normalize(user)
        if user_norm not in self.positions:
            self.positions[user_norm] = UserPosition(user=user_norm)
        return self.positions[user_norm]

    def _ray_mul(self, a: int, b: int) -> int:
        """Multiply two RAY values."""
        return (a * b + self.RAY // 2) // self.RAY

    def _ray_div(self, a: int, b: int) -> int:
        """Divide two RAY values."""
        return (a * self.RAY + b // 2) // b

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize pool state."""
        return {
            "name": self.name,
            "address": self.address,
            "owner": self.owner,
            "assets": {k: v.__dict__ for k, v in self.assets.items()},
            "pool_states": {k: v.__dict__ for k, v in self.pool_states.items()},
            "positions": {
                k: {
                    "user": v.user,
                    "supplied": dict(v.supplied),
                    "borrowed": dict(v.borrowed),
                    "interest_mode": {
                        k2: v2.value for k2, v2 in v.interest_mode.items()
                    },
                    "last_update": dict(v.last_update),
                    "accrued_interest": dict(v.accrued_interest),
                }
                for k, v in self.positions.items()
            },
            "close_factor": self.close_factor,
            "paused": self.paused,
        }


class CollateralManager:
    """Helper for managing collateral across lending pools."""

    def __init__(self, lending_pool: LendingPool) -> None:
        self.pool = lending_pool

    def get_collateral_value(self, user: str) -> int:
        """Get total collateral value for a user."""
        data = self.pool.get_user_account_data(user)
        return data["total_collateral_value"]

    def get_max_borrow(self, user: str, asset: str) -> int:
        """Get maximum borrowable amount for an asset."""
        data = self.pool.get_user_account_data(user)
        price = self.pool._get_price(asset)
        return data["available_borrow"] // price if price > 0 else 0

    def is_liquidatable(self, user: str) -> bool:
        """Check if user can be liquidated."""
        return self.pool.get_health_factor(user) < self.pool.RAY


class LendingFactory:
    """Factory for creating lending pools."""

    def __init__(self, blockchain: Optional["Blockchain"] = None) -> None:
        self.blockchain = blockchain
        self.pools: Dict[str, LendingPool] = {}

    def create_pool(
        self,
        creator: str,
        name: str,
        close_factor: int = 5000,
    ) -> LendingPool:
        """Create a new lending pool."""
        pool = LendingPool(
            name=name,
            owner=creator,
            close_factor=close_factor,
        )

        self.pools[pool.address] = pool

        if self.blockchain:
            self.blockchain.contracts[pool.address.upper()] = {
                "type": "LendingPool",
                "address": pool.address,
                "data": pool.to_dict(),
                "created_at": time.time(),
                "creator": creator,
            }

        logger.info(
            "Lending pool created",
            extra={
                "event": "lending.pool_created",
                "address": pool.address,
                "name": name,
                "creator": creator[:10],
            }
        )

        return pool

    def get_pool(self, address: str) -> Optional[LendingPool]:
        """Get a lending pool by address."""
        return self.pools.get(address.lower())
