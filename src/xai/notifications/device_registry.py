"""
Device registration and management for push notifications.

This module handles registering and tracking devices for push notifications,
including device tokens, platform information, and notification preferences.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class DevicePlatform(Enum):
    """Mobile platform types."""

    IOS = "ios"
    ANDROID = "android"
    WEB = "web"

@dataclass
class DeviceInfo:
    """
    Information about a registered device.

    Attributes:
        device_token: Push notification token (FCM or APNs)
        platform: Device platform
        user_address: Blockchain address owning this device
        device_id: Optional unique device identifier
        last_active: Last time device was active
        enabled: Whether notifications are enabled
        notification_types: Set of enabled notification types
        metadata: Additional device metadata (OS version, app version, etc)
    """

    device_token: str
    platform: DevicePlatform
    user_address: str
    device_id: str | None = None
    last_active: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True
    notification_types: set[str] = field(default_factory=lambda: {
        "transaction", "confirmation", "security", "governance"
    })
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for storage."""
        return {
            "device_token": self.device_token,
            "platform": self.platform.value,
            "user_address": self.user_address,
            "device_id": self.device_id,
            "last_active": self.last_active.isoformat(),
            "enabled": self.enabled,
            "notification_types": list(self.notification_types),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> DeviceInfo:
        """Create DeviceInfo from dictionary."""
        return cls(
            device_token=data["device_token"],
            platform=DevicePlatform(data["platform"]),
            user_address=data["user_address"],
            device_id=data.get("device_id"),
            last_active=datetime.fromisoformat(data["last_active"]),
            enabled=data.get("enabled", True),
            notification_types=set(data.get("notification_types", [])),
            metadata=data.get("metadata", {}),
        )

class DeviceRegistry:
    """
    Device registration and management system.

    Handles device registration, unregistration, and lookup for push notifications.
    Stores device information in SQLite with indexes for efficient queries.

    Thread-safe for concurrent access from multiple API requests.
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize device registry.

        Args:
            db_path: Path to SQLite database. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_token TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    user_address TEXT NOT NULL,
                    device_id TEXT,
                    last_active TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    notification_types TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Index for looking up devices by address
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_address
                ON devices(user_address)
            """)

            # Index for platform-specific queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform
                ON devices(platform)
            """)

            conn.commit()

    def register_device(
        self,
        user_address: str,
        device_token: str,
        platform: str,
        device_id: str | None = None,
        notification_types: set[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DeviceInfo:
        """
        Register a device for push notifications.

        If device_token already exists, updates the registration.

        Args:
            user_address: Blockchain address owning the device
            device_token: Push notification token (FCM or APNs)
            platform: Device platform (ios, android, web)
            device_id: Optional unique device identifier
            notification_types: Set of notification types to enable
            metadata: Additional device metadata

        Returns:
            DeviceInfo for the registered device

        Raises:
            ValueError: If platform is invalid or required fields are missing
        """
        if not user_address or not device_token:
            raise ValueError("user_address and device_token are required")

        try:
            platform_enum = DevicePlatform(platform.lower())
        except ValueError:
            raise ValueError(f"Invalid platform: {platform}. Must be ios, android, or web")

        # Use default notification types if not provided
        if notification_types is None:
            notification_types = {"transaction", "confirmation", "security", "governance"}

        device_info = DeviceInfo(
            device_token=device_token,
            platform=platform_enum,
            user_address=user_address,
            device_id=device_id,
            notification_types=notification_types,
            metadata=metadata or {},
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO devices (
                    device_token, platform, user_address, device_id,
                    last_active, enabled, notification_types, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                device_info.device_token,
                device_info.platform.value,
                device_info.user_address,
                device_info.device_id,
                device_info.last_active.isoformat(),
                1 if device_info.enabled else 0,
                json.dumps(list(device_info.notification_types)),
                json.dumps(device_info.metadata),
            ))
            conn.commit()

        logger.info(
            "Device registered",
            extra={
                "user_address": user_address,
                "platform": platform,
                "device_id": device_id,
            }
        )

        return device_info

    def unregister_device(self, device_token: str) -> bool:
        """
        Remove device registration.

        Args:
            device_token: Push notification token to unregister

        Returns:
            True if device was unregistered, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM devices WHERE device_token = ?",
                (device_token,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info("Device unregistered", extra={"device_token": device_token[:10] + "..."})

        return deleted

    def get_device(self, device_token: str) -> DeviceInfo | None:
        """
        Get device information by token.

        Args:
            device_token: Push notification token

        Returns:
            DeviceInfo if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE device_token = ?",
                (device_token,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_device_info(row)

    def get_devices_for_address(self, address: str) -> list[DeviceInfo]:
        """
        Get all devices registered to an address.

        Args:
            address: Blockchain address

        Returns:
            List of DeviceInfo objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE user_address = ? AND enabled = 1",
                (address,)
            )
            rows = cursor.fetchall()

        return [self._row_to_device_info(row) for row in rows]

    def update_last_active(self, device_token: str) -> bool:
        """
        Update last active timestamp for a device.

        Args:
            device_token: Push notification token

        Returns:
            True if updated, False if device not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE devices
                SET last_active = ?
                WHERE device_token = ?
            """, (datetime.utcnow().isoformat(), device_token))
            conn.commit()
            return cursor.rowcount > 0

    def update_notification_settings(
        self,
        device_token: str,
        enabled: bool | None = None,
        notification_types: set[str] | None = None,
    ) -> bool:
        """
        Update notification settings for a device.

        Args:
            device_token: Push notification token
            enabled: Whether to enable/disable all notifications
            notification_types: Set of notification types to enable

        Returns:
            True if updated, False if device not found
        """
        updates = []
        params = []

        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)

        if notification_types is not None:
            updates.append("notification_types = ?")
            params.append(json.dumps(list(notification_types)))

        if not updates:
            return False

        params.append(device_token)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE devices SET {', '.join(updates)} WHERE device_token = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_devices_by_platform(self, platform: str) -> list[DeviceInfo]:
        """
        Get all enabled devices for a specific platform.

        Args:
            platform: Platform name (ios, android, web)

        Returns:
            List of DeviceInfo objects
        """
        try:
            platform_enum = DevicePlatform(platform.lower())
        except ValueError:
            return []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE platform = ? AND enabled = 1",
                (platform_enum.value,)
            )
            rows = cursor.fetchall()

        return [self._row_to_device_info(row) for row in rows]

    def cleanup_inactive_devices(self, days: int = 90) -> int:
        """
        Remove devices that haven't been active for specified days.

        Args:
            days: Number of days of inactivity before removal

        Returns:
            Number of devices removed
        """
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        cutoff_str = datetime.fromtimestamp(cutoff).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM devices WHERE last_active < ?",
                (cutoff_str,)
            )
            conn.commit()
            removed = cursor.rowcount

        if removed > 0:
            logger.info(f"Cleaned up {removed} inactive devices (>{days} days)")

        return removed

    def _row_to_device_info(self, row: sqlite3.Row) -> DeviceInfo:
        """Convert database row to DeviceInfo."""
        return DeviceInfo(
            device_token=row["device_token"],
            platform=DevicePlatform(row["platform"]),
            user_address=row["user_address"],
            device_id=row["device_id"],
            last_active=datetime.fromisoformat(row["last_active"]),
            enabled=bool(row["enabled"]),
            notification_types=set(json.loads(row["notification_types"])),
            metadata=json.loads(row["metadata"]),
        )

    def get_stats(self) -> dict[str, any]:
        """
        Get registry statistics.

        Returns:
            Dict with device counts by platform and status
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    platform,
                    enabled,
                    COUNT(*) as count
                FROM devices
                GROUP BY platform, enabled
            """)
            rows = cursor.fetchall()

        stats = {
            "total": 0,
            "enabled": 0,
            "disabled": 0,
            "by_platform": {},
        }

        for row in rows:
            platform, enabled, count = row
            stats["total"] += count

            if enabled:
                stats["enabled"] += count
            else:
                stats["disabled"] += count

            if platform not in stats["by_platform"]:
                stats["by_platform"][platform] = {"enabled": 0, "disabled": 0}

            if enabled:
                stats["by_platform"][platform]["enabled"] = count
            else:
                stats["by_platform"][platform]["disabled"] = count

        return stats
