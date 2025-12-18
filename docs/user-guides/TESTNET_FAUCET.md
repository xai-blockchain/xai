# XAI Testnet Faucet

Get free testnet XAI tokens for development, testing, and experimentation. The testnet faucet provides an easy way to obtain XAI tokens without mining or purchasing.

**Important:** Testnet XAI has no real value and is only for testing purposes.

---

## Quick Start

### CLI Method (Easiest)

```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS
```

### API Method

```bash
curl -X POST http://localhost:12001/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_YOUR_ADDRESS"}'
```

### Web UI Method

```bash
# Start the faucet web interface
cd docker/faucet
docker-compose up -d

# Open http://localhost:8086 in your browser
```

---

## Faucet Specifications

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Amount** | 100 XAI | Tokens per successful request |
| **Rate Limit (Address)** | 1 hour | Cooldown between requests to same address |
| **Rate Limit (IP)** | 10/hour | Maximum requests per IP address |
| **Delivery Time** | ~2 minutes | Tokens arrive in next block |
| **API Endpoint** | `/faucet/claim` | HTTP POST endpoint |
| **Port (Node API)** | 18545 | Testnet P2P port |
| **Port (RPC)** | 18546 | Testnet RPC port |
| **Port (Web UI)** | 8086 | Docker faucet web interface |
| **Address Prefix** | `TXAI` | Required prefix for testnet addresses |

---

## Access Methods

### 1. CLI Access (Recommended)

The easiest way to request testnet tokens using the wallet CLI.

```bash
# Basic usage
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS

# Specify custom node URL
python src/xai/wallet/cli.py request-faucet \
  --address TXAI_YOUR_ADDRESS \
  --base-url http://remote-node:18545

# Success response:
# ✅ Testnet faucet claim successful!
# 100 XAI will be added to your address after the next block.
# Note: This is testnet XAI - it has no real value!
```

**Advantages:**
- Simplest method
- Built into wallet CLI
- Handles authentication automatically
- Clear error messages

### 2. API Access (Programmatic)

Direct HTTP API access for integration with scripts and applications.

**Endpoint:**
```
POST http://localhost:12001/faucet/claim
```

**Request Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "address": "TXAI_YOUR_ADDRESS"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "amount": 100.0,
  "txid": "a1b2c3d4e5f6...",
  "message": "Testnet faucet claim successful! 100 XAI will be added to your address after the next block.",
  "note": "This is testnet XAI - it has no real value!"
}
```

**Example with cURL:**
```bash
curl -X POST http://localhost:12001/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```

**Example with Python requests:**
```python
import requests

response = requests.post(
    'http://localhost:12001/faucet/claim',
    json={'address': 'TXAI_YOUR_ADDRESS'}
)

data = response.json()
if data.get('success'):
    print(f"Received {data['amount']} XAI")
    print(f"Transaction ID: {data['txid']}")
else:
    print(f"Error: {data.get('error')}")
```

**Example with JavaScript (Node.js):**
```javascript
const fetch = require('node-fetch');

async function requestFaucet(address) {
  const response = await fetch('http://localhost:12001/faucet/claim', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address })
  });

  const data = await response.json();
  if (data.success) {
    console.log(`Received ${data.amount} XAI`);
    console.log(`Transaction ID: ${data.txid}`);
  } else {
    console.error(`Error: ${data.error}`);
  }
}

requestFaucet('TXAI_YOUR_ADDRESS');
```

### 3. Web UI Access

User-friendly web interface for requesting testnet tokens.

**Setup:**
```bash
cd /home/hudson/blockchain-projects/xai/docker/faucet
docker-compose up -d
```

**Access:**
Open your browser to `http://localhost:8086`

**Usage:**
1. Enter your TXAI address in the input field
2. Click "Request Tokens" button
3. Wait for confirmation message
4. Tokens arrive in ~2 minutes (next block)

**Features:**
- Simple, clean interface
- Real-time validation
- Cooldown timer display
- Transaction ID display
- Mobile-friendly

**Environment Variables (docker-compose.yml):**
```yaml
environment:
  XAI_API_URL: http://xai-testnet-bootstrap:8080
  FAUCET_PORT: 8086
  FAUCET_AMOUNT: 100
  FAUCET_COOLDOWN: 3600  # 1 hour in seconds
```

---

## Rate Limiting

The faucet implements multiple rate limiting mechanisms to prevent abuse.

### Address-Based Rate Limit

**Limit:** 1 request per hour per address

**Error Response (429):**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "rate_limited",
  "context": {
    "address": "TXAI_YOUR_ADDRESS",
    "identifier": "TXAI_YOUR_ADDRESS:192.168.1.100"
  }
}
```

### IP-Based Rate Limit

**Limit:** 10 requests per hour per IP address

This prevents someone from creating multiple addresses to abuse the faucet.

### Identifier Format

The faucet tracks requests using a combined identifier:
```
{address}:{ip_address}
```

Example: `TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa:192.168.1.100`

---

## Error Responses

### Invalid Address

**Status Code:** 400 Bad Request

**Response:**
```json
{
  "success": false,
  "error": "Invalid address for this network. Expected prefix TXAI.",
  "code": "invalid_address",
  "context": {
    "address": "XAI_WRONG_PREFIX",
    "expected_prefix": "TXAI"
  }
}
```

**Common Causes:**
- Using mainnet address (XAI prefix) on testnet
- Typo in address
- Invalid address format

### Rate Limited

**Status Code:** 429 Too Many Requests

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "rate_limited",
  "context": {
    "address": "TXAI_YOUR_ADDRESS"
  }
}
```

**Common Causes:**
- Requesting again within 1 hour
- Too many requests from same IP

### Faucet Disabled

**Status Code:** 403 Forbidden

**Response:**
```json
{
  "success": false,
  "error": "Faucet is disabled on this network",
  "code": "faucet_disabled"
}
```

**Common Causes:**
- Running on mainnet (faucet is testnet-only)
- Faucet disabled in configuration
- Node not in testnet mode

### Faucet Misconfigured

**Status Code:** 503 Service Unavailable

**Response:**
```json
{
  "success": false,
  "error": "Faucet amount is not configured",
  "code": "faucet_misconfigured"
}
```

**Common Causes:**
- Configuration error on server
- Faucet amount set to 0

---

## Configuration

### Node Configuration (testnet.yaml)

```yaml
features:
  faucet_enabled: true  # Enable faucet
  faucet_amount: 100.0  # XAI per request
```

### Environment Variables

```bash
# Enable faucet
export XAI_FAUCET_ENABLED=true

# Set faucet amount
export XAI_FAUCET_AMOUNT=100.0

# Network must be testnet
export XAI_NETWORK=testnet
```

### Development vs Production

| Environment | Faucet Enabled | Amount |
|-------------|----------------|--------|
| **Development** | Yes | 1000.0 XAI |
| **Testnet** | Yes | 100.0 XAI |
| **Staging** | Yes | 50.0 XAI |
| **Production** | No | 0.0 XAI |

**Security:** The faucet is automatically disabled on mainnet/production.

---

## Troubleshooting

### Tokens Not Received

**Wait for next block:**
```bash
# Check current block height
curl http://localhost:12001/stats

# Wait ~2 minutes, check again
curl http://localhost:12001/stats

# Verify balance
python src/xai/wallet/cli.py balance --address TXAI_YOUR_ADDRESS
```

**Check transaction status:**
```bash
# Using the txid from faucet response
curl http://localhost:12001/transaction/{txid}
```

### Invalid Address Error

**Verify address prefix:**
```bash
# Testnet addresses must start with "TXAI"
# Mainnet addresses start with "XAI"

# Generate testnet address
export XAI_NETWORK=testnet
python src/xai/wallet/cli.py generate-address
```

### Rate Limit Exceeded

**Wait for cooldown:**
```bash
# Rate limit is 1 hour per address
# Use a different address if you need tokens immediately

# Generate another address
python src/xai/wallet/cli.py generate-address
```

### Connection Refused

**Ensure node is running:**
```bash
# Start testnet node
export XAI_NETWORK=testnet
python -m xai.core.node

# Check node health
curl http://localhost:12001/health
```

**Check network configuration:**
```bash
# Verify testnet ports
netstat -an | grep 18545
netstat -an | grep 18546
```

### Web UI Not Loading

**Check Docker status:**
```bash
cd docker/faucet
docker-compose ps
docker-compose logs
```

**Restart web UI:**
```bash
docker-compose down
docker-compose up -d
```

---

## Best Practices

### For Developers

1. **Use CLI Method:** Simplest and most reliable
2. **Check Balance First:** Verify you don't already have tokens
3. **Wait for Confirmations:** Allow 1 block (~2 min) for delivery
4. **Respect Rate Limits:** Don't spam the faucet
5. **Share Tokens:** Transfer to other test addresses instead of requesting more

### For Applications

1. **Handle Errors Gracefully:** Check response codes and error messages
2. **Implement Retry Logic:** Respect rate limits with exponential backoff
3. **Cache Responses:** Don't request unnecessarily
4. **Validate Addresses:** Check prefix before submitting
5. **Monitor Rate Limits:** Track when cooldown expires

### Security Considerations

1. **Different Keys:** Never use mainnet private keys on testnet
2. **No Real Value:** Remember testnet tokens are worthless
3. **Public Endpoint:** Don't send sensitive data to faucet
4. **Rate Limit Awareness:** Design apps to handle rate limiting

---

## Advanced Usage

### Automated Testing Scripts

```bash
#!/bin/bash
# automated-test-setup.sh

# Generate test addresses
for i in {1..5}; do
  python src/xai/wallet/cli.py generate-address > "wallet_$i.txt"
done

# Request faucet for each (with 1 hour delay between)
for i in {1..5}; do
  ADDRESS=$(cat "wallet_$i.txt" | grep "Address:" | awk '{print $2}')
  python src/xai/wallet/cli.py request-faucet --address "$ADDRESS"

  if [ $i -lt 5 ]; then
    echo "Waiting 1 hour before next request..."
    sleep 3600
  fi
done
```

### CI/CD Integration

```yaml
# .github/workflows/integration-test.yml
- name: Setup Testnet Account
  run: |
    # Generate test wallet
    python src/xai/wallet/cli.py generate-address > wallet.txt

    # Extract address
    ADDRESS=$(grep "Address:" wallet.txt | awk '{print $2}')

    # Request testnet tokens
    python src/xai/wallet/cli.py request-faucet --address "$ADDRESS"

    # Wait for block
    sleep 180

    # Verify balance
    python src/xai/wallet/cli.py balance --address "$ADDRESS"
```

### Multi-Environment Testing

```bash
# test-environments.sh

# Development (1000 XAI)
export XAI_NETWORK=development
python src/xai/wallet/cli.py request-faucet --address TXAI_DEV_ADDRESS

# Testnet (100 XAI)
export XAI_NETWORK=testnet
python src/xai/wallet/cli.py request-faucet --address TXAI_TEST_ADDRESS

# Staging (50 XAI)
export XAI_NETWORK=staging
python src/xai/wallet/cli.py request-faucet --address TXAI_STAGE_ADDRESS
```

---

## Related Documentation

- **[Quick Start Guide](../QUICK_START.md)** - Get started in 5 minutes
- **[Testnet Guide](TESTNET_GUIDE.md)** - Complete testnet documentation
- **[Wallet Setup](wallet-setup.md)** - Wallet management guide
- **[API Documentation](../api/)** - Full API reference
- **[CLI Guide](../CLI_GUIDE.md)** - Complete CLI reference

---

**Last Updated:** January 2025 | **XAI Version:** 0.2.0 | **Testnet Active**
