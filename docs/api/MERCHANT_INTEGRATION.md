# Merchant Payment Integration Guide

Complete guide for integrating XAI payment processing into merchant applications.

## Overview

The XAI merchant payment system provides:
- Payment request creation and tracking
- QR code generation for point-of-sale
- Webhook notifications for payment events
- Payment verification and validation
- Automatic expiration handling
- Transaction confirmation tracking

## Quick Start

```python
from xai.merchant import MerchantPaymentProcessor, WebhookEvent

# Initialize processor
processor = MerchantPaymentProcessor(
    merchant_id="YOUR_MERCHANT_ID",
    webhook_secret="your_webhook_secret",
    default_expiry_minutes=60,
    required_confirmations=6
)

# Create payment request
payment = processor.create_payment_request(
    address="XAI1234567890abcdef1234567890abcdef12345678",
    amount=100.0,
    memo="Order #12345"
)

print(f"Payment request: {payment.request_id}")
print(f"Expires at: {payment.expires_at}")
```

## MerchantPaymentProcessor API

### Initialization

```python
processor = MerchantPaymentProcessor(
    merchant_id="YOUR_MERCHANT_ID",
    webhook_secret="your_webhook_secret",       # Optional: For webhook signatures
    default_expiry_minutes=60,                   # Default: 60 minutes
    required_confirmations=6                     # Default: 6 confirmations
)
```

### Creating Payment Requests

```python
payment_request = processor.create_payment_request(
    address="XAI1234567890abcdef1234567890abcdef12345678",  # Required
    amount=100.0,                                # Required
    memo="Order #12345",                         # Optional
    invoice_id="INV-001",                        # Optional
    customer_id="CUST-999",                      # Optional
    expiry_minutes=30,                           # Optional: Default 60
    webhook_url="https://yoursite.com/webhook",  # Optional
    metadata={"order_type": "online"},           # Optional
    required_confirmations=12                    # Optional: Default 6
)
```

**Returns:** `PaymentRequest` object with:
- `request_id`: Unique payment request identifier
- `merchant_id`: Your merchant ID
- `address`: Recipient XAI address
- `amount`: Payment amount
- `status`: Payment status (pending, paid, expired, cancelled)
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp
- `paid_txid`: Transaction ID (when paid)
- `confirmations`: Current confirmation count
- `webhook_url`: Webhook notification URL

### Checking Payment Status

```python
# Get payment request
payment = processor.get_payment_request(request_id)

if payment:
    print(f"Status: {payment.status.value}")
    print(f"Paid: {payment.paid_txid}")
    print(f"Confirmations: {payment.confirmations}/{payment.required_confirmations}")
    print(f"Confirmed: {payment.is_confirmed()}")
    print(f"Expired: {payment.is_expired()}")
```

### Updating Payment Status

```python
# Update with transaction info (typically called by blockchain monitor)
success = processor.update_payment_status(
    request_id=payment.request_id,
    txid="tx123abc",
    confirmations=3
)

if success:
    print("Payment status updated")
```

### Payment Verification

```python
# Verify payment matches request
result = processor.verify_payment(
    request_id=payment.request_id,
    txid="tx123abc",
    amount=100.0,
    recipient="XAI1234567890abcdef1234567890abcdef12345678"
)

if result["valid"]:
    print("Payment verified successfully")
else:
    print(f"Verification failed: {result['error']}")
    print(f"Error code: {result['error_code']}")
```

**Verification Checks:**
- Payment request exists and not expired
- Amount matches expected amount (within 0.000001 tolerance)
- Recipient address matches
- Not already paid by different transaction

**Error Codes:**
- `request_not_found`: Payment request ID not found
- `request_expired`: Payment request has expired
- `already_paid`: Already paid by different transaction
- `amount_mismatch`: Payment amount doesn't match
- `recipient_mismatch`: Recipient address doesn't match

### Cancelling Payments

```python
# Cancel pending payment request
success = processor.cancel_payment_request(request_id)

if success:
    print("Payment request cancelled")
else:
    print("Cannot cancel (not pending or not found)")
```

### Expiration Handling

```python
# Check for expired payments
expired_ids = processor.check_expired_payments()
print(f"Expired: {len(expired_ids)} payments")

# Or check individual payment
if payment.is_expired():
    print("Payment has expired")
```

## Webhook Notifications

### Starting Webhook Delivery

```python
# Start background webhook delivery thread
processor.start_webhook_delivery()

# Stop when shutting down
processor.stop_webhook_delivery()
```

### Webhook Events

- **payment.created** - Payment request created
- **payment.pending** - Payment received (awaiting confirmations)
- **payment.confirmed** - Payment fully confirmed
- **payment.expired** - Payment request expired
- **payment.cancelled** - Payment request cancelled
- **payment.failed** - Payment processing failed

### Webhook Payload Format

```json
{
  "event": "payment.confirmed",
  "timestamp": 1703001234,
  "signature": "hmac_sha256_signature",
  "data": {
    "request_id": "uuid",
    "merchant_id": "YOUR_MERCHANT_ID",
    "address": "XAI1234567890abcdef1234567890abcdef12345678",
    "amount": 100.0,
    "currency": "XAI",
    "memo": "Order #12345",
    "invoice_id": "INV-001",
    "customer_id": "CUST-999",
    "status": "paid",
    "paid_txid": "tx123abc",
    "paid_at": 1703001500,
    "confirmations": 6,
    "confirmed_at": 1703002000,
    "metadata": {"order_type": "online"}
  }
}
```

### Webhook Signature Verification

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload, secret):
    """Verify webhook signature to ensure authenticity."""
    signature = payload.pop("signature", "")

    # Regenerate signature
    payload_json = json.dumps(payload, sort_keys=True)
    expected = hmac.new(
        secret.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)

# In your webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.json

    if not verify_webhook_signature(payload.copy(), WEBHOOK_SECRET):
        return jsonify({"error": "Invalid signature"}), 401

    event = payload["event"]
    data = payload["data"]

    if event == "payment.confirmed":
        # Process confirmed payment
        print(f"Payment confirmed: {data['request_id']}")
        # Update order status, send confirmation email, etc.

    return jsonify({"status": "received"}), 200
```

### Event Handlers (Alternative to Webhooks)

```python
# Register event handler function
def on_payment_confirmed(payment_request):
    print(f"Payment {payment_request.request_id} confirmed!")
    # Send confirmation email
    # Update inventory
    # etc.

processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, on_payment_confirmed)

# Multiple handlers can be registered for same event
processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, send_receipt_email)
processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, update_inventory)
```

## Point of Sale Integration

Complete example for retail POS:

```python
from xai.merchant import MerchantPaymentProcessor
from xai.mobile.qr_transactions import TransactionQRGenerator
from PIL import Image
from io import BytesIO
import time

# Initialize
processor = MerchantPaymentProcessor(
    merchant_id="STORE_123",
    default_expiry_minutes=15
)

def process_sale(items, total_amount):
    """Process a sale with QR code payment."""
    # Create payment request
    payment = processor.create_payment_request(
        address="XAI1234567890abcdef1234567890abcdef12345678",
        amount=total_amount,
        memo=f"Purchase: {', '.join(items)}",
        expiry_minutes=5
    )

    # Generate QR code
    qr_bytes = TransactionQRGenerator.generate_payment_request_qr(
        address=payment.address,
        amount=payment.amount,
        message=payment.memo,
        return_format="bytes"
    )

    # Display QR code on POS screen
    img = Image.open(BytesIO(qr_bytes))
    img.show()  # Or display on POS terminal

    print(f"Scan to pay {total_amount} XAI")
    print(f"Payment expires in 5 minutes")

    # Monitor payment
    start_time = time.time()
    while time.time() - start_time < 300:  # 5 minutes
        updated = processor.get_payment_request(payment.request_id)

        if updated.status.value == "paid":
            print(f"Payment received: {updated.paid_txid}")

            # Wait for confirmations
            while not updated.is_confirmed():
                time.sleep(5)
                updated = processor.get_payment_request(payment.request_id)
                print(f"Confirmations: {updated.confirmations}/{updated.required_confirmations}")

            print("Payment confirmed!")
            print_receipt(payment, updated)
            return True

        time.sleep(2)

    print("Payment timeout - cancelling")
    processor.cancel_payment_request(payment.request_id)
    return False

# Use it
items = ["Cappuccino", "Croissant"]
total = 5.50

if process_sale(items, total):
    print("Sale completed!")
else:
    print("Sale cancelled")
```

## E-Commerce Integration

Example for online store checkout:

```python
from flask import Flask, jsonify, request
from xai.merchant import MerchantPaymentProcessor, WebhookEvent

app = Flask(__name__)

processor = MerchantPaymentProcessor(
    merchant_id="WEBSTORE_456",
    webhook_secret="webhook_secret_key",
    default_expiry_minutes=60
)
processor.start_webhook_delivery()

# Event handler for confirmed payments
def on_payment_confirmed(payment_request):
    """Handle confirmed payment."""
    invoice_id = payment_request.invoice_id
    customer_id = payment_request.customer_id

    # Update order status in database
    update_order_status(invoice_id, "paid", payment_request.paid_txid)

    # Send confirmation email
    send_order_confirmation(customer_id, invoice_id)

    # Process fulfillment
    process_order_fulfillment(invoice_id)

processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, on_payment_confirmed)

@app.route("/checkout", methods=["POST"])
def checkout():
    """Create payment request for checkout."""
    data = request.json

    # Create payment request
    payment = processor.create_payment_request(
        address=get_merchant_address(),
        amount=data["total"],
        memo=f"Order #{data['order_id']}",
        invoice_id=data["order_id"],
        customer_id=data["customer_id"],
        webhook_url="https://yourstore.com/webhook/xai",
        metadata={
            "customer_email": data["email"],
            "items": data["items"]
        }
    )

    # Generate QR code
    from xai.mobile.qr_transactions import TransactionQRGenerator
    qr_code = TransactionQRGenerator.generate_payment_request_qr(
        address=payment.address,
        amount=payment.amount,
        message=payment.memo,
        return_format="base64"
    )

    return jsonify({
        "request_id": payment.request_id,
        "amount": payment.amount,
        "address": payment.address,
        "qr_code": qr_code,
        "expires_at": payment.expires_at
    })

@app.route("/payment/status/<request_id>", methods=["GET"])
def payment_status(request_id):
    """Check payment status."""
    payment = processor.get_payment_request(request_id)

    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify({
        "request_id": payment.request_id,
        "status": payment.status.value,
        "paid_txid": payment.paid_txid,
        "confirmations": payment.confirmations,
        "confirmed": payment.is_confirmed(),
        "expired": payment.is_expired()
    })
```

## Statistics and Monitoring

```python
# Get processor statistics
stats = processor.get_statistics()

print(f"Merchant: {stats['merchant_id']}")
print(f"Total requests: {stats['payment_requests']['total']}")
print(f"Pending: {stats['payment_requests']['pending']}")
print(f"Paid: {stats['payment_requests']['paid']}")
print(f"Expired: {stats['payment_requests']['expired']}")
print(f"Cancelled: {stats['payment_requests']['cancelled']}")
print(f"Webhooks delivered: {stats['webhooks']['delivered']}")
print(f"Webhooks failed: {stats['webhooks']['failed']}")

# Get webhook delivery history
deliveries = processor.get_webhook_deliveries(request_id=payment.request_id)
for delivery in deliveries:
    print(f"Event: {delivery.event}")
    print(f"Status: {delivery.status.value}")
    print(f"Attempts: {delivery.attempts}")
```

## Payment Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting payment |
| `paid` | Payment received, awaiting confirmations |
| `expired` | Payment request expired |
| `cancelled` | Payment request cancelled |
| `failed` | Payment processing failed |

## Best Practices

1. **Always verify payments** - Use `verify_payment()` before fulfilling orders
2. **Wait for confirmations** - Check `is_confirmed()` for high-value transactions
3. **Handle expiration** - Set appropriate expiry times and monitor expired payments
4. **Secure webhooks** - Always verify webhook signatures
5. **Monitor statistics** - Track payment success rates and webhook delivery
6. **Handle errors gracefully** - Implement retry logic for webhook failures
7. **Test thoroughly** - Use test mode before production deployment

## Testing

```bash
# Run merchant payment processor tests
pytest tests/xai_tests/unit/test_merchant_payment_processor.py -v

# Run payment API tests
pytest tests/xai_tests/unit/test_payment_qr.py -v
```

## Production Deployment

For production use:

1. Use persistent storage (Redis/database) instead of in-memory storage
2. Implement webhook retry queue with exponential backoff
3. Monitor webhook delivery failures
4. Set up alerting for payment issues
5. Implement rate limiting
6. Use HTTPS for all webhook URLs
7. Rotate webhook secrets regularly
8. Implement idempotency for webhook handlers

## Support

For issues or questions:
- Documentation: `/docs/api/PAYMENT_QR_API.md`
- API Reference: `/docs/api/openapi.yaml`
- Source: `/src/xai/merchant/`
