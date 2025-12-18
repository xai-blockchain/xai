# XAI Merchant Payment Integration

Production-ready merchant payment processing for XAI blockchain.

## Features

- Payment request creation and tracking
- QR code generation for point-of-sale
- Webhook notifications for payment events
- Payment verification and validation
- Automatic expiration handling
- Transaction confirmation tracking
- Event-driven architecture
- HMAC signature verification for webhooks

## Quick Start

```python
from xai.merchant import MerchantPaymentProcessor

# Initialize
processor = MerchantPaymentProcessor(
    merchant_id="YOUR_MERCHANT_ID",
    webhook_secret="your_secret",
    required_confirmations=6
)

# Create payment
payment = processor.create_payment_request(
    address="XAI1234567890abcdef1234567890abcdef12345678",
    amount=100.0,
    memo="Order #12345"
)

print(f"Payment request: {payment.request_id}")
```

## Components

### MerchantPaymentProcessor

Core payment processing class with:
- Payment request creation and management
- Status tracking and updates
- Payment verification
- Webhook delivery with retry logic
- Event handlers
- Statistics tracking

### PaymentRequest

Dataclass representing a payment request:
- `request_id`: Unique identifier
- `merchant_id`: Merchant identifier
- `address`: Payment recipient address
- `amount`: Payment amount
- `status`: Current status (pending/paid/expired/cancelled)
- `paid_txid`: Transaction ID when paid
- `confirmations`: Current confirmation count
- Methods: `is_expired()`, `is_confirmed()`, `to_dict()`

### Webhook System

Automatic webhook delivery with:
- HMAC-SHA256 signature verification
- Exponential backoff retry (1m, 5m, 15m, 1h, 6h)
- Background delivery thread
- Delivery status tracking
- Event-based notifications

### Event Handlers

Register handlers for payment events:
```python
def on_confirmed(payment):
    print(f"Payment {payment.request_id} confirmed!")

processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, on_confirmed)
```

## Examples

See `/src/xai/merchant/examples/` for complete examples:
- `point_of_sale_example.py` - POS terminal integration

## API Reference

### Creating Payments

```python
payment = processor.create_payment_request(
    address=str,                    # Required: Recipient address
    amount=float,                   # Required: Payment amount
    memo=str,                       # Optional: Payment memo
    invoice_id=str,                 # Optional: Invoice ID
    customer_id=str,                # Optional: Customer ID
    expiry_minutes=int,             # Optional: Expiry time
    webhook_url=str,                # Optional: Webhook URL
    metadata=dict,                  # Optional: Metadata
    required_confirmations=int      # Optional: Required confirmations
)
```

### Checking Status

```python
payment = processor.get_payment_request(request_id)
print(f"Status: {payment.status.value}")
print(f"Confirmed: {payment.is_confirmed()}")
print(f"Expired: {payment.is_expired()}")
```

### Verifying Payments

```python
result = processor.verify_payment(
    request_id=str,
    txid=str,
    amount=float,
    recipient=str
)

if result["valid"]:
    print("Payment verified!")
```

### Managing Lifecycle

```python
# Cancel payment
processor.cancel_payment_request(request_id)

# Check expired
expired = processor.check_expired_payments()

# Get statistics
stats = processor.get_statistics()
```

## Webhook Events

- `payment.created` - Request created
- `payment.pending` - Payment received, awaiting confirmations
- `payment.confirmed` - Payment fully confirmed
- `payment.expired` - Request expired
- `payment.cancelled` - Request cancelled
- `payment.failed` - Processing failed

## Security

### Webhook Signature Verification

Webhooks include HMAC-SHA256 signatures:

```python
import hmac
import hashlib
import json

def verify_webhook(payload, secret):
    signature = payload.pop("signature")
    expected = hmac.new(
        secret.encode(),
        json.dumps(payload, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### Best Practices

1. Always verify webhook signatures
2. Use HTTPS for webhook URLs
3. Wait for required confirmations before fulfilling orders
4. Set appropriate expiry times
5. Monitor payment statistics
6. Implement idempotent webhook handlers
7. Use persistent storage in production

## Testing

```bash
pytest tests/xai_tests/unit/test_merchant_payment_processor.py -v
```

Tests cover:
- Payment creation and validation
- Status updates and confirmations
- Payment verification
- Webhook signatures
- Event handlers
- Expiration handling
- Error cases

## Documentation

- [Merchant Integration Guide](/docs/api/MERCHANT_INTEGRATION.md) - Complete integration guide
- [Payment QR API](/docs/api/PAYMENT_QR_API.md) - REST API reference

## Production Deployment

For production use:

1. **Storage**: Replace in-memory storage with Redis/database
2. **Monitoring**: Set up payment monitoring and alerting
3. **Webhooks**: Implement webhook retry queue
4. **Security**: Rotate webhook secrets regularly
5. **Rate Limiting**: Add rate limiting for API endpoints
6. **Logging**: Enhanced logging for audit trails
7. **Backup**: Regular backup of payment data

## License

Part of the XAI blockchain project.
