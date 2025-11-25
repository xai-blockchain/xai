# XAI Block Explorer - Local Testing Interface

## Overview

Simple web-based block explorer for viewing and exploring the XAI blockchain locally.

**IMPORTANT:** This is for LOCAL TESTING ONLY - not intended for production use!

## Features

✅ View blockchain statistics
✅ Browse all blocks
✅ View block details and transactions
✅ Search transactions by ID
✅ View address balances and transaction history
✅ Auto-refreshing statistics
✅ Dark theme optimized for readability
✅ Responsive design

## Requirements

```bash
pip install flask flask-cors requests
```

## Usage

### 1. Start XAI Node (Required)

First, start the XAI blockchain node:

```bash
# For testnet
export XAI_NETWORK=testnet
python core/node.py
```

The node will run on `http://localhost:8545` (mainnet) or `http://localhost:18545` (testnet).

### 2. Start Block Explorer

In a new terminal:

```bash
python block_explorer.py
```

The explorer will run on `http://localhost:8080`.

### 3. Open in Browser

Visit: `http://localhost:8080`

## Configuration

You can configure the node URL using an environment variable:

```bash
# For testnet node
export XAI_NODE_URL=http://localhost:18545
python block_explorer.py

# For mainnet node
export XAI_NODE_URL=http://localhost:8545
python block_explorer.py
```

## Pages

### Homepage (/)
- Blockchain statistics dashboard
- Recent blocks table
- Network information
- Auto-refreshing stats every 10 seconds

### Blocks (/blocks)
- List all blocks
- Pagination support
- Block hash, difficulty, nonce, transaction count
- Click to view block details

### Block Detail (/block/<index>)
- Full block information
- All transactions in the block
- Merkle root and proof-of-work details
- Navigation to previous/next blocks

### Transaction Detail (/transaction/<txid>)
- Full transaction information
- Sender and recipient addresses
- Amount and fees
- Signature and public key (if available)
- Transaction type

### Address Detail (/address/<address>)
- Address balance
- Full transaction history
- Sent/received transaction breakdown

### Search (/search)
- Search by block number
- Search by transaction ID
- Search by address
- Auto-redirects to appropriate page

## Features Explained

### Statistics Dashboard
Displays real-time blockchain metrics:
- Total blocks mined
- Total transactions
- Pending transactions
- Total supply
- Network difficulty
- Unique addresses

### Auto-Refresh
Statistics automatically refresh every 10 seconds without page reload.

### UTC Timestamps
All timestamps displayed in UTC for anonymity protection.

### Color-Coded Transactions
- 🔵 Blue (COINBASE) - Mining rewards
- 🟢 Green - Received
- 🔴 Red - Sent
- 🟡 Yellow - Special types (airdrop, refund, etc.)

### Hash Truncation
Long hashes are truncated for readability but show full hash on hover.

## API Endpoints Used

The explorer uses these XAI node endpoints:

- `GET /stats` - Blockchain statistics
- `GET /blocks?limit=N&offset=M` - List blocks with pagination
- `GET /blocks/<index>` - Specific block details
- `GET /transaction/<txid>` - Transaction details
- `GET /balance/<address>` - Address balance
- `GET /history/<address>` - Transaction history

## Troubleshooting

### "Cannot connect to node"

**Problem:** Block explorer cannot reach the XAI node.

**Solutions:**
1. Ensure XAI node is running: `python core/node.py`
2. Check node is accessible: `curl http://localhost:8545/stats`
3. For testnet, use correct port: `export XAI_NODE_URL=http://localhost:18545`
4. Check firewall settings

### No blocks showing

**Problem:** Blockchain is empty.

**Solution:** Start mining blocks:
```bash
curl -X POST http://localhost:8545/mine \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "XAI..."}'
```

### Wrong network (XAI vs TXAI addresses)

**Problem:** Explorer shows wrong address prefix.

**Solution:** Make sure node and explorer are on same network:
```bash
# Both testnet
export XAI_NETWORK=testnet
python core/node.py &
export XAI_NODE_URL=http://localhost:18545
python block_explorer.py
```

### Port conflicts

**Problem:** Port 8080 already in use.

**Solution:** Edit `block_explorer.py` line 160 to use a different port:
```python
app.run(host='0.0.0.0', port=8888, debug=True)
```

## Development

### Modifying Templates

All HTML templates are in `templates/` directory:
- `base.html` - Base template with navigation
- `index.html` - Homepage
- `blocks.html` - Block list
- `block.html` - Block details
- `transaction.html` - Transaction details
- `address.html` - Address details
- `search.html` - Search results

### Adding Features

To add new features:
1. Add route in `block_explorer.py`
2. Create corresponding template in `templates/`
3. Use existing node API endpoints or create new ones

### Styling

All CSS is inline in `base.html` for simplicity. Modify the `<style>` section to change appearance.

## Security Notes

⚠️ **LOCAL TESTING ONLY**
- Not designed for public deployment
- No authentication or rate limiting
- Debug mode enabled
- Intended for development environment only

⚠️ **ANONYMITY PROTECTION**
- All timestamps in UTC
- No personal identifiers displayed
- Only wallet addresses shown

## Limitations

This is a minimal block explorer for testing:
- No real-time websocket updates
- Basic search (no fuzzy matching)
- No charts or graphs
- No mempool visualization
- No transaction pool monitoring
- No rich list
- No network topology visualization

For production use, consider building a full-featured explorer with:
- WebSocket support for real-time updates
- Advanced search and filtering
- Data visualization
- Caching layer
- API rate limiting
- User authentication (if needed)

## Example Workflow

1. **Start node:**
   ```bash
   export XAI_NETWORK=testnet
   python core/node.py
   ```

2. **Start explorer:**
   ```bash
   export XAI_NODE_URL=http://localhost:18545
   python block_explorer.py
   ```

3. **Open browser:** `http://localhost:8080`

4. **Get testnet coins:**
   ```bash
   curl -X POST http://localhost:18545/faucet/claim \
     -H "Content-Type: application/json" \
     -d '{"address": "TXAI..."}'
   ```

5. **Mine a block:**
   ```bash
   curl -X POST http://localhost:18545/mine \
     -H "Content-Type: application/json" \
     -d '{"miner_address": "TXAI..."}'
   ```

6. **View in explorer:** Refresh homepage to see new block

---

**Remember:** This explorer is for LOCAL TESTING ONLY!

**Last Updated:** 2025-11-09 (UTC)
