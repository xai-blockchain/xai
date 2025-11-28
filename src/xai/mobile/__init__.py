"""
Mobile wallet and light client functionality

Includes:
- QR code generation for transactions (Task 179)
- Mobile wallet bridge for offline signing (Task 180)
- Mobile cache differential sync (Task 176)
- Mini app registry sandboxing (Task 175)
"""

from xai.mobile.qr_transactions import (
    TransactionQRGenerator,
    MobilePaymentEncoder,
    QRCodeValidator,
    QRCODE_AVAILABLE
)

from xai.mobile.offline_bridge import (
    OfflineSigningBridge,
    UnsignedTransaction,
    SignedTransaction,
    QROfflineBridge,
    BatchOfflineSigning
)

from xai.mobile.cache_sync import (
    MobileCacheSyncManager,
    IncrementalSyncProtocol,
    MobileCacheStorage,
    SyncCheckpoint,
    DiffUpdate
)

from xai.mobile.mini_app_sandbox import (
    MiniAppRegistry,
    AppSandbox,
    MiniApp,
    AppPermission
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
    "AppPermission"
]
