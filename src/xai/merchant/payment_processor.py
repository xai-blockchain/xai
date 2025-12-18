"""
Merchant Payment Processor

Provides merchant-focused payment processing capabilities including:
- Payment request creation and tracking
- Webhook notifications for payment events
- Payment verification and validation
- Invoice management
- Automatic expiration handling
"""

from __future__ import annotations

import logging
import time
import hmac
import hashlib
import json
import threading
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available - webhook delivery disabled")


class PaymentStatus(Enum):
    """Payment request status"""
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class WebhookEvent(Enum):
    """Webhook event types"""
    PAYMENT_CREATED = "payment.created"
    PAYMENT_PENDING = "payment.pending"
    PAYMENT_CONFIRMED = "payment.confirmed"
    PAYMENT_EXPIRED = "payment.expired"
    PAYMENT_CANCELLED = "payment.cancelled"
    PAYMENT_FAILED = "payment.failed"


class WebhookDeliveryStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    ABANDONED = "abandoned"


@dataclass
class PaymentRequest:
    """Represents a merchant payment request"""
    request_id: str
    merchant_id: str
    address: str
    amount: float
    currency: str = "XAI"
    memo: str = ""
    invoice_id: Optional[str] = None
    customer_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: int = field(default_factory=lambda: int(time.time()))
    expires_at: Optional[int] = None
    paid_at: Optional[int] = None
    confirmed_at: Optional[int] = None

    # Status tracking
    status: PaymentStatus = PaymentStatus.PENDING
    paid_txid: Optional[str] = None
    confirmations: int = 0
    required_confirmations: int = 6

    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_events: List[str] = field(default_factory=lambda: [e.value for e in WebhookEvent])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    def is_expired(self) -> bool:
        """Check if payment request has expired"""
        if self.expires_at is None:
            return False
        if self.status == PaymentStatus.PAID:
            return False  # Paid payments don't expire
        return int(time.time()) > self.expires_at

    def is_confirmed(self) -> bool:
        """Check if payment is confirmed"""
        return self.confirmations >= self.required_confirmations


@dataclass
class WebhookDelivery:
    """Tracks webhook delivery attempts"""
    delivery_id: str
    request_id: str
    event: str
    url: str
    payload: Dict[str, Any]

    created_at: int = field(default_factory=lambda: int(time.time()))
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING

    attempts: int = 0
    max_attempts: int = 5
    last_attempt_at: Optional[int] = None
    next_attempt_at: Optional[int] = None

    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None

    def should_retry(self) -> bool:
        """Check if delivery should be retried"""
        if self.status == WebhookDeliveryStatus.DELIVERED:
            return False
        if self.attempts >= self.max_attempts:
            return False
        if self.next_attempt_at is None:
            return True
        return int(time.time()) >= self.next_attempt_at

    def calculate_next_attempt(self) -> int:
        """Calculate next retry time with exponential backoff"""
        # Exponential backoff: 1min, 5min, 15min, 1hour, 6hours
        delays = [60, 300, 900, 3600, 21600]
        delay = delays[min(self.attempts, len(delays) - 1)]
        return int(time.time()) + delay


class MerchantPaymentProcessor:
    """
    Merchant payment processor with webhook notifications.

    This class provides merchant-focused payment processing:
    - Payment request creation and tracking
    - Webhook notifications for payment events
    - Payment verification and validation
    - Automatic expiration handling
    """

    def __init__(
        self,
        merchant_id: str,
        webhook_secret: Optional[str] = None,
        default_expiry_minutes: int = 60,
        required_confirmations: int = 6
    ):
        """
        Initialize merchant payment processor.

        Args:
            merchant_id: Unique merchant identifier
            webhook_secret: Secret key for webhook signature verification
            default_expiry_minutes: Default payment expiry time in minutes
            required_confirmations: Required confirmations for payment finality
        """
        self.merchant_id = merchant_id
        self.webhook_secret = webhook_secret
        self.default_expiry_minutes = default_expiry_minutes
        self.required_confirmations = required_confirmations

        # Storage
        self._payment_requests: Dict[str, PaymentRequest] = {}
        self._webhook_deliveries: Dict[str, WebhookDelivery] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Background webhook delivery
        self._webhook_thread: Optional[threading.Thread] = None
        self._webhook_queue: List[WebhookDelivery] = []
        self._webhook_lock = threading.Lock()
        self._running = False

    def create_payment_request(
        self,
        address: str,
        amount: float,
        memo: str = "",
        invoice_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        expiry_minutes: Optional[int] = None,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        required_confirmations: Optional[int] = None
    ) -> PaymentRequest:
        """
        Create a new payment request.

        Args:
            address: Recipient XAI address
            amount: Payment amount
            memo: Payment memo/description
            invoice_id: Optional invoice identifier
            customer_id: Optional customer identifier
            expiry_minutes: Payment expiry time (uses default if not specified)
            webhook_url: URL for webhook notifications
            metadata: Additional metadata to store with payment
            required_confirmations: Required confirmations (uses default if not specified)

        Returns:
            PaymentRequest object

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if not address or not address.startswith("XAI"):
            raise ValueError("Invalid XAI address")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if memo and len(memo) > 1000:
            raise ValueError("Memo exceeds 1000 characters")

        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())

        # Calculate expiry
        expiry_mins = expiry_minutes if expiry_minutes is not None else self.default_expiry_minutes
        expires_at = int(time.time()) + (expiry_mins * 60) if expiry_mins > 0 else int(time.time())

        # Create payment request
        payment_request = PaymentRequest(
            request_id=request_id,
            merchant_id=self.merchant_id,
            address=address,
            amount=amount,
            memo=memo,
            invoice_id=invoice_id,
            customer_id=customer_id,
            expires_at=expires_at,
            webhook_url=webhook_url,
            webhook_secret=self.webhook_secret,
            metadata=metadata or {},
            required_confirmations=required_confirmations or self.required_confirmations
        )

        # Store payment request
        self._payment_requests[request_id] = payment_request

        # Trigger payment created event
        self._trigger_event(WebhookEvent.PAYMENT_CREATED, payment_request)

        logger.info(
            "Payment request created",
            extra={
                "event": "payment.created",
                "request_id": request_id,
                "merchant_id": self.merchant_id,
                "amount": amount,
                "address": address,
                "expires_at": expires_at
            }
        )

        return payment_request

    def get_payment_request(self, request_id: str) -> Optional[PaymentRequest]:
        """
        Get payment request by ID.

        Args:
            request_id: Payment request ID

        Returns:
            PaymentRequest or None if not found
        """
        return self._payment_requests.get(request_id)

    def update_payment_status(
        self,
        request_id: str,
        txid: str,
        confirmations: int = 0
    ) -> bool:
        """
        Update payment status with transaction info.

        Args:
            request_id: Payment request ID
            txid: Transaction ID
            confirmations: Number of confirmations

        Returns:
            True if updated successfully
        """
        payment_request = self._payment_requests.get(request_id)
        if not payment_request:
            logger.warning(f"Payment request not found: {request_id}")
            return False

        # Check if expired
        if payment_request.is_expired():
            if payment_request.status == PaymentStatus.PENDING:
                payment_request.status = PaymentStatus.EXPIRED
                self._trigger_event(WebhookEvent.PAYMENT_EXPIRED, payment_request)
            return False

        # Update payment status
        old_status = payment_request.status
        payment_request.paid_txid = txid
        payment_request.confirmations = confirmations

        # First payment detection
        if old_status == PaymentStatus.PENDING:
            payment_request.status = PaymentStatus.PAID
            payment_request.paid_at = int(time.time())
            self._trigger_event(WebhookEvent.PAYMENT_PENDING, payment_request)

        # Confirmation milestone reached
        if confirmations >= payment_request.required_confirmations:
            if payment_request.confirmed_at is None:
                payment_request.confirmed_at = int(time.time())
                self._trigger_event(WebhookEvent.PAYMENT_CONFIRMED, payment_request)

        logger.info(
            "Payment status updated",
            extra={
                "event": "payment.updated",
                "request_id": request_id,
                "txid": txid,
                "confirmations": confirmations,
                "status": payment_request.status.value
            }
        )

        return True

    def cancel_payment_request(self, request_id: str) -> bool:
        """
        Cancel a pending payment request.

        Args:
            request_id: Payment request ID

        Returns:
            True if cancelled successfully
        """
        payment_request = self._payment_requests.get(request_id)
        if not payment_request:
            return False

        if payment_request.status != PaymentStatus.PENDING:
            return False

        payment_request.status = PaymentStatus.CANCELLED
        self._trigger_event(WebhookEvent.PAYMENT_CANCELLED, payment_request)

        logger.info(
            "Payment request cancelled",
            extra={
                "event": "payment.cancelled",
                "request_id": request_id,
                "merchant_id": self.merchant_id
            }
        )

        return True

    def verify_payment(
        self,
        request_id: str,
        txid: str,
        amount: float,
        recipient: str
    ) -> Dict[str, Any]:
        """
        Verify a payment against a request.

        Args:
            request_id: Payment request ID
            txid: Transaction ID
            amount: Payment amount
            recipient: Recipient address

        Returns:
            Verification result dictionary
        """
        payment_request = self._payment_requests.get(request_id)

        if not payment_request:
            return {
                "valid": False,
                "error": "Payment request not found",
                "error_code": "request_not_found"
            }

        # Check expiry
        if payment_request.is_expired():
            return {
                "valid": False,
                "error": "Payment request expired",
                "error_code": "request_expired",
                "expires_at": payment_request.expires_at
            }

        # Check already paid
        if payment_request.status == PaymentStatus.PAID and payment_request.paid_txid != txid:
            return {
                "valid": False,
                "error": "Payment request already paid",
                "error_code": "already_paid",
                "paid_txid": payment_request.paid_txid
            }

        # Verify amount
        if abs(amount - payment_request.amount) > 0.000001:  # Floating point tolerance
            return {
                "valid": False,
                "error": "Amount mismatch",
                "error_code": "amount_mismatch",
                "expected": payment_request.amount,
                "received": amount
            }

        # Verify recipient
        if recipient != payment_request.address:
            return {
                "valid": False,
                "error": "Recipient mismatch",
                "error_code": "recipient_mismatch",
                "expected": payment_request.address,
                "received": recipient
            }

        # Verification passed
        return {
            "valid": True,
            "request_id": request_id,
            "merchant_id": payment_request.merchant_id,
            "amount": payment_request.amount,
            "status": payment_request.status.value,
            "confirmations": payment_request.confirmations,
            "required_confirmations": payment_request.required_confirmations,
            "confirmed": payment_request.is_confirmed()
        }

    def check_expired_payments(self) -> List[str]:
        """
        Check for expired payment requests and update their status.

        Returns:
            List of expired request IDs
        """
        expired_requests = []
        current_time = int(time.time())

        for request_id, payment_request in self._payment_requests.items():
            if (payment_request.status == PaymentStatus.PENDING and
                payment_request.expires_at and
                current_time > payment_request.expires_at):

                payment_request.status = PaymentStatus.EXPIRED
                self._trigger_event(WebhookEvent.PAYMENT_EXPIRED, payment_request)
                expired_requests.append(request_id)

                logger.info(
                    "Payment request expired",
                    extra={
                        "event": "payment.expired",
                        "request_id": request_id,
                        "expired_at": payment_request.expires_at
                    }
                )

        return expired_requests

    def _trigger_event(self, event: WebhookEvent, payment_request: PaymentRequest):
        """
        Trigger event handlers and webhook notifications.

        Args:
            event: Webhook event type
            payment_request: Payment request object
        """
        # Call registered event handlers
        handlers = self._event_handlers.get(event.value, [])
        for handler in handlers:
            try:
                handler(payment_request)
            except Exception as e:
                logger.error(
                    f"Event handler failed for {event.value}",
                    extra={"error": str(e), "request_id": payment_request.request_id}
                )

        # Queue webhook delivery
        if payment_request.webhook_url and event.value in payment_request.webhook_events:
            self._queue_webhook(event, payment_request)

    def _queue_webhook(self, event: WebhookEvent, payment_request: PaymentRequest):
        """
        Queue webhook for delivery.

        Args:
            event: Webhook event type
            payment_request: Payment request object
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Webhook skipped - requests library not available")
            return

        import uuid
        delivery_id = str(uuid.uuid4())

        # Build webhook payload
        payload = {
            "event": event.value,
            "timestamp": int(time.time()),
            "data": payment_request.to_dict()
        }

        # Add signature if secret is configured
        if payment_request.webhook_secret:
            signature = self._generate_webhook_signature(payload, payment_request.webhook_secret)
            payload["signature"] = signature

        # Create delivery record
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            request_id=payment_request.request_id,
            event=event.value,
            url=payment_request.webhook_url,
            payload=payload
        )

        # Store and queue for delivery
        self._webhook_deliveries[delivery_id] = delivery
        with self._webhook_lock:
            self._webhook_queue.append(delivery)

        # Start webhook delivery thread if not running
        if not self._running:
            self.start_webhook_delivery()

    def _generate_webhook_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            payload: Webhook payload
            secret: Webhook secret key

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_webhook_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Webhook payload
            signature: Provided signature
            secret: Webhook secret key

        Returns:
            True if signature is valid
        """
        expected_signature = self._generate_webhook_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)

    def start_webhook_delivery(self):
        """Start background webhook delivery thread"""
        if self._running:
            return

        self._running = True
        self._webhook_thread = threading.Thread(target=self._webhook_delivery_worker, daemon=True)
        self._webhook_thread.start()
        logger.info("Webhook delivery thread started")

    def stop_webhook_delivery(self):
        """Stop background webhook delivery thread"""
        self._running = False
        if self._webhook_thread:
            self._webhook_thread.join(timeout=5)
        logger.info("Webhook delivery thread stopped")

    def _webhook_delivery_worker(self):
        """Background worker for webhook delivery"""
        while self._running:
            try:
                # Get pending webhooks
                with self._webhook_lock:
                    pending = [d for d in self._webhook_queue if d.should_retry()]
                    if pending:
                        delivery = pending[0]
                        self._webhook_queue.remove(delivery)
                    else:
                        delivery = None

                if delivery:
                    self._deliver_webhook(delivery)
                else:
                    time.sleep(1)  # Sleep if no pending webhooks

            except Exception as e:
                logger.error(f"Webhook delivery worker error: {e}")
                time.sleep(5)

    def _deliver_webhook(self, delivery: WebhookDelivery):
        """
        Deliver webhook to endpoint.

        Args:
            delivery: WebhookDelivery object
        """
        if not REQUESTS_AVAILABLE:
            return

        delivery.attempts += 1
        delivery.last_attempt_at = int(time.time())
        delivery.status = WebhookDeliveryStatus.RETRYING if delivery.attempts > 1 else WebhookDeliveryStatus.PENDING

        try:
            # Send webhook
            response = requests.post(
                delivery.url,
                json=delivery.payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "XAI-MerchantProcessor/1.0",
                    "X-XAI-Event": delivery.event,
                    "X-XAI-Delivery-ID": delivery.delivery_id
                },
                timeout=10
            )

            delivery.response_code = response.status_code
            delivery.response_body = response.text[:1000]  # Store first 1000 chars

            # Check success
            if 200 <= response.status_code < 300:
                delivery.status = WebhookDeliveryStatus.DELIVERED
                logger.info(
                    "Webhook delivered successfully",
                    extra={
                        "delivery_id": delivery.delivery_id,
                        "request_id": delivery.request_id,
                        "event": delivery.event,
                        "attempts": delivery.attempts
                    }
                )
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            delivery.error_message = str(e)

            # Retry logic
            if delivery.attempts < delivery.max_attempts:
                delivery.next_attempt_at = delivery.calculate_next_attempt()
                with self._webhook_lock:
                    self._webhook_queue.append(delivery)  # Re-queue for retry

                logger.warning(
                    "Webhook delivery failed, will retry",
                    extra={
                        "delivery_id": delivery.delivery_id,
                        "request_id": delivery.request_id,
                        "attempts": delivery.attempts,
                        "next_attempt": delivery.next_attempt_at,
                        "error": str(e)
                    }
                )
            else:
                delivery.status = WebhookDeliveryStatus.ABANDONED
                logger.error(
                    "Webhook delivery abandoned after max attempts",
                    extra={
                        "delivery_id": delivery.delivery_id,
                        "request_id": delivery.request_id,
                        "attempts": delivery.attempts,
                        "error": str(e)
                    }
                )

    def on_event(self, event: WebhookEvent, handler: Callable):
        """
        Register an event handler.

        Args:
            event: Event type to listen for
            handler: Callable that accepts PaymentRequest
        """
        if event.value not in self._event_handlers:
            self._event_handlers[event.value] = []
        self._event_handlers[event.value].append(handler)

    def get_webhook_deliveries(self, request_id: Optional[str] = None) -> List[WebhookDelivery]:
        """
        Get webhook delivery history.

        Args:
            request_id: Optional filter by payment request ID

        Returns:
            List of webhook deliveries
        """
        if request_id:
            return [d for d in self._webhook_deliveries.values() if d.request_id == request_id]
        return list(self._webhook_deliveries.values())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get payment processor statistics.

        Returns:
            Statistics dictionary
        """
        total_requests = len(self._payment_requests)
        pending = sum(1 for p in self._payment_requests.values() if p.status == PaymentStatus.PENDING)
        paid = sum(1 for p in self._payment_requests.values() if p.status == PaymentStatus.PAID)
        expired = sum(1 for p in self._payment_requests.values() if p.status == PaymentStatus.EXPIRED)
        cancelled = sum(1 for p in self._payment_requests.values() if p.status == PaymentStatus.CANCELLED)

        total_webhooks = len(self._webhook_deliveries)
        webhooks_delivered = sum(1 for w in self._webhook_deliveries.values()
                                 if w.status == WebhookDeliveryStatus.DELIVERED)
        webhooks_failed = sum(1 for w in self._webhook_deliveries.values()
                              if w.status == WebhookDeliveryStatus.ABANDONED)

        return {
            "merchant_id": self.merchant_id,
            "payment_requests": {
                "total": total_requests,
                "pending": pending,
                "paid": paid,
                "expired": expired,
                "cancelled": cancelled
            },
            "webhooks": {
                "total": total_webhooks,
                "delivered": webhooks_delivered,
                "failed": webhooks_failed,
                "pending": len(self._webhook_queue)
            },
            "webhook_delivery_running": self._running
        }
