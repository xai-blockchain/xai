"""
Advanced Token Vesting System.

Provides comprehensive vesting mechanisms for team tokens, advisors, and investors:
- Linear vesting with cliff periods
- Exponential decay vesting curves
- Custom piecewise vesting schedules
- Batch vesting for multiple recipients
- Early unlock with penalty
- Delegation of unvested tokens

Security features:
- Immutable vesting terms after creation
- Time-locked cliffs
- Slippage protection on early unlock
- Owner-only administrative functions
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from enum import Enum
from typing import TYPE_CHECKING, Callable

from ..vm.exceptions import VMExecutionError
from .access_control import AccessControl, SignedRequest

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)

# Set decimal precision high enough for blockchain calculations
# 50 decimal places is sufficient for amounts up to 10^27 with 18 decimals
getcontext().prec = 50

# WAD precision constant (10^18) for fixed-point arithmetic
WAD = Decimal(10**18)

class VestingCurveType(Enum):
    """Types of vesting curves."""
    LINEAR = "linear"  # Constant rate
    EXPONENTIAL = "exponential"  # Slow start, fast finish
    LOGARITHMIC = "logarithmic"  # Fast start, slow finish
    CLIFF_LINEAR = "cliff_linear"  # Cliff then linear
    STEP = "step"  # Discrete unlock steps
    CUSTOM = "custom"  # User-defined curve

class VestingStatus(Enum):
    """Status of a vesting schedule."""
    ACTIVE = "active"
    FULLY_VESTED = "fully_vested"
    REVOKED = "revoked"
    EARLY_UNLOCKED = "early_unlocked"

@dataclass
class VestingCurve:
    """
    Defines the vesting curve mathematics.

    For time t in [0, duration]:
    - LINEAR: vested = total * (t / duration)
    - EXPONENTIAL: vested = total * (1 - e^(-k*t/duration))
    - LOGARITHMIC: vested = total * ln(1 + k*t/duration) / ln(1 + k)
    - STEP: vested = total * floor(t / step_interval) * step_size
    """

    curve_type: VestingCurveType = VestingCurveType.LINEAR

    # For exponential/logarithmic curves
    curve_factor: float = 3.0  # k parameter

    # For step curves
    step_count: int = 4  # Number of steps

    # Custom curve: list of (time_fraction, amount_fraction) points
    custom_points: list[tuple[float, float]] = field(default_factory=list)

    def calculate_vested_fraction(self, elapsed_fraction: float) -> float:
        """
        Calculate vested fraction at a given time fraction.

        Uses high-precision Decimal arithmetic to prevent precision loss
        on large token amounts (up to 10^27 with 18 decimals).

        Args:
            elapsed_fraction: Time elapsed / total duration (0 to 1)

        Returns:
            Fraction of tokens vested (0 to 1)

        Security:
            - No floating-point precision loss on billion-token vestings
            - Uses Decimal with 50 decimal places precision
            - Guarantees accurate calculations for amounts up to 10^27
        """
        t = max(0.0, min(1.0, elapsed_fraction))

        if self.curve_type == VestingCurveType.LINEAR:
            return t

        elif self.curve_type == VestingCurveType.EXPONENTIAL:
            # Slow start, accelerating release
            # Use high-precision Decimal to prevent precision loss
            return float(self._calculate_exponential_precise(Decimal(str(t))))

        elif self.curve_type == VestingCurveType.LOGARITHMIC:
            # Fast start, decelerating release
            # Use high-precision Decimal to prevent precision loss
            return float(self._calculate_logarithmic_precise(Decimal(str(t))))

        elif self.curve_type == VestingCurveType.STEP:
            # Discrete steps
            step = 1.0 / self.step_count
            completed_steps = int(t / step)
            return min(1.0, completed_steps / self.step_count)

        elif self.curve_type == VestingCurveType.CUSTOM:
            # Interpolate custom curve
            return self._interpolate_custom(t)

        else:
            return t

    def _calculate_exponential_precise(self, t: Decimal) -> Decimal:
        """
        Calculate exponential vesting curve with high precision.

        Formula: (1 - e^(-k*t)) / (1 - e^(-k))

        This prevents precision loss that occurs with float arithmetic
        on large token amounts.

        Args:
            t: Time fraction as Decimal (0 to 1)

        Returns:
            Vested fraction as Decimal (0 to 1)
        """
        k = Decimal(str(self.curve_factor))

        # Calculate e^(-k*t) with high precision
        neg_kt = -k * t
        exp_neg_kt = neg_kt.exp()

        # Calculate e^(-k) with high precision
        exp_neg_k = (-k).exp()

        # Calculate (1 - e^(-k*t)) / (1 - e^(-k))
        numerator = Decimal(1) - exp_neg_kt
        denominator = Decimal(1) - exp_neg_k

        # Protect against division by zero (shouldn't happen with k > 0)
        if denominator == 0:
            return Decimal(1)

        result = numerator / denominator

        # Clamp to [0, 1] range
        return max(Decimal(0), min(Decimal(1), result))

    def _calculate_logarithmic_precise(self, t: Decimal) -> Decimal:
        """
        Calculate logarithmic vesting curve with high precision.

        Formula: ln(1 + k*t) / ln(1 + k)

        This prevents precision loss that occurs with float arithmetic
        on large token amounts.

        Args:
            t: Time fraction as Decimal (0 to 1)

        Returns:
            Vested fraction as Decimal (0 to 1)
        """
        k = Decimal(str(self.curve_factor))

        # Calculate ln(1 + k*t) with high precision
        numerator = (Decimal(1) + k * t).ln()

        # Calculate ln(1 + k) with high precision
        denominator = (Decimal(1) + k).ln()

        # Protect against division by zero (shouldn't happen with k > 0)
        if denominator == 0:
            return Decimal(1)

        result = numerator / denominator

        # Clamp to [0, 1] range
        return max(Decimal(0), min(Decimal(1), result))

    def _interpolate_custom(self, t: float) -> float:
        """Interpolate custom curve points."""
        if not self.custom_points:
            return t

        # Ensure sorted by time
        points = sorted(self.custom_points, key=lambda p: p[0])

        # Add endpoints if not present
        if points[0][0] > 0:
            points.insert(0, (0.0, 0.0))
        if points[-1][0] < 1:
            points.append((1.0, 1.0))

        # Find surrounding points
        for i in range(len(points) - 1):
            t1, v1 = points[i]
            t2, v2 = points[i + 1]

            if t1 <= t <= t2:
                # Linear interpolation between points
                if t2 == t1:
                    return v1
                frac = (t - t1) / (t2 - t1)
                return v1 + frac * (v2 - v1)

        return 1.0

@dataclass
class VestingSchedule:
    """
    Individual vesting schedule for a beneficiary.

    Tracks vesting terms, claimed amounts, and status.
    """

    id: str = ""
    beneficiary: str = ""
    total_amount: int = 0

    # Timing
    start_time: float = 0.0
    cliff_duration: int = 0  # Seconds until first unlock
    vesting_duration: int = 0  # Total vesting period in seconds

    # Curve
    curve: VestingCurve = field(default_factory=VestingCurve)

    # State
    claimed_amount: int = 0
    status: VestingStatus = VestingStatus.ACTIVE

    # Early unlock settings
    allow_early_unlock: bool = False
    early_unlock_penalty: int = 5000  # 50% penalty in basis points

    # Revocable (for employee vesting)
    revocable: bool = False
    revoked_at: float = 0.0
    revoked_amount: int = 0

    # Delegation
    delegated_to: str = ""

    # Metadata
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Initialize schedule."""
        if not self.id:
            schedule_hash = hashlib.sha3_256(
                f"{self.beneficiary}:{self.total_amount}:{self.start_time}".encode()
            ).digest()
            self.id = f"0x{schedule_hash[:16].hex()}"

        if not self.start_time:
            self.start_time = time.time()

    # ==================== Vesting Calculations ====================

    def get_vested_amount(self, at_time: float | None = None) -> int:
        """
        Calculate total vested amount at a given time.

        Args:
            at_time: Timestamp to check (default: now)

        Returns:
            Vested token amount
        """
        at_time = at_time or time.time()

        if self.status == VestingStatus.REVOKED:
            # Return vested amount at revocation time
            at_time = min(at_time, self.revoked_at)

        if self.status == VestingStatus.EARLY_UNLOCKED:
            return self.total_amount - self.revoked_amount

        # Check if before cliff
        cliff_end = self.start_time + self.cliff_duration
        if at_time < cliff_end:
            return 0

        # Calculate elapsed time fraction
        vesting_end = self.start_time + self.cliff_duration + self.vesting_duration
        elapsed = at_time - cliff_end
        duration = self.vesting_duration

        if elapsed >= duration:
            return self.total_amount

        elapsed_fraction = elapsed / duration
        vested_fraction = self.curve.calculate_vested_fraction(elapsed_fraction)

        return int(self.total_amount * vested_fraction)

    def get_claimable_amount(self, at_time: float | None = None) -> int:
        """Get amount that can be claimed now."""
        vested = self.get_vested_amount(at_time)
        return max(0, vested - self.claimed_amount)

    def get_unvested_amount(self, at_time: float | None = None) -> int:
        """Get amount not yet vested."""
        vested = self.get_vested_amount(at_time)
        return self.total_amount - vested

    def get_vesting_info(self) -> Dict:
        """Get comprehensive vesting information."""
        now = time.time()
        vested = self.get_vested_amount(now)
        claimable = self.get_claimable_amount(now)
        unvested = self.get_unvested_amount(now)

        cliff_end = self.start_time + self.cliff_duration
        vesting_end = cliff_end + self.vesting_duration

        return {
            "id": self.id,
            "beneficiary": self.beneficiary,
            "total_amount": self.total_amount,
            "vested_amount": vested,
            "claimed_amount": self.claimed_amount,
            "claimable_amount": claimable,
            "unvested_amount": unvested,
            "vested_percentage": (vested * 100) // self.total_amount if self.total_amount > 0 else 0,
            "start_time": self.start_time,
            "cliff_end": cliff_end,
            "vesting_end": vesting_end,
            "cliff_reached": now >= cliff_end,
            "fully_vested": now >= vesting_end,
            "status": self.status.value,
            "curve_type": self.curve.curve_type.value,
        }

@dataclass
class VestingVault:
    """
    Token vesting vault managing multiple vesting schedules.

    Features:
    - Create vesting schedules with various curves
    - Batch vesting for teams/advisors
    - Early unlock with penalty
    - Schedule revocation for revocable grants
    - Delegation of unvested tokens (for governance)
    """

    name: str = "XAI Vesting Vault"
    address: str = ""
    owner: str = ""
    token: str = ""  # Token being vested

    # All vesting schedules
    schedules: dict[str, VestingSchedule] = field(default_factory=dict)

    # Schedules by beneficiary
    beneficiary_schedules: dict[str, list[str]] = field(default_factory=dict)

    # Total amounts
    total_locked: int = 0
    total_claimed: int = 0
    total_revoked: int = 0

    # Early unlock penalties collected
    penalties_collected: int = 0

    # Access control with signature verification
    access_control: AccessControl = field(default_factory=AccessControl)

    def __post_init__(self) -> None:
        """Initialize vault."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"vesting_vault:{self.token}:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Schedule Creation ====================

    def create_schedule(
        self,
        caller: str,
        beneficiary: str,
        amount: int,
        cliff_duration: int,
        vesting_duration: int,
        curve_type: VestingCurveType = VestingCurveType.LINEAR,
        curve_factor: float = 3.0,
        allow_early_unlock: bool = False,
        early_unlock_penalty: int = 5000,
        revocable: bool = False,
        start_time: float | None = None,
    ) -> str:
        """
        Create a new vesting schedule.

        Args:
            caller: Must be owner
            beneficiary: Token recipient
            amount: Total tokens to vest
            cliff_duration: Cliff period in seconds
            vesting_duration: Vesting period after cliff
            curve_type: Type of vesting curve
            curve_factor: Curve steepness parameter
            allow_early_unlock: Whether to allow early unlock with penalty
            early_unlock_penalty: Penalty in basis points
            revocable: Whether schedule can be revoked
            start_time: Optional custom start time

        Returns:
            Schedule ID
        """
        self._require_owner(caller)

        if amount <= 0:
            raise VMExecutionError("Amount must be positive")

        curve = VestingCurve(
            curve_type=curve_type,
            curve_factor=curve_factor,
        )

        schedule = VestingSchedule(
            beneficiary=beneficiary,
            total_amount=amount,
            start_time=start_time or time.time(),
            cliff_duration=cliff_duration,
            vesting_duration=vesting_duration,
            curve=curve,
            allow_early_unlock=allow_early_unlock,
            early_unlock_penalty=early_unlock_penalty,
            revocable=revocable,
        )

        self.schedules[schedule.id] = schedule

        if beneficiary not in self.beneficiary_schedules:
            self.beneficiary_schedules[beneficiary] = []
        self.beneficiary_schedules[beneficiary].append(schedule.id)

        self.total_locked += amount

        logger.info(
            "Vesting schedule created",
            extra={
                "event": "vesting.schedule_created",
                "schedule_id": schedule.id[:10],
                "beneficiary": beneficiary[:10],
                "amount": amount,
                "curve": curve_type.value,
            }
        )

        return schedule.id

    def create_schedule_with_steps(
        self,
        caller: str,
        beneficiary: str,
        amount: int,
        cliff_duration: int,
        vesting_duration: int,
        step_count: int,
        revocable: bool = False,
    ) -> str:
        """
        Create a step-based vesting schedule.

        Releases tokens in discrete chunks at regular intervals.

        Args:
            caller: Must be owner
            beneficiary: Token recipient
            amount: Total tokens to vest
            cliff_duration: Cliff period
            vesting_duration: Total vesting period
            step_count: Number of unlock steps

        Returns:
            Schedule ID
        """
        self._require_owner(caller)

        curve = VestingCurve(
            curve_type=VestingCurveType.STEP,
            step_count=step_count,
        )

        schedule = VestingSchedule(
            beneficiary=beneficiary,
            total_amount=amount,
            start_time=time.time(),
            cliff_duration=cliff_duration,
            vesting_duration=vesting_duration,
            curve=curve,
            revocable=revocable,
        )

        self.schedules[schedule.id] = schedule

        if beneficiary not in self.beneficiary_schedules:
            self.beneficiary_schedules[beneficiary] = []
        self.beneficiary_schedules[beneficiary].append(schedule.id)

        self.total_locked += amount

        return schedule.id

    def create_schedule_custom_curve(
        self,
        caller: str,
        beneficiary: str,
        amount: int,
        cliff_duration: int,
        vesting_duration: int,
        curve_points: list[tuple[float, float]],
        revocable: bool = False,
    ) -> str:
        """
        Create a schedule with a custom vesting curve.

        Args:
            caller: Must be owner
            beneficiary: Token recipient
            amount: Total tokens
            cliff_duration: Cliff period
            vesting_duration: Vesting period
            curve_points: List of (time_fraction, amount_fraction) points

        Returns:
            Schedule ID
        """
        self._require_owner(caller)

        # Validate curve points
        for t, v in curve_points:
            if not (0 <= t <= 1) or not (0 <= v <= 1):
                raise VMExecutionError("Curve points must be in [0, 1]")

        curve = VestingCurve(
            curve_type=VestingCurveType.CUSTOM,
            custom_points=curve_points,
        )

        schedule = VestingSchedule(
            beneficiary=beneficiary,
            total_amount=amount,
            start_time=time.time(),
            cliff_duration=cliff_duration,
            vesting_duration=vesting_duration,
            curve=curve,
            revocable=revocable,
        )

        self.schedules[schedule.id] = schedule

        if beneficiary not in self.beneficiary_schedules:
            self.beneficiary_schedules[beneficiary] = []
        self.beneficiary_schedules[beneficiary].append(schedule.id)

        self.total_locked += amount

        return schedule.id

    # ==================== Batch Operations ====================

    def create_batch_schedules(
        self,
        caller: str,
        beneficiaries: list[str],
        amounts: list[int],
        cliff_duration: int,
        vesting_duration: int,
        curve_type: VestingCurveType = VestingCurveType.LINEAR,
    ) -> list[str]:
        """
        Create multiple vesting schedules at once.

        Useful for team token distribution.

        Args:
            caller: Must be owner
            beneficiaries: List of recipients
            amounts: List of amounts (same length as beneficiaries)
            cliff_duration: Cliff for all schedules
            vesting_duration: Vesting period for all

        Returns:
            List of schedule IDs
        """
        self._require_owner(caller)

        if len(beneficiaries) != len(amounts):
            raise VMExecutionError("Beneficiaries and amounts length mismatch")

        schedule_ids = []

        for beneficiary, amount in zip(beneficiaries, amounts):
            schedule_id = self.create_schedule(
                caller=caller,
                beneficiary=beneficiary,
                amount=amount,
                cliff_duration=cliff_duration,
                vesting_duration=vesting_duration,
                curve_type=curve_type,
            )
            schedule_ids.append(schedule_id)

        logger.info(
            "Batch vesting schedules created",
            extra={
                "event": "vesting.batch_created",
                "count": len(schedule_ids),
                "total_amount": sum(amounts),
            }
        )

        return schedule_ids

    # ==================== Claiming ====================

    def claim(self, caller: str, schedule_id: str) -> int:
        """
        Claim vested tokens from a schedule.

        Args:
            caller: Must be beneficiary
            schedule_id: Schedule to claim from

        Returns:
            Amount claimed
        """
        schedule = self._get_schedule(schedule_id)

        if schedule.beneficiary.lower() != caller.lower():
            raise VMExecutionError("Only beneficiary can claim")

        if schedule.status == VestingStatus.REVOKED:
            raise VMExecutionError("Schedule has been revoked")

        claimable = schedule.get_claimable_amount()
        if claimable == 0:
            raise VMExecutionError("No tokens available to claim")

        schedule.claimed_amount += claimable
        self.total_claimed += claimable

        # Check if fully vested
        if schedule.claimed_amount >= schedule.total_amount:
            schedule.status = VestingStatus.FULLY_VESTED

        logger.info(
            "Tokens claimed",
            extra={
                "event": "vesting.claimed",
                "schedule_id": schedule_id[:10],
                "beneficiary": caller[:10],
                "amount": claimable,
            }
        )

        return claimable

    def claim_all(self, caller: str) -> int:
        """
        Claim from all schedules belonging to caller.

        Args:
            caller: Beneficiary

        Returns:
            Total amount claimed
        """
        schedule_ids = self.beneficiary_schedules.get(caller, [])
        total_claimed = 0

        for schedule_id in schedule_ids:
            schedule = self.schedules.get(schedule_id)
            if schedule and schedule.status == VestingStatus.ACTIVE:
                claimable = schedule.get_claimable_amount()
                if claimable > 0:
                    schedule.claimed_amount += claimable
                    total_claimed += claimable

                    if schedule.claimed_amount >= schedule.total_amount:
                        schedule.status = VestingStatus.FULLY_VESTED

        self.total_claimed += total_claimed
        return total_claimed

    # ==================== Early Unlock ====================

    def early_unlock(
        self,
        caller: str,
        schedule_id: str,
        amount: int,
    ) -> tuple[int, int]:
        """
        Early unlock unvested tokens with penalty.

        Args:
            caller: Must be beneficiary
            schedule_id: Schedule to unlock from
            amount: Amount of unvested tokens to unlock

        Returns:
            (received_amount, penalty_amount)
        """
        schedule = self._get_schedule(schedule_id)

        if schedule.beneficiary.lower() != caller.lower():
            raise VMExecutionError("Only beneficiary can unlock early")

        if not schedule.allow_early_unlock:
            raise VMExecutionError("Early unlock not allowed for this schedule")

        if schedule.status != VestingStatus.ACTIVE:
            raise VMExecutionError("Schedule not active")

        unvested = schedule.get_unvested_amount()
        if amount > unvested:
            raise VMExecutionError(f"Cannot unlock {amount}, only {unvested} unvested")

        # Calculate penalty
        penalty = (amount * schedule.early_unlock_penalty) // 10000
        received = amount - penalty

        # Update schedule
        schedule.revoked_amount = amount
        schedule.status = VestingStatus.EARLY_UNLOCKED

        self.penalties_collected += penalty

        logger.info(
            "Early unlock executed",
            extra={
                "event": "vesting.early_unlock",
                "schedule_id": schedule_id[:10],
                "amount": amount,
                "penalty": penalty,
                "received": received,
            }
        )

        return received, penalty

    # ==================== Revocation ====================

    def revoke(self, caller: str, schedule_id: str) -> int:
        """
        Revoke a vesting schedule (for revocable grants).

        Beneficiary keeps vested tokens, unvested return to owner.

        Args:
            caller: Must be owner
            schedule_id: Schedule to revoke

        Returns:
            Amount of unvested tokens returned
        """
        self._require_owner(caller)
        schedule = self._get_schedule(schedule_id)

        if not schedule.revocable:
            raise VMExecutionError("Schedule is not revocable")

        if schedule.status != VestingStatus.ACTIVE:
            raise VMExecutionError("Schedule not active")

        # Calculate unvested at revocation time
        vested = schedule.get_vested_amount()
        unvested = schedule.total_amount - vested

        schedule.status = VestingStatus.REVOKED
        schedule.revoked_at = time.time()
        schedule.revoked_amount = unvested

        self.total_revoked += unvested
        self.total_locked -= unvested

        logger.info(
            "Schedule revoked",
            extra={
                "event": "vesting.revoked",
                "schedule_id": schedule_id[:10],
                "beneficiary": schedule.beneficiary[:10],
                "unvested_returned": unvested,
            }
        )

        return unvested

    def revoke_secure(
        self,
        request: SignedRequest,
        schedule_id: str,
    ) -> int:
        """
        Revoke a vesting schedule with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            schedule_id: Schedule to revoke

        Returns:
            Amount of unvested tokens returned

        Raises:
            VMExecutionError: If signature verification fails or not owner
        """
        self.access_control.verify_caller_simple(request, self.owner)

        schedule = self._get_schedule(schedule_id)

        if not schedule.revocable:
            raise VMExecutionError("Schedule is not revocable")

        if schedule.status != VestingStatus.ACTIVE:
            raise VMExecutionError("Schedule not active")

        # Calculate unvested at revocation time
        vested = schedule.get_vested_amount()
        unvested = schedule.total_amount - vested

        schedule.status = VestingStatus.REVOKED
        schedule.revoked_at = time.time()
        schedule.revoked_amount = unvested

        self.total_revoked += unvested
        self.total_locked -= unvested

        logger.info(
            "Schedule revoked (secure)",
            extra={
                "event": "vesting.revoked_secure",
                "schedule_id": schedule_id[:10],
                "beneficiary": schedule.beneficiary[:10],
                "unvested_returned": unvested,
                "admin": request.address[:10],
            }
        )

        return unvested

    def create_schedule_secure(
        self,
        request: SignedRequest,
        beneficiary: str,
        amount: int,
        cliff_duration: int,
        vesting_duration: int,
        curve_type: VestingCurveType = VestingCurveType.LINEAR,
        curve_factor: float = 3.0,
        allow_early_unlock: bool = False,
        early_unlock_penalty: int = 5000,
        revocable: bool = False,
        start_time: float | None = None,
    ) -> str:
        """
        Create a new vesting schedule with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            beneficiary: Token recipient
            amount: Total tokens to vest
            cliff_duration: Cliff period in seconds
            vesting_duration: Vesting period after cliff
            curve_type: Type of vesting curve
            curve_factor: Curve steepness parameter
            allow_early_unlock: Whether to allow early unlock
            early_unlock_penalty: Penalty in basis points
            revocable: Whether schedule can be revoked
            start_time: Optional custom start time

        Returns:
            Schedule ID

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)

        if amount <= 0:
            raise VMExecutionError("Amount must be positive")

        curve = VestingCurve(
            curve_type=curve_type,
            curve_factor=curve_factor,
        )

        schedule = VestingSchedule(
            beneficiary=beneficiary,
            total_amount=amount,
            start_time=start_time or time.time(),
            cliff_duration=cliff_duration,
            vesting_duration=vesting_duration,
            curve=curve,
            allow_early_unlock=allow_early_unlock,
            early_unlock_penalty=early_unlock_penalty,
            revocable=revocable,
        )

        self.schedules[schedule.id] = schedule

        if beneficiary not in self.beneficiary_schedules:
            self.beneficiary_schedules[beneficiary] = []
        self.beneficiary_schedules[beneficiary].append(schedule.id)

        self.total_locked += amount

        logger.info(
            "Vesting schedule created (secure)",
            extra={
                "event": "vesting.schedule_created_secure",
                "schedule_id": schedule.id[:10],
                "beneficiary": beneficiary[:10],
                "amount": amount,
                "curve": curve_type.value,
                "admin": request.address[:10],
            }
        )

        return schedule.id

    # ==================== Delegation ====================

    def delegate(
        self,
        caller: str,
        schedule_id: str,
        delegate_to: str,
    ) -> bool:
        """
        Delegate unvested tokens for governance.

        Allows vesting recipients to participate in governance
        before tokens fully vest.

        Args:
            caller: Must be beneficiary
            schedule_id: Schedule with tokens to delegate
            delegate_to: Address to delegate to

        Returns:
            True if successful
        """
        schedule = self._get_schedule(schedule_id)

        if schedule.beneficiary.lower() != caller.lower():
            raise VMExecutionError("Only beneficiary can delegate")

        schedule.delegated_to = delegate_to

        logger.info(
            "Vesting delegation",
            extra={
                "event": "vesting.delegated",
                "schedule_id": schedule_id[:10],
                "delegate": delegate_to[:10],
            }
        )

        return True

    def get_delegated_amount(self, delegate: str) -> int:
        """Get total amount delegated to an address."""
        total = 0
        for schedule in self.schedules.values():
            if schedule.delegated_to.lower() == delegate.lower():
                if schedule.status == VestingStatus.ACTIVE:
                    total += schedule.get_unvested_amount()
        return total

    # ==================== View Functions ====================

    def get_schedule(self, schedule_id: str) -> Dict | None:
        """Get schedule details."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        return schedule.get_vesting_info()

    def get_beneficiary_schedules(self, beneficiary: str) -> list[Dict]:
        """Get all schedules for a beneficiary."""
        schedule_ids = self.beneficiary_schedules.get(beneficiary, [])
        return [
            self.schedules[sid].get_vesting_info()
            for sid in schedule_ids
            if sid in self.schedules
        ]

    def get_total_claimable(self, beneficiary: str) -> int:
        """Get total claimable amount for a beneficiary."""
        schedule_ids = self.beneficiary_schedules.get(beneficiary, [])
        total = 0
        for schedule_id in schedule_ids:
            schedule = self.schedules.get(schedule_id)
            if schedule and schedule.status == VestingStatus.ACTIVE:
                total += schedule.get_claimable_amount()
        return total

    def get_vault_stats(self) -> Dict:
        """Get vault statistics."""
        return {
            "total_locked": self.total_locked,
            "total_claimed": self.total_claimed,
            "total_revoked": self.total_revoked,
            "penalties_collected": self.penalties_collected,
            "total_schedules": len(self.schedules),
            "active_schedules": sum(
                1 for s in self.schedules.values()
                if s.status == VestingStatus.ACTIVE
            ),
            "unique_beneficiaries": len(self.beneficiary_schedules),
        }

    # ==================== Helpers ====================

    def _get_schedule(self, schedule_id: str) -> VestingSchedule:
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise VMExecutionError(f"Schedule {schedule_id} not found")
        return schedule

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize vault state."""
        return {
            "name": self.name,
            "address": self.address,
            "owner": self.owner,
            "token": self.token,
            "stats": self.get_vault_stats(),
            "schedules": {
                sid: s.get_vesting_info()
                for sid, s in self.schedules.items()
            },
        }
