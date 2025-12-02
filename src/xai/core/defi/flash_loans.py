"""
Flash Loan Implementation.

Provides uncollateralized loans that must be repaid within a single transaction.
Used for arbitrage, collateral swaps, and liquidations.

Security features:
- Same-transaction repayment enforcement
- Fee collection
- Reentrancy protection
- Balance verification
"""

from __future__ import annotations

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, TYPE_CHECKING

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


@dataclass
class FlashLoanRequest:
    """Flash loan request details."""

    id: str
    borrower: str
    assets: List[str]
    amounts: List[int]
    fee_amounts: List[int]
    receiver_callback: Optional[Callable] = None
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # pending, executing, repaid, defaulted


@dataclass
class FlashLoanProvider:
    """
    Flash loan provider implementation.

    Provides uncollateralized loans that must be repaid in the same transaction
    plus a fee. Commonly used for:
    - Arbitrage across DEXes
    - Collateral swaps
    - Self-liquidation
    - Leverage adjustment

    Security features:
    - Atomic execution (repayment enforced in same tx)
    - Balance verification before/after
    - Reentrancy protection
    - Fee collection
    """

    name: str = "XAI Flash Loans"
    address: str = ""
    owner: str = ""

    # Supported assets and their pools
    liquidity_pools: Dict[str, int] = field(default_factory=dict)  # asset -> amount

    # Fee configuration (basis points)
    flash_loan_fee: int = 9  # 0.09% (same as Aave)

    # Protocol reserves
    collected_fees: Dict[str, int] = field(default_factory=dict)

    # Active loans (for reentrancy protection)
    _active_loans: Dict[str, FlashLoanRequest] = field(default_factory=dict)
    _execution_lock: threading.Lock = field(default_factory=threading.Lock)

    # Statistics
    total_loans: int = 0
    total_volume: Dict[str, int] = field(default_factory=dict)

    # Constants
    BASIS_POINTS: int = 10000

    def __post_init__(self) -> None:
        """Initialize provider."""
        if not self.address:
            import hashlib
            addr_hash = hashlib.sha3_256(f"{self.name}{time.time()}".encode()).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Flash Loan Operations ====================

    def flash_loan(
        self,
        borrower: str,
        receiver: str,
        assets: List[str],
        amounts: List[int],
        callback: Optional[Callable[[str, List[str], List[int], List[int], bytes], bool]] = None,
        params: bytes = b"",
    ) -> bool:
        """
        Execute a flash loan.

        The callback function must return True and the borrowed amounts
        plus fees must be returned to this contract before the function returns.

        Args:
            borrower: Address initiating the loan
            receiver: Address receiving the funds and callback
            assets: List of asset addresses/symbols
            amounts: List of amounts to borrow
            callback: Function to execute with borrowed funds
            params: Additional params to pass to callback

        Returns:
            True if successful

        Raises:
            VMExecutionError: If loan cannot be executed or repaid
        """
        if len(assets) != len(amounts):
            raise VMExecutionError("Assets and amounts length mismatch")

        if len(assets) == 0:
            raise VMExecutionError("Must borrow at least one asset")

        # Generate loan ID
        loan_id = f"{borrower}:{time.time()}"

        # Check for reentrancy
        with self._execution_lock:
            if borrower in self._active_loans:
                raise VMExecutionError("Flash loan already in progress for borrower")

            # Calculate fees
            fee_amounts = [
                (amount * self.flash_loan_fee) // self.BASIS_POINTS
                for amount in amounts
            ]

            # Verify liquidity
            for i, asset in enumerate(assets):
                pool_liquidity = self.liquidity_pools.get(asset, 0)
                if amounts[i] > pool_liquidity:
                    raise VMExecutionError(
                        f"Insufficient liquidity for {asset}: "
                        f"requested {amounts[i]}, available {pool_liquidity}"
                    )

            # Record loan
            loan = FlashLoanRequest(
                id=loan_id,
                borrower=borrower,
                assets=assets,
                amounts=amounts,
                fee_amounts=fee_amounts,
                receiver_callback=callback,
                status="executing",
            )
            self._active_loans[borrower] = loan

        try:
            # Record balances before
            balances_before = {
                asset: self.liquidity_pools.get(asset, 0)
                for asset in assets
            }

            # "Transfer" funds to borrower (in real impl would be actual transfer)
            for i, asset in enumerate(assets):
                self.liquidity_pools[asset] = (
                    self.liquidity_pools.get(asset, 0) - amounts[i]
                )

            logger.info(
                "Flash loan executed",
                extra={
                    "event": "flash_loan.borrow",
                    "loan_id": loan_id,
                    "borrower": borrower[:10],
                    "assets": assets,
                    "amounts": amounts,
                }
            )

            # Execute callback
            if callback:
                success = callback(
                    borrower,  # initiator
                    assets,
                    amounts,
                    fee_amounts,
                    params,
                )
                if not success:
                    raise VMExecutionError("Flash loan callback failed")

            # Verify repayment by checking actual pool balances
            # The callback MUST have returned the borrowed funds + fees
            # We verify by comparing current balance to expected balance
            #
            # SECURITY: Two-step verification to prevent attack where only fees are paid
            # 1. Verify principal was returned (balance >= original)
            # 2. Verify fees were paid (balance >= original + fees)

            for i, asset in enumerate(assets):
                current_balance = self.liquidity_pools.get(asset, 0)
                original_balance = balances_before[asset]
                required_return = amounts[i] + fee_amounts[i]
                expected_with_fees = original_balance + fee_amounts[i]

                # CRITICAL SECURITY CHECK #1: Verify principal was returned
                # Attack scenario: Attacker borrows 1000 tokens, pays only 9 token fee, keeps 1000
                # This check prevents that by ensuring balance is at least back to original
                if current_balance < original_balance:
                    principal_shortfall = original_balance - current_balance
                    logger.error(
                        "Flash loan principal not repaid",
                        extra={
                            "event": "flash_loan.principal_not_repaid",
                            "asset": asset,
                            "borrowed": amounts[i],
                            "original_balance": original_balance,
                            "current_balance": current_balance,
                            "principal_shortfall": principal_shortfall,
                            "borrower": borrower[:16],
                        }
                    )
                    raise VMExecutionError(
                        f"Flash loan principal not repaid for {asset}: "
                        f"borrowed {amounts[i]}, "
                        f"original balance {original_balance}, "
                        f"current balance {current_balance}, "
                        f"shortfall {principal_shortfall}"
                    )

                # CRITICAL SECURITY CHECK #2: Verify fees were paid
                # After confirming principal is back, verify the required fees were also paid
                # Expected balance = original + fees (not original + principal + fees, since principal
                # was borrowed from the pool, so returning it gets us back to original)
                if current_balance < expected_with_fees:
                    fee_shortfall = expected_with_fees - current_balance
                    logger.error(
                        "Flash loan fees not paid",
                        extra={
                            "event": "flash_loan.fees_not_paid",
                            "asset": asset,
                            "required_fee": fee_amounts[i],
                            "expected_balance": expected_with_fees,
                            "current_balance": current_balance,
                            "fee_shortfall": fee_shortfall,
                            "borrower": borrower[:16],
                        }
                    )
                    raise VMExecutionError(
                        f"Flash loan fees not paid for {asset}: "
                        f"required fee {fee_amounts[i]}, "
                        f"expected balance {expected_with_fees}, "
                        f"current balance {current_balance}, "
                        f"fee shortfall {fee_shortfall}"
                    )

                # Log successful repayment verification
                logger.info(
                    "Flash loan repayment verified",
                    extra={
                        "event": "flash_loan.repayment_verified",
                        "asset": asset,
                        "principal": amounts[i],
                        "fee": fee_amounts[i],
                        "total_returned": required_return,
                        "new_balance": current_balance,
                        "borrower": borrower[:10],
                    }
                )

                # Collect fees
                self.collected_fees[asset] = (
                    self.collected_fees.get(asset, 0) + fee_amounts[i]
                )

                # Update statistics
                self.total_volume[asset] = (
                    self.total_volume.get(asset, 0) + amounts[i]
                )

            loan.status = "repaid"
            self.total_loans += 1

            logger.info(
                "Flash loan repaid",
                extra={
                    "event": "flash_loan.repaid",
                    "loan_id": loan_id,
                    "borrower": borrower[:10],
                    "fees_paid": fee_amounts,
                }
            )

            return True

        except Exception as e:
            # Revert state on failure
            for i, asset in enumerate(assets):
                self.liquidity_pools[asset] = (
                    self.liquidity_pools.get(asset, 0) + amounts[i]
                )
            loan.status = "defaulted"
            raise VMExecutionError(f"Flash loan failed: {e}")

        finally:
            # Clean up active loan
            with self._execution_lock:
                if borrower in self._active_loans:
                    del self._active_loans[borrower]

    def flash_loan_simple(
        self,
        borrower: str,
        asset: str,
        amount: int,
        callback: Optional[Callable[[str, str, int, int, bytes], bool]] = None,
        params: bytes = b"",
    ) -> bool:
        """
        Simple flash loan for a single asset.

        Args:
            borrower: Borrower address
            asset: Asset to borrow
            amount: Amount to borrow
            callback: Callback function
            params: Additional params

        Returns:
            True if successful
        """
        # Wrap single asset in multi-asset interface
        def wrapped_callback(
            initiator: str,
            assets: List[str],
            amounts: List[int],
            fees: List[int],
            data: bytes,
        ) -> bool:
            if callback:
                return callback(initiator, assets[0], amounts[0], fees[0], data)
            return True

        return self.flash_loan(
            borrower=borrower,
            receiver=borrower,
            assets=[asset],
            amounts=[amount],
            callback=wrapped_callback,
            params=params,
        )

    # ==================== Liquidity Management ====================

    def add_liquidity(self, caller: str, asset: str, amount: int) -> bool:
        """
        Add liquidity to the flash loan pool.

        SECURITY: Owner-only access to prevent unauthorized liquidity manipulation.
        Unrestricted liquidity addition could allow attackers to:
        - Manipulate pool pricing and create artificial trading advantages
        - Disrupt fee calculations and economics
        - Front-run legitimate liquidity operations
        - Create imbalanced pools for exploit opportunities

        Args:
            caller: Liquidity provider (must be owner)
            asset: Asset symbol
            amount: Amount to add

        Returns:
            True if successful

        Raises:
            VMExecutionError: If caller is not owner or amount is invalid
        """
        # CRITICAL SECURITY: Require owner authorization
        # This prevents unauthorized liquidity manipulation attacks
        self._require_owner(caller)

        if amount <= 0:
            raise VMExecutionError("Amount must be positive")

        previous_balance = self.liquidity_pools.get(asset, 0)
        self.liquidity_pools[asset] = previous_balance + amount

        logger.info(
            "Liquidity added to flash loan pool",
            extra={
                "event": "flash_loan.liquidity_added",
                "owner": caller[:10],
                "asset": asset,
                "amount": amount,
                "previous_balance": previous_balance,
                "new_balance": self.liquidity_pools[asset],
            }
        )

        return True

    def remove_liquidity(self, caller: str, asset: str, amount: int) -> bool:
        """
        Remove liquidity from the flash loan pool.

        Args:
            caller: Liquidity provider
            asset: Asset symbol
            amount: Amount to remove

        Returns:
            True if successful
        """
        self._require_owner(caller)

        current = self.liquidity_pools.get(asset, 0)
        if amount > current:
            raise VMExecutionError(f"Insufficient liquidity: {amount} > {current}")

        self.liquidity_pools[asset] = current - amount

        return True

    # ==================== Fee Management ====================

    def set_flash_loan_fee(self, caller: str, fee: int) -> bool:
        """
        Set flash loan fee.

        Args:
            caller: Must be owner
            fee: Fee in basis points

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if fee > 1000:  # Max 10%
            raise VMExecutionError("Fee cannot exceed 10%")

        self.flash_loan_fee = fee
        return True

    def withdraw_fees(self, caller: str, asset: str, amount: int) -> bool:
        """
        Withdraw collected fees.

        Args:
            caller: Must be owner
            asset: Asset to withdraw
            amount: Amount to withdraw

        Returns:
            True if successful
        """
        self._require_owner(caller)

        collected = self.collected_fees.get(asset, 0)
        if amount > collected:
            raise VMExecutionError(f"Insufficient fees: {amount} > {collected}")

        self.collected_fees[asset] = collected - amount
        return True

    # ==================== View Functions ====================

    def get_max_flash_loan(self, asset: str) -> int:
        """Get maximum flash loan amount for an asset."""
        return self.liquidity_pools.get(asset, 0)

    def get_flash_loan_fee_amount(self, asset: str, amount: int) -> int:
        """Calculate fee for a flash loan."""
        return (amount * self.flash_loan_fee) // self.BASIS_POINTS

    def get_pool_stats(self) -> Dict:
        """Get flash loan pool statistics."""
        return {
            "total_loans": self.total_loans,
            "total_volume": dict(self.total_volume),
            "collected_fees": dict(self.collected_fees),
            "available_liquidity": dict(self.liquidity_pools),
            "fee_rate": self.flash_loan_fee,
        }

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        return address.lower()

    def _require_owner(self, caller: str) -> None:
        if self._normalize(caller) != self._normalize(self.owner):
            raise VMExecutionError("Caller is not owner")

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize state."""
        return {
            "name": self.name,
            "address": self.address,
            "owner": self.owner,
            "liquidity_pools": dict(self.liquidity_pools),
            "flash_loan_fee": self.flash_loan_fee,
            "collected_fees": dict(self.collected_fees),
            "total_loans": self.total_loans,
            "total_volume": dict(self.total_volume),
        }
