# XAI Python SDK Documentation

The XAI Python SDK provides a comprehensive interface for interacting with the XAI blockchain. It supports wallet management, transactions, mining, governance, trading, and blockchain queries.

## Installation

```bash
pip install xai-sdk
```

For development:

```bash
git clone https://github.com/xai-blockchain/xai-sdk-python.git
cd xai-sdk-python
pip install -e .
```

## Quick Start

```python
from xai_sdk import XAIClient

# Initialize client
client = XAIClient(
    base_url="http://localhost:12001",
    api_key="your-api-key"
)

# Create a wallet
wallet = client.wallet.create()
print(f"Address: {wallet.address}")

# Get balance
balance = client.wallet.get_balance(wallet.address)
print(f"Balance: {balance.balance}")

# Send a transaction
tx = client.transaction.send(
    from_address=wallet.address,
    to_address="XAI_RECIPIENT_ADDRESS",
    amount="100",
    signature="signed_tx_data"
)
print(f"Transaction hash: {tx.hash}")

# Cleanup
client.close()
```

### Context Manager

```python
with XAIClient(api_key="your-api-key") as client:
    health = client.health_check()
    if health["status"] == "ok":
        print("Node is healthy")
```

## Authentication

### API Key Authentication

```python
client = XAIClient(
    base_url="https://api.xai-blockchain.io",
    api_key="your-api-key"
)
```

The API key is sent in the `X-API-Key` header for all requests.

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | `http://localhost:12001` | API endpoint URL |
| `api_key` | str | None | API key for authentication |
| `timeout` | int | 30 | Request timeout in seconds |
| `max_retries` | int | 3 | Maximum retry attempts |
| `api_version` | str | "v1" | API version (v1) |

## XAIClient

The main client class that provides unified access to all blockchain operations.

```python
from xai_sdk import XAIClient

client = XAIClient(api_key="your-key")

# Sub-clients
client.wallet       # Wallet operations
client.transaction  # Transaction operations
client.blockchain   # Blockchain queries
client.mining       # Mining operations
client.governance   # Governance operations
client.trading      # Trading operations
```

### Methods

#### health_check()

Check API health status.

```python
health = client.health_check()
# Returns: {"status": "healthy", "blockchain": {...}, "services": {...}}
```

#### get_info()

Get node information.

```python
info = client.get_info()
# Returns: {"status": "online", "version": "1.0.0", "node": "AXN Full Node"}
```

## WalletClient

Manages wallet creation and balance queries.

### create()

Create a new wallet.

```python
from xai_sdk.models import WalletType

# Standard wallet
wallet = client.wallet.create()

# Embedded wallet (for apps)
wallet = client.wallet.create(
    wallet_type=WalletType.EMBEDDED,
    name="My Wallet"
)

print(wallet.address)      # "XAI..."
print(wallet.public_key)   # Public key hex
print(wallet.private_key)  # Private key (only returned on create)
```

### get()

Retrieve wallet information.

```python
wallet = client.wallet.get("XAI_ADDRESS")
print(wallet.address)
print(wallet.nonce)
```

### get_balance()

Get wallet balance.

```python
balance = client.wallet.get_balance("XAI_ADDRESS")

print(balance.balance)            # Total balance
print(balance.available_balance)  # Available balance
print(balance.locked_balance)     # Locked balance
print(balance.nonce)              # Current nonce
```

### get_transactions()

Get transaction history for a wallet.

```python
result = client.wallet.get_transactions(
    address="XAI_ADDRESS",
    limit=50,
    offset=0
)

for tx in result["transactions"]:
    print(f"{tx['hash']}: {tx['amount']}")
print(f"Total: {result['total']}")
```

### create_embedded()

Create an embedded wallet for an application.

```python
embedded = client.wallet.create_embedded(
    app_id="my-app-id",
    user_id="user-123",
    metadata={"role": "standard"}
)
print(embedded["address"])
print(embedded["wallet_id"])
```

### login_embedded()

Login to an embedded wallet.

```python
session = client.wallet.login_embedded(
    wallet_id="wallet-id",
    password="secure-password"
)
print(session["token"])
```

## TransactionClient

Handles transaction creation, submission, and tracking.

### send()

Send a transaction.

```python
tx = client.transaction.send(
    from_address="XAI_SENDER",
    to_address="XAI_RECIPIENT",
    amount="1000",
    gas_limit="21000",
    gas_price="1",
    nonce=5,
    signature="signed_data"
)

print(tx.hash)
print(tx.status)  # TransactionStatus.PENDING
```

### get()

Get transaction details.

```python
tx = client.transaction.get("0x_TRANSACTION_HASH")

print(tx.hash)
print(tx.from_address)
print(tx.to_address)
print(tx.amount)
print(tx.status)
print(tx.confirmations)
print(tx.block_number)
```

### get_status()

Get transaction status.

```python
status = client.transaction.get_status("0x_TRANSACTION_HASH")
print(status["status"])
print(status["confirmations"])
```

### estimate_fee()

Estimate transaction fee.

```python
estimate = client.transaction.estimate_fee(
    from_address="XAI_SENDER",
    to_address="XAI_RECIPIENT",
    amount="1000",
    data="optional_hex_data"
)

print(estimate["fee"])
print(estimate["gas_limit"])
print(estimate["gas_price"])
```

### is_confirmed()

Check if transaction is confirmed.

```python
if client.transaction.is_confirmed("0x_TX_HASH", confirmations=6):
    print("Transaction is confirmed")
```

### wait_for_confirmation()

Wait for transaction confirmation with polling.

```python
tx = client.transaction.wait_for_confirmation(
    tx_hash="0x_TX_HASH",
    confirmations=6,
    timeout=600,      # 10 minutes
    poll_interval=5   # Check every 5 seconds
)
print(f"Confirmed in block {tx.block_number}")
```

## BlockchainClient

Query blockchain state and blocks.

### get_block()

Get block by number.

```python
block = client.blockchain.get_block(12345)

print(block.number)
print(block.hash)
print(block.parent_hash)
print(block.timestamp)
print(block.miner)
print(block.difficulty)
print(block.transactions)  # Transaction count
```

### list_blocks()

List recent blocks.

```python
result = client.blockchain.list_blocks(limit=20, offset=0)

for block in result["blocks"]:
    print(f"Block {block.number}: {block.hash}")
print(f"Total blocks: {result['total']}")
```

### get_block_transactions()

Get transactions in a block.

```python
transactions = client.blockchain.get_block_transactions(12345)
for tx in transactions:
    print(tx["hash"])
```

### get_sync_status()

Get blockchain sync status.

```python
sync = client.blockchain.get_sync_status()
print(f"Syncing: {sync['syncing']}")
print(f"Current block: {sync['current_block']}")
print(f"Highest block: {sync['highest_block']}")
```

### is_synced()

Check if blockchain is synced.

```python
if client.blockchain.is_synced():
    print("Blockchain is synchronized")
```

### get_stats()

Get blockchain statistics.

```python
stats = client.blockchain.get_stats()

print(f"Total blocks: {stats.total_blocks}")
print(f"Total transactions: {stats.total_transactions}")
print(f"Total accounts: {stats.total_accounts}")
print(f"Difficulty: {stats.difficulty}")
print(f"Hashrate: {stats.hashrate}")
print(f"Avg block time: {stats.average_block_time}")
print(f"Total supply: {stats.total_supply}")
```

### get_health()

Get node health status.

```python
health = client.blockchain.get_health()
print(health["status"])
```

## MiningClient

Control mining operations.

### start()

Start mining.

```python
result = client.mining.start(threads=4)
print(result["message"])
```

### stop()

Stop mining.

```python
result = client.mining.stop()
print(result["message"])
```

### get_status()

Get mining status.

```python
status = client.mining.get_status()

print(f"Mining: {status.mining}")
print(f"Threads: {status.threads}")
print(f"Hashrate: {status.hashrate}")
print(f"Blocks found: {status.blocks_found}")
print(f"Difficulty: {status.current_difficulty}")
print(f"Uptime: {status.uptime}")
```

### get_rewards()

Get mining rewards for an address.

```python
rewards = client.mining.get_rewards("XAI_MINER_ADDRESS")
print(f"Total rewards: {rewards['total']}")
print(f"Pending: {rewards['pending']}")
```

### is_mining()

Check if mining is active.

```python
if client.mining.is_mining():
    print("Mining is active")
```

## GovernanceClient

Manage governance proposals and voting.

### list_proposals()

List governance proposals.

```python
result = client.governance.list_proposals(
    status="active",  # Optional filter
    limit=20,
    offset=0
)

for proposal in result["proposals"]:
    print(f"{proposal.id}: {proposal.title}")
    print(f"  Votes: {proposal.votes_for} for, {proposal.votes_against} against")
```

### get_proposal()

Get proposal details.

```python
proposal = client.governance.get_proposal(proposal_id=1)

print(proposal.title)
print(proposal.description)
print(proposal.creator)
print(proposal.status)
print(proposal.votes_for)
print(proposal.votes_against)
print(proposal.voting_ends_at)
```

### create_proposal()

Create a governance proposal.

```python
proposal = client.governance.create_proposal(
    title="Increase Block Size",
    description="Proposal to increase block size to 2MB",
    proposer="XAI_PROPOSER_ADDRESS",
    duration=604800,  # 7 days
    metadata={"category": "protocol"}
)
print(f"Created proposal {proposal.id}")
```

### vote()

Vote on a proposal.

```python
result = client.governance.vote(
    proposal_id=1,
    voter="XAI_VOTER_ADDRESS",
    choice="yes"  # "yes", "no", or "abstain"
)
print(result["message"])
```

### get_active_proposals()

Get currently active proposals.

```python
proposals = client.governance.get_active_proposals()
for p in proposals:
    print(f"{p.id}: {p.title} - Ends {p.voting_ends_at}")
```

### get_proposal_votes()

Get vote breakdown for a proposal.

```python
votes = client.governance.get_proposal_votes(proposal_id=1)
print(f"For: {votes['votes_for']}")
print(f"Against: {votes['votes_against']}")
print(f"Abstain: {votes['votes_abstain']}")
print(f"Total: {votes['total_votes']}")
```

## TradingClient

Peer-to-peer trading operations.

### register_session()

Register a trading session.

```python
session = client.trading.register_session(
    wallet_address="XAI_ADDRESS",
    peer_id="peer-identifier"
)
print(session["session_id"])
```

### list_orders()

List active trade orders.

```python
orders = client.trading.list_orders()
for order in orders:
    print(f"{order.id}: {order.from_amount} -> {order.to_amount}")
    print(f"  Status: {order.status}")
```

### create_order()

Create a trade order.

```python
order = client.trading.create_order(
    from_address="XAI_SENDER",
    to_address="XAI_RECIPIENT",
    from_amount="100",
    to_amount="90",
    timeout=3600  # 1 hour
)
print(f"Order ID: {order.id}")
```

### cancel_order()

Cancel a trade order.

```python
result = client.trading.cancel_order(order_id="order-123")
print(result["message"])
```

### get_order_status()

Get order status.

```python
status = client.trading.get_order_status(order_id="order-123")
print(status["status"])
```

## Data Models

### Wallet

```python
from xai_sdk.models import Wallet, WalletType

wallet = Wallet(
    address="XAI...",
    public_key="04...",
    created_at=datetime.now(),
    wallet_type=WalletType.STANDARD,
    nonce=0
)
```

### Balance

```python
from xai_sdk.models import Balance

balance = Balance(
    address="XAI...",
    balance="1000000",
    locked_balance="0",
    available_balance="1000000",
    nonce=5
)
```

### Transaction

```python
from xai_sdk.models import Transaction, TransactionStatus

tx = Transaction(
    hash="0x...",
    from_address="XAI_SENDER",
    to_address="XAI_RECIPIENT",
    amount="1000",
    timestamp=datetime.now(),
    status=TransactionStatus.CONFIRMED,
    fee="10",
    block_number=12345,
    confirmations=6
)
```

### Block

```python
from xai_sdk.models import Block

block = Block(
    number=12345,
    hash="0x...",
    parent_hash="0x...",
    timestamp=1234567890,
    miner="XAI_MINER",
    difficulty="1000000",
    gas_limit="8000000",
    gas_used="500000",
    transactions=50
)
```

### Proposal

```python
from xai_sdk.models import Proposal, ProposalStatus

proposal = Proposal(
    id=1,
    title="Proposal Title",
    description="Description",
    creator="XAI_CREATOR",
    status=ProposalStatus.ACTIVE,
    created_at=datetime.now(),
    votes_for=100,
    votes_against=50
)
```

## Error Handling

The SDK provides specific exception classes for different error types:

```python
from xai_sdk.exceptions import (
    XAIError,              # Base exception
    AuthenticationError,   # API key issues
    AuthorizationError,    # Permission denied
    ValidationError,       # Invalid input
    RateLimitError,        # Rate limit exceeded
    NetworkError,          # Connection issues
    TimeoutError,          # Request timeout
    NotFoundError,         # Resource not found
    TransactionError,      # Transaction failed
    WalletError,           # Wallet operation failed
    MiningError,           # Mining operation failed
    GovernanceError        # Governance operation failed
)

try:
    tx = client.transaction.send(...)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except TransactionError as e:
    print(f"Transaction failed: {e.message}")
except XAIError as e:
    print(f"Error [{e.code}]: {e.message}")
```

### Retry Logic

The HTTP client includes automatic retry with exponential backoff for transient errors:

```python
client = XAIClient(
    api_key="your-key",
    max_retries=5,           # Retry up to 5 times
    timeout=60               # 60 second timeout
)
```

Retries occur for:
- HTTP 429 (Rate Limit)
- HTTP 500 (Internal Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

## Complete Example

```python
from xai_sdk import XAIClient
from xai_sdk.exceptions import TransactionError, WalletError

def transfer_funds(api_key: str, recipient: str, amount: str):
    """Transfer funds to a recipient address."""

    with XAIClient(api_key=api_key) as client:
        # Check node health
        health = client.health_check()
        if health["status"] != "healthy":
            raise RuntimeError("Node is not healthy")

        # Create sender wallet
        try:
            sender = client.wallet.create()
            print(f"Created wallet: {sender.address}")
        except WalletError as e:
            raise RuntimeError(f"Failed to create wallet: {e}")

        # Check balance
        balance = client.wallet.get_balance(sender.address)
        if float(balance.available_balance) < float(amount):
            raise RuntimeError("Insufficient balance")

        # Estimate fee
        fee_estimate = client.transaction.estimate_fee(
            from_address=sender.address,
            to_address=recipient,
            amount=amount
        )
        print(f"Estimated fee: {fee_estimate['fee']}")

        # Send transaction
        try:
            tx = client.transaction.send(
                from_address=sender.address,
                to_address=recipient,
                amount=amount,
                gas_limit=fee_estimate.get("gas_limit", "21000"),
                signature="YOUR_SIGNATURE_HERE"
            )
            print(f"Transaction submitted: {tx.hash}")
        except TransactionError as e:
            raise RuntimeError(f"Transaction failed: {e}")

        # Wait for confirmation
        try:
            confirmed_tx = client.transaction.wait_for_confirmation(
                tx_hash=tx.hash,
                confirmations=6,
                timeout=300
            )
            print(f"Transaction confirmed in block {confirmed_tx.block_number}")
            return confirmed_tx
        except TransactionError as e:
            raise RuntimeError(f"Transaction not confirmed: {e}")

# Usage
transfer_funds("your-api-key", "XAI_RECIPIENT", "1000")
```

## API Reference

### Client Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `base_url` | str | `http://localhost:12001` | API base URL |
| `api_key` | str | None | Authentication key |
| `timeout` | int | 30 | Request timeout (seconds) |
| `max_retries` | int | 3 | Max retry attempts |
| `pool_connections` | int | 10 | Connection pool size |
| `pool_maxsize` | int | 10 | Max pool connections |
| `api_version` | str | "v1" | API version |

### HTTP Headers

All requests include:

```
Content-Type: application/json
User-Agent: XAI-SDK/1.0
X-API-Key: <your-api-key>
```

### Rate Limits

Default rate limits:
- Standard endpoints: 100 requests/minute
- Transaction submission: 10 requests/minute
- Mining operations: 5 requests/minute
- Faucet: 1 request/hour

Rate limit headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```
