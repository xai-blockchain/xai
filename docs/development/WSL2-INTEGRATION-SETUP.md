# WSL2 Integration Setup for XAI Blockchain Testing

## Overview
Bitcoin Core and Foundry (Anvil) are now running on WSL2 and accessible from bcpc for XAI atomic swap testing.

## Connection Details

### WSL2 Information
- **WSL2 IP**: 172.22.113.72 (internal)
- **Access via bcpc**: Use Windows laptop IPs (192.168.100.1 or 192.168.0.101)
- **Port forwarding**: Windows netsh portproxy configured

### Bitcoin Core (Regtest)
- **RPC Endpoint (from bcpc)**: http://192.168.100.1:18443
- **RPC User**: btcuser
- **RPC Password**: btcpass123
- **Chain**: regtest
- **Blocks**: 101 (with mature coinbase)
- **Wallet**: testwallet (50 BTC available, 5000 BTC immature)
- **Config**: ~/.bitcoin/bitcoin.conf on WSL2

### Foundry Anvil (Ethereum Local Node)
- **RPC Endpoint (from bcpc)**: http://192.168.100.1:8545
- **Chain ID**: 31337 (default Anvil)
- **Default Accounts**: 10 accounts funded with 10000 ETH each
- **First Account**: 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266

## Installation Paths (WSL2)

### Bitcoin Core
- **Binaries**: /usr/local/bin/{bitcoind,bitcoin-cli}
- **Version**: 27.0
- **Data Dir**: ~/.bitcoin

### Foundry
- **Binaries**: ~/.foundry/bin/{anvil,forge,cast,chisel}
- **Version**: 1.5.0-stable

## Services Status

### Bitcoin Core
```bash
ssh wsl2 "bitcoin-cli -regtest getblockchaininfo"
ssh wsl2 "bitcoin-cli -regtest getwalletinfo"
```

### Anvil
```bash
ssh wsl2 "ps aux | grep anvil"
```

## Testing Connectivity from bcpc

### Bitcoin RPC
```bash
curl -s -X POST http://192.168.100.1:18443 \
  -u btcuser:btcpass123 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"1.0","id":"test","method":"getblockchaininfo","params":[]}'
```

### Anvil RPC
```bash
curl -s -X POST http://192.168.100.1:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## Windows Port Forwarding Rules

The following Windows netsh portproxy rules forward traffic from Windows network interfaces to WSL2:

```
192.168.100.1:18443 -> 172.22.113.72:18443  (Bitcoin - Ethernet)
192.168.0.101:18443 -> 172.22.113.72:18443  (Bitcoin - WiFi)
192.168.100.1:8545  -> 172.22.113.72:8545   (Anvil - Ethernet)
192.168.0.101:8545  -> 172.22.113.72:8545   (Anvil - WiFi)
```

View rules:
```bash
ssh winpc "netsh interface portproxy show v4tov4"
```

## Windows Firewall Rules

Inbound rules created for:
- Bitcoin Core WSL (port 18443)
- Anvil WSL (port 8545)

## Starting/Stopping Services

### Bitcoin Core
```bash
# Start
ssh wsl2 "bitcoind -regtest -daemon"

# Stop
ssh wsl2 "bitcoin-cli -regtest stop"

# Generate blocks
ssh wsl2 "bitcoin-cli -regtest -generate 10"
```

### Anvil
```bash
# Start
ssh wsl2 "nohup ~/.foundry/bin/anvil --host 0.0.0.0 --port 8545 > /tmp/anvil.log 2>&1 &"

# Stop
ssh wsl2 "pkill anvil"

# Check logs
ssh wsl2 "tail -f /tmp/anvil.log"
```

## XAI Integration Testing

XAI atomic swap tests can now connect to:

1. **Bitcoin regtest node** at http://192.168.100.1:18443
   - Use for HTLC creation, Bitcoin transaction testing
   - Wallet "testwallet" has spendable funds

2. **Anvil Ethereum node** at http://192.168.100.1:8545
   - Use for smart contract deployment and testing
   - 10 funded accounts available

## Notes

- Services are currently running in background (not as systemd services)
- To make persistent, create WSL2 startup scripts or systemd services
- Bitcoin has txindex enabled for full transaction lookup
- Anvil mines blocks instantly on transaction submission
