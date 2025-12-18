# Payment QR Code API

Payment QR code generation and tracking endpoints for XAI blockchain.

## Overview

The Payment QR API provides endpoints for generating QR codes for XAI payments, creating tracked payment requests, and parsing payment URIs. This enables mobile wallets and point-of-sale systems to easily integrate XAI payments.

## Payment URI Format

Payment URIs follow the format:
```
xai:<address>?amount=<amount>&memo=<memo>&exp=<timestamp>
```

Example:
```
xai:XAI1234567890abcdef1234567890abcdef12345678?amount=100.50&memo=Invoice%20123&exp=1703001234
```

## Endpoints

### GET /payment/qr/<address>

Generate a simple QR code for an address.

**Query Parameters:**
- `format` (optional): Response format - `image` (default) or `base64`

**Response (image format):**
- Content-Type: `image/png`
- Body: PNG image data

**Response (base64 format):**
```json
{
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "qr_code": "<base64_encoded_png>",
  "uri": "xai:XAI1234567890abcdef1234567890abcdef12345678",
  "format": "base64"
}
```

**Example:**
```bash
# Get QR as PNG image
curl http://localhost:12001/payment/qr/XAI1234567890abcdef1234567890abcdef12345678

# Get QR as base64 JSON
curl http://localhost:12001/payment/qr/XAI1234567890abcdef1234567890abcdef12345678?format=base64
```

### POST /payment/qr

Generate a payment request QR code with amount, memo, and expiry.

**Request Body:**
```json
{
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": "100.50",
  "memo": "Invoice #123",
  "expiry_minutes": 30,
  "format": "base64"
}
```

**Fields:**
- `address` (required): Recipient address
- `amount` (optional): Payment amount
- `memo` (optional): Payment memo (max 1000 chars)
- `expiry_minutes` (optional): Expiry time in minutes
- `format` (optional): Response format - `image` or `base64` (default)

**Response (base64 format):**
```json
{
  "qr_code": "<base64_encoded_png>",
  "uri": "xai:XAI...?amount=100.50&memo=Invoice%20123&exp=1703001234",
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": 100.50,
  "memo": "Invoice #123",
  "expires_at": 1703001234,
  "format": "base64"
}
```

**Example:**
```bash
curl -X POST http://localhost:12001/payment/qr \
  -H "Content-Type: application/json" \
  -d '{
    "address": "XAI1234567890abcdef1234567890abcdef12345678",
    "amount": "100.50",
    "memo": "Coffee purchase",
    "expiry_minutes": 15
  }'
```

### POST /payment/request

Create a tracked payment request with QR code.

**Request Body:**
```json
{
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": "100.50",
  "memo": "Invoice #123",
  "expiry_minutes": 30,
  "callback_url": "https://merchant.com/webhook"
}
```

**Fields:**
- `address` (required): Recipient address
- `amount` (required): Payment amount
- `memo` (optional): Payment memo
- `expiry_minutes` (optional): Expiry time (default: 60)
- `callback_url` (optional): Webhook URL for payment notification

**Response (201 Created):**
```json
{
  "request_id": "uuid-here",
  "qr_code": "<base64_encoded_png>",
  "uri": "xai:XAI...?amount=100.50&memo=Invoice%20123&exp=1703001234",
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": 100.50,
  "memo": "Invoice #123",
  "expires_at": 1703001234,
  "created_at": 1703000234,
  "status": "pending"
}
```

**Example:**
```bash
curl -X POST http://localhost:12001/payment/request \
  -H "Content-Type: application/json" \
  -d '{
    "address": "XAI1234567890abcdef1234567890abcdef12345678",
    "amount": "75.00",
    "memo": "Order #456"
  }'
```

### GET /payment/request/<request_id>

Check payment request status.

**Response:**
```json
{
  "request_id": "uuid-here",
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": 100.50,
  "memo": "Invoice #123",
  "expires_at": 1703001234,
  "created_at": 1703000234,
  "status": "pending",
  "paid_txid": null,
  "paid_at": null
}
```

**Status Values:**
- `pending`: Awaiting payment
- `paid`: Payment received
- `expired`: Request expired
- `cancelled`: Request cancelled

**When paid:**
```json
{
  ...
  "status": "paid",
  "paid_txid": "tx123...",
  "paid_at": 1703000500
}
```

**Example:**
```bash
curl http://localhost:12001/payment/request/uuid-here
```

### POST /payment/parse

Parse a payment URI from QR code scan.

**Request Body:**
```json
{
  "uri": "xai:XAI...?amount=100.50&memo=Invoice%20123&exp=1703001234"
}
```

**Response:**
```json
{
  "address": "XAI1234567890abcdef1234567890abcdef12345678",
  "amount": 100.50,
  "memo": "Invoice 123",
  "expires_at": 1703001234,
  "valid": true,
  "expired": false
}
```

**Example:**
```bash
curl -X POST http://localhost:12001/payment/parse \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "xai:XAI1234567890abcdef1234567890abcdef12345678?amount=50.00"
  }'
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed explanation",
  "code": "error_code"
}
```

**Common Error Codes:**
- `qrcode_unavailable`: QR code library not installed
- `invalid_address`: Invalid XAI address format
- `invalid_amount`: Invalid or negative amount
- `invalid_expiry`: Invalid expiry time
- `memo_too_long`: Memo exceeds 1000 characters
- `missing_address`: Address field missing
- `missing_amount`: Amount field missing
- `missing_uri`: URI field missing
- `invalid_uri`: Malformed payment URI
- `request_not_found`: Payment request not found
- `qr_generation_error`: QR code generation failed
- `parse_error`: URI parsing failed

## Usage Examples

### Point of Sale System

```python
import requests

# Create payment request
response = requests.post("http://localhost:12001/payment/request", json={
    "address": "XAI1234567890abcdef1234567890abcdef12345678",
    "amount": "25.00",
    "memo": "Coffee and pastry",
    "expiry_minutes": 5
})

request_data = response.json()
request_id = request_data["request_id"]
qr_code = request_data["qr_code"]

# Display QR code to customer
# ... show QR on screen ...

# Poll for payment
import time
while True:
    status = requests.get(f"http://localhost:12001/payment/request/{request_id}")
    status_data = status.json()

    if status_data["status"] == "paid":
        print(f"Payment received! TX: {status_data['paid_txid']}")
        break
    elif status_data["status"] == "expired":
        print("Payment request expired")
        break

    time.sleep(2)
```

### Mobile Wallet QR Scan

```python
import requests

# User scans QR code, app extracts URI
scanned_uri = "xai:XAI1234567890abcdef1234567890abcdef12345678?amount=50.00&memo=Lunch"

# Parse the URI
response = requests.post("http://localhost:12001/payment/parse", json={
    "uri": scanned_uri
})

payment_info = response.json()

# Display to user
print(f"Pay {payment_info['amount']} XAI")
print(f"To: {payment_info['address']}")
print(f"Memo: {payment_info['memo']}")
print(f"Valid: {payment_info['valid']}")
print(f"Expired: {payment_info['expired']}")

# User confirms and sends transaction
# ...
```

### Simple Address QR

```python
import requests
from io import BytesIO
from PIL import Image

# Get QR code as PNG
response = requests.get(
    "http://localhost:12001/payment/qr/XAI1234567890abcdef1234567890abcdef12345678"
)

# Display the QR code
img = Image.open(BytesIO(response.content))
img.show()

# Or get as base64
response = requests.get(
    "http://localhost:12001/payment/qr/XAI1234567890abcdef1234567890abcdef12345678?format=base64"
)
data = response.json()
qr_base64 = data["qr_code"]
# ... use base64 string in HTML/mobile app ...
```

## Security Considerations

1. **Address Validation**: All addresses are validated using XAI's checksum validation
2. **Input Sanitization**: All inputs are sanitized to prevent injection attacks
3. **Amount Validation**: Amounts are validated to prevent overflow and negative values
4. **Memo Length Limits**: Memos are limited to 1000 characters
5. **Expiry Enforcement**: Expired payment requests cannot be paid
6. **QR Data Limits**: QR data is limited to 4096 bytes to prevent memory issues

## Requirements

- Python 3.12+
- `qrcode[pil]>=7.4.0` package
- Flask web framework
- XAI blockchain node

## Installation

The qrcode library is included in requirements:

```bash
pip install -r src/xai/requirements.txt
```

Or install manually:

```bash
pip install 'qrcode[pil]>=7.4.0'
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/xai_tests/unit/test_payment_qr.py -v
```

Tests cover:
- QR code generation (image and base64)
- Payment requests with various parameters
- Payment tracking and status updates
- URI parsing and validation
- Error handling for invalid inputs
- Edge cases and boundary conditions
