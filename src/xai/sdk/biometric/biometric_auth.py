from __future__ import annotations

"""
Biometric Authentication Framework - Python Reference Implementation

This module provides an abstract interface for biometric authentication
that can be used as a reference for mobile SDK implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BiometricType(Enum):
    """Types of biometric authentication supported."""
    FACE_ID = "face_id"
    TOUCH_ID = "touch_id"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"
    VOICE = "voice"
    NONE = "none"

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
    UNKNOWN = "unknown"

@dataclass
class BiometricResult:
    """Result of a biometric authentication attempt."""
    success: bool
    auth_type: BiometricType
    error_code: BiometricError | None = None
    error_message: str | None = None
    timestamp: int | None = None  # Unix timestamp

@dataclass
class BiometricCapability:
    """Device biometric capabilities."""
    available: bool
    enrolled: bool
    biometric_types: list[BiometricType]
    hardware_detected: bool
    security_level: str  # "strong", "weak", "none"

class BiometricAuthProvider(ABC):
    """
    Abstract base class for biometric authentication providers.

    Mobile SDKs should implement this interface using platform-specific APIs:
    - iOS: LocalAuthentication framework (LAContext)
    - Android: BiometricPrompt API
    - React Native: react-native-biometrics wrapper
    """

    @abstractmethod
    def is_available(self) -> BiometricCapability:
        """
        Check if biometric authentication is available on the device.

        Returns:
            BiometricCapability with device capabilities

        Platform-specific:
            - iOS: Check LAContext.canEvaluatePolicy()
            - Android: Check BiometricManager.canAuthenticate()
        """
        pass

    @abstractmethod
    def authenticate(
        self,
        prompt_message: str = "Authenticate to access your wallet",
        cancel_button_text: str = "Cancel",
        fallback_to_passcode: bool = True,
        timeout_seconds: int = 30
    ) -> BiometricResult:
        """
        Prompt user for biometric authentication.

        Args:
            prompt_message: Message to display to user
            cancel_button_text: Text for cancel button
            fallback_to_passcode: Allow device passcode as fallback
            timeout_seconds: Authentication timeout

        Returns:
            BiometricResult with authentication outcome

        Platform-specific:
            - iOS: LAContext.evaluatePolicy()
            - Android: BiometricPrompt.authenticate()
        """
        pass

    @abstractmethod
    def get_auth_type(self) -> BiometricType:
        """
        Get the primary biometric type available on the device.

        Returns:
            BiometricType enum value

        Platform-specific:
            - iOS: Check LAContext.biometryType
            - Android: Check BiometricManager capabilities
        """
        pass

    @abstractmethod
    def invalidate_authentication(self) -> bool:
        """
        Invalidate the current authentication session.

        Returns:
            True if successfully invalidated

        Platform-specific:
            - iOS: Invalidate LAContext
            - Android: Cancel BiometricPrompt
        """
        pass

class MockBiometricProvider(BiometricAuthProvider):
    """
    Mock implementation for testing and development.

    This should NOT be used in production. It's provided as a reference
    implementation and for testing purposes only.
    """

    def __init__(self, simulate_type: BiometricType = BiometricType.FINGERPRINT):
        self._simulate_type = simulate_type
        self._is_enrolled = True
        self._fail_next = False

    def is_available(self) -> BiometricCapability:
        """Check mock biometric availability."""
        return BiometricCapability(
            available=True,
            enrolled=self._is_enrolled,
            biometric_types=[self._simulate_type],
            hardware_detected=True,
            security_level="strong"
        )

    def authenticate(
        self,
        prompt_message: str = "Authenticate to access your wallet",
        cancel_button_text: str = "Cancel",
        fallback_to_passcode: bool = True,
        timeout_seconds: int = 30
    ) -> BiometricResult:
        """Simulate biometric authentication."""
        import time

        if not self._is_enrolled:
            return BiometricResult(
                success=False,
                auth_type=BiometricType.NONE,
                error_code=BiometricError.NOT_ENROLLED,
                error_message="No biometrics enrolled on device",
                timestamp=int(time.time())
            )

        if self._fail_next:
            self._fail_next = False
            return BiometricResult(
                success=False,
                auth_type=self._simulate_type,
                error_code=BiometricError.AUTHENTICATION_FAILED,
                error_message="Authentication failed",
                timestamp=int(time.time())
            )

        return BiometricResult(
            success=True,
            auth_type=self._simulate_type,
            timestamp=int(time.time())
        )

    def get_auth_type(self) -> BiometricType:
        """Get simulated biometric type."""
        return self._simulate_type

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
