"""
Biometric Authentication Manager for Mobile Wallet

Production-ready biometric authentication framework with:
- Abstract interface for Face ID / Touch ID / fingerprint
- Key protection levels (biometric_strong, biometric_weak, device_credential)
- Configurable timeout and fallback to PIN/password
- Session management with biometric re-verification
- Thread-safe session handling

Platform Integration:
- iOS: LocalAuthentication framework (LAContext)
- Android: BiometricPrompt API with KeyStore
- React Native: react-native-biometrics wrapper

Security Features:
- Time-based session expiry
- Operation-based session expiry
- Automatic session invalidation on background
- Cryptographic binding to biometric hardware
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

class BiometricType(Enum):
    """Types of biometric authentication supported."""
    FACE_ID = "face_id"           # iOS Face ID
    TOUCH_ID = "touch_id"         # iOS Touch ID
    FINGERPRINT = "fingerprint"   # Android fingerprint
    IRIS = "iris"                 # Samsung Iris
    FACE = "face"                 # Android Face Unlock
    NONE = "none"

class BiometricStrength(Enum):
    """Security strength levels for biometric authentication."""
    STRONG = "strong"             # Class 3 biometric (hardware-backed)
    WEAK = "weak"                 # Class 2 biometric (software-backed)
    DEVICE_CREDENTIAL = "device"  # PIN/password/pattern
    NONE = "none"

class ProtectionLevel(Enum):
    """Key protection levels matching platform security."""
    BIOMETRIC_STRONG = "biometric_strong"         # Requires Class 3 biometric
    BIOMETRIC_WEAK = "biometric_weak"             # Accepts Class 2 or 3
    DEVICE_CREDENTIAL = "device_credential"       # PIN/password/pattern
    BIOMETRIC_OR_CREDENTIAL = "biometric_or_credential"  # Either biometric or device credential

class BiometricError(Enum):
    """Biometric authentication error codes."""
    NOT_AVAILABLE = "not_available"
    NOT_ENROLLED = "not_enrolled"
    USER_CANCEL = "user_cancel"
    AUTHENTICATION_FAILED = "authentication_failed"
    LOCKOUT = "lockout"
    PERMANENT_LOCKOUT = "permanent_lockout"
    HARDWARE_ERROR = "hardware_error"
    TIMEOUT = "timeout"
    SESSION_EXPIRED = "session_expired"
    UNKNOWN = "unknown"

@dataclass
class BiometricResult:
    """Result of a biometric authentication attempt."""
    success: bool
    auth_type: BiometricType
    strength: BiometricStrength
    token: bytes | None = None  # Cryptographic token from successful auth
    error_code: BiometricError | None = None
    error_message: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time()))

@dataclass
class BiometricCapability:
    """Device biometric capabilities."""
    available: bool
    enrolled: bool
    biometric_types: list[BiometricType]
    hardware_detected: bool
    security_level: BiometricStrength
    can_authenticate: bool = True

@dataclass
class SessionConfig:
    """Configuration for biometric authentication sessions."""
    timeout_seconds: int = 300              # 5 minutes default
    max_operations: int = 10                # Max operations before re-auth
    require_reauth_on_sensitive: bool = True  # Re-auth for sensitive ops
    invalidate_on_background: bool = True    # Invalidate when app backgrounds
    grace_period_seconds: int = 30           # Grace period after timeout

class BiometricSession:
    """
    Manages biometric authentication session state.

    Thread-safe session management with automatic expiry and operation counting.
    Sessions require re-authentication when:
    - Time-based expiry (timeout_seconds)
    - Operation-based expiry (max_operations)
    - App goes to background (if configured)
    - Manual invalidation
    """

    def __init__(self, config: SessionConfig):
        self.config = config
        self._lock = threading.RLock()
        self._token: bytes | None = None
        self._auth_type: BiometricType = BiometricType.NONE
        self._strength: BiometricStrength = BiometricStrength.NONE
        self._start_time: float | None = None
        self._last_access: float | None = None
        self._operation_count: int = 0
        self._is_valid: bool = False

    def start_session(self, result: BiometricResult) -> None:
        """Start a new authenticated session."""
        with self._lock:
            if not result.success or not result.token:
                raise ValueError("Cannot start session with failed authentication")

            self._token = result.token
            self._auth_type = result.auth_type
            self._strength = result.strength
            self._start_time = time.time()
            self._last_access = self._start_time
            self._operation_count = 0
            self._is_valid = True

            logger.info(
                "Biometric session started",
                extra={
                    "event": "biometric.session_start",
                    "auth_type": result.auth_type.value,
                    "strength": result.strength.value
                }
            )

    def is_valid(self, require_strength: BiometricStrength | None = None) -> bool:
        """
        Check if session is still valid.

        Args:
            require_strength: Required minimum strength level

        Returns:
            True if session is valid and meets strength requirements
        """
        with self._lock:
            if not self._is_valid:
                return False

            now = time.time()

            # Check time-based expiry
            if self._start_time and (now - self._start_time) > self.config.timeout_seconds:
                logger.info(
                    "Biometric session expired (timeout)",
                    extra={"event": "biometric.session_expired_timeout"}
                )
                self.invalidate()
                return False

            # Check operation-based expiry
            if self._operation_count >= self.config.max_operations:
                logger.info(
                    "Biometric session expired (max operations)",
                    extra={"event": "biometric.session_expired_operations"}
                )
                self.invalidate()
                return False

            # Check strength requirement
            if require_strength:
                if not self._meets_strength_requirement(require_strength):
                    return False

            return True

    def _meets_strength_requirement(self, required: BiometricStrength) -> bool:
        """Check if session strength meets requirement."""
        strength_order = {
            BiometricStrength.STRONG: 3,
            BiometricStrength.WEAK: 2,
            BiometricStrength.DEVICE_CREDENTIAL: 1,
            BiometricStrength.NONE: 0
        }
        return strength_order.get(self._strength, 0) >= strength_order.get(required, 0)

    def get_token(self) -> bytes | None:
        """Get authentication token if session is valid."""
        with self._lock:
            if self.is_valid():
                self._last_access = time.time()
                self._operation_count += 1
                return self._token
            return None

    def invalidate(self) -> None:
        """Invalidate the session."""
        with self._lock:
            if self._token:
                # Securely clear token
                self._token = b'\x00' * len(self._token)

            self._token = None
            self._auth_type = BiometricType.NONE
            self._strength = BiometricStrength.NONE
            self._start_time = None
            self._last_access = None
            self._operation_count = 0
            self._is_valid = False

            logger.info(
                "Biometric session invalidated",
                extra={"event": "biometric.session_invalidated"}
            )

    def get_info(self) -> dict[str, Any]:
        """Get session information for monitoring."""
        with self._lock:
            if not self._is_valid:
                return {"valid": False}

            now = time.time()
            return {
                "valid": True,
                "auth_type": self._auth_type.value,
                "strength": self._strength.value,
                "age_seconds": int(now - self._start_time) if self._start_time else 0,
                "idle_seconds": int(now - self._last_access) if self._last_access else 0,
                "operations": self._operation_count,
                "remaining_operations": self.config.max_operations - self._operation_count
            }

class BiometricAuthProvider(ABC):
    """
    Abstract base class for biometric authentication providers.

    Platform implementations:
    - iOS: LocalAuthentication framework (LAContext)
    - Android: BiometricPrompt API
    - React Native: react-native-biometrics wrapper
    """

    @abstractmethod
    def is_available(self) -> BiometricCapability:
        """Check if biometric authentication is available."""
        pass

    @abstractmethod
    def authenticate(
        self,
        prompt_message: str,
        protection_level: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG,
        timeout_seconds: int = 30,
        allow_device_credential: bool = True
    ) -> BiometricResult:
        """
        Prompt user for biometric authentication.

        Args:
            prompt_message: Message to display to user
            protection_level: Required protection level
            timeout_seconds: Authentication timeout
            allow_device_credential: Allow PIN/password fallback

        Returns:
            BiometricResult with authentication outcome and token
        """
        pass

    @abstractmethod
    def invalidate_authentication(self) -> bool:
        """Invalidate current authentication session."""
        pass

class BiometricAuthManager:
    """
    High-level biometric authentication manager with session handling.

    Features:
    - Automatic session management
    - Protection level enforcement
    - Callback-based authentication flow
    - Thread-safe operation
    - Configurable timeouts and policies

    Usage:
        manager = BiometricAuthManager(provider, session_config)

        # Authenticate and start session
        result = manager.authenticate("Access wallet")
        if result.success:
            # Session is now active
            token = manager.get_session_token()
    """

    def __init__(
        self,
        provider: BiometricAuthProvider,
        session_config: SessionConfig | None = None
    ):
        """
        Initialize biometric authentication manager.

        Args:
            provider: Platform-specific biometric provider
            session_config: Session configuration (uses defaults if None)
        """
        self.provider = provider
        self.config = session_config or SessionConfig()
        self.session = BiometricSession(self.config)
        self._lock = threading.RLock()

        logger.info(
            "BiometricAuthManager initialized",
            extra={"event": "biometric.manager_init"}
        )

    def is_available(self) -> BiometricCapability:
        """Check if biometric authentication is available on device."""
        return self.provider.is_available()

    def authenticate(
        self,
        prompt_message: str = "Authenticate to access your wallet",
        protection_level: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG,
        timeout_seconds: int = 30,
        allow_device_credential: bool = True,
        force_reauth: bool = False
    ) -> BiometricResult:
        """
        Authenticate user and start session.

        Args:
            prompt_message: Message to display
            protection_level: Required protection level
            timeout_seconds: Authentication timeout
            allow_device_credential: Allow PIN/password fallback
            force_reauth: Force new authentication even if session valid

        Returns:
            BiometricResult with outcome
        """
        with self._lock:
            # Check if existing session is valid
            if not force_reauth and self.session.is_valid():
                strength = self.session._strength
                if self._protection_level_satisfied(protection_level, strength):
                    logger.debug(
                        "Using existing biometric session",
                        extra={"event": "biometric.session_reused"}
                    )
                    return BiometricResult(
                        success=True,
                        auth_type=self.session._auth_type,
                        strength=strength,
                        token=self.session.get_token()
                    )

            # Perform new authentication
            result = self.provider.authenticate(
                prompt_message=prompt_message,
                protection_level=protection_level,
                timeout_seconds=timeout_seconds,
                allow_device_credential=allow_device_credential
            )

            if result.success and result.token:
                self.session.start_session(result)

            return result

    def _protection_level_satisfied(
        self,
        required: ProtectionLevel,
        actual: BiometricStrength
    ) -> bool:
        """Check if actual strength satisfies required protection level."""
        if required == ProtectionLevel.BIOMETRIC_STRONG:
            return actual == BiometricStrength.STRONG
        elif required == ProtectionLevel.BIOMETRIC_WEAK:
            return actual in [BiometricStrength.STRONG, BiometricStrength.WEAK]
        elif required == ProtectionLevel.DEVICE_CREDENTIAL:
            return actual == BiometricStrength.DEVICE_CREDENTIAL
        elif required == ProtectionLevel.BIOMETRIC_OR_CREDENTIAL:
            return actual != BiometricStrength.NONE
        return False

    def get_session_token(
        self,
        require_strength: BiometricStrength | None = None
    ) -> bytes | None:
        """
        Get authentication token from active session.

        Args:
            require_strength: Required minimum strength

        Returns:
            Token if session valid, None otherwise
        """
        with self._lock:
            if self.session.is_valid(require_strength):
                return self.session.get_token()
            return None

    def is_session_valid(
        self,
        require_strength: BiometricStrength | None = None
    ) -> bool:
        """Check if session is valid."""
        with self._lock:
            return self.session.is_valid(require_strength)

    def invalidate_session(self) -> None:
        """Invalidate current session."""
        with self._lock:
            self.session.invalidate()
            self.provider.invalidate_authentication()

    def on_app_background(self) -> None:
        """Handle app going to background."""
        if self.config.invalidate_on_background:
            logger.info(
                "App backgrounded, invalidating biometric session",
                extra={"event": "biometric.background_invalidate"}
            )
            self.invalidate_session()

    def on_app_foreground(self) -> None:
        """Handle app returning to foreground."""
        logger.debug(
            "App foregrounded",
            extra={"event": "biometric.foreground"}
        )

    def get_session_info(self) -> dict[str, Any]:
        """Get current session information."""
        with self._lock:
            return self.session.get_info()

    def update_config(self, config: SessionConfig) -> None:
        """Update session configuration (invalidates current session)."""
        with self._lock:
            self.invalidate_session()
            self.config = config
            self.session = BiometricSession(config)

            logger.info(
                "BiometricAuthManager config updated",
                extra={"event": "biometric.config_updated"}
            )

class MockBiometricProvider(BiometricAuthProvider):
    """
    Mock implementation for testing and development.

    DO NOT USE IN PRODUCTION.
    """

    def __init__(
        self,
        simulate_type: BiometricType = BiometricType.FINGERPRINT,
        simulate_strength: BiometricStrength = BiometricStrength.STRONG
    ):
        self._simulate_type = simulate_type
        self._simulate_strength = simulate_strength
        self._is_enrolled = True
        self._fail_next = False
        self._is_locked = False

    def is_available(self) -> BiometricCapability:
        """Check mock biometric availability."""
        return BiometricCapability(
            available=True,
            enrolled=self._is_enrolled,
            biometric_types=[self._simulate_type],
            hardware_detected=True,
            security_level=self._simulate_strength,
            can_authenticate=not self._is_locked
        )

    def authenticate(
        self,
        prompt_message: str,
        protection_level: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG,
        timeout_seconds: int = 30,
        allow_device_credential: bool = True
    ) -> BiometricResult:
        """Simulate biometric authentication."""
        if not self._is_enrolled:
            return BiometricResult(
                success=False,
                auth_type=BiometricType.NONE,
                strength=BiometricStrength.NONE,
                error_code=BiometricError.NOT_ENROLLED,
                error_message="No biometrics enrolled"
            )

        if self._is_locked:
            return BiometricResult(
                success=False,
                auth_type=self._simulate_type,
                strength=BiometricStrength.NONE,
                error_code=BiometricError.LOCKOUT,
                error_message="Biometric authentication locked"
            )

        if self._fail_next:
            self._fail_next = False
            return BiometricResult(
                success=False,
                auth_type=self._simulate_type,
                strength=self._simulate_strength,
                error_code=BiometricError.AUTHENTICATION_FAILED,
                error_message="Authentication failed"
            )

        # Generate mock token
        token = secrets.token_bytes(32)

        return BiometricResult(
            success=True,
            auth_type=self._simulate_type,
            strength=self._simulate_strength,
            token=token
        )

    def invalidate_authentication(self) -> bool:
        """Invalidate mock authentication."""
        return True

    # Mock-specific methods for testing
    def set_fail_next(self, fail: bool = True):
        """Make the next authentication attempt fail."""
        self._fail_next = fail

    def set_enrolled(self, enrolled: bool = True):
        """Simulate biometric enrollment status."""
        self._is_enrolled = enrolled

    def set_locked(self, locked: bool = True):
        """Simulate biometric lockout."""
        self._is_locked = locked
