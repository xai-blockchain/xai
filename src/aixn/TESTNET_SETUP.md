# XAI Testnet Setup Guide

## Overview

XAI blockchain now supports both **testnet** and **mainnet** configurations for safe testing before production launch.

## Network Comparison

| Feature | Testnet | Mainnet |
|---------|---------|---------|
| **Network ID** | 0xABCD | 0x5841 |
| **Address Prefix** | TXAI | AIXN |
| **Default Port** | 18545 | 8545 |
| **RPC Port** | 18546 | 8546 |
| **Genesis File** | `genesis_testnet.json` | `genesis_new.json` |
| **Initial Difficulty** | 2 (easier) | 4 (production) |
| **Blockchain File** | `blockchain_testnet.json` | `blockchain.json` |
| **Wallet Directory** | `wallets_testnet/` | `wallets/` |
| **Data Directory** | `data_testnet/` | `data/` |
| **Faucet** | ENABLED (100 XAI per claim) | DISABLED |
| **Chain Reset** | Allowed | NOT allowed |
| **Pre-mine** | 22,400 XAI (1/1000 of mainnet) | 22.4M XAI |

## Switching Between Networks

### Method 1: Environment Variable (Recommended)

**For Testnet:**
```bash
# Windows
set XAI_NETWORK=testnet
python core/node.py

# Linux/Mac
export XAI_NETWORK=testnet
python core/node.py
```

**For Mainnet:**
```bash
# Windows
set XAI_NETWORK=mainnet
python core/node.py

# Linux/Mac
export XAI_NETWORK=mainnet
python core/node.py
```

### Method 2: Edit config.py

Open `config.py` and change line 15:

```python
# For testnet
NETWORK = 'testnet'

# For mainnet
NETWORK = 'mainnet'
```

## Testnet Features

### 1. Easier Mining
- Lower difficulty (2 vs 4) means faster block mining
- Great for testing without powerful hardware

### 2. Free Testnet XAI Faucet
Get free testnet coins to test with:

```bash
curl -X POST http://localhost:18545/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI..."}'
```

Response:
```json
{
  "success": true,
  "amount": 100.0,
  "txid": "...",
  "message": "Testnet faucet claim successful! 100.0 XAI will be added to your address after the next block.",
  "note": "This is testnet XAI - it has no real value!"
}
```

### 3. Separate Data
Testnet and mainnet use completely separate:
- Blockchain files
- Wallet directories
- Data directories

You can run both networks on the same machine without conflicts (just use different ports).

### 4. Chain Reset Allowed
On testnet, you can reset the blockchain for fresh testing:
```bash
rm blockchain_testnet.json
rm -rf data_testnet/
```

**WARNING:** NEVER reset mainnet! (`Config.ALLOW_CHAIN_RESET = False` prevents this)

## Testing Workflow

### Recommended Pre-Mainnet Testing:

1. **Start on Testnet**
   ```bash
   export XAI_NETWORK=testnet
   python core/node.py
   ```

2. **Claim Testnet XAI**
   ```bash
   curl -X POST http://localhost:18545/faucet/claim \
     -H "Content-Type: application/json" \
     -d '{"address": "TXAI..."}'
   ```

3. **Test All Features**
   - Send transactions
   - Mine blocks
   - Test wallet claiming
   - Test token burning
   - Test AI features
   - Test governance
   - Test atomic swaps
   - Etc.

4. **Run Comprehensive Tests**
   ```bash
   pytest tests/
   ```

5. **Security Audit**
   - Code review
   - Vulnerability scanning
   - Penetration testing

6. **Switch to Mainnet** (only when ready!)
   ```bash
   export XAI_NETWORK=mainnet
   python core/node.py
   ```

## Genesis Files

### Testnet Genesis (`genesis_testnet.json`)
- 22,400 XAI total pre-mine (1/1000 of mainnet)
- Used for local testing
- Can be regenerated if needed

### Mainnet Genesis (`genesis_new.json`)
- 22.4M XAI total pre-mine
- **PERMANENT** - cannot be changed after launch
- Must be distributed identically to all nodes

## Port Configuration

### Testnet Ports
- Node: `18545`
- RPC: `18546`

### Mainnet Ports
- Node: `8545`
- RPC: `8546`

You can override ports with environment variables:
```bash
export XAI_PORT=9000
export XAI_RPC_PORT=9001
```

## Address Prefixes

### Testnet: `TXAI`
Example: `TXAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b`

### Mainnet: `AIXN`
Example: `AIXN7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b`

This prevents accidental mixing of testnet and mainnet addresses.

## Supply Cap (Same on Both Networks)

Both testnet and mainnet enforce the same **121M XAI** supply cap to ensure emission testing matches production.

## Best Practices

### DO:
✅ Test everything on testnet first
✅ Use testnet for development
✅ Use faucet to get free testnet XAI
✅ Reset testnet chain as needed
✅ Run comprehensive tests on testnet

### DON'T:
❌ Use testnet XAI as real value
❌ Mix testnet and mainnet addresses
❌ Skip testnet testing
❌ Launch mainnet without thorough testing
❌ Reset mainnet blockchain

## Troubleshooting

### Issue: "Wrong address prefix"
**Solution:** You're using a mainnet address on testnet (or vice versa)
- Testnet uses `TXAI` prefix
- Mainnet uses `AIXN` prefix

### Issue: "Cannot connect to port 8545"
**Solution:** You may be running testnet (port 18545)
```bash
curl http://localhost:18545/stats
```

### Issue: "Faucet endpoint not found"
**Solution:** Faucet only works on testnet
- Check `XAI_NETWORK=testnet` is set
- Faucet disabled on mainnet for security

## Next Steps

After successful testnet testing:

1. ✅ Build block explorer (local testing only)
2. ✅ Add comprehensive test suite
3. ✅ Perform security review and fixes
4. ✅ Create deployment scripts for node operators
5. ✅ Create pre-mine script for mainnet
6. ✅ Create blockchain upload/distribution guide

## Environment Variables Reference

```bash
# Network selection (testnet or mainnet)
XAI_NETWORK=testnet

# Node configuration
XAI_HOST=0.0.0.0
XAI_PORT=18545

# Paths (optional - config provides defaults)
XAI_DATA_DIR=/path/to/data
XAI_WALLET_DIR=/path/to/wallets
```

## Support

For testnet support:
- Check node logs
- Verify `XAI_NETWORK` environment variable
- Ensure correct ports and prefixes
- Use faucet to get testnet XAI

---

**Remember:** Testnet XAI has NO real value. It's for testing only!

**Last Updated:** 2025-11-09 (UTC)
