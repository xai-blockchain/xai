"""
Push notification service for XAI mobile apps.

This module implements push notification delivery via:
- Firebase Cloud Messaging (FCM) for Android and Web
- Apple Push Notification Service (APNs) for iOS

The service gracefully handles missing API keys for development environments
and provides comprehensive error handling and retry logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import aiohttp

from xai.notifications.device_registry import DeviceInfo, DevicePlatform, DeviceRegistry
from xai.notifications.notification_types import NotificationPayload

logger = logging.getLogger(__name__)

class NotificationError(Exception):
    """Base exception for notification delivery errors."""
    pass

class InvalidTokenError(NotificationError):
    """Device token is invalid and should be removed."""
    pass

class RateLimitError(NotificationError):
    """Rate limit exceeded for notification service."""
    pass

@dataclass
class DeliveryResult:
    """Result of notification delivery attempt."""
    success: bool
    device_token: str
    error: str | None = None
    should_retry: bool = False
    should_unregister: bool = False

class PushNotificationService:
    """
    Push notification delivery service supporting FCM and APNs.

    This service handles the actual delivery of push notifications to mobile devices.
    It includes retry logic, error handling, and graceful degradation when API keys
    are not configured (development mode).

    API keys are read from environment variables:
    - XAI_FCM_SERVER_KEY: Firebase Cloud Messaging server key
    - XAI_APNS_KEY_ID: Apple Push Notification Service key ID
    - XAI_APNS_TEAM_ID: Apple team ID
    - XAI_APNS_KEY_PATH: Path to APNs .p8 key file

    If keys are not configured, the service logs warnings but doesn't raise errors,
    allowing the application to run in development mode.
    """

    FCM_URL = "https://fcm.googleapis.com/fcm/send"
    APNS_SANDBOX_URL = "https://api.sandbox.push.apple.com"
    APNS_PRODUCTION_URL = "https://api.push.apple.com"

    def __init__(
        self,
        device_registry: DeviceRegistry,
        fcm_key: str | None = None,
        apns_config: dict[str, str] | None = None,
        use_apns_sandbox: bool = True,
    ):
        """
        Initialize push notification service.

        Args:
            device_registry: Device registry for looking up devices
            fcm_key: FCM server key (if None, reads from XAI_FCM_SERVER_KEY env var)
            apns_config: APNs configuration dict with key_id, team_id, key_path
            use_apns_sandbox: Whether to use APNs sandbox (development) or production
        """
        self.device_registry = device_registry
        self.fcm_key = fcm_key or os.getenv("XAI_FCM_SERVER_KEY")
        self.apns_config = apns_config or self._load_apns_config()
        self.apns_url = self.APNS_SANDBOX_URL if use_apns_sandbox else self.APNS_PRODUCTION_URL

        # Warn if keys are not configured
        if not self.fcm_key:
            logger.warning(
                "FCM server key not configured. Push notifications to Android/Web will not work. "
                "Set XAI_FCM_SERVER_KEY environment variable."
            )

        if not self.apns_config:
            logger.warning(
                "APNs not configured. Push notifications to iOS will not work. "
                "Set XAI_APNS_KEY_ID, XAI_APNS_TEAM_ID, and XAI_APNS_KEY_PATH environment variables."
            )

    def _load_apns_config(self) -> dict[str, str] | None:
        """Load APNs configuration from environment variables."""
        key_id = os.getenv("XAI_APNS_KEY_ID")
        team_id = os.getenv("XAI_APNS_TEAM_ID")
        key_path = os.getenv("XAI_APNS_KEY_PATH")

        if not all([key_id, team_id, key_path]):
            return None

        return {
            "key_id": key_id,
            "team_id": team_id,
            "key_path": key_path,
        }

    async def send_to_address(
        self,
        address: str,
        payload: NotificationPayload,
        notification_type: str | None = None,
    ) -> list[DeliveryResult]:
        """
        Send notification to all devices registered to an address.

        Args:
            address: Blockchain address
            payload: Notification payload to send
            notification_type: Optional filter for notification type preference

        Returns:
            List of DeliveryResult for each device
        """
        devices = self.device_registry.get_devices_for_address(address)

        if not devices:
            logger.debug(f"No devices registered for address {address}")
            return []

        # Filter by notification type preference if specified
        if notification_type:
            devices = [
                d for d in devices
                if notification_type in d.notification_types
            ]

        if not devices:
            logger.debug(
                f"No devices with {notification_type} enabled for address {address}"
            )
            return []

        # Send to all devices concurrently
        tasks = [
            self.send_to_device(device, payload)
            for device in devices
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        delivery_results = []
        for device, result in zip(devices, results):
            if isinstance(result, Exception):
                logger.error(
                    "Notification delivery failed",
                    extra={
                        "device_token": device.device_token[:10] + "...",
                        "error": str(result),
                    }
                )
                delivery_results.append(
                    DeliveryResult(
                        success=False,
                        device_token=device.device_token,
                        error=str(result),
                        should_retry=True,
                    )
                )
            else:
                delivery_results.append(result)

                # Unregister devices with invalid tokens
                if result.should_unregister:
                    logger.info(
                        "Unregistering device with invalid token",
                        extra={"device_token": device.device_token[:10] + "..."}
                    )
                    self.device_registry.unregister_device(device.device_token)

        return delivery_results

    async def send_to_device(
        self,
        device: DeviceInfo,
        payload: NotificationPayload,
    ) -> DeliveryResult:
        """
        Send notification to a specific device.

        Args:
            device: Device information
            payload: Notification payload

        Returns:
            DeliveryResult with delivery status
        """
        if device.platform == DevicePlatform.IOS:
            return await self._send_apns(device, payload)
        elif device.platform in (DevicePlatform.ANDROID, DevicePlatform.WEB):
            return await self._send_fcm(device, payload)
        else:
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error=f"Unsupported platform: {device.platform}",
            )

    async def _send_fcm(
        self,
        device: DeviceInfo,
        payload: NotificationPayload,
    ) -> DeliveryResult:
        """Send notification via Firebase Cloud Messaging."""
        if not self.fcm_key:
            logger.warning("FCM key not configured, skipping notification")
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error="FCM not configured",
            )

        headers = {
            "Authorization": f"Bearer {self.fcm_key}",
            "Content-Type": "application/json",
        }

        fcm_payload = payload.to_fcm_payload()
        fcm_payload["to"] = device.device_token

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.FCM_URL,
                    headers=headers,
                    json=fcm_payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    response_data = await response.json()

                    if response.status == 200 and response_data.get("success") == 1:
                        logger.debug(
                            "FCM notification sent successfully",
                            extra={"device_token": device.device_token[:10] + "..."}
                        )
                        self.device_registry.update_last_active(device.device_token)
                        return DeliveryResult(
                            success=True,
                            device_token=device.device_token,
                        )

                    # Handle FCM error codes
                    error = response_data.get("results", [{}])[0].get("error", "Unknown error")

                    # Invalid token errors - unregister device
                    if error in ("NotRegistered", "InvalidRegistration"):
                        return DeliveryResult(
                            success=False,
                            device_token=device.device_token,
                            error=error,
                            should_unregister=True,
                        )

                    # Retriable errors
                    if error in ("Unavailable", "InternalServerError"):
                        return DeliveryResult(
                            success=False,
                            device_token=device.device_token,
                            error=error,
                            should_retry=True,
                        )

                    # Other errors
                    return DeliveryResult(
                        success=False,
                        device_token=device.device_token,
                        error=error,
                    )

        except asyncio.TimeoutError:
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error="Request timeout",
                should_retry=True,
            )
        except Exception as e:
            logger.error(
                "FCM delivery error",
                extra={
                    "error": str(e),
                    "device_token": device.device_token[:10] + "...",
                }
            )
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error=str(e),
                should_retry=True,
            )

    async def _send_apns(
        self,
        device: DeviceInfo,
        payload: NotificationPayload,
    ) -> DeliveryResult:
        """Send notification via Apple Push Notification Service."""
        if not self.apns_config:
            logger.warning("APNs not configured, skipping notification")
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error="APNs not configured",
            )

        # For production implementation, would need:
        # 1. JWT token generation from .p8 key
        # 2. HTTP/2 connection to APNs
        # 3. Proper APNs response parsing

        # This is a placeholder implementation showing the structure
        logger.warning(
            "APNs integration requires additional dependencies (jwt, h2). "
            "Notification not sent."
        )

        return DeliveryResult(
            success=False,
            device_token=device.device_token,
            error="APNs integration not fully implemented",
        )

    async def send_transaction_notification(
        self,
        address: str,
        tx_hash: str,
        amount: str,
        from_address: str,
        to_address: str,
        is_incoming: bool,
    ) -> list[DeliveryResult]:
        """
        Send transaction notification to an address.

        Args:
            address: Address to notify
            tx_hash: Transaction hash
            amount: Transaction amount
            from_address: Sender address
            to_address: Recipient address
            is_incoming: Whether this is incoming to the address

        Returns:
            List of DeliveryResult
        """
        from xai.notifications.notification_types import create_transaction_notification

        payload = create_transaction_notification(
            tx_hash=tx_hash,
            amount=amount,
            from_address=from_address,
            to_address=to_address,
            is_incoming=is_incoming,
        )

        return await self.send_to_address(address, payload, "transaction")

    async def send_confirmation_notification(
        self,
        address: str,
        tx_hash: str,
        confirmations: int,
        required_confirmations: int = 6,
    ) -> list[DeliveryResult]:
        """
        Send transaction confirmation notification.

        Args:
            address: Address to notify
            tx_hash: Transaction hash
            confirmations: Current confirmations
            required_confirmations: Total required

        Returns:
            List of DeliveryResult
        """
        from xai.notifications.notification_types import create_confirmation_notification

        payload = create_confirmation_notification(
            tx_hash=tx_hash,
            confirmations=confirmations,
            required_confirmations=required_confirmations,
        )

        return await self.send_to_address(address, payload, "confirmation")

    async def send_price_alert(
        self,
        address: str,
        price: float,
        threshold: float,
        crossed_direction: str,
    ) -> list[DeliveryResult]:
        """
        Send price alert notification.

        Args:
            address: Address to notify
            price: Current price
            threshold: Alert threshold
            crossed_direction: "above" or "below"

        Returns:
            List of DeliveryResult
        """
        from xai.notifications.notification_types import create_price_alert_notification

        payload = create_price_alert_notification(
            price=price,
            threshold=threshold,
            crossed_direction=crossed_direction,
        )

        return await self.send_to_address(address, payload, "price_alert")

    async def send_security_alert(
        self,
        address: str,
        event_type: str,
        message: str,
        severity: str = "high",
    ) -> list[DeliveryResult]:
        """
        Send security alert notification.

        Args:
            address: Address to notify
            event_type: Type of security event
            message: Alert message
            severity: Severity level

        Returns:
            List of DeliveryResult
        """
        from xai.notifications.notification_types import create_security_notification

        payload = create_security_notification(
            event_type=event_type,
            message=message,
            severity=severity,
        )

        # Security notifications always sent regardless of preferences
        return await self.send_to_address(address, payload)

    async def send_test_notification(
        self,
        device_token: str,
    ) -> DeliveryResult:
        """
        Send a test notification to verify device registration.

        Args:
            device_token: Device token to test

        Returns:
            DeliveryResult
        """
        device = self.device_registry.get_device(device_token)
        if not device:
            return DeliveryResult(
                success=False,
                device_token=device_token,
                error="Device not registered",
            )

        from xai.notifications.notification_types import (
            NotificationPayload,
            NotificationPriority,
            NotificationType,
        )

        payload = NotificationPayload(
            notification_type=NotificationType.SECURITY,
            title="XAI Test Notification",
            body="Your device is successfully registered for push notifications!",
            priority=NotificationPriority.NORMAL,
            data={"test": "true"},
        )

        return await self.send_to_device(device, payload)
