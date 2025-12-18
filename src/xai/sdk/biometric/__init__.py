"""
XAI Biometric Authentication SDK

Provides secure biometric authentication for mobile wallet applications.
"""

from .biometric_auth import (
    BiometricAuthProvider,
    BiometricType,
    BiometricError,
    BiometricResult,
    BiometricCapability,
    MockBiometricProvider,
)

from .secure_key_derivation import (
    SecureKeyDerivation,
    DerivedKey,
    EncryptedWalletKey,
    BiometricTokenCache,
)

__all__ = [
    # Authentication
    'BiometricAuthProvider',
    'BiometricType',
    'BiometricError',
    'BiometricResult',
    'BiometricCapability',
    'MockBiometricProvider',
    # Key Derivation
    'SecureKeyDerivation',
    'DerivedKey',
    'EncryptedWalletKey',
    'BiometricTokenCache',
]

__version__ = '1.0.0'
