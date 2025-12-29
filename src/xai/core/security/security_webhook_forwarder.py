"""
XAI Blockchain - Security Webhook Forwarder

Asynchronous webhook sender for security events with:
- Retry with exponential backoff
- Queue persistence with optional encryption
- Severity-based filtering
- Thread-safe delivery

This module handles security event forwarding to external SIEM/monitoring systems.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from queue import Full, Queue
from typing import Any, Callable

import requests
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SecurityWebhookForwarder:
    """Asynchronous webhook sender with retry/backoff for security events.

    This class provides:
    - Background thread for non-blocking delivery
    - Automatic retry with exponential backoff
    - Optional queue persistence with encryption
    - Severity-based event filtering

    Attributes:
        url: Webhook endpoint URL
        timeout: HTTP request timeout in seconds
        max_retries: Maximum delivery attempts per event
        dropped_events: Count of events dropped due to queue overflow
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int = 5,
        max_retries: int = 3,
        backoff: float = 1.5,
        max_queue: int = 500,
        start_worker: bool = True,
        queue_path: str | None = None,
        encryption_key: str | None = None,
    ) -> None:
        """Initialize the security webhook forwarder.

        Args:
            url: Webhook endpoint URL
            headers: HTTP headers for requests (e.g., Authorization)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per event
            backoff: Exponential backoff multiplier
            max_queue: Maximum queue size before dropping events
            start_worker: Whether to start background worker immediately
            queue_path: Optional path for queue persistence
            encryption_key: Optional Fernet key for queue encryption
        """
        self.url = url
        self.headers = dict(headers)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.max_backoff = 30.0
        self.dropped_events = 0
        self.queue_path = queue_path
        self._fernet = self._build_fernet(encryption_key)
        self.queue: Queue[dict[str, Any]] = Queue(maxsize=max_queue)
        self._load_persisted_events()
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        if start_worker:
            self._worker_thread = threading.Thread(
                target=self._worker,
                name="security-webhook-worker",
                daemon=True,
            )
            self._worker_thread.start()

    def enqueue(self, payload: dict[str, Any]) -> bool:
        """Add an event to the delivery queue.

        Args:
            payload: Event payload to deliver

        Returns:
            True if enqueued, False if dropped
        """
        try:
            self.queue.put_nowait(payload)
            self._persist_queue()
            return True
        except Full:
            self.dropped_events += 1
            logger.warning(
                "Dropping webhook event %s (queue full)",
                payload.get("event_type"),
                extra={"event": "security.webhook_queue_full"},
            )
            return False

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background worker gracefully.

        Args:
            timeout: Maximum seconds to wait for worker shutdown
        """
        if self._worker_thread and self._worker_thread.is_alive():
            self._stop_event.set()
            self._worker_thread.join(timeout=timeout)
            logger.info(
                "Security webhook forwarder stopped",
                extra={"event": "security.webhook_stopped"},
            )

    def _worker(self) -> None:
        """Background worker that processes the delivery queue."""
        while not self._stop_event.is_set():
            try:
                # Use timeout to check stop event periodically
                payload = self.queue.get(timeout=1.0)
                try:
                    self._deliver(payload)
                finally:
                    self.queue.task_done()
                    self._persist_queue()
            except Exception:
                # Queue.get timeout raises Empty, continue loop
                continue

    def _deliver(self, payload: dict[str, Any]) -> bool:
        """Deliver a single event with retry logic.

        Args:
            payload: Event payload to deliver

        Returns:
            True if delivered successfully
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout,
                    headers=self.headers,
                )
                response.raise_for_status()
                return True
            except requests.RequestException as exc:
                attempt += 1
                if attempt >= self.max_retries:
                    logger.error(
                        "Failed to deliver webhook event %s after %d attempts: %s",
                        payload.get("event_type"),
                        self.max_retries,
                        type(exc).__name__,
                        extra={"event": "security.webhook_delivery_failed"},
                    )
                    return False
                delay = min(self.backoff * attempt, self.max_backoff)
                time.sleep(delay)
        return False

    def _persist_queue(self) -> None:
        """Persist queue to disk if path configured."""
        if not self.queue_path:
            return
        try:
            directory = os.path.dirname(self.queue_path) or os.getcwd()
            os.makedirs(directory, exist_ok=True)
            snapshot = list(self.queue.queue)
            data = json.dumps(snapshot).encode("utf-8")
            if self._fernet:
                data = self._fernet.encrypt(data)
            with open(self.queue_path, "wb") as handle:
                handle.write(data)
        except (OSError, IOError, ValueError, TypeError) as exc:
            logger.warning(
                "Failed to persist webhook queue: %s",
                type(exc).__name__,
                extra={"event": "security.webhook_queue_persist_failed"},
            )

    def _load_persisted_events(self) -> None:
        """Load persisted events from disk on startup."""
        if not self.queue_path or not os.path.exists(self.queue_path):
            return
        try:
            with open(self.queue_path, "rb") as handle:
                data = handle.read()
            if self._fernet:
                try:
                    data = self._fernet.decrypt(data)
                except InvalidToken:
                    logger.error(
                        "Failed to decrypt webhook queue: invalid token",
                        extra={"event": "security.webhook_queue_decrypt_failed"},
                    )
                    return
            payloads = json.loads(data.decode("utf-8"))
            for item in payloads:
                try:
                    self.queue.put_nowait(item)
                except Full:
                    self.dropped_events += 1
                    break
        except (OSError, IOError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Failed to load webhook queue: %s",
                type(exc).__name__,
                extra={"event": "security.webhook_queue_load_failed"},
            )

    @staticmethod
    def _build_fernet(raw_key: str | None) -> Fernet | None:
        """Build Fernet cipher from key string.

        Args:
            raw_key: Base64 or hex-encoded key

        Returns:
            Fernet instance or None if no key
        """
        if not raw_key:
            return None
        key = raw_key.strip().encode("utf-8")
        try:
            return Fernet(key)
        except (ValueError, TypeError):
            logger.debug("Failed to create Fernet cipher from raw key, trying hex decode")
            try:
                hex_bytes = bytes.fromhex(raw_key.strip())
                return Fernet(base64.urlsafe_b64encode(hex_bytes))
            except (ValueError, TypeError) as exc:
                logger.error(
                    "Invalid webhook queue encryption key",
                    extra={"event": "security.webhook_queue_key_invalid"},
                )
                return None


def create_security_webhook_sink(
    url: str,
    token: str = "",
    timeout: int = 5,
    max_retries: int = 3,
    backoff: float = 1.5,
    queue_path: str | None = None,
    encryption_key: str | None = None,
) -> Callable[[str, dict[str, Any], str], None] | None:
    """Create a security event sink function for the SecurityEventRouter.

    This factory function creates a closure that filters events by severity
    and forwards them to a webhook endpoint.

    Args:
        url: Webhook endpoint URL
        token: Bearer token for authentication
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        backoff: Exponential backoff multiplier
        queue_path: Optional path for queue persistence
        encryption_key: Optional encryption key for queue

    Returns:
        Sink function or None if URL is empty
    """
    sanitized_url = (url or "").strip()
    if not sanitized_url:
        return None

    base_headers = {"Content-Type": "application/json"}
    auth_token = (token or "").strip()
    if auth_token:
        scheme = "Bearer " if not auth_token.lower().startswith("bearer ") else ""
        base_headers["Authorization"] = f"{scheme}{auth_token}".strip()

    forwarder = SecurityWebhookForwarder(
        sanitized_url,
        base_headers,
        timeout=timeout,
        max_retries=max(1, max_retries),
        backoff=max(backoff, 0.1),
        queue_path=queue_path,
        encryption_key=encryption_key,
    )

    def _sink(event_type: str, details: dict[str, Any], severity: str) -> None:
        """Filter and forward security events."""
        normalized = (severity or "INFO").upper()
        # Only forward WARNING and above
        if normalized not in {"WARNING", "WARN", "ERROR", "CRITICAL"}:
            return

        payload = {
            "event_type": event_type,
            "severity": normalized,
            "timestamp": time.time(),
            "details": details,
        }

        forwarder.enqueue(payload)

    return _sink


__all__ = ["SecurityWebhookForwarder", "create_security_webhook_sink"]
