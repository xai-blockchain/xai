"""
Emergency Circuit Breaker System.

Provides automated and manual safety mechanisms for DeFi protocols:
- Price deviation circuit breakers
- Collateral ratio monitoring
- Volume spike detection
- Oracle failure fallback
- Emergency pause functionality
- Time-delayed recovery

Security features:
- Multi-sig emergency actions
- Automated threat detection
- Graceful degradation
- Audit trail for all actions
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable

from ..vm.exceptions import VMExecutionError
from .access_control import AccessControl, Role, RoleBasedAccessControl, SignedRequest

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)

class BreakerType(Enum):
    """Types of circuit breakers."""
    PRICE_DEVIATION = "price_deviation"
    COLLATERAL_RATIO = "collateral_ratio"
    VOLUME_SPIKE = "volume_spike"
    ORACLE_FAILURE = "oracle_failure"
    LIQUIDITY_DRAIN = "liquidity_drain"
    GAS_SPIKE = "gas_spike"
    CUSTOM = "custom"

class BreakerStatus(Enum):
    """Status of a circuit breaker."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    COOLING_DOWN = "cooling_down"
    DISABLED = "disabled"

class ProtectionLevel(Enum):
    """Level of protection when breaker triggers."""
    WARN = "warn"  # Log warning only
    LIMIT = "limit"  # Limit operations
    PAUSE = "pause"  # Pause affected operations
    HALT = "halt"  # Complete halt

@dataclass
class BreakerEvent:
    """Record of a circuit breaker event."""
    breaker_id: str
    event_type: str  # "triggered", "recovered", "manual_override"
    timestamp: float
    details: Dict
    actor: str = ""  # Who triggered (address or "system")

@dataclass
class CircuitBreaker:
    """
    Individual circuit breaker configuration.

    Monitors a specific metric and triggers when thresholds are exceeded.
    """

    id: str = ""
    name: str = ""
    breaker_type: BreakerType = BreakerType.CUSTOM

    # Target (pool, protocol, or system-wide)
    target: str = ""

    # Thresholds
    warning_threshold: int = 0
    trigger_threshold: int = 0

    # Time windows
    monitoring_window: int = 300  # 5 minutes default
    cooldown_period: int = 3600  # 1 hour cooldown after trigger

    # Protection level
    protection_level: ProtectionLevel = ProtectionLevel.PAUSE

    # Status
    status: BreakerStatus = BreakerStatus.ACTIVE
    triggered_at: float = 0.0
    cooldown_until: float = 0.0

    # Metrics history
    metrics_history: list[tuple[float, int]] = field(default_factory=list)
    max_history_size: int = 1000

    # Events
    events: list[BreakerEvent] = field(default_factory=list)

    # Recovery requirements
    require_manual_recovery: bool = False
    recovery_threshold: int = 0  # Value must drop below this to auto-recover

    def __post_init__(self) -> None:
        """Initialize breaker."""
        if not self.id:
            breaker_hash = hashlib.sha3_256(
                f"{self.name}:{self.target}:{time.time()}".encode()
            ).digest()
            self.id = f"0x{breaker_hash[:16].hex()}"

    def record_metric(self, value: int) -> str | None:
        """
        Record a metric value and check thresholds.

        Args:
            value: Current metric value

        Returns:
            Action to take ("warn", "trigger", None)
        """
        now = time.time()

        # Add to history
        self.metrics_history.append((now, value))

        # Trim old history
        cutoff = now - self.monitoring_window
        self.metrics_history = [
            (t, v) for t, v in self.metrics_history
            if t >= cutoff
        ][-self.max_history_size:]

        # Check if in cooldown
        if self.status == BreakerStatus.COOLING_DOWN:
            if now >= self.cooldown_until:
                self.status = BreakerStatus.ACTIVE
            else:
                return None

        # Skip if already triggered
        if self.status == BreakerStatus.TRIGGERED:
            # Check for auto-recovery
            if not self.require_manual_recovery and self.recovery_threshold > 0:
                if value < self.recovery_threshold:
                    self._recover("system")
            return None

        if self.status == BreakerStatus.DISABLED:
            return None

        # Check thresholds
        if value >= self.trigger_threshold:
            return "trigger"
        elif value >= self.warning_threshold:
            return "warn"

        return None

    def trigger(self, actor: str = "system", details: Dict | None = None) -> None:
        """Trigger the circuit breaker."""
        now = time.time()

        self.status = BreakerStatus.TRIGGERED
        self.triggered_at = now

        event = BreakerEvent(
            breaker_id=self.id,
            event_type="triggered",
            timestamp=now,
            details=details or {},
            actor=actor,
        )
        self.events.append(event)

        logger.warning(
            "Circuit breaker triggered",
            extra={
                "event": "breaker.triggered",
                "breaker_id": self.id[:10],
                "breaker_name": self.name,
                "target": self.target[:10] if self.target else "system",
                "level": self.protection_level.value,
            }
        )

    def _recover(self, actor: str) -> None:
        """Recover from triggered state."""
        now = time.time()

        self.status = BreakerStatus.COOLING_DOWN
        self.cooldown_until = now + self.cooldown_period

        event = BreakerEvent(
            breaker_id=self.id,
            event_type="recovered",
            timestamp=now,
            details={"recovery_actor": actor},
            actor=actor,
        )
        self.events.append(event)

        logger.info(
            "Circuit breaker recovered",
            extra={
                "event": "breaker.recovered",
                "breaker_id": self.id[:10],
                "cooldown_until": self.cooldown_until,
            }
        )

    def manual_recover(self, actor: str) -> bool:
        """Manually recover breaker (for require_manual_recovery)."""
        if self.status != BreakerStatus.TRIGGERED:
            return False

        self._recover(actor)
        return True

    def get_recent_events(self, limit: int = 10) -> list[Dict]:
        """Get recent breaker events."""
        return [
            {
                "breaker_id": e.breaker_id,
                "type": e.event_type,
                "timestamp": e.timestamp,
                "actor": e.actor,
                "details": e.details,
            }
            for e in self.events[-limit:]
        ]

@dataclass
class PriceDeviationBreaker(CircuitBreaker):
    """
    Circuit breaker for price deviation.

    Triggers when price moves too fast relative to TWAP or reference.
    """

    reference_price: int = 0
    twap_period: int = 3600  # 1 hour TWAP
    max_deviation_bps: int = 1000  # 10% deviation triggers

    def __post_init__(self) -> None:
        """Initialize price breaker."""
        super().__post_init__()
        self.breaker_type = BreakerType.PRICE_DEVIATION
        self.name = self.name or "Price Deviation Breaker"

    def check_price(self, current_price: int, twap: int | None = None) -> str | None:
        """
        Check price against reference/TWAP.

        Args:
            current_price: Current spot price
            twap: Optional TWAP (uses reference_price if not provided)

        Returns:
            Action to take
        """
        reference = twap or self.reference_price
        if reference == 0:
            return None

        # Calculate deviation in basis points
        deviation = abs(current_price - reference) * 10000 // reference

        # Update thresholds dynamically
        self.trigger_threshold = self.max_deviation_bps
        self.warning_threshold = self.max_deviation_bps * 7 // 10  # 70% of trigger

        return self.record_metric(deviation)

@dataclass
class CollateralRatioBreaker(CircuitBreaker):
    """
    Circuit breaker for collateral ratio monitoring.

    Triggers when system-wide collateralization drops too low.
    """

    min_collateral_ratio: int = 15000  # 150% minimum
    critical_ratio: int = 12000  # 120% critical

    def __post_init__(self) -> None:
        """Initialize collateral breaker."""
        super().__post_init__()
        self.breaker_type = BreakerType.COLLATERAL_RATIO
        self.name = self.name or "Collateral Ratio Breaker"
        self.trigger_threshold = self.critical_ratio
        self.warning_threshold = self.min_collateral_ratio

    def check_ratio(self, total_collateral: int, total_debt: int) -> str | None:
        """
        Check collateralization ratio.

        Args:
            total_collateral: Total collateral value
            total_debt: Total debt value

        Returns:
            Action to take
        """
        if total_debt == 0:
            return None

        ratio = total_collateral * 10000 // total_debt
        # Invert logic - lower ratio is worse
        # Use inverse for threshold comparison
        inverse = 10000 * 10000 // ratio if ratio > 0 else 100000

        return self.record_metric(inverse)

@dataclass
class VolumeSpikeBreaker(CircuitBreaker):
    """
    Circuit breaker for volume spike detection.

    Triggers on unusual trading volume that might indicate attack.
    """

    baseline_volume: int = 0
    spike_multiplier: int = 10  # 10x normal volume triggers

    def __post_init__(self) -> None:
        """Initialize volume breaker."""
        super().__post_init__()
        self.breaker_type = BreakerType.VOLUME_SPIKE
        self.name = self.name or "Volume Spike Breaker"

    def check_volume(self, current_volume: int) -> str | None:
        """Check if volume is spiking."""
        if self.baseline_volume == 0:
            return None

        ratio = current_volume * 100 // self.baseline_volume
        self.trigger_threshold = self.spike_multiplier * 100
        self.warning_threshold = self.spike_multiplier * 50  # 5x

        return self.record_metric(ratio)

    def update_baseline(self, new_baseline: int) -> None:
        """Update baseline volume (e.g., from moving average)."""
        self.baseline_volume = new_baseline

@dataclass
class OracleFailureBreaker(CircuitBreaker):
    """
    Circuit breaker for oracle failures.

    Triggers when oracle data becomes stale or unreliable.
    """

    max_staleness: int = 3600  # 1 hour max staleness
    min_sources: int = 2  # Minimum oracle sources required

    def __post_init__(self) -> None:
        """Initialize oracle breaker."""
        super().__post_init__()
        self.breaker_type = BreakerType.ORACLE_FAILURE
        self.name = self.name or "Oracle Failure Breaker"
        self.protection_level = ProtectionLevel.HALT  # Critical

    def check_oracle_health(
        self,
        last_update: float,
        active_sources: int,
    ) -> str | None:
        """
        Check oracle health.

        Args:
            last_update: Timestamp of last price update
            active_sources: Number of active oracle sources

        Returns:
            Action to take
        """
        staleness = time.time() - last_update

        # Check staleness
        if staleness >= self.max_staleness:
            self.trigger("system", {"reason": "stale_data", "staleness": staleness})
            return "trigger"

        if staleness >= self.max_staleness * 0.7:
            return "warn"

        # Check sources
        if active_sources < self.min_sources:
            self.trigger("system", {"reason": "insufficient_sources", "sources": active_sources})
            return "trigger"

        return None

@dataclass
class CircuitBreakerRegistry:
    """
    Central registry for managing circuit breakers.

    Provides:
    - Centralized breaker management
    - Emergency pause capability
    - Multi-sig guardian actions
    - Audit trail
    """

    address: str = ""
    owner: str = ""

    # Guardians who can trigger emergency actions
    guardians: dict[str, bool] = field(default_factory=dict)
    guardian_threshold: int = 1  # Number of guardians needed

    # All breakers
    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

    # Breakers by target
    breakers_by_target: dict[str, list[str]] = field(default_factory=dict)

    # Global pause state
    global_pause: bool = False
    global_pause_until: float = 0.0

    # Action callbacks
    pause_callbacks: dict[str, Callable] = field(default_factory=dict)

    # Audit log
    audit_log: list[Dict] = field(default_factory=list)

    # Access control with signature verification
    access_control: AccessControl = field(default_factory=AccessControl)
    rbac: RoleBasedAccessControl | None = None

    def __post_init__(self) -> None:
        """Initialize registry."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"breaker_registry:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

        # Initialize RBAC with owner as admin
        if self.owner and not self.rbac:
            self.rbac = RoleBasedAccessControl(
                access_control=self.access_control,
                admin_address=self.owner,
            )

    # ==================== Guardian Management ====================

    def add_guardian(self, caller: str, guardian: str) -> bool:
        """Add a guardian address."""
        self._require_owner(caller)
        self.guardians[guardian.lower()] = True

        self._log_action(caller, "add_guardian", {"guardian": guardian})
        return True

    def remove_guardian(self, caller: str, guardian: str) -> bool:
        """Remove a guardian address."""
        self._require_owner(caller)
        self.guardians[guardian.lower()] = False

        self._log_action(caller, "remove_guardian", {"guardian": guardian})
        return True

    # ==================== Breaker Management ====================

    def register_breaker(self, caller: str, breaker: CircuitBreaker) -> str:
        """
        Register a circuit breaker.

        Args:
            caller: Must be owner or guardian
            breaker: Breaker to register

        Returns:
            Breaker ID
        """
        self._require_guardian_or_owner(caller)

        self.breakers[breaker.id] = breaker

        if breaker.target:
            if breaker.target not in self.breakers_by_target:
                self.breakers_by_target[breaker.target] = []
            self.breakers_by_target[breaker.target].append(breaker.id)

        self._log_action(caller, "register_breaker", {
            "breaker_id": breaker.id,
            "type": breaker.breaker_type.value,
            "target": breaker.target,
        })

        logger.info(
            "Circuit breaker registered",
            extra={
                "event": "registry.breaker_registered",
                "breaker_id": breaker.id[:10],
                "type": breaker.breaker_type.value,
            }
        )

        return breaker.id

    def disable_breaker(self, caller: str, breaker_id: str) -> bool:
        """Disable a circuit breaker."""
        self._require_guardian_or_owner(caller)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        breaker.status = BreakerStatus.DISABLED

        self._log_action(caller, "disable_breaker", {"breaker_id": breaker_id})
        return True

    def enable_breaker(self, caller: str, breaker_id: str) -> bool:
        """Enable a disabled circuit breaker."""
        self._require_guardian_or_owner(caller)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        breaker.status = BreakerStatus.ACTIVE

        self._log_action(caller, "enable_breaker", {"breaker_id": breaker_id})
        return True

    # ==================== Emergency Actions ====================

    def emergency_pause(self, caller: str, duration: int = 3600) -> bool:
        """
        Emergency pause all operations.

        Args:
            caller: Must be guardian
            duration: Pause duration in seconds

        Returns:
            True if paused
        """
        self._require_guardian(caller)

        self.global_pause = True
        self.global_pause_until = time.time() + duration

        # Execute pause callbacks
        for name, callback in self.pause_callbacks.items():
            try:
                callback(True)
            except (TypeError, ValueError, RuntimeError, AttributeError, KeyError) as e:
                logger.error(
                    "Pause callback failed: %s - %s",
                    type(e).__name__,
                    str(e),
                    extra={
                        "callback_name": name,
                        "error_type": type(e).__name__,
                        "event": "circuit_breaker.callback_error"
                    }
                )

        self._log_action(caller, "emergency_pause", {"duration": duration})

        logger.warning(
            "Emergency pause activated",
            extra={
                "event": "registry.emergency_pause",
                "duration": duration,
                "guardian": caller[:10],
            }
        )

        return True

    def unpause(self, caller: str) -> bool:
        """Unpause operations."""
        self._require_guardian_or_owner(caller)

        self.global_pause = False
        self.global_pause_until = 0

        # Execute unpause callbacks
        for name, callback in self.pause_callbacks.items():
            try:
                callback(False)
            except (TypeError, ValueError, RuntimeError, AttributeError, KeyError) as e:
                logger.error(
                    "Unpause callback failed: %s - %s",
                    type(e).__name__,
                    str(e),
                    extra={
                        "callback_name": name,
                        "error_type": type(e).__name__,
                        "event": "circuit_breaker.callback_error"
                    }
                )

        self._log_action(caller, "unpause", {})

        logger.info(
            "Operations unpaused",
            extra={"event": "registry.unpaused", "guardian": caller[:10]}
        )

        return True

    def manual_trigger(
        self,
        caller: str,
        breaker_id: str,
        reason: str,
    ) -> bool:
        """
        Manually trigger a circuit breaker.

        Args:
            caller: Must be guardian
            breaker_id: Breaker to trigger
            reason: Reason for manual trigger

        Returns:
            True if triggered
        """
        self._require_guardian(caller)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        breaker.trigger(caller, {"reason": reason, "manual": True})

        self._log_action(caller, "manual_trigger", {
            "breaker_id": breaker_id,
            "reason": reason,
        })

        return True

    def manual_recover(self, caller: str, breaker_id: str) -> bool:
        """Manually recover a triggered breaker."""
        self._require_guardian(caller)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        breaker.manual_recover(caller)

        self._log_action(caller, "manual_recover", {"breaker_id": breaker_id})

        return True

    # ==================== Monitoring ====================

    def check_target(self, target: str) -> tuple[bool, list[str]]:
        """
        Check if operations on a target are allowed.

        Args:
            target: Pool or protocol address

        Returns:
            (allowed, list of blocking breaker IDs)
        """
        # Check global pause
        if self.global_pause:
            if time.time() < self.global_pause_until:
                return False, ["global_pause"]
            else:
                self.global_pause = False

        # Check target-specific breakers
        blocking = []
        breaker_ids = self.breakers_by_target.get(target, [])

        for breaker_id in breaker_ids:
            breaker = self.breakers.get(breaker_id)
            if not breaker:
                continue

            if breaker.status == BreakerStatus.TRIGGERED:
                if breaker.protection_level in (
                    ProtectionLevel.PAUSE,
                    ProtectionLevel.HALT
                ):
                    blocking.append(breaker_id)

        return len(blocking) == 0, blocking

    def is_operation_allowed(
        self,
        target: str,
        operation: str,
    ) -> bool:
        """
        Check if a specific operation is allowed.

        Args:
            target: Pool or protocol
            operation: Type of operation (e.g., "swap", "borrow")

        Returns:
            True if allowed
        """
        allowed, _ = self.check_target(target)
        return allowed

    def get_triggered_breakers(self) -> list[Dict]:
        """Get all currently triggered breakers."""
        return [
            {
                "id": b.id,
                "name": b.name,
                "type": b.breaker_type.value,
                "target": b.target,
                "protection_level": b.protection_level.value,
                "triggered_at": b.triggered_at,
            }
            for b in self.breakers.values()
            if b.status == BreakerStatus.TRIGGERED
        ]

    def get_system_health(self) -> Dict:
        """Get overall system health status."""
        triggered = [b for b in self.breakers.values() if b.status == BreakerStatus.TRIGGERED]
        cooling = [b for b in self.breakers.values() if b.status == BreakerStatus.COOLING_DOWN]

        return {
            "global_pause": self.global_pause,
            "global_pause_until": self.global_pause_until if self.global_pause else None,
            "total_breakers": len(self.breakers),
            "active_breakers": len([b for b in self.breakers.values() if b.status == BreakerStatus.ACTIVE]),
            "triggered_breakers": len(triggered),
            "cooling_down": len(cooling),
            "triggered_details": [
                {"id": b.id, "name": b.name, "level": b.protection_level.value}
                for b in triggered
            ],
            "guardians_active": sum(1 for g in self.guardians.values() if g),
        }

    # ==================== Secure Functions (Signature-Verified) ====================

    def emergency_pause_secure(
        self,
        request: SignedRequest,
        duration: int = 3600,
    ) -> bool:
        """
        Emergency pause all operations with signature verification.

        SECURE: Requires cryptographic proof of guardian role.

        Args:
            request: Signed request from guardian
            duration: Pause duration in seconds

        Returns:
            True if paused

        Raises:
            VMExecutionError: If signature verification fails or not guardian
        """
        # Verify caller has guardian role with valid signature
        if self.rbac:
            self.rbac.verify_role_simple(request, Role.GUARDIAN.value)
        else:
            # Fall back to manual guardian check
            if not self.guardians.get(request.address.lower(), False):
                raise VMExecutionError("Caller is not guardian")
            self.access_control.verify_caller_simple(request, request.address)

        self.global_pause = True
        self.global_pause_until = time.time() + duration

        # Execute pause callbacks
        for name, callback in self.pause_callbacks.items():
            try:
                callback(True)
            except (TypeError, ValueError, RuntimeError, AttributeError, KeyError) as e:
                logger.error(
                    "Pause callback failed: %s - %s",
                    type(e).__name__,
                    str(e),
                    extra={
                        "callback_name": name,
                        "error_type": type(e).__name__,
                        "event": "circuit_breaker.callback_error"
                    }
                )

        self._log_action(request.address, "emergency_pause_secure", {"duration": duration})

        logger.warning(
            "Emergency pause activated (secure)",
            extra={
                "event": "registry.emergency_pause_secure",
                "duration": duration,
                "guardian": request.address[:10],
            }
        )

        return True

    def unpause_secure(self, request: SignedRequest) -> bool:
        """
        Unpause operations with signature verification.

        SECURE: Requires cryptographic proof of guardian or owner role.

        Args:
            request: Signed request from guardian or owner

        Returns:
            True if unpaused

        Raises:
            VMExecutionError: If signature verification fails
        """
        # Verify caller is guardian or owner with valid signature
        is_guardian = self.guardians.get(request.address.lower(), False)
        is_owner = request.address.lower() == self.owner.lower()

        if not is_guardian and not is_owner:
            raise VMExecutionError("Caller is not guardian or owner")

        if is_owner:
            self.access_control.verify_caller_simple(request, self.owner)
        else:
            if self.rbac:
                self.rbac.verify_role_simple(request, Role.GUARDIAN.value)
            else:
                self.access_control.verify_caller_simple(request, request.address)

        self.global_pause = False
        self.global_pause_until = 0

        # Execute unpause callbacks
        for name, callback in self.pause_callbacks.items():
            try:
                callback(False)
            except (TypeError, ValueError, RuntimeError, AttributeError, KeyError) as e:
                logger.error(
                    "Unpause callback failed: %s - %s",
                    type(e).__name__,
                    str(e),
                    extra={
                        "callback_name": name,
                        "error_type": type(e).__name__,
                        "event": "circuit_breaker.callback_error"
                    }
                )

        self._log_action(request.address, "unpause_secure", {})

        logger.info(
            "Operations unpaused (secure)",
            extra={
                "event": "registry.unpaused_secure",
                "actor": request.address[:10],
            }
        )

        return True

    def manual_trigger_secure(
        self,
        request: SignedRequest,
        breaker_id: str,
        reason: str,
    ) -> bool:
        """
        Manually trigger a circuit breaker with signature verification.

        SECURE: Requires cryptographic proof of guardian role.

        Args:
            request: Signed request from guardian
            breaker_id: Breaker to trigger
            reason: Reason for manual trigger

        Returns:
            True if triggered

        Raises:
            VMExecutionError: If signature verification fails or not guardian
        """
        # Verify caller has guardian role with valid signature
        if self.rbac:
            self.rbac.verify_role_simple(request, Role.GUARDIAN.value)
        else:
            if not self.guardians.get(request.address.lower(), False):
                raise VMExecutionError("Caller is not guardian")
            self.access_control.verify_caller_simple(request, request.address)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        breaker.trigger(request.address, {"reason": reason, "manual": True})

        self._log_action(request.address, "manual_trigger_secure", {
            "breaker_id": breaker_id,
            "reason": reason,
        })

        logger.warning(
            "Circuit breaker manually triggered (secure)",
            extra={
                "event": "registry.manual_trigger_secure",
                "breaker_id": breaker_id[:10],
                "reason": reason,
                "guardian": request.address[:10],
            }
        )

        return True

    def update_thresholds_secure(
        self,
        request: SignedRequest,
        breaker_id: str,
        warning_threshold: int | None = None,
        trigger_threshold: int | None = None,
    ) -> bool:
        """
        Update circuit breaker thresholds with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            breaker_id: Breaker to update
            warning_threshold: New warning threshold (optional)
            trigger_threshold: New trigger threshold (optional)

        Returns:
            True if updated

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)

        breaker = self.breakers.get(breaker_id)
        if not breaker:
            raise VMExecutionError(f"Breaker {breaker_id} not found")

        if warning_threshold is not None:
            breaker.warning_threshold = warning_threshold

        if trigger_threshold is not None:
            breaker.trigger_threshold = trigger_threshold

        self._log_action(request.address, "update_thresholds_secure", {
            "breaker_id": breaker_id,
            "warning": warning_threshold,
            "trigger": trigger_threshold,
        })

        logger.info(
            "Breaker thresholds updated (secure)",
            extra={
                "event": "registry.thresholds_updated_secure",
                "breaker_id": breaker_id[:10],
                "admin": request.address[:10],
            }
        )

        return True

    def add_guardian_secure(
        self,
        request: SignedRequest,
        guardian: str,
    ) -> bool:
        """
        Add a guardian address with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            guardian: Guardian address to add

        Returns:
            True if added

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.guardians[guardian.lower()] = True

        # Also grant guardian role in RBAC if available
        if self.rbac:
            self.rbac.roles[Role.GUARDIAN.value].add(guardian.lower())

        self._log_action(request.address, "add_guardian_secure", {"guardian": guardian})

        logger.info(
            "Guardian added (secure)",
            extra={
                "event": "registry.guardian_added_secure",
                "guardian": guardian[:10],
                "admin": request.address[:10],
            }
        )

        return True

    def remove_guardian_secure(
        self,
        request: SignedRequest,
        guardian: str,
    ) -> bool:
        """
        Remove a guardian address with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            guardian: Guardian address to remove

        Returns:
            True if removed

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.guardians[guardian.lower()] = False

        # Also revoke guardian role in RBAC if available
        if self.rbac:
            self.rbac.roles[Role.GUARDIAN.value].discard(guardian.lower())

        self._log_action(request.address, "remove_guardian_secure", {"guardian": guardian})

        logger.info(
            "Guardian removed (secure)",
            extra={
                "event": "registry.guardian_removed_secure",
                "guardian": guardian[:10],
                "admin": request.address[:10],
            }
        )

        return True

    # ==================== Callbacks ====================

    def register_pause_callback(
        self,
        name: str,
        callback: Callable[[bool], None],
    ) -> None:
        """
        Register a callback for pause/unpause events.

        Args:
            name: Callback identifier
            callback: Function taking bool (True=pause, False=unpause)
        """
        self.pause_callbacks[name] = callback

    # ==================== Audit ====================

    def _log_action(self, actor: str, action: str, details: Dict) -> None:
        """Log an action to audit trail."""
        self.audit_log.append({
            "timestamp": time.time(),
            "actor": actor,
            "action": action,
            "details": details,
        })

        # Keep last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> list[Dict]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]

    # ==================== Helpers ====================

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

    def _require_guardian(self, caller: str) -> None:
        if not self.guardians.get(caller.lower(), False):
            raise VMExecutionError("Caller is not guardian")

    def _require_guardian_or_owner(self, caller: str) -> None:
        is_guardian = self.guardians.get(caller.lower(), False)
        is_owner = caller.lower() == self.owner.lower()

        if not is_guardian and not is_owner:
            raise VMExecutionError("Caller is not guardian or owner")
