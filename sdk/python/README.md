# XAI Blockchain Python SDK

A comprehensive Python SDK for interacting with the XAI Blockchain platform.

## Features

- **Complete API Coverage**: Wallet, transaction, blockchain, mining, governance, and trading operations
- **Type Hints**: Full type annotations for IDE support
- **Error Handling**: Comprehensive exception handling with specific error types
- **Connection Pooling**: Efficient HTTP connection management
- **Retry Logic**: Automatic retry with exponential backoff
- **Rate Limiting**: Built-in rate limit handling
- **WebSocket Support**: Real-time event streaming
- **Production Ready**: Thoroughly tested and documented

## Installation

### From PyPI

```bash
pip install xai-blockchain-sdk
```

### From Source

```bash
git clone https://github.com/xai-blockchain/sdk-python
cd sdk-python
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from xai_sdk import XAIClient

# Initialize client
client = XAIClient(api_key="your-api-key")

# Create wallet
wallet = client.wallet.create()
print(f"Wallet address: {wallet.address}")

# Get balance
balance = client.wallet.get_balance(wallet.address)
print(f"Balance: {balance.balance}")

# Send transaction
tx = client.transaction.send(
    from_address=wallet.address,
    to_address="0x...",
    amount="1000000000000000000"
)
print(f"Transaction hash: {tx.hash}")

# Close client
client.close()
```

### Using Context Manager

```python
from xai_sdk import XAIClient

# Auto cleanup on exit
with XAIClient(api_key="your-api-key") as client:
    wallet = client.wallet.create()
    print(f"Created wallet: {wallet.address}")
```

## Client Configuration

```python
from xai_sdk import XAIClient

# Local development
client = XAIClient()

# Testnet with API key
client = XAIClient(
    base_url="https://testnet-api.xai-blockchain.io",
    api_key="your-api-key"
)

# Mainnet with custom timeout
client = XAIClient(
    base_url="https://api.xai-blockchain.io",
    api_key="your-api-key",
    timeout=60,
    max_retries=5
)
```

## Available Clients

### Wallet Client

```python
# Create wallet
wallet = client.wallet.create()

# Get wallet info
wallet = client.wallet.get("0x...")

# Get balance
balance = client.wallet.get_balance("0x...")

# Get transaction history
history = client.wallet.get_transactions("0x...", limit=20)

# Create embedded wallet
embedded = client.wallet.create_embedded(
    app_id="my_app",
    user_id="user_123"
)
```

### Transaction Client

```python
# Send transaction
tx = client.transaction.send(
    from_address="0x...",
    to_address="0x...",
    amount="1000000000000000000"
)

# Get transaction
tx = client.transaction.get("0x...")

# Check status
status = client.transaction.get_status("0x...")

# Estimate fee
fee = client.transaction.estimate_fee(
    from_address="0x...",
    to_address="0x...",
    amount="1000000000000000000"
)

# Wait for confirmation
confirmed_tx = client.transaction.wait_for_confirmation(
    tx_hash="0x...",
    confirmations=1,
    timeout=600
)
```

### Blockchain Client

```python
# Get block
block = client.blockchain.get_block(12345)

# List blocks
blocks = client.blockchain.list_blocks(limit=20)

# Get blockchain stats
stats = client.blockchain.get_stats()

# Check sync status
sync = client.blockchain.get_sync_status()

# Get node health
health = client.blockchain.get_health()
```

### Mining Client

```python
# Start mining
result = client.mining.start(threads=4)

# Stop mining
result = client.mining.stop()

# Get mining status
status = client.mining.get_status()

# Get rewards
rewards = client.mining.get_rewards("0x...")
```

### Governance Client

```python
# List proposals
proposals = client.governance.list_proposals(status="active")

# Get proposal
proposal = client.governance.get_proposal(1)

# Create proposal
proposal = client.governance.create_proposal(
    title="Increase mining reward",
    description="...",
    proposer="0x...",
    duration=604800
)

# Vote on proposal
vote = client.governance.vote(
    proposal_id=1,
    voter="0x...",
    choice="yes"
)
```

### Trading Client

```python
# Register session
session = client.trading.register_session(
    wallet_address="0x...",
    peer_id="peer-123"
)

# List orders
orders = client.trading.list_orders()

# Create order
order = client.trading.create_order(
    from_address="0x...",
    to_address="0x...",
    from_amount="1000000000000000000",
    to_amount="500000000000000000"
)
```

## Error Handling

The SDK provides specific exception classes for different error types:

```python
from xai_sdk import (
    XAIClient,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    TransactionError,
    WalletError,
)

client = XAIClient(api_key="your-api-key")

try:
    wallet = client.wallet.create()
except ValidationError as e:
    print(f"Validation error: {e.message}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except NetworkError as e:
    print(f"Network error: {e.message}")
except TransactionError as e:
    print(f"Transaction error: {e.message}")
except WalletError as e:
    print(f"Wallet error: {e.message}")
```

## Rate Limiting

The SDK automatically handles rate limiting:

```python
from xai_sdk import RateLimitError
import time

try:
    balance = client.wallet.get_balance("0x...")
except RateLimitError as e:
    wait_time = e.retry_after or 60
    print(f"Rate limited. Waiting {wait_time}s...")
    time.sleep(wait_time)
    balance = client.wallet.get_balance("0x...")
```

## Retry Logic

The SDK uses exponential backoff for retries:

```python
# Configure retry behavior
client = XAIClient(
    api_key="your-api-key",
    max_retries=5  # Retry up to 5 times
)

# Requests will automatically retry on:
# - Network errors
# - Server errors (5xx)
# - Rate limiting (429)
```

## Examples

Complete examples are provided in the `examples/` directory:

- `create_wallet.py` - Create and manage wallets
- `send_transaction.py` - Send and track transactions
- `check_balance.py` - Check balances and history
- `query_blockchain.py` - Query blockchain data
- `atomic_swap_example.py` - Peer-to-peer trading

Run examples:

```bash
python examples/create_wallet.py
python examples/send_transaction.py
python examples/check_balance.py
python examples/query_blockchain.py
python examples/atomic_swap_example.py
```

## Documentation

- [API Reference](../../docs/API_REFERENCE.md) - Complete API documentation
- [Authentication Guide](../../docs/AUTHENTICATION.md) - Authentication methods
- [Error Handling Guide](../../docs/ERROR_HANDLING.md) - Error handling patterns
- [WebSocket & Rate Limiting](../../docs/WEBSOCKET_AND_RATE_LIMITING.md) - Real-time updates

## Environment Variables

```bash
# API configuration
export XAI_API_KEY="your-api-key"
export XAI_API_URL="http://localhost:5000"
export XAI_TIMEOUT="30"
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=xai_sdk

# Run specific test file
pytest tests/test_wallet_client.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black xai_sdk/

# Lint code
pylint xai_sdk/

# Type checking
mypy xai_sdk/

# Security check
bandit -r xai_sdk/
```

### Building Package

```bash
# Build distribution
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

- **Documentation**: https://docs.xai-blockchain.io
- **GitHub Issues**: https://github.com/xai-blockchain/sdk-python/issues
- **Discord**: https://discord.gg/xai-blockchain
- **Email**: support@xai-blockchain.io

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Security

For security issues, please email security@xai-blockchain.io instead of using the issue tracker.
