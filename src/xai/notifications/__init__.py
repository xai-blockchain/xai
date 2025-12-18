"""
Push notification infrastructure for XAI mobile applications.

This module provides a complete push notification system supporting:
- Firebase Cloud Messaging (FCM) for Android
- Apple Push Notification Service (APNs) for iOS
- Device registration and management
- Multiple notification types (transactions, confirmations, price alerts, security, governance)
- Privacy-focused design with user control

Components:
- notification_types: Notification type definitions and payload structures
- device_registry: Device registration and management
- push_service: FCM and APNs integration for sending notifications
"""

from xai.notifications.notification_types import (
    NotificationType,
    NotificationPayload,
    NotificationPriority,
)
from xai.notifications.device_registry import (
    DeviceRegistry,
    DeviceInfo,
    DevicePlatform,
)
from xai.notifications.push_service import (
    PushNotificationService,
    NotificationError,
)

__all__ = [
    "NotificationType",
    "NotificationPayload",
    "NotificationPriority",
    "DeviceRegistry",
    "DeviceInfo",
    "DevicePlatform",
    "PushNotificationService",
    "NotificationError",
]
