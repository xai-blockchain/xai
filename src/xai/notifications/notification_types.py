"""
Notification type definitions and payload structures for XAI push notifications.

This module defines the types of notifications supported by the XAI system,
their priority levels, and the data structures for notification payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class NotificationType(Enum):
    """Types of push notifications supported by XAI."""

    TRANSACTION = "transaction"  # Incoming/outgoing transaction
    CONFIRMATION = "confirmation"  # Transaction confirmation update
    PRICE_ALERT = "price_alert"  # Price threshold crossed
    SECURITY = "security"  # Security-related alerts (new device, suspicious activity)
    GOVERNANCE = "governance"  # Governance proposals and votes
    MINING = "mining"  # Mining rewards and status updates
    CONTRACT = "contract"  # Smart contract events
    SOCIAL_RECOVERY = "social_recovery"  # Social recovery requests

class NotificationPriority(Enum):
    """Priority levels for push notifications."""

    LOW = "low"  # Can be batched, no alert
    NORMAL = "normal"  # Standard notification
    HIGH = "high"  # Important, with alert
    CRITICAL = "critical"  # Security-critical, bypasses quiet hours

@dataclass
class NotificationPayload:
    """
    Complete notification payload for push delivery.

    This structure contains all data needed to send a push notification
    via FCM or APNs, including display content and custom data.

    Attributes:
        notification_type: Type of notification
        title: Notification title (shown prominently)
        body: Notification body text
        priority: Delivery priority
        data: Custom key-value data for the mobile app
        badge: Badge count for iOS (None = no change, 0 = clear)
        sound: Sound to play (None = default, "silent" = no sound)
        click_action: Deep link or action when notification is tapped
        timestamp: When notification was created
        ttl: Time-to-live in seconds (how long to retry delivery)
    """

    notification_type: NotificationType
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: dict[str, Any] = field(default_factory=dict)
    badge: int | None = None
    sound: str | None = "default"
    click_action: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 86400  # 24 hours default

    def to_fcm_payload(self) -> dict[str, Any]:
        """
        Convert to Firebase Cloud Messaging payload format.

        Returns:
            Dict containing FCM-compatible notification structure
        """
        payload: dict[str, Any] = {
            "notification": {
                "title": self.title,
                "body": self.body,
            },
            "data": {
                **self.data,
                "type": self.notification_type.value,
                "timestamp": self.timestamp.isoformat(),
                "priority": self.priority.value,
            },
            "android": {
                "priority": self._fcm_priority(),
                "ttl": f"{self.ttl}s",
            },
        }

        if self.sound:
            payload["notification"]["sound"] = self.sound

        if self.click_action:
            payload["notification"]["click_action"] = self.click_action
            payload["data"]["click_action"] = self.click_action

        return payload

    def to_apns_payload(self) -> dict[str, Any]:
        """
        Convert to Apple Push Notification Service payload format.

        Returns:
            Dict containing APNs-compatible notification structure
        """
        aps: dict[str, Any] = {
            "alert": {
                "title": self.title,
                "body": self.body,
            },
            "sound": self.sound if self.sound and self.sound != "silent" else None,
        }

        if self.badge is not None:
            aps["badge"] = self.badge

        # APNs priority: 10 = immediate, 5 = power-efficient
        priority = 10 if self.priority in (NotificationPriority.HIGH, NotificationPriority.CRITICAL) else 5

        payload = {
            "aps": {k: v for k, v in aps.items() if v is not None},
            "type": self.notification_type.value,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            **self.data,
        }

        if self.click_action:
            payload["click_action"] = self.click_action

        return {
            "payload": payload,
            "priority": priority,
            "expiration": int(self.timestamp.timestamp()) + self.ttl,
        }

    def _fcm_priority(self) -> str:
        """Map internal priority to FCM priority string."""
        if self.priority in (NotificationPriority.HIGH, NotificationPriority.CRITICAL):
            return "high"
        return "normal"

def create_transaction_notification(
    tx_hash: str,
    amount: str,
    from_address: str,
    to_address: str,
    is_incoming: bool,
    confirmed: bool = False,
) -> NotificationPayload:
    """
    Create a notification for a transaction.

    Args:
        tx_hash: Transaction hash
        amount: Transaction amount (formatted with token symbol)
        from_address: Sender address
        to_address: Recipient address
        is_incoming: True if this is an incoming transaction
        confirmed: True if transaction is confirmed

    Returns:
        NotificationPayload ready to send
    """
    direction = "Received" if is_incoming else "Sent"
    status = "confirmed" if confirmed else "pending"

    title = f"{direction} {amount}"
    body = f"From: {from_address[:10]}..." if is_incoming else f"To: {to_address[:10]}..."

    return NotificationPayload(
        notification_type=NotificationType.TRANSACTION,
        title=title,
        body=body,
        priority=NotificationPriority.HIGH if is_incoming else NotificationPriority.NORMAL,
        data={
            "tx_hash": tx_hash,
            "amount": amount,
            "from": from_address,
            "to": to_address,
            "direction": "incoming" if is_incoming else "outgoing",
            "status": status,
        },
        click_action=f"xai://transaction/{tx_hash}",
    )

def create_confirmation_notification(
    tx_hash: str,
    confirmations: int,
    required_confirmations: int = 6,
) -> NotificationPayload:
    """
    Create a notification for transaction confirmation milestone.

    Args:
        tx_hash: Transaction hash
        confirmations: Current number of confirmations
        required_confirmations: Total confirmations needed

    Returns:
        NotificationPayload ready to send
    """
    title = "Transaction Confirmed"
    body = f"{confirmations}/{required_confirmations} confirmations"

    return NotificationPayload(
        notification_type=NotificationType.CONFIRMATION,
        title=title,
        body=body,
        priority=NotificationPriority.NORMAL,
        data={
            "tx_hash": tx_hash,
            "confirmations": confirmations,
            "required": required_confirmations,
        },
        click_action=f"xai://transaction/{tx_hash}",
        sound="silent" if confirmations < required_confirmations else "default",
    )

def create_price_alert_notification(
    price: float,
    threshold: float,
    crossed_direction: str,
    token: str = "XAI",
) -> NotificationPayload:
    """
    Create a notification for price alert.

    Args:
        price: Current price
        threshold: Price threshold that was crossed
        crossed_direction: "above" or "below"
        token: Token symbol

    Returns:
        NotificationPayload ready to send
    """
    title = f"{token} Price Alert"
    body = f"Price {crossed_direction} ${threshold:.4f} (now ${price:.4f})"

    return NotificationPayload(
        notification_type=NotificationType.PRICE_ALERT,
        title=title,
        body=body,
        priority=NotificationPriority.NORMAL,
        data={
            "token": token,
            "price": str(price),
            "threshold": str(threshold),
            "direction": crossed_direction,
        },
        click_action="xai://price-alerts",
    )

def create_security_notification(
    event_type: str,
    message: str,
    severity: str = "high",
) -> NotificationPayload:
    """
    Create a security-related notification.

    Args:
        event_type: Type of security event (new_device, suspicious_login, etc)
        message: Human-readable security message
        severity: Severity level (low, medium, high, critical)

    Returns:
        NotificationPayload ready to send
    """
    priority_map = {
        "low": NotificationPriority.LOW,
        "medium": NotificationPriority.NORMAL,
        "high": NotificationPriority.HIGH,
        "critical": NotificationPriority.CRITICAL,
    }

    return NotificationPayload(
        notification_type=NotificationType.SECURITY,
        title="Security Alert",
        body=message,
        priority=priority_map.get(severity.lower(), NotificationPriority.HIGH),
        data={
            "event_type": event_type,
            "severity": severity,
        },
        click_action="xai://security",
        sound="default",  # Always alert for security
    )

def create_governance_notification(
    proposal_id: str,
    title: str,
    action: str,
    time_remaining: str | None = None,
) -> NotificationPayload:
    """
    Create a governance-related notification.

    Args:
        proposal_id: Proposal identifier
        title: Proposal title
        action: Action type (new_proposal, vote_reminder, result, etc)
        time_remaining: Optional time remaining for voting

    Returns:
        NotificationPayload ready to send
    """
    body = f"Proposal: {title}"
    if time_remaining:
        body += f" ({time_remaining} remaining)"

    return NotificationPayload(
        notification_type=NotificationType.GOVERNANCE,
        title="Governance Update",
        body=body,
        priority=NotificationPriority.NORMAL,
        data={
            "proposal_id": proposal_id,
            "action": action,
            "time_remaining": time_remaining or "",
        },
        click_action=f"xai://governance/proposal/{proposal_id}",
    )
