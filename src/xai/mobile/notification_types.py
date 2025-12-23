"""
Notification type definitions for XAI mobile push notifications.

This module provides a wrapper around the core notification type infrastructure
located in xai.notifications.notification_types for mobile-specific use cases.

All notification type definitions are implemented in xai.notifications.notification_types.
This module re-exports the main classes for convenience.
"""

# Re-export all notification types from xai.notifications
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

__all__ = [
    "NotificationType",
    "NotificationPriority",
    "NotificationPayload",
    "create_transaction_notification",
    "create_confirmation_notification",
    "create_price_alert_notification",
    "create_security_notification",
    "create_governance_notification",
]
