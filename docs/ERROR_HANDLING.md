# XAI Blockchain API - Error Handling Guide

Comprehensive guide for handling errors in the XAI Blockchain API.

## Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Error Codes](#error-codes)
- [SDK Exception Classes](#sdk-exception-classes)
- [Error Handling Patterns](#error-handling-patterns)
- [Best Practices](#best-practices)
- [Debugging](#debugging)

---

## Error Response Format

All API error responses follow a consistent format:

```json
{
  "code": 400,
  "message": "Invalid address format",
  "error": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| code | integer | HTTP status code |
| message | string | Human-readable error message |
| error | string | Machine-readable error code |
| timestamp | string | ISO 8601 timestamp of error |

---

## HTTP Status Codes

| Code | Name | Description |
|---|---|---|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server encountered an error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Error Codes

### Validation Errors (400)

| Code | Message | Description |
|---|---|---|
| VALIDATION_ERROR | Invalid address format | Address doesn't match expected format |
| VALIDATION_ERROR | Invalid amount | Amount is negative or invalid |
| VALIDATION_ERROR | Invalid transaction data | Transaction data is malformed |
| INVALID_PARAMS | Missing required parameter | Required field is missing |

### Authentication Errors (401)

| Code | Message | Description |
|---|---|---|
| UNAUTHORIZED | Invalid API key | API key is invalid or revoked |
| UNAUTHORIZED | Token expired | JWT token has expired |
| UNAUTHORIZED | Missing authorization | No auth header provided |

### Rate Limit Errors (429)

| Code | Message | Description |
|---|---|---|
| RATE_LIMITED | Rate limit exceeded | Too many requests in time window |

### Server Errors (500, 503)

| Code | Message | Description |
|---|---|---|
| INTERNAL_ERROR | Database error | Backend database error |
| SERVICE_UNAVAILABLE | Service under maintenance | Service temporarily unavailable |

---

## SDK Exception Classes

The Python SDK provides specific exception classes for different error types:

### Base Exception

```python
from xai_sdk import XAIError

# Base class for all errors
try:
    result = client.wallet.create()
except XAIError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")
    print(f"Details: {e.error_details}")
```

### Specific Exception Classes

```python
from xai_sdk import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    NotFoundError,
    ConflictError,
    InternalServerError,
    ServiceUnavailableError,
    TransactionError,
    WalletError,
    MiningError,
    GovernanceError,
)
```

### Exception Hierarchy

```
XAIError (base)
├── AuthenticationError
├── AuthorizationError
├── ValidationError
├── RateLimitError
├── NetworkError
├── TimeoutError
├── NotFoundError
├── ConflictError
├── InternalServerError
├── ServiceUnavailableError
├── TransactionError
├── WalletError
├── MiningError
└── GovernanceError
```

---

## Error Handling Patterns

### 1. Basic Try-Catch

```python
from xai_sdk import XAIClient, XAIError

client = XAIClient(api_key="your-api-key")

try:
    wallet = client.wallet.create()
except XAIError as e:
    print(f"Error: {e.message}")
```

### 2. Specific Error Handling

```python
from xai_sdk import (
    ValidationError,
    AuthenticationError,
    NetworkError,
    XAIError
)

try:
    tx = client.transaction.send(
        from_address="invalid",
        to_address="0x...",
        amount="1000"
    )
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except NetworkError as e:
    print(f"Network error: {e.message}")
except XAIError as e:
    print(f"Unknown error: {e.message}")
```

### 3. Retry with Exponential Backoff

```python
import time
from xai_sdk import RateLimitError, NetworkError

def call_with_retry(func, max_retries=3, initial_delay=1):
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or delay
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                delay *= 2  # Exponential backoff
            else:
                raise
        except NetworkError as e:
            if attempt < max_retries - 1:
                print(f"Network error. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise

# Usage
def get_balance():
    return client.wallet.get_balance("0x...")

balance = call_with_retry(get_balance)
```

### 4. Error Recovery

```python
from xai_sdk import TransactionError

def send_transaction_safely(from_addr, to_addr, amount):
    try:
        # Estimate fee first
        fee = client.transaction.estimate_fee(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount
        )
        
        # Check if sender has enough balance
        balance = client.wallet.get_balance(from_addr)
        total_needed = int(amount) + int(fee['estimated_fee'])
        
        if int(balance.balance) < total_needed:
            raise ValidationError(
                f"Insufficient balance. Need {total_needed}, have {balance.balance}"
            )
        
        # Send transaction
        tx = client.transaction.send(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount,
            gas_limit=fee['gas_limit'],
            gas_price=fee['gas_price']
        )
        
        return tx
        
    except ValidationError as e:
        print(f"Cannot send transaction: {e.message}")
        return None
    except TransactionError as e:
        print(f"Transaction failed: {e.message}")
        return None

tx = send_transaction_safely("0x...", "0x...", "1000")
```

### 5. Contextual Error Handling

```python
from xai_sdk import XAIClient, XAIError

class BlockchainClient:
    def __init__(self, api_key):
        self.client = XAIClient(api_key=api_key)
    
    def create_wallet_safe(self):
        """Create wallet with error context."""
        try:
            return self.client.wallet.create()
        except XAIError as e:
            self.log_error(
                operation="create_wallet",
                error_code=e.code,
                error_message=e.message
            )
            raise
    
    def log_error(self, operation, error_code, error_message):
        """Log error with context."""
        print(f"[{operation}] Error {error_code}: {error_message}")
```

### 6. Graceful Degradation

```python
from xai_sdk import NetworkError, ServiceUnavailableError

def get_blockchain_info():
    """Get blockchain info with fallback."""
    try:
        stats = client.blockchain.get_stats()
        return stats
    except (NetworkError, ServiceUnavailableError):
        print("Service unavailable, using cached data...")
        return load_cached_stats()

def load_cached_stats():
    """Load cached stats from local storage."""
    import json
    try:
        with open("cached_stats.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
```

### 7. Validation Before API Call

```python
from xai_sdk import ValidationError

def validate_address(address):
    """Validate address format."""
    if not address:
        raise ValidationError("Address cannot be empty")
    if not address.startswith("0x"):
        raise ValidationError("Address must start with 0x")
    if len(address) != 42:
        raise ValidationError("Address must be 42 characters")
    return True

def validate_amount(amount):
    """Validate amount."""
    try:
        int_amount = int(amount)
        if int_amount < 0:
            raise ValidationError("Amount cannot be negative")
        return True
    except ValueError:
        raise ValidationError("Amount must be a valid integer")

def safe_send_transaction(from_addr, to_addr, amount):
    """Send transaction with validation."""
    try:
        validate_address(from_addr)
        validate_address(to_addr)
        validate_amount(amount)
        
        return client.transaction.send(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount
        )
    except ValidationError as e:
        print(f"Validation failed: {e.message}")
        return None
```

---

## Best Practices

### 1. Always Use Try-Catch

```python
# Good
try:
    wallet = client.wallet.create()
except XAIError as e:
    handle_error(e)

# Bad - errors will propagate unhandled
wallet = client.wallet.create()
```

### 2. Log Errors

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = client.wallet.get_balance("0x...")
except XAIError as e:
    logger.error(f"Failed to get balance: {e.message}", exc_info=True)
```

### 3. Don't Swallow All Exceptions

```python
# Bad - swallows all errors
try:
    result = client.wallet.create()
except:
    pass

# Good - only catch expected errors
try:
    result = client.wallet.create()
except (ValidationError, NetworkError) as e:
    logger.error(f"Known error: {e.message}")
except XAIError as e:
    logger.error(f"Unexpected SDK error: {e.message}")
```

### 4. Use Specific Exceptions

```python
# Bad - too generic
try:
    tx = client.transaction.send("0x...", "0x...", "1000")
except Exception as e:
    print(e)

# Good - specific exceptions
try:
    tx = client.transaction.send("0x...", "0x...", "1000")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except TransactionError as e:
    print(f"Transaction failed: {e.message}")
```

### 5. Include Context in Errors

```python
class APIWrapper:
    def send_transaction(self, from_addr, to_addr, amount):
        try:
            return self.client.transaction.send(
                from_address=from_addr,
                to_address=to_addr,
                amount=amount
            )
        except TransactionError as e:
            # Include context in error message
            raise TransactionError(
                f"Failed to send {amount} from {from_addr} to {to_addr}: {e.message}",
                code=e.code
            )
```

### 6. Handle Rate Limits Properly

```python
from xai_sdk import RateLimitError
import time

def call_with_rate_limit_handling(func):
    try:
        return func()
    except RateLimitError as e:
        retry_after = e.retry_after or 60
        print(f"Rate limited. Retrying after {retry_after}s")
        time.sleep(retry_after)
        return func()
```

### 7. Validate Input Early

```python
def transfer_funds(from_addr, to_addr, amount):
    # Validate first
    if not from_addr or not to_addr or not amount:
        raise ValidationError("Missing required parameters")
    
    try:
        return client.transaction.send(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount
        )
    except XAIError as e:
        logger.error(f"Transfer failed: {e.message}")
        return None
```

---

## Debugging

### 1. Enable Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("xai_sdk")
logger.setLevel(logging.DEBUG)

# Now all SDK operations will be logged
client = XAIClient(api_key="your-api-key")
```

### 2. Inspect Error Details

```python
try:
    wallet = client.wallet.create()
except XAIError as e:
    print(f"Error Code: {e.code}")
    print(f"Error Message: {e.message}")
    print(f"Error Details: {e.error_details}")
    print(f"Full Traceback:")
    import traceback
    traceback.print_exc()
```

### 3. Use Debugger

```python
import pdb
from xai_sdk import XAIClient

client = XAIClient(api_key="your-api-key")

try:
    wallet = client.wallet.create()
except XAIError as e:
    pdb.post_mortem()  # Drop into debugger on error
```

### 4. Print Request/Response

```python
import requests
import logging

# Enable requests logging
logging.basicConfig(level=logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

client = XAIClient(api_key="your-api-key")
# All HTTP requests will be logged
```

### 5. Test Error Scenarios

```python
from xai_sdk import XAIClient, ValidationError, NetworkError

def test_invalid_address_error():
    client = XAIClient(api_key="test-key")
    
    with pytest.raises(ValidationError):
        client.wallet.get_balance("invalid-address")

def test_network_error_handling():
    client = XAIClient(base_url="http://invalid-url")
    
    with pytest.raises(NetworkError):
        client.blockchain.get_stats()
```

---

## Common Errors and Solutions

### Error: "Invalid address format"

**Cause**: Address doesn't match expected format

**Solution**:
```python
# Address should start with 0x and be 42 characters
address = "0x" + "0" * 40  # Valid format
balance = client.wallet.get_balance(address)
```

### Error: "Rate limit exceeded"

**Cause**: Too many requests in short time

**Solution**:
```python
from xai_sdk import RateLimitError
import time

try:
    balance = client.wallet.get_balance("0x...")
except RateLimitError as e:
    time.sleep(e.retry_after or 60)
    balance = client.wallet.get_balance("0x...")
```

### Error: "Token expired"

**Cause**: JWT token has expired

**Solution**:
```python
# Re-authenticate or use refresh token
token = refresh_jwt_token(refresh_token)
client = XAIClient(api_key=token)
```

### Error: "Insufficient balance"

**Cause**: Account doesn't have enough funds

**Solution**:
```python
# Check balance before sending
balance = client.wallet.get_balance(wallet_address)
if int(balance.balance) < int(amount):
    print("Insufficient balance")
else:
    tx = client.transaction.send(...)
```

---

## Support

For error-related issues:
- **Documentation**: https://docs.xai-blockchain.io
- **GitHub Issues**: https://github.com/xai-blockchain/sdk-python/issues
- **Discord**: https://discord.gg/xai-blockchain
- **Email**: support@xai-blockchain.io
