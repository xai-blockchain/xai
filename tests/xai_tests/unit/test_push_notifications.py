"""
Tests for push notification infrastructure.

Covers:
- Device registration and management
- Notification payload creation
- Push service delivery (mocked)
- API endpoints
- Error handling
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from xai.notifications.notification_types import (
    NotificationType,
    NotificationPriority,
    NotificationPayload,
    create_transaction_notification,
    create_confirmation_notification,
    create_price_alert_notification,
    create_security_notification,
    create_governance_notification,
)
from xai.notifications.device_registry import (
    DeviceRegistry,
    DeviceInfo,
    DevicePlatform,
)
from xai.notifications.push_service import (
    PushNotificationService,
    DeliveryResult,
    NotificationError,
)


class TestNotificationTypes:
    """Test notification type definitions and payload creation."""

    def test_notification_payload_creation(self):
        """Test basic notification payload creation."""
        payload = NotificationPayload(
            notification_type=NotificationType.TRANSACTION,
            title="Test Transaction",
            body="Transaction received",
            priority=NotificationPriority.HIGH,
            data={"tx_hash": "abc123"},
        )

        assert payload.notification_type == NotificationType.TRANSACTION
        assert payload.title == "Test Transaction"
        assert payload.body == "Transaction received"
        assert payload.priority == NotificationPriority.HIGH
        assert payload.data["tx_hash"] == "abc123"

    def test_fcm_payload_conversion(self):
        """Test conversion to FCM payload format."""
        payload = NotificationPayload(
            notification_type=NotificationType.SECURITY,
            title="Security Alert",
            body="New device detected",
            priority=NotificationPriority.CRITICAL,
            sound="default",
        )

        fcm_payload = payload.to_fcm_payload()

        assert fcm_payload["notification"]["title"] == "Security Alert"
        assert fcm_payload["notification"]["body"] == "New device detected"
        assert fcm_payload["data"]["type"] == "security"
        assert fcm_payload["data"]["priority"] == "critical"
        assert fcm_payload["android"]["priority"] == "high"

    def test_apns_payload_conversion(self):
        """Test conversion to APNs payload format."""
        payload = NotificationPayload(
            notification_type=NotificationType.TRANSACTION,
            title="Transaction",
            body="Payment received",
            priority=NotificationPriority.NORMAL,
            badge=5,
        )

        apns_payload = payload.to_apns_payload()

        assert apns_payload["payload"]["aps"]["alert"]["title"] == "Transaction"
        assert apns_payload["payload"]["aps"]["alert"]["body"] == "Payment received"
        assert apns_payload["payload"]["aps"]["badge"] == 5
        assert apns_payload["payload"]["type"] == "transaction"
        assert apns_payload["priority"] == 5  # Power-efficient for normal priority

    def test_create_transaction_notification_incoming(self):
        """Test transaction notification creation for incoming transactions."""
        notification = create_transaction_notification(
            tx_hash="0xabc123",
            amount="10.5 XAI",
            from_address="XAI1111111111111111111111111111111111111111",
            to_address="XAI2222222222222222222222222222222222222222",
            is_incoming=True,
        )

        assert notification.notification_type == NotificationType.TRANSACTION
        assert "Received" in notification.title
        assert "10.5 XAI" in notification.title
        assert "From:" in notification.body
        assert notification.priority == NotificationPriority.HIGH
        assert notification.data["tx_hash"] == "0xabc123"
        assert notification.data["direction"] == "incoming"

    def test_create_transaction_notification_outgoing(self):
        """Test transaction notification creation for outgoing transactions."""
        notification = create_transaction_notification(
            tx_hash="0xdef456",
            amount="5.0 XAI",
            from_address="XAI1111111111111111111111111111111111111111",
            to_address="XAI2222222222222222222222222222222222222222",
            is_incoming=False,
        )

        assert "Sent" in notification.title
        assert "To:" in notification.body
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.data["direction"] == "outgoing"

    def test_create_confirmation_notification(self):
        """Test confirmation notification creation."""
        notification = create_confirmation_notification(
            tx_hash="0xabc123",
            confirmations=3,
            required_confirmations=6,
        )

        assert notification.notification_type == NotificationType.CONFIRMATION
        assert "Confirmed" in notification.title
        assert "3/6" in notification.body
        assert notification.data["confirmations"] == 3
        assert notification.sound == "silent"  # Not fully confirmed yet

    def test_create_price_alert_notification(self):
        """Test price alert notification creation."""
        notification = create_price_alert_notification(
            price=1.23,
            threshold=1.20,
            crossed_direction="above",
            token="XAI",
        )

        assert notification.notification_type == NotificationType.PRICE_ALERT
        assert "XAI" in notification.title
        assert "above" in notification.body
        assert "$1.2000" in notification.body
        assert notification.data["price"] == "1.23"

    def test_create_security_notification(self):
        """Test security notification creation."""
        notification = create_security_notification(
            event_type="new_device",
            message="New device login detected",
            severity="critical",
        )

        assert notification.notification_type == NotificationType.SECURITY
        assert "Security Alert" in notification.title
        assert notification.priority == NotificationPriority.CRITICAL
        assert notification.data["event_type"] == "new_device"

    def test_create_governance_notification(self):
        """Test governance notification creation."""
        notification = create_governance_notification(
            proposal_id="PROP-001",
            title="Increase block size",
            action="new_proposal",
            time_remaining="3 days",
        )

        assert notification.notification_type == NotificationType.GOVERNANCE
        assert "Governance" in notification.title
        assert "3 days" in notification.body
        assert notification.data["proposal_id"] == "PROP-001"


class TestDeviceRegistry:
    """Test device registration and management."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create device registry with temporary database."""
        db_path = tmp_path / "test_devices.db"
        return DeviceRegistry(db_path=db_path)

    def test_register_device(self, registry):
        """Test device registration."""
        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="fcm_token_abc123",
            platform="android",
            device_id="device_001",
            notification_types={"transaction", "security"},
            metadata={"os_version": "13.0"},
        )

        assert device.device_token == "fcm_token_abc123"
        assert device.platform == DevicePlatform.ANDROID
        assert device.user_address == "XAI1111111111111111111111111111111111111111"
        assert device.enabled is True
        assert "transaction" in device.notification_types
        assert device.metadata["os_version"] == "13.0"

    def test_register_device_defaults(self, registry):
        """Test device registration with defaults."""
        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="apns_token_xyz789",
            platform="ios",
        )

        assert device.platform == DevicePlatform.IOS
        # Default notification types
        assert "transaction" in device.notification_types
        assert "confirmation" in device.notification_types
        assert "security" in device.notification_types

    def test_register_device_invalid_platform(self, registry):
        """Test device registration with invalid platform."""
        with pytest.raises(ValueError, match="Invalid platform"):
            registry.register_device(
                user_address="XAI1111111111111111111111111111111111111111",
                device_token="token",
                platform="invalid",
            )

    def test_unregister_device(self, registry):
        """Test device unregistration."""
        registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="token_123",
            platform="android",
        )

        assert registry.unregister_device("token_123") is True
        assert registry.get_device("token_123") is None

    def test_unregister_nonexistent_device(self, registry):
        """Test unregistering nonexistent device."""
        assert registry.unregister_device("nonexistent") is False

    def test_get_device(self, registry):
        """Test device lookup."""
        registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="token_123",
            platform="android",
        )

        device = registry.get_device("token_123")
        assert device is not None
        assert device.device_token == "token_123"

    def test_get_devices_for_address(self, registry):
        """Test getting all devices for an address."""
        address = "XAI1111111111111111111111111111111111111111"

        registry.register_device(address, "token_1", "android")
        registry.register_device(address, "token_2", "ios")
        registry.register_device("XAI2222222222222222222222222222222222222222", "token_3", "android")

        devices = registry.get_devices_for_address(address)
        assert len(devices) == 2
        assert any(d.device_token == "token_1" for d in devices)
        assert any(d.device_token == "token_2" for d in devices)

    def test_update_last_active(self, registry):
        """Test updating device last active timestamp."""
        registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="token_123",
            platform="android",
        )

        original = registry.get_device("token_123")
        assert registry.update_last_active("token_123") is True

        updated = registry.get_device("token_123")
        assert updated.last_active >= original.last_active

    def test_update_notification_settings(self, registry):
        """Test updating notification settings."""
        registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="token_123",
            platform="android",
        )

        assert registry.update_notification_settings(
            "token_123",
            enabled=False,
            notification_types={"security"},
        ) is True

        device = registry.get_device("token_123")
        assert device.enabled is False
        assert device.notification_types == {"security"}

    def test_get_devices_by_platform(self, registry):
        """Test getting devices by platform."""
        registry.register_device("XAI1111111111111111111111111111111111111111", "token_1", "android")
        registry.register_device("XAI2222222222222222222222222222222222222222", "token_2", "ios")
        registry.register_device("XAI3333333333333333333333333333333333333333", "token_3", "android")

        android_devices = registry.get_devices_by_platform("android")
        assert len(android_devices) == 2

        ios_devices = registry.get_devices_by_platform("ios")
        assert len(ios_devices) == 1

    def test_cleanup_inactive_devices(self, registry):
        """Test cleaning up inactive devices."""
        # Register recent device
        registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="recent_token",
            platform="android",
        )

        # Register old device by modifying database directly
        import sqlite3
        old_date = (datetime.utcnow() - timedelta(days=100)).isoformat()
        with sqlite3.connect(registry.db_path) as conn:
            conn.execute("""
                INSERT INTO devices (
                    device_token, platform, user_address, device_id,
                    last_active, enabled, notification_types, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "old_token", "android",
                "XAI2222222222222222222222222222222222222222",
                None, old_date, 1, '["transaction"]', '{}', old_date
            ))
            conn.commit()

        removed = registry.cleanup_inactive_devices(days=90)
        assert removed == 1

        assert registry.get_device("recent_token") is not None
        assert registry.get_device("old_token") is None

    def test_get_stats(self, registry):
        """Test getting registry statistics."""
        registry.register_device("XAI1111111111111111111111111111111111111111", "token_1", "android")
        registry.register_device("XAI2222222222222222222222222222222222222222", "token_2", "ios")

        # Disable one device
        registry.update_notification_settings("token_1", enabled=False)

        stats = registry.get_stats()
        assert stats["total"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 1
        assert "android" in stats["by_platform"]
        assert "ios" in stats["by_platform"]


class TestPushService:
    """Test push notification service."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create device registry."""
        db_path = tmp_path / "test_devices.db"
        return DeviceRegistry(db_path=db_path)

    @pytest.fixture
    def service(self, registry):
        """Create push service with mocked credentials."""
        return PushNotificationService(
            device_registry=registry,
            fcm_key="test_fcm_key",
            apns_config={"key_id": "test", "team_id": "test", "key_path": "/test.p8"},
        )

    @pytest.mark.asyncio
    async def test_send_fcm_success(self, service, registry):
        """Test successful FCM delivery."""
        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="fcm_token",
            platform="android",
        )

        payload = NotificationPayload(
            notification_type=NotificationType.TRANSACTION,
            title="Test",
            body="Test notification",
        )

        # Mock successful FCM response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": 1})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service._send_fcm(device, payload)

        assert result.success is True
        assert result.device_token == "fcm_token"

    @pytest.mark.asyncio
    async def test_send_fcm_invalid_token(self, service, registry):
        """Test FCM delivery with invalid token."""
        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="invalid_token",
            platform="android",
        )

        payload = NotificationPayload(
            notification_type=NotificationType.TRANSACTION,
            title="Test",
            body="Test notification",
        )

        # Mock FCM error response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": 0,
            "results": [{"error": "NotRegistered"}]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service._send_fcm(device, payload)

        assert result.success is False
        assert result.should_unregister is True

    @pytest.mark.asyncio
    async def test_send_to_address(self, service, registry):
        """Test sending notification to all devices for an address."""
        address = "XAI1111111111111111111111111111111111111111"

        registry.register_device(address, "token_1", "android")
        registry.register_device(address, "token_2", "ios")

        payload = NotificationPayload(
            notification_type=NotificationType.SECURITY,
            title="Security Alert",
            body="Test alert",
        )

        # Mock successful responses
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": 1})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await service.send_to_address(address, payload)

        # Should attempt delivery to 2 devices (FCM for Android, APNs warning for iOS)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_send_transaction_notification(self, service, registry):
        """Test high-level transaction notification helper."""
        address = "XAI1111111111111111111111111111111111111111"
        registry.register_device(address, "token_1", "android")

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": 1})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await service.send_transaction_notification(
                address=address,
                tx_hash="0xabc123",
                amount="10.0 XAI",
                from_address="XAI1111111111111111111111111111111111111111",
                to_address="XAI2222222222222222222222222222222222222222",
                is_incoming=True,
            )

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_send_test_notification(self, service, registry):
        """Test sending test notification."""
        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="test_token",
            platform="android",
        )

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": 1})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service.send_test_notification("test_token")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_send_without_fcm_key(self, registry):
        """Test service behavior without FCM key."""
        service = PushNotificationService(
            device_registry=registry,
            fcm_key=None,  # No key
        )

        device = registry.register_device(
            user_address="XAI1111111111111111111111111111111111111111",
            device_token="token",
            platform="android",
        )

        payload = NotificationPayload(
            notification_type=NotificationType.TRANSACTION,
            title="Test",
            body="Test",
        )

        result = await service._send_fcm(device, payload)

        assert result.success is False
        assert "not configured" in result.error
