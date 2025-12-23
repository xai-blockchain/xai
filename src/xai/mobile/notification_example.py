#!/usr/bin/env python3
"""
Example usage of XAI push notification framework.

This script demonstrates how to use the push notification system
to send notifications to registered mobile devices.

Run from project root:
    python3 src/xai/mobile/notification_example.py
"""

import asyncio
from pathlib import Path

from xai.mobile import (
    DevicePlatform,
    DeviceRegistry,
    NotificationPriority,
    NotificationType,
    PushNotificationService,
    create_security_notification,
    create_transaction_notification,
)


async def example_transaction_notification():
    """Example: Send transaction notification to an address."""
    # Initialize services
    db_path = Path("/tmp/example_devices.db")
    device_registry = DeviceRegistry(db_path=db_path)
    push_service = PushNotificationService(device_registry)

    # Register example device
    user_address = "XAI1234567890abcdef1234567890abcdef123456"
    device = device_registry.register_device(
        user_address=user_address,
        device_token="example_fcm_token_abc123",
        platform="android",
        notification_types={"transaction", "confirmation", "security"},
    )

    print(f"Registered device: {device.device_token}")
    print(f"Platform: {device.platform.value}")
    print(f"Notification types: {device.notification_types}")

    # Send transaction notification
    results = await push_service.send_transaction_notification(
        address=user_address,
        tx_hash="0xabc123def456",
        amount="10.5 XAI",
        from_address="XAI9876543210fedcba9876543210fedcba987654",
        to_address=user_address,
        is_incoming=True,
    )

    print("\nNotification results:")
    for result in results:
        if result.success:
            print(f"  SUCCESS: Sent to {result.device_token[:10]}...")
        else:
            print(f"  FAILED: {result.error}")
            if result.should_retry:
                print("    (will retry)")
            if result.should_unregister:
                print("    (invalid token, unregistering)")


async def example_security_alert():
    """Example: Send security alert to all user devices."""
    db_path = Path("/tmp/example_devices.db")
    device_registry = DeviceRegistry(db_path=db_path)
    push_service = PushNotificationService(device_registry)

    user_address = "XAI1234567890abcdef1234567890abcdef123456"

    # Register multiple devices for the same user
    devices = [
        ("android", "fcm_token_phone_001"),
        ("ios", "apns_token_tablet_002"),
    ]

    for platform, token in devices:
        device_registry.register_device(
            user_address=user_address,
            device_token=token,
            platform=platform,
        )

    print(f"Registered {len(devices)} devices for {user_address}")

    # Send security alert
    results = await push_service.send_security_alert(
        address=user_address,
        event_type="new_device_login",
        message="New device login detected from unknown location",
        severity="critical",
    )

    print(f"\nSent security alert to {len(results)} devices")
    for result in results:
        print(f"  Device: {result.device_token[:15]}... - Success: {result.success}")


def example_device_management():
    """Example: Device registration and settings management."""
    db_path = Path("/tmp/example_devices.db")
    device_registry = DeviceRegistry(db_path=db_path)

    user_address = "XAI1234567890abcdef1234567890abcdef123456"

    # Register device
    device = device_registry.register_device(
        user_address=user_address,
        device_token="example_token_123",
        platform="android",
        metadata={"os_version": "13.0", "app_version": "1.2.0"},
    )

    print(f"Registered device: {device.device_token}")

    # Get all devices for address
    devices = device_registry.get_devices_for_address(user_address)
    print(f"\nDevices for {user_address}: {len(devices)}")
    for d in devices:
        print(f"  - {d.platform.value}: {d.device_token[:15]}...")
        print(f"    Enabled: {d.enabled}")
        print(f"    Types: {d.notification_types}")

    # Update notification settings
    device_registry.update_notification_settings(
        device_token="example_token_123",
        enabled=True,
        notification_types={"transaction", "security"},  # Disable confirmation
    )

    print("\nUpdated notification settings")

    # Get updated device
    updated = device_registry.get_device("example_token_123")
    print(f"New notification types: {updated.notification_types}")

    # Get statistics
    stats = device_registry.get_stats()
    print(f"\nRegistry statistics:")
    print(f"  Total devices: {stats['total']}")
    print(f"  Enabled: {stats['enabled']}")
    print(f"  Disabled: {stats['disabled']}")
    print(f"  By platform: {stats['by_platform']}")

    # Cleanup
    device_registry.unregister_device("example_token_123")
    print("\nDevice unregistered")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("XAI Push Notification Framework - Examples")
    print("=" * 60)

    print("\n1. Transaction Notification Example")
    print("-" * 60)
    await example_transaction_notification()

    print("\n\n2. Security Alert Example")
    print("-" * 60)
    await example_security_alert()

    print("\n\n3. Device Management Example")
    print("-" * 60)
    example_device_management()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("\nNote: These examples use mock credentials.")
    print("Set XAI_FCM_SERVER_KEY and XAI_APNS_* environment variables")
    print("for actual push notification delivery.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
