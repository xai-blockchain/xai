# SDK Integration

This guide provides examples for integrating with the XAI blockchain using Python and JavaScript/TypeScript.

## Installation

### Python SDK

```bash
pip install xai-sdk
# Or install from source:
pip install -e ./src/xai/sdk/python
```

### JavaScript/TypeScript SDK

```bash
npm install @xai/sdk
# Or install from source:
cd src/xai/sdk/typescript && npm install && npm run build
```

---

## Python Examples

### Initialize Client

```python
from xai_sdk import XAIClient

# Local development node (default port 12001)
client = XAIClient(base_url="http://localhost:12001")

# Testnet with API key
client = XAIClient(
    base_url="https://testnet-api.xai-blockchain.io",
    api_key="your-api-key",
    timeout=30,
    max_retries=3
)

# Use as context manager for automatic cleanup
with XAIClient() as client:
    health = client.health_check()
    print(f"Node status: {health['status']}")
```

### Create Wallet/Keypair

```python
from xai.core.wallet import Wallet

# Generate a new wallet with secp256k1 keypair
wallet = Wallet()
print(f"Address: {wallet.address}")
print(f"Public Key: {wallet.public_key}")
# WARNING: Never log or expose private keys in production!

# Create from existing private key
wallet = Wallet(private_key="your_hex_private_key")

# Create from BIP-39 mnemonic (24 words)
mnemonic = Wallet.generate_mnemonic(strength=256)  # 24 words
print(f"Mnemonic: {mnemonic}")  # SAVE THIS SECURELY!

# Restore wallet from mnemonic
wallet = Wallet.from_mnemonic(
    mnemonic_phrase=mnemonic,
    passphrase="optional_extra_security",
    account_index=0,
    address_index=0
)

# Save encrypted wallet to file
wallet.save_to_file("my_wallet.json", password="strong_password")

# Load wallet from encrypted file
loaded_wallet = Wallet.load_from_file("my_wallet.json", password="strong_password")

# Export to WIF (Wallet Import Format)
wif = wallet.export_to_wif()
restored = Wallet.import_from_wif(wif)

# Sign a message
message = "Hello, XAI!"
signature = wallet.sign_message(message)
is_valid = wallet.verify_signature(message, signature, wallet.public_key)
```

### Get Balance

```python
import requests

NODE_URL = "http://localhost:12001"

def get_balance(address: str) -> dict:
    """Get balance for an XAI address."""
    response = requests.get(
        f"{NODE_URL}/balance/{address}",
        headers={"X-API-Key": "your-api-key"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Example usage
balance_info = get_balance("TXAIabcd1234...")
print(f"Address: {balance_info['address']}")
print(f"Balance: {balance_info['balance']} XAI")

# Using the SDK client
from xai_sdk import XAIClient

with XAIClient() as client:
    balance = client.wallet.get_balance("TXAIabcd1234...")
    print(f"Balance: {balance.balance}")
    print(f"Available: {balance.available_balance}")
    print(f"Nonce: {balance.nonce}")
```

### Send Transaction

```python
import hashlib
import time
import requests
from xai.core.wallet import Wallet
from xai.core.blockchain import Transaction

NODE_URL = "http://localhost:12001"
API_KEY = "your-api-key"

def send_transaction(
    wallet: Wallet,
    recipient: str,
    amount: float,
    fee: float = 0.001
) -> dict:
    """Create, sign, and send a transaction."""

    # Get current nonce for sender
    nonce_resp = requests.get(
        f"{NODE_URL}/address/{wallet.address}/nonce",
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    nonce_resp.raise_for_status()
    nonce = nonce_resp.json()["next_nonce"]

    # Create transaction
    tx = Transaction(
        sender=wallet.address,
        recipient=recipient,
        amount=amount,
        fee=fee,
        public_key=wallet.public_key,
        nonce=nonce
    )
    tx.timestamp = time.time()

    # Calculate transaction hash and sign
    tx.txid = tx.calculate_hash()
    tx.signature = wallet.sign_message(tx.txid)

    # Submit transaction
    payload = {
        "sender": tx.sender,
        "recipient": tx.recipient,
        "amount": tx.amount,
        "fee": tx.fee,
        "public_key": tx.public_key,
        "signature": tx.signature,
        "nonce": tx.nonce,
        "timestamp": tx.timestamp,
        "txid": tx.txid
    }

    response = requests.post(
        f"{NODE_URL}/send",
        json=payload,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Example usage
wallet = Wallet.load_from_file("my_wallet.json", password="strong_password")
result = send_transaction(
    wallet=wallet,
    recipient="TXAIrecipient123...",
    amount=10.0,
    fee=0.001
)
print(f"Transaction ID: {result['txid']}")
print(f"Message: {result['message']}")
```

### Query Blocks and Transactions

```python
import requests

NODE_URL = "http://localhost:12001"

def get_blocks(limit: int = 10, offset: int = 0) -> dict:
    """Get paginated list of blocks."""
    response = requests.get(
        f"{NODE_URL}/blocks",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def get_block_by_index(index: int) -> dict:
    """Get a specific block by index."""
    response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_block_by_hash(block_hash: str) -> dict:
    """Get a specific block by hash."""
    response = requests.get(f"{NODE_URL}/block/{block_hash}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_transaction(txid: str) -> dict:
    """Get transaction details by ID."""
    response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_address_history(address: str, limit: int = 50, offset: int = 0) -> dict:
    """Get transaction history for an address."""
    response = requests.get(
        f"{NODE_URL}/history/{address}",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Example usage
blocks = get_blocks(limit=5)
print(f"Total blocks: {blocks['total']}")
for block in blocks['blocks']:
    print(f"Block {block.get('index')}: {block.get('hash', '')[:16]}...")

# Get latest block
latest = get_block_by_index(blocks['total'] - 1)
print(f"Latest block difficulty: {latest.get('difficulty')}")

# Get transaction history
history = get_address_history("TXAIabcd1234...", limit=10)
print(f"Total transactions: {history['transaction_count']}")
for tx in history['transactions']:
    print(f"  TX: {tx.get('txid', '')[:16]}... Amount: {tx.get('amount')}")
```

### Check Node Health and Stats

```python
import requests

NODE_URL = "http://localhost:12001"

def get_health() -> dict:
    """Check node health status."""
    response = requests.get(f"{NODE_URL}/health", timeout=30)
    return response.json()

def get_stats() -> dict:
    """Get blockchain statistics."""
    response = requests.get(f"{NODE_URL}/stats", timeout=30)
    response.raise_for_status()
    return response.json()

def get_mempool_stats() -> dict:
    """Get mempool statistics and fee recommendations."""
    response = requests.get(f"{NODE_URL}/mempool/stats", timeout=30)
    response.raise_for_status()
    return response.json()

# Example usage
health = get_health()
print(f"Status: {health['status']}")
print(f"Blockchain Height: {health['blockchain'].get('height')}")
print(f"Peers: {health['network'].get('peers')}")

stats = get_stats()
print(f"Chain Height: {stats.get('chain_height')}")
print(f"Total Supply: {stats.get('total_circulating_supply')}")
print(f"Mining: {stats.get('is_mining')}")

mempool = get_mempool_stats()
print(f"Pending TXs: {mempool['pressure']['pending_transactions']}")
print(f"Recommended fee (standard): {mempool['fees']['recommended_fee_rates']['standard']}")
```

### Claim Testnet Faucet

```python
import requests

NODE_URL = "http://localhost:12001"

def claim_faucet(address: str, api_key: str) -> dict:
    """Claim testnet tokens from faucet."""
    response = requests.post(
        f"{NODE_URL}/faucet/claim",
        json={"address": address},
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Example usage (testnet only)
result = claim_faucet("TXAIabcd1234...", "your-api-key")
print(f"Amount received: {result['amount']} XAI")
print(f"Transaction ID: {result['txid']}")
print(f"Note: {result['note']}")
```

---

## JavaScript/TypeScript Examples

### Initialize Client

```typescript
import { XAIClient } from '@xai/sdk';

// Local development node
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',
});

// Testnet with API key
const client = new XAIClient({
  baseUrl: 'https://testnet-api.xai-blockchain.io',
  apiKey: 'your-api-key',
  timeout: 30000,
  maxRetries: 3,
});

// Check node health
const health = await client.blockchain.getHealth();
console.log(`Node status: ${health.status}`);
```

### Create Wallet (using REST API)

```typescript
const NODE_URL = 'http://localhost:12001';

interface WalletResponse {
  address: string;
  public_key: string;
  created_at: string;
  private_key?: string;
}

async function createWallet(apiKey: string): Promise<WalletResponse> {
  const response = await fetch(`${NODE_URL}/wallet/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
    },
    body: JSON.stringify({ wallet_type: 'standard' }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create wallet: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const wallet = await createWallet('your-api-key');
console.log(`New wallet address: ${wallet.address}`);
// WARNING: Store private_key securely and never log in production!
```

### Get Balance

```typescript
const NODE_URL = 'http://localhost:12001';

interface BalanceResponse {
  address: string;
  balance: number;
}

async function getBalance(address: string): Promise<BalanceResponse> {
  const response = await fetch(`${NODE_URL}/balance/${address}`);

  if (!response.ok) {
    throw new Error(`Failed to get balance: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const balance = await getBalance('TXAIabcd1234...');
console.log(`Balance: ${balance.balance} XAI`);

// Using SDK
import { XAIClient } from '@xai/sdk';

const client = new XAIClient();
const walletBalance = await client.wallet.getBalance('TXAIabcd1234...');
console.log(`Balance: ${walletBalance.balance}`);
console.log(`Available: ${walletBalance.availableBalance}`);
```

### Send Transaction

```typescript
const NODE_URL = 'http://localhost:12001';
const API_KEY = 'your-api-key';

interface TransactionPayload {
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  public_key: string;
  signature: string;
  nonce: number;
  timestamp: number;
  txid?: string;
}

interface NonceResponse {
  address: string;
  confirmed_nonce: number;
  next_nonce: number;
  pending_nonce: number | null;
}

interface SendResponse {
  success: boolean;
  txid: string;
  message: string;
}

async function getNonce(address: string): Promise<NonceResponse> {
  const response = await fetch(`${NODE_URL}/address/${address}/nonce`, {
    headers: { 'X-API-Key': API_KEY },
  });

  if (!response.ok) {
    throw new Error(`Failed to get nonce: ${response.statusText}`);
  }

  return response.json();
}

async function sendTransaction(tx: TransactionPayload): Promise<SendResponse> {
  const response = await fetch(`${NODE_URL}/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(tx),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Transaction failed: ${error.error || response.statusText}`);
  }

  return response.json();
}

// Example: Full transaction flow (pseudocode - signing requires crypto library)
async function transfer(
  senderAddress: string,
  senderPublicKey: string,
  signMessage: (msg: string) => string,  // Your signing function
  recipient: string,
  amount: number
): Promise<SendResponse> {
  // 1. Get nonce
  const nonceInfo = await getNonce(senderAddress);

  // 2. Build transaction
  const timestamp = Date.now() / 1000;
  const tx: TransactionPayload = {
    sender: senderAddress,
    recipient,
    amount,
    fee: 0.001,
    public_key: senderPublicKey,
    nonce: nonceInfo.next_nonce,
    timestamp,
    signature: '',  // Will be set after signing
  };

  // 3. Create transaction hash and sign
  // Note: Use proper crypto library for production
  const txHash = await calculateTxHash(tx);
  tx.txid = txHash;
  tx.signature = signMessage(txHash);

  // 4. Submit transaction
  return sendTransaction(tx);
}
```

### Query Blocks and Transactions

```typescript
const NODE_URL = 'http://localhost:12001';

interface BlocksResponse {
  total: number;
  limit: number;
  offset: number;
  blocks: Block[];
}

interface Block {
  index: number;
  hash: string;
  previous_hash: string;
  timestamp: number;
  difficulty: number;
  transactions: Transaction[];
}

interface TransactionResponse {
  found: boolean;
  block?: number;
  confirmations?: number;
  status?: string;
  transaction: Transaction;
}

interface Transaction {
  txid: string;
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  timestamp: number;
}

async function getBlocks(limit = 10, offset = 0): Promise<BlocksResponse> {
  const response = await fetch(
    `${NODE_URL}/blocks?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    throw new Error(`Failed to get blocks: ${response.statusText}`);
  }

  return response.json();
}

async function getBlock(index: number): Promise<Block> {
  const response = await fetch(`${NODE_URL}/blocks/${index}`);

  if (!response.ok) {
    throw new Error(`Failed to get block: ${response.statusText}`);
  }

  return response.json();
}

async function getTransaction(txid: string): Promise<TransactionResponse> {
  const response = await fetch(`${NODE_URL}/transaction/${txid}`);

  if (!response.ok) {
    throw new Error(`Failed to get transaction: ${response.statusText}`);
  }

  return response.json();
}

async function getAddressHistory(
  address: string,
  limit = 50,
  offset = 0
): Promise<{ transactions: Transaction[]; transaction_count: number }> {
  const response = await fetch(
    `${NODE_URL}/history/${address}?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    throw new Error(`Failed to get history: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const blocks = await getBlocks(5);
console.log(`Total blocks: ${blocks.total}`);

for (const block of blocks.blocks) {
  console.log(`Block ${block.index}: ${block.hash.slice(0, 16)}...`);
}

const tx = await getTransaction('abc123...');
if (tx.found) {
  console.log(`Transaction confirmed in block ${tx.block}`);
  console.log(`Confirmations: ${tx.confirmations}`);
}
```

### Check Node Health

```typescript
const NODE_URL = 'http://localhost:12001';

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  blockchain: {
    accessible: boolean;
    height: number;
    difficulty: number;
    total_supply: number;
  };
  services: {
    api: string;
    storage: string;
    p2p: string;
  };
  network: {
    peers: number;
  };
}

interface StatsResponse {
  chain_height: number;
  total_circulating_supply: number;
  difficulty: number;
  pending_transactions_count: number;
  is_mining: boolean;
  peers: number;
  node_uptime: number;
}

async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${NODE_URL}/health`);
  return response.json();
}

async function getStats(): Promise<StatsResponse> {
  const response = await fetch(`${NODE_URL}/stats`);

  if (!response.ok) {
    throw new Error(`Failed to get stats: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const health = await getHealth();
console.log(`Status: ${health.status}`);
console.log(`Height: ${health.blockchain.height}`);
console.log(`Peers: ${health.network.peers}`);

const stats = await getStats();
console.log(`Chain Height: ${stats.chain_height}`);
console.log(`Mining: ${stats.is_mining}`);
console.log(`Uptime: ${Math.floor(stats.node_uptime / 3600)}h`);
```

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Node info and available endpoints |
| `/health` | GET | Health check with diagnostics |
| `/stats` | GET | Blockchain statistics |
| `/balance/<address>` | GET | Get address balance |
| `/address/<address>/nonce` | GET | Get address nonce info |
| `/history/<address>` | GET | Transaction history (paginated) |
| `/blocks` | GET | List blocks (paginated) |
| `/blocks/<index>` | GET | Get block by index |
| `/block/<hash>` | GET | Get block by hash |
| `/transaction/<txid>` | GET | Get transaction details |
| `/transactions` | GET | List pending transactions |
| `/send` | POST | Submit signed transaction |
| `/mempool` | GET | Mempool overview |
| `/mempool/stats` | GET | Fee recommendations |
| `/faucet/claim` | POST | Claim testnet tokens |

## Authentication

Most write operations require API key authentication:

```
X-API-Key: your-api-key
```

For production use, also include Bearer token authentication as specified in the OpenAPI spec.

## Error Handling

All endpoints return structured error responses:

```json
{
  "success": false,
  "error": "Error description",
  "code": "error_code",
  "context": {}
}
```

Common error codes:
- `invalid_payload` - Malformed request data
- `rate_limited` - Too many requests
- `transaction_rejected` - Transaction validation failed
- `invalid_signature` - Cryptographic signature invalid
