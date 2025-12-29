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
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from xai.notifications.device_registry import DeviceInfo, DevicePlatform, DeviceRegistry
from xai.notifications.notification_types import NotificationPayload

logger = logging.getLogger(__name__)


@dataclass
class APNsConfig:
    """Configuration for Apple Push Notification Service authentication."""

    key_id: str
    team_id: str
    auth_key: str  # Contents of the .p8 file
    bundle_id: str


@dataclass
class APNsJWTCache:
    """Cache for APNs JWT tokens with expiration tracking."""

    token: str | None = None
    issued_at: float = 0.0
    # APNs tokens are valid for 1 hour, but we refresh at 55 minutes
    ttl_seconds: int = 55 * 60

    def is_valid(self) -> bool:
        """Check if the cached token is still valid."""
        if not self.token:
            return False
        return (time.time() - self.issued_at) < self.ttl_seconds

    def clear(self) -> None:
        """Clear the cached token."""
        self.token = None
        self.issued_at = 0.0

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
    - XAI_APNS_BUNDLE_ID: iOS app bundle identifier

    If keys are not configured, the service logs warnings but doesn't raise errors,
    allowing the application to run in development mode.
    """

    FCM_URL = "https://fcm.googleapis.com/fcm/send"
    APNS_SANDBOX_URL = "https://api.sandbox.push.apple.com"
    APNS_PRODUCTION_URL = "https://api.push.apple.com"

    # APNs error codes that indicate the token is invalid and device should be unregistered
    APNS_INVALID_TOKEN_REASONS = frozenset({
        "BadDeviceToken",
        "Unregistered",
        "DeviceTokenNotForTopic",
        "ExpiredProviderToken",
    })

    # APNs error codes that are retryable
    APNS_RETRYABLE_REASONS = frozenset({
        "InternalServerError",
        "ServiceUnavailable",
        "Shutdown",
    })

    def __init__(
        self,
        device_registry: DeviceRegistry,
        fcm_key: str | None = None,
        apns_config: APNsConfig | dict[str, str] | None = None,
        use_apns_sandbox: bool = True,
        apns_max_retries: int = 3,
        apns_retry_delay: float = 1.0,
    ):
        """
        Initialize push notification service.

        Args:
            device_registry: Device registry for looking up devices
            fcm_key: FCM server key (if None, reads from XAI_FCM_SERVER_KEY env var)
            apns_config: APNs configuration (APNsConfig or dict with key_id, team_id, key_path, bundle_id)
            use_apns_sandbox: Whether to use APNs sandbox (development) or production
            apns_max_retries: Maximum number of retry attempts for APNs
            apns_retry_delay: Base delay in seconds between retries (exponential backoff)
        """
        self.device_registry = device_registry
        self.fcm_key = fcm_key or os.getenv("XAI_FCM_SERVER_KEY")
        self.use_apns_sandbox = use_apns_sandbox
        self.apns_url = self.APNS_SANDBOX_URL if use_apns_sandbox else self.APNS_PRODUCTION_URL
        self.apns_max_retries = apns_max_retries
        self.apns_retry_delay = apns_retry_delay

        # Initialize APNs config
        if isinstance(apns_config, APNsConfig):
            self.apns_config = apns_config
        elif isinstance(apns_config, dict):
            self.apns_config = self._dict_to_apns_config(apns_config)
        else:
            self.apns_config = self._load_apns_config()

        # JWT token cache for APNs
        self._apns_jwt_cache = APNsJWTCache()

        # Warn if keys are not configured
        if not self.fcm_key:
            logger.warning(
                "FCM server key not configured. Push notifications to Android/Web will not work. "
                "Set XAI_FCM_SERVER_KEY environment variable."
            )

        if not self.apns_config:
            logger.warning(
                "APNs not configured. Push notifications to iOS will not work. "
                "Set XAI_APNS_KEY_ID, XAI_APNS_TEAM_ID, XAI_APNS_KEY_PATH, and XAI_APNS_BUNDLE_ID "
                "environment variables."
            )

    def _dict_to_apns_config(self, config_dict: dict[str, str]) -> APNsConfig | None:
        """Convert a configuration dict to APNsConfig, loading auth key from file if needed."""
        key_id = config_dict.get("key_id")
        team_id = config_dict.get("team_id")
        bundle_id = config_dict.get("bundle_id")

        # Get auth key either directly or from file path
        auth_key = config_dict.get("auth_key")
        if not auth_key and config_dict.get("key_path"):
            try:
                with open(config_dict["key_path"], "r") as f:
                    auth_key = f.read()
            except OSError as e:
                logger.error(f"Failed to read APNs key file: {e}")
                return None

        if not all([key_id, team_id, auth_key, bundle_id]):
            return None

        return APNsConfig(
            key_id=key_id,
            team_id=team_id,
            auth_key=auth_key,
            bundle_id=bundle_id,
        )

    def _load_apns_config(self) -> APNsConfig | None:
        """Load APNs configuration from environment variables."""
        key_id = os.getenv("XAI_APNS_KEY_ID")
        team_id = os.getenv("XAI_APNS_TEAM_ID")
        key_path = os.getenv("XAI_APNS_KEY_PATH")
        bundle_id = os.getenv("XAI_APNS_BUNDLE_ID")

        if not all([key_id, team_id, key_path, bundle_id]):
            return None

        # Read the auth key from file
        try:
            with open(key_path, "r") as f:
                auth_key = f.read()
        except OSError as e:
            logger.error(f"Failed to read APNs key file from {key_path}: {e}")
            return None

        return APNsConfig(
            key_id=key_id,
            team_id=team_id,
            auth_key=auth_key,
            bundle_id=bundle_id,
        )

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

    def _generate_apns_jwt(self) -> str:
        """
        Generate a JWT token for APNs authentication.

        The token is cached and reused until it expires (55 minutes).

        Returns:
            JWT token string for APNs authorization header

        Raises:
            NotificationError: If JWT generation fails
        """
        # Return cached token if still valid
        if self._apns_jwt_cache.is_valid():
            return self._apns_jwt_cache.token

        try:
            import jwt
        except ImportError:
            raise NotificationError(
                "PyJWT is required for APNs. Install with: pip install PyJWT"
            )

        if not self.apns_config:
            raise NotificationError("APNs not configured")

        try:
            now = int(time.time())
            token = jwt.encode(
                {
                    "iss": self.apns_config.team_id,
                    "iat": now,
                },
                self.apns_config.auth_key,
                algorithm="ES256",
                headers={
                    "kid": self.apns_config.key_id,
                },
            )

            # Cache the token
            self._apns_jwt_cache.token = token
            self._apns_jwt_cache.issued_at = now

            logger.debug("Generated new APNs JWT token")
            return token

        except jwt.PyJWTError as e:
            logger.error(f"Failed to generate APNs JWT: {e}")
            raise NotificationError(f"Failed to generate APNs JWT: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating APNs JWT: {e}")
            raise NotificationError(f"APNs JWT generation failed: {e}") from e

    async def _send_apns(
        self,
        device: DeviceInfo,
        payload: NotificationPayload,
    ) -> DeliveryResult:
        """
        Send notification via Apple Push Notification Service.

        Uses HTTP/2 connection with JWT-based authentication.
        Includes retry logic with exponential backoff for transient errors.

        Args:
            device: Device info with iOS device token
            payload: Notification payload to send

        Returns:
            DeliveryResult with delivery status
        """
        if not self.apns_config:
            logger.warning("APNs not configured, skipping notification")
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error="APNs not configured",
            )

        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for APNs. Install with: pip install httpx[http2]")
            return DeliveryResult(
                success=False,
                device_token=device.device_token,
                error="httpx not installed (required for APNs HTTP/2)",
            )

        # Get APNs-formatted payload
        apns_data = payload.to_apns_payload()
        apns_payload = apns_data["payload"]
        priority = apns_data.get("priority", 10)
        expiration = apns_data.get("expiration", 0)

        # Retry loop with exponential backoff
        last_error: str | None = None
        for attempt in range(self.apns_max_retries + 1):
            try:
                result = await self._send_apns_request(
                    device_token=device.device_token,
                    payload=apns_payload,
                    priority=priority,
                    expiration=expiration,
                )

                if result.success:
                    self.device_registry.update_last_active(device.device_token)
                    return result

                # Check if error is retryable
                if result.should_retry and attempt < self.apns_max_retries:
                    delay = self.apns_retry_delay * (2 ** attempt)
                    logger.debug(
                        f"APNs request failed with retryable error, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{self.apns_max_retries})"
                    )
                    await asyncio.sleep(delay)
                    last_error = result.error
                    continue

                return result

            except NotificationError as e:
                # JWT generation or configuration errors - not retryable
                return DeliveryResult(
                    success=False,
                    device_token=device.device_token,
                    error=str(e),
                )
            except Exception as e:
                logger.error(f"APNs request error (attempt {attempt + 1}): {e}")
                last_error = str(e)

                if attempt < self.apns_max_retries:
                    delay = self.apns_retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                return DeliveryResult(
                    success=False,
                    device_token=device.device_token,
                    error=f"APNs delivery failed after {self.apns_max_retries + 1} attempts: {last_error}",
                    should_retry=True,
                )

        # Should not reach here, but handle it
        return DeliveryResult(
            success=False,
            device_token=device.device_token,
            error=f"APNs delivery failed: {last_error}",
            should_retry=True,
        )

    async def _send_apns_request(
        self,
        device_token: str,
        payload: dict[str, Any],
        priority: int = 10,
        expiration: int = 0,
    ) -> DeliveryResult:
        """
        Send a single APNs request via HTTP/2.

        Args:
            device_token: iOS device token
            payload: APNs payload dictionary
            priority: APNs priority (10 = immediate, 5 = power-efficient)
            expiration: Unix timestamp when notification expires (0 = immediate delivery only)

        Returns:
            DeliveryResult with delivery status

        Raises:
            NotificationError: If JWT generation fails
        """
        import httpx

        # Generate or use cached JWT
        jwt_token = self._generate_apns_jwt()

        url = f"{self.apns_url}/3/device/{device_token}"

        headers = {
            "authorization": f"bearer {jwt_token}",
            "apns-topic": self.apns_config.bundle_id,
            "apns-push-type": "alert",
            "apns-priority": str(priority),
        }

        if expiration > 0:
            headers["apns-expiration"] = str(expiration)

        try:
            async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )

                # Success
                if response.status_code == 200:
                    logger.debug(
                        "APNs notification sent successfully",
                        extra={"device_token": device_token[:10] + "..."}
                    )
                    return DeliveryResult(
                        success=True,
                        device_token=device_token,
                    )

                # Parse error response
                try:
                    error_data = response.json()
                    reason = error_data.get("reason", "Unknown")
                except (json.JSONDecodeError, ValueError):
                    reason = f"HTTP {response.status_code}"

                logger.warning(
                    f"APNs notification failed",
                    extra={
                        "device_token": device_token[:10] + "...",
                        "status_code": response.status_code,
                        "reason": reason,
                    }
                )

                # Check if token is invalid (device should be unregistered)
                if reason in self.APNS_INVALID_TOKEN_REASONS:
                    return DeliveryResult(
                        success=False,
                        device_token=device_token,
                        error=reason,
                        should_unregister=True,
                    )

                # Check if error is retryable
                if reason in self.APNS_RETRYABLE_REASONS or response.status_code >= 500:
                    return DeliveryResult(
                        success=False,
                        device_token=device_token,
                        error=reason,
                        should_retry=True,
                    )

                # Handle specific status codes
                if response.status_code == 403:
                    # Invalid JWT - clear cache and retry
                    self._apns_jwt_cache.clear()
                    return DeliveryResult(
                        success=False,
                        device_token=device_token,
                        error=f"APNs authentication failed: {reason}",
                        should_retry=True,
                    )

                if response.status_code == 429:
                    # Rate limited
                    return DeliveryResult(
                        success=False,
                        device_token=device_token,
                        error="APNs rate limit exceeded",
                        should_retry=True,
                    )

                # Other errors (400, 410, etc.)
                return DeliveryResult(
                    success=False,
                    device_token=device_token,
                    error=reason,
                )

        except httpx.TimeoutException:
            return DeliveryResult(
                success=False,
                device_token=device_token,
                error="APNs request timeout",
                should_retry=True,
            )
        except httpx.ConnectError as e:
            return DeliveryResult(
                success=False,
                device_token=device_token,
                error=f"APNs connection error: {e}",
                should_retry=True,
            )
        except httpx.HTTPStatusError as e:
            return DeliveryResult(
                success=False,
                device_token=device_token,
                error=f"APNs HTTP error: {e}",
                should_retry=True,
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
