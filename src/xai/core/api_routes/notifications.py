"""
Push notification API endpoints for XAI.

This module provides REST API endpoints for managing push notifications:
- Device registration and unregistration
- Notification preferences management
- Test notification delivery
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)

def register_notification_routes(routes: "NodeAPIRoutes") -> None:
    """
    Register notification-related API endpoints.

    Args:
        routes: NodeAPIRoutes instance containing app and blockchain
    """
    app = routes.app
    blockchain = routes.blockchain

    # Get or create notification components
    notification_service = getattr(blockchain, "_notification_service", None)
    device_registry = getattr(blockchain, "_device_registry", None)

    if not notification_service or not device_registry:
        # Initialize notification components lazily
        from pathlib import Path

        from xai.notifications.device_registry import DeviceRegistry
        from xai.notifications.push_service import PushNotificationService

        # Store device registry in blockchain's data directory
        if hasattr(blockchain, "base_dir"):
            db_path = Path(blockchain.base_dir) / "devices.db"
        else:
            db_path = None

        device_registry = DeviceRegistry(db_path=db_path)
        notification_service = PushNotificationService(device_registry)

        # Cache on blockchain instance
        blockchain._device_registry = device_registry
        blockchain._notification_service = notification_service

        logger.info("Initialized push notification service")

    @app.route("/notifications/register", methods=["POST"])
    def register_device() -> tuple[dict[str, Any], int]:
        """
        Register a device for push notifications.

        Request Body:
            {
                "user_address": "XAI...",
                "device_token": "fcm_token_or_apns_token",
                "platform": "ios" | "android" | "web",
                "device_id": "optional_unique_device_id",
                "notification_types": ["transaction", "confirmation", "security"],
                "metadata": {"os_version": "15.0", "app_version": "1.0.0"}
            }

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 201 with device info on success
                - 400 if validation fails
                - 500 on internal error

        Example:
            POST /notifications/register
            {
                "user_address": "XAI1234567890abcdef...",
                "device_token": "fcm_abc123...",
                "platform": "android"
            }
        """
        try:
            data = request.get_json()
            if not data:
                return routes._error_response(
                    "Request body required",
                    status=400,
                    code="missing_body",
                )

            # Validate required fields
            user_address = data.get("user_address")
            device_token = data.get("device_token")
            platform = data.get("platform")

            if not user_address or not device_token or not platform:
                return routes._error_response(
                    "Missing required fields: user_address, device_token, platform",
                    status=400,
                    code="missing_fields",
                )

            # Validate address format
            try:
                from xai.core.consensus.validation import validate_address
                validate_address(user_address, allow_special=False)
            except ValueError as e:
                return routes._error_response(
                    f"Invalid address: {str(e)}",
                    status=400,
                    code="invalid_address",
                )

            # Optional fields
            device_id = data.get("device_id")
            notification_types = data.get("notification_types")
            metadata = data.get("metadata", {})

            if notification_types:
                notification_types = set(notification_types)

            # Register device
            device_info = device_registry.register_device(
                user_address=user_address,
                device_token=device_token,
                platform=platform,
                device_id=device_id,
                notification_types=notification_types,
                metadata=metadata,
            )

            logger.info(
                "Device registered via API",
                extra={
                    "user_address": user_address,
                    "platform": platform,
                }
            )

            return jsonify({
                "status": "registered",
                "device": device_info.to_dict(),
            }), 201

        except ValueError as e:
            return routes._error_response(
                str(e),
                status=400,
                code="validation_error",
            )
        except Exception as e:
            logger.error(
                "Device registration failed",
                extra={"error": str(e)}
            )
            return routes._error_response(
                "Failed to register device",
                status=500,
                code="registration_failed",
            )

    @app.route("/notifications/unregister", methods=["DELETE"])
    def unregister_device() -> tuple[dict[str, Any], int]:
        """
        Unregister a device from push notifications.

        Request Body:
            {
                "device_token": "fcm_token_or_apns_token"
            }

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 200 if device was unregistered
                - 404 if device not found
                - 400 if validation fails

        Example:
            DELETE /notifications/unregister
            {"device_token": "fcm_abc123..."}
        """
        try:
            data = request.get_json()
            if not data:
                return routes._error_response(
                    "Request body required",
                    status=400,
                    code="missing_body",
                )

            device_token = data.get("device_token")
            if not device_token:
                return routes._error_response(
                    "device_token required",
                    status=400,
                    code="missing_token",
                )

            success = device_registry.unregister_device(device_token)

            if success:
                return jsonify({
                    "status": "unregistered",
                    "device_token": device_token,
                }), 200
            else:
                return routes._error_response(
                    "Device not found",
                    status=404,
                    code="device_not_found",
                )

        except Exception as e:
            logger.error(
                "Device unregistration failed",
                extra={"error": str(e)}
            )
            return routes._error_response(
                "Failed to unregister device",
                status=500,
                code="unregistration_failed",
            )

    @app.route("/notifications/settings/<device_token>", methods=["GET"])
    def get_notification_settings(device_token: str) -> tuple[dict[str, Any], int]:
        """
        Get notification settings for a device.

        Path Parameters:
            device_token: Push notification token

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 200 with device settings
                - 404 if device not found

        Example:
            GET /notifications/settings/fcm_abc123...
        """
        device = device_registry.get_device(device_token)

        if not device:
            return routes._error_response(
                "Device not found",
                status=404,
                code="device_not_found",
            )

        return jsonify({
            "device_token": device.device_token,
            "platform": device.platform.value,
            "user_address": device.user_address,
            "enabled": device.enabled,
            "notification_types": list(device.notification_types),
            "last_active": device.last_active.isoformat(),
        }), 200

    @app.route("/notifications/settings/<device_token>", methods=["PUT"])
    def update_notification_settings(device_token: str) -> tuple[dict[str, Any], int]:
        """
        Update notification settings for a device.

        Path Parameters:
            device_token: Push notification token

        Request Body:
            {
                "enabled": true | false,
                "notification_types": ["transaction", "confirmation", ...]
            }

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 200 if updated successfully
                - 404 if device not found
                - 400 if validation fails

        Example:
            PUT /notifications/settings/fcm_abc123...
            {
                "enabled": true,
                "notification_types": ["transaction", "security"]
            }
        """
        try:
            data = request.get_json()
            if not data:
                return routes._error_response(
                    "Request body required",
                    status=400,
                    code="missing_body",
                )

            enabled = data.get("enabled")
            notification_types = data.get("notification_types")

            if notification_types is not None:
                notification_types = set(notification_types)

            success = device_registry.update_notification_settings(
                device_token=device_token,
                enabled=enabled,
                notification_types=notification_types,
            )

            if not success:
                return routes._error_response(
                    "Device not found",
                    status=404,
                    code="device_not_found",
                )

            # Get updated settings
            device = device_registry.get_device(device_token)

            return jsonify({
                "status": "updated",
                "settings": {
                    "enabled": device.enabled,
                    "notification_types": list(device.notification_types),
                },
            }), 200

        except Exception as e:
            logger.error(
                "Settings update failed",
                extra={"error": str(e)}
            )
            return routes._error_response(
                "Failed to update settings",
                status=500,
                code="update_failed",
            )

    @app.route("/notifications/test", methods=["POST"])
    def send_test_notification() -> tuple[dict[str, Any], int]:
        """
        Send a test notification to verify device registration.

        Request Body:
            {
                "device_token": "fcm_token_or_apns_token"
            }

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 200 if notification sent successfully
                - 404 if device not found
                - 503 if notification service unavailable
                - 500 on delivery error

        Example:
            POST /notifications/test
            {"device_token": "fcm_abc123..."}
        """
        try:
            data = request.get_json()
            if not data:
                return routes._error_response(
                    "Request body required",
                    status=400,
                    code="missing_body",
                )

            device_token = data.get("device_token")
            if not device_token:
                return routes._error_response(
                    "device_token required",
                    status=400,
                    code="missing_token",
                )

            # Run async notification in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    notification_service.send_test_notification(device_token)
                )
            finally:
                loop.close()

            if result.success:
                return jsonify({
                    "status": "sent",
                    "device_token": device_token,
                }), 200
            elif result.error == "Device not registered":
                return routes._error_response(
                    result.error,
                    status=404,
                    code="device_not_found",
                )
            else:
                return routes._error_response(
                    f"Notification delivery failed: {result.error}",
                    status=503,
                    code="delivery_failed",
                )

        except Exception as e:
            logger.error(
                "Test notification failed",
                extra={"error": str(e)}
            )
            return routes._error_response(
                "Failed to send test notification",
                status=500,
                code="test_failed",
            )

    @app.route("/notifications/devices/<address>", methods=["GET"])
    def get_devices_for_address(address: str) -> tuple[dict[str, Any], int]:
        """
        Get all devices registered to an address.

        Path Parameters:
            address: Blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code):
                - 200 with list of devices
                - 400 if address invalid

        Example:
            GET /notifications/devices/XAI1234567890abcdef...
        """
        try:
            from xai.core.consensus.validation import validate_address
            validate_address(address, allow_special=False)
        except ValueError as e:
            return routes._error_response(
                f"Invalid address: {str(e)}",
                status=400,
                code="invalid_address",
            )

        devices = device_registry.get_devices_for_address(address)

        return jsonify({
            "address": address,
            "device_count": len(devices),
            "devices": [
                {
                    "device_token": d.device_token[:10] + "...",  # Truncate for privacy
                    "platform": d.platform.value,
                    "enabled": d.enabled,
                    "notification_types": list(d.notification_types),
                    "last_active": d.last_active.isoformat(),
                }
                for d in devices
            ],
        }), 200

    @app.route("/notifications/stats", methods=["GET"])
    def get_notification_stats() -> dict[str, Any]:
        """
        Get push notification system statistics.

        Returns:
            dict containing device counts by platform and status

        Example:
            GET /notifications/stats
        """
        stats = device_registry.get_stats()

        return jsonify({
            "stats": stats,
        })
