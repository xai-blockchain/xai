"""
Push notification service for XAI mobile apps.

This module provides a wrapper around the core notification infrastructure
located in xai.notifications for mobile-specific use cases.

All push notification functionality is implemented in xai.notifications.
This module re-exports the main classes for convenience.
"""

from xai.notifications.device_registry import (
    DeviceInfo,
    DevicePlatform,
    DeviceRegistry,
)
from xai.notifications.notification_types import (
    NotificationPayload,
    NotificationPriority,
    NotificationType,
    create_confirmation_notification,
    create_governance_notification,
    create_price_alert_notification,
    create_security_notification,
    create_transaction_notification,
)

# Re-export all notification infrastructure from xai.notifications
from xai.notifications.push_service import (
    DeliveryResult,
    InvalidTokenError,
    NotificationError,
    PushNotificationService,
    RateLimitError,
)

__all__ = [
    # Push Service
    "PushNotificationService",
    "DeliveryResult",
    "NotificationError",
    "InvalidTokenError",
    "RateLimitError",
    # Device Registry
    "DeviceRegistry",
    "DeviceInfo",
    "DevicePlatform",
    # Notification Types
    "NotificationPayload",
    "NotificationType",
    "NotificationPriority",
    # Notification Helpers
    "create_transaction_notification",
    "create_confirmation_notification",
    "create_price_alert_notification",
    "create_security_notification",
    "create_governance_notification",
]
