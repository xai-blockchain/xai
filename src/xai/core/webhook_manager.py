"""
Webhook Manager - Event Notification System for XAI Blockchain

Provides webhook registration, event dispatch, and delivery management:
- Webhook registration and management
- Event subscription by type
- Delivery with retry logic
- Webhook verification via signature
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Supported webhook event types."""

    NEW_BLOCK = "new_block"
    NEW_TRANSACTION = "new_transaction"
    GOVERNANCE_VOTE = "governance_vote"
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_EXECUTED = "proposal_executed"
    BALANCE_CHANGE = "balance_change"
    CONTRACT_DEPLOYED = "contract_deployed"
    CONTRACT_CALLED = "contract_called"
    MINING_REWARD = "mining_reward"
    AI_TASK_COMPLETED = "ai_task_completed"


@dataclass
class WebhookRegistration:
    """Webhook registration record."""

    id: str
    url: str
    events: list[str]
    secret: str
    owner: str
    created_at: float = field(default_factory=time.time)
    active: bool = True
    failure_count: int = 0
    last_delivery: float | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "owner": self.owner,
            "created_at": self.created_at,
            "active": self.active,
            "failure_count": self.failure_count,
            "last_delivery": self.last_delivery,
            "last_error": self.last_error,
        }


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt record."""

    webhook_id: str
    event_type: str
    payload: dict[str, Any]
    attempt: int = 1
    timestamp: float = field(default_factory=time.time)
    success: bool = False
    status_code: int | None = None
    error: str | None = None


class WebhookManager:
    """
    Manages webhook registrations and event delivery.

    Thread-safe implementation with async delivery and retry logic.
    """

    # Maximum retries for failed deliveries
    MAX_RETRIES = 3
    # Base delay between retries (exponential backoff)
    RETRY_BASE_DELAY = 5.0
    # Maximum failures before auto-disable
    MAX_FAILURE_COUNT = 10
    # Delivery timeout in seconds
    DELIVERY_TIMEOUT = 30
    # Maximum webhooks per owner
    MAX_WEBHOOKS_PER_OWNER = 10
    # Maximum events per webhook
    MAX_EVENTS_PER_WEBHOOK = 20

    def __init__(
        self,
        max_workers: int = 4,
        storage_path: str | None = None,
    ):
        self._webhooks: dict[str, WebhookRegistration] = {}
        self._event_subscriptions: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="webhook")
        self._delivery_history: list[WebhookDelivery] = []
        self._storage_path = storage_path
        self._running = True

        # Load persisted webhooks if storage path provided
        if storage_path:
            self._load_webhooks()

        logger.info(
            "WebhookManager initialized",
            extra={"max_workers": max_workers, "storage": storage_path},
        )

    def register_webhook(
        self,
        url: str,
        events: list[str],
        owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Register a new webhook.

        Args:
            url: Webhook endpoint URL (must be HTTPS in production)
            events: List of event types to subscribe to
            owner: Owner address for the webhook
            metadata: Optional metadata for the webhook

        Returns:
            Registration result with webhook_id and secret
        """
        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {
                "success": False,
                "error": {
                    "code": "invalid_url",
                    "message": "URL must use HTTP or HTTPS protocol",
                },
            }

        # Validate events
        valid_events = [e.value for e in WebhookEvent]
        invalid_events = [e for e in events if e not in valid_events]
        if invalid_events:
            return {
                "success": False,
                "error": {
                    "code": "invalid_events",
                    "message": f"Invalid event types: {invalid_events}",
                    "details": {"valid_events": valid_events},
                },
            }

        if len(events) > self.MAX_EVENTS_PER_WEBHOOK:
            return {
                "success": False,
                "error": {
                    "code": "too_many_events",
                    "message": f"Maximum {self.MAX_EVENTS_PER_WEBHOOK} events per webhook",
                },
            }

        with self._lock:
            # Check owner limit
            owner_count = sum(
                1 for w in self._webhooks.values() if w.owner == owner and w.active
            )
            if owner_count >= self.MAX_WEBHOOKS_PER_OWNER:
                return {
                    "success": False,
                    "error": {
                        "code": "webhook_limit_reached",
                        "message": f"Maximum {self.MAX_WEBHOOKS_PER_OWNER} webhooks per owner",
                    },
                }

            # Generate webhook ID and secret
            webhook_id = f"wh_{secrets.token_hex(8)}"
            secret = secrets.token_hex(32)

            registration = WebhookRegistration(
                id=webhook_id,
                url=url,
                events=events,
                secret=secret,
                owner=owner,
                metadata=metadata or {},
            )

            self._webhooks[webhook_id] = registration

            # Update event subscriptions
            for event in events:
                if event not in self._event_subscriptions:
                    self._event_subscriptions[event] = []
                self._event_subscriptions[event].append(webhook_id)

            # Persist if storage configured
            self._save_webhooks()

        logger.info(
            "Webhook registered",
            extra={
                "webhook_id": webhook_id,
                "url": url,
                "events": events,
                "owner": owner,
            },
        )

        return {
            "success": True,
            "webhook_id": webhook_id,
            "secret": secret,
            "events": events,
            "message": "Webhook registered successfully",
        }

    def unregister_webhook(self, webhook_id: str, owner: str) -> dict[str, Any]:
        """
        Unregister a webhook.

        Args:
            webhook_id: Webhook ID to remove
            owner: Owner address (must match registration)

        Returns:
            Unregistration result
        """
        with self._lock:
            webhook = self._webhooks.get(webhook_id)

            if not webhook:
                return {
                    "success": False,
                    "error": {
                        "code": "not_found",
                        "message": f"Webhook {webhook_id} not found",
                    },
                }

            if webhook.owner != owner:
                return {
                    "success": False,
                    "error": {
                        "code": "unauthorized",
                        "message": "Not authorized to modify this webhook",
                    },
                }

            # Remove from subscriptions
            for event in webhook.events:
                if event in self._event_subscriptions:
                    self._event_subscriptions[event] = [
                        w for w in self._event_subscriptions[event] if w != webhook_id
                    ]

            del self._webhooks[webhook_id]
            self._save_webhooks()

        logger.info(
            "Webhook unregistered",
            extra={"webhook_id": webhook_id, "owner": owner},
        )

        return {"success": True, "message": "Webhook removed"}

    def update_webhook(
        self,
        webhook_id: str,
        owner: str,
        events: list[str] | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update webhook configuration.

        Args:
            webhook_id: Webhook ID to update
            owner: Owner address (must match)
            events: New event list (optional)
            active: Enable/disable webhook (optional)

        Returns:
            Update result
        """
        with self._lock:
            webhook = self._webhooks.get(webhook_id)

            if not webhook:
                return {
                    "success": False,
                    "error": {"code": "not_found", "message": "Webhook not found"},
                }

            if webhook.owner != owner:
                return {
                    "success": False,
                    "error": {"code": "unauthorized", "message": "Not authorized"},
                }

            if events is not None:
                # Validate events
                valid_events = [e.value for e in WebhookEvent]
                invalid_events = [e for e in events if e not in valid_events]
                if invalid_events:
                    return {
                        "success": False,
                        "error": {
                            "code": "invalid_events",
                            "message": f"Invalid events: {invalid_events}",
                        },
                    }

                # Update subscriptions
                for old_event in webhook.events:
                    if old_event in self._event_subscriptions:
                        self._event_subscriptions[old_event] = [
                            w for w in self._event_subscriptions[old_event] if w != webhook_id
                        ]

                for new_event in events:
                    if new_event not in self._event_subscriptions:
                        self._event_subscriptions[new_event] = []
                    self._event_subscriptions[new_event].append(webhook_id)

                webhook.events = events

            if active is not None:
                webhook.active = active
                if active:
                    webhook.failure_count = 0  # Reset on re-enable

            self._save_webhooks()

        return {"success": True, "webhook": webhook.to_dict()}

    def get_webhook(self, webhook_id: str, owner: str | None = None) -> dict[str, Any] | None:
        """Get webhook details."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None
        if owner and webhook.owner != owner:
            return None
        return webhook.to_dict()

    def list_webhooks(self, owner: str | None = None) -> list[dict[str, Any]]:
        """List all webhooks, optionally filtered by owner."""
        with self._lock:
            webhooks = list(self._webhooks.values())
            if owner:
                webhooks = [w for w in webhooks if w.owner == owner]
            return [w.to_dict() for w in webhooks]

    def dispatch_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        async_delivery: bool = True,
    ) -> int:
        """
        Dispatch an event to all subscribed webhooks.

        Args:
            event_type: Type of event (from WebhookEvent)
            payload: Event payload data
            async_delivery: If True, deliver in background threads

        Returns:
            Number of webhooks notified
        """
        with self._lock:
            webhook_ids = self._event_subscriptions.get(event_type, [])
            active_webhooks = [
                self._webhooks[wid]
                for wid in webhook_ids
                if wid in self._webhooks and self._webhooks[wid].active
            ]

        if not active_webhooks:
            return 0

        logger.debug(
            "Dispatching event",
            extra={
                "event_type": event_type,
                "webhook_count": len(active_webhooks),
            },
        )

        # Build event envelope
        event_envelope = {
            "event": event_type,
            "timestamp": time.time(),
            "data": payload,
        }

        for webhook in active_webhooks:
            if async_delivery and self._running:
                self._executor.submit(
                    self._deliver_webhook, webhook, event_type, event_envelope
                )
            else:
                self._deliver_webhook(webhook, event_type, event_envelope)

        return len(active_webhooks)

    def _deliver_webhook(
        self,
        webhook: WebhookRegistration,
        event_type: str,
        payload: dict[str, Any],
        attempt: int = 1,
    ) -> bool:
        """
        Deliver webhook with retry logic.

        Args:
            webhook: Webhook registration
            event_type: Event type being delivered
            payload: Event payload
            attempt: Current attempt number

        Returns:
            True if delivery succeeded
        """
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            attempt=attempt,
        )

        try:
            # Generate signature
            signature = self._generate_signature(webhook.secret, payload)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": event_type,
                "X-Webhook-ID": webhook.id,
                "X-Webhook-Timestamp": str(int(time.time())),
            }

            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=self.DELIVERY_TIMEOUT,
            )

            delivery.status_code = response.status_code
            delivery.success = 200 <= response.status_code < 300

            if delivery.success:
                with self._lock:
                    webhook.last_delivery = time.time()
                    webhook.failure_count = 0
                    webhook.last_error = None

                logger.debug(
                    "Webhook delivered",
                    extra={
                        "webhook_id": webhook.id,
                        "event": event_type,
                        "status": response.status_code,
                    },
                )
            else:
                delivery.error = f"HTTP {response.status_code}"
                raise requests.HTTPError(f"Webhook returned {response.status_code}")

        except requests.RequestException as e:
            delivery.success = False
            delivery.error = str(e)

            logger.warning(
                "Webhook delivery failed",
                extra={
                    "webhook_id": webhook.id,
                    "attempt": attempt,
                    "error": str(e),
                },
            )

            with self._lock:
                webhook.failure_count += 1
                webhook.last_error = str(e)

                # Auto-disable after too many failures
                if webhook.failure_count >= self.MAX_FAILURE_COUNT:
                    webhook.active = False
                    logger.error(
                        "Webhook disabled due to failures",
                        extra={"webhook_id": webhook.id},
                    )

            # Retry with exponential backoff
            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)
                return self._deliver_webhook(webhook, event_type, payload, attempt + 1)

        # Record delivery attempt
        with self._lock:
            self._delivery_history.append(delivery)
            # Keep only recent history
            if len(self._delivery_history) > 1000:
                self._delivery_history = self._delivery_history[-500:]

        return delivery.success

    def _generate_signature(self, secret: str, payload: dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    def verify_signature(
        self, webhook_id: str, signature: str, payload: dict[str, Any]
    ) -> bool:
        """Verify a webhook signature (for testing/verification endpoints)."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return False

        expected = self._generate_signature(webhook.secret, payload)
        return hmac.compare_digest(signature, expected)

    def get_delivery_stats(self, webhook_id: str | None = None) -> dict[str, Any]:
        """Get delivery statistics."""
        with self._lock:
            history = self._delivery_history
            if webhook_id:
                history = [d for d in history if d.webhook_id == webhook_id]

        total = len(history)
        successful = sum(1 for d in history if d.success)

        return {
            "total_deliveries": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
        }

    def _save_webhooks(self) -> None:
        """Persist webhooks to storage."""
        if not self._storage_path:
            return

        try:
            data = {
                wid: {
                    "id": w.id,
                    "url": w.url,
                    "events": w.events,
                    "secret": w.secret,
                    "owner": w.owner,
                    "created_at": w.created_at,
                    "active": w.active,
                    "metadata": w.metadata,
                }
                for wid, w in self._webhooks.items()
            }

            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except (IOError, OSError) as e:
            logger.error("Failed to save webhooks: %s", e)

    def _load_webhooks(self) -> None:
        """Load webhooks from storage."""
        if not self._storage_path:
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for wid, wdata in data.items():
                registration = WebhookRegistration(
                    id=wdata["id"],
                    url=wdata["url"],
                    events=wdata["events"],
                    secret=wdata["secret"],
                    owner=wdata["owner"],
                    created_at=wdata.get("created_at", time.time()),
                    active=wdata.get("active", True),
                    metadata=wdata.get("metadata", {}),
                )
                self._webhooks[wid] = registration

                # Rebuild subscriptions
                for event in registration.events:
                    if event not in self._event_subscriptions:
                        self._event_subscriptions[event] = []
                    self._event_subscriptions[event].append(wid)

            logger.info("Loaded %d webhooks from storage", len(self._webhooks))

        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.error("Failed to load webhooks: %s", e)

    def shutdown(self) -> None:
        """Shutdown the webhook manager."""
        self._running = False
        self._executor.shutdown(wait=True)
        self._save_webhooks()
        logger.info("WebhookManager shutdown complete")


# Module-level singleton
_webhook_manager: WebhookManager | None = None
_manager_lock = threading.Lock()


def get_webhook_manager(
    storage_path: str | None = None,
    create: bool = True,
) -> WebhookManager | None:
    """Get the global webhook manager instance."""
    global _webhook_manager

    with _manager_lock:
        if _webhook_manager is None and create:
            _webhook_manager = WebhookManager(storage_path=storage_path)
        return _webhook_manager


def dispatch_event(event_type: str, payload: dict[str, Any]) -> int:
    """Convenience function to dispatch an event."""
    manager = get_webhook_manager(create=False)
    if manager:
        return manager.dispatch_event(event_type, payload)
    return 0
