"""
Mobile wallet and light client functionality

Includes:
- QR code generation for transactions (Task 179)
- Mobile wallet bridge for offline signing (Task 180)
- Mobile cache differential sync (Task 176)
- Mini app registry sandboxing (Task 175)
- Push notifications (FCM/APNs integration)
- Mobile telemetry tracking and analytics
- Network optimization for mobile clients
- Biometric authentication framework
- Secure enclave integration for iOS/Android
- Biometric-protected wallet operations
"""

from xai.mobile.biometric_auth import (
    BiometricAuthManager,
    BiometricAuthProvider,
    BiometricCapability,
    BiometricError,
    BiometricResult,
    BiometricSession,
    BiometricStrength,
    BiometricType,
    MockBiometricProvider,
    ProtectionLevel,
    SessionConfig,
)
from xai.mobile.biometric_wallet import (
    AuthenticationFailedError,
    AuthenticationRequiredError,
    BiometricWallet,
    BiometricWalletError,
    BiometricWalletFactory,
    OperationAudit,
    SecurityPolicy,
    WalletLockedError,
)
from xai.mobile.cache_sync import (
    DiffUpdate,
    IncrementalSyncProtocol,
    MobileCacheStorage,
    MobileCacheSyncManager,
    SyncCheckpoint,
)
from xai.mobile.mini_app_sandbox import AppPermission, AppSandbox, MiniApp, MiniAppRegistry
from xai.mobile.network_optimizer import (
    BandwidthMode,
    ConnectionType,
    NetworkOptimizer,
    NetworkProfile,
    QueuedTransaction,
)
from xai.mobile.notification_types import (
    NotificationPayload,
    NotificationPriority,
    NotificationType,
    create_confirmation_notification,
    create_governance_notification,
    create_price_alert_notification,
    create_security_notification,
    create_transaction_notification,
)
from xai.mobile.offline_bridge import (
    BatchOfflineSigning,
    OfflineSigningBridge,
    QROfflineBridge,
    SignedTransaction,
    UnsignedTransaction,
)
from xai.mobile.push_notifications import (
    DeliveryResult,
    DeviceInfo,
    DevicePlatform,
    DeviceRegistry,
    InvalidTokenError,
    NotificationError,
    PushNotificationService,
    RateLimitError,
)
from xai.mobile.qr_transactions import (
    QRCODE_AVAILABLE,
    MobilePaymentEncoder,
    QRCodeValidator,
    TransactionQRGenerator,
)
from xai.mobile.secure_enclave import (
    AttestationLevel,
    AttestationResult,
    KeyAlgorithm,
    KeyProtection,
    MockSecureEnclaveProvider,
    SecureEnclaveManager,
    SecureEnclaveProvider,
    SecureKey,
    SignatureResult,
)
from xai.mobile.sync_manager import (
    BandwidthThrottle,
    MobileSyncManager,
    NetworkCondition,
    SyncState,
    SyncStatistics,
)
from xai.mobile.telemetry import (
    AggregatedStats,
    MobileTelemetryCollector,
    TelemetryEvent,
)

__all__ = [
    # QR Code
    "TransactionQRGenerator",
    "MobilePaymentEncoder",
    "QRCodeValidator",
    "QRCODE_AVAILABLE",
    # Offline Signing
    "OfflineSigningBridge",
    "UnsignedTransaction",
    "SignedTransaction",
    "QROfflineBridge",
    "BatchOfflineSigning",
    # Cache Sync
    "MobileCacheSyncManager",
    "IncrementalSyncProtocol",
    "MobileCacheStorage",
    "SyncCheckpoint",
    "DiffUpdate",
    # Mini Apps
    "MiniAppRegistry",
    "AppSandbox",
    "MiniApp",
    "AppPermission",
    # Push Notifications
    "PushNotificationService",
    "DeliveryResult",
    "NotificationError",
    "InvalidTokenError",
    "RateLimitError",
    "DeviceRegistry",
    "DeviceInfo",
    "DevicePlatform",
    "NotificationPayload",
    "NotificationType",
    "NotificationPriority",
    "create_transaction_notification",
    "create_confirmation_notification",
    "create_price_alert_notification",
    "create_security_notification",
    "create_governance_notification",
    # Mobile Sync Manager
    "MobileSyncManager",
    "SyncState",
    "NetworkCondition",
    "SyncStatistics",
    "BandwidthThrottle",
    # Telemetry
    "MobileTelemetryCollector",
    "TelemetryEvent",
    "AggregatedStats",
    # Network Optimizer
    "NetworkOptimizer",
    "NetworkProfile",
    "ConnectionType",
    "BandwidthMode",
    "QueuedTransaction",
    # Biometric Authentication
    "BiometricAuthManager",
    "BiometricAuthProvider",
    "MockBiometricProvider",
    "BiometricSession",
    "SessionConfig",
    "BiometricType",
    "BiometricStrength",
    "BiometricError",
    "BiometricResult",
    "BiometricCapability",
    "ProtectionLevel",
    # Secure Enclave
    "SecureEnclaveManager",
    "SecureEnclaveProvider",
    "MockSecureEnclaveProvider",
    "SecureKey",
    "KeyAlgorithm",
    "KeyProtection",
    "AttestationLevel",
    "SignatureResult",
    "AttestationResult",
    # Biometric Wallet
    "BiometricWallet",
    "BiometricWalletFactory",
    "SecurityPolicy",
    "OperationAudit",
    "BiometricWalletError",
    "AuthenticationRequiredError",
    "AuthenticationFailedError",
    "WalletLockedError",
]
