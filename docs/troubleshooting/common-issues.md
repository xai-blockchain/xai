# Troubleshooting Guide

Solutions to common XAI node issues.

## Node Won't Start

### Python Version Error

**Symptom**: `SyntaxError` or `ImportError` on startup

**Solution**:
```bash
# Check Python version (need 3.10+)
python3 --version

# Install Python 3.11 on Ubuntu
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Create new venv with correct Python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Missing Dependencies

**Symptom**: `ModuleNotFoundError`

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Port Already in Use

**Symptom**: `Address already in use` error

**Solution**:
```bash
# Find process using port
sudo lsof -i :8545
sudo lsof -i :8333

# Kill process or use different port
python -m xai.core.node --port 8546 --p2p-port 8334
```

### Permission Denied

**Symptom**: `PermissionError` accessing data directory

**Solution**:
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/xai

# Or specify writable directory
export XAI_DATA_DIR=/tmp/xai-test
```

## Sync Issues

### Node Not Syncing

**Symptom**: Block height stuck, not increasing

**Check**:
```bash
# Check peer connections
curl -s http://localhost:8545/peers | jq '. | length'

# Check sync status
curl -s http://localhost:8545/stats | jq '{chain_height, peer_count}'
```

**Solutions**:
1. Add more peers:
   ```bash
   # Restart with explicit peers
   python -m xai.core.node --peers https://testnet-rpc.xaiblockchain.com
   ```

2. Download checkpoint:
   ```bash
   sudo systemctl stop xai
   rm -rf ~/xai/data/*
   curl -sL https://artifacts.xaiblockchain.com/snapshots/latest.tar.gz | tar -xzf - -C ~/xai/data/
   sudo systemctl start xai
   ```

3. Reset and resync:
   ```bash
   sudo systemctl stop xai
   rm -rf ~/xai/data/*
   sudo systemctl start xai
   ```

### Sync Falling Behind

**Symptom**: Node syncs but can't keep up with network

**Solutions**:
- Check hardware meets requirements (see [Hardware Requirements](../getting-started/hardware-requirements.md))
- Reduce log level: `export XAI_LOG_LEVEL=WARNING`
- Check disk I/O: `iostat -x 1`
- Consider SSD upgrade

## Peer Connection Issues

### No Peers Found

**Symptom**: `peer_count: 0`

**Solutions**:
1. Check firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 8333/tcp
   ```

2. Verify bootstrap peers are reachable:
   ```bash
   curl -s https://testnet-rpc.xaiblockchain.com/stats
   ```

3. Check DNS resolution:
   ```bash
   nslookup testnet-rpc.xaiblockchain.com
   ```

### Peers Disconnecting

**Symptom**: Peers connect then disconnect

**Solutions**:
- Check network stability
- Verify time sync: `timedatectl status`
- Check if behind NAT - may need port forwarding

## WebSocket Issues

### WebSocket Connection Refused

**Symptom**: Cannot connect to WebSocket endpoint

**Check**:
```bash
# Test local WS
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8766/
```

**Solutions**:
- Ensure WebSocket port is open
- Check if WS is enabled in configuration
- Verify SSL/TLS for `wss://` connections

## Database Issues

### Database Corruption

**Symptom**: `LevelDB` errors, node crashes on startup

**Solution**:
```bash
# Stop node
sudo systemctl stop xai

# Backup current data
mv ~/xai/data ~/xai/data.backup

# Restore from checkpoint or resync
curl -sL https://artifacts.xaiblockchain.com/snapshots/latest.tar.gz | tar -xzf - -C ~/xai/data/

# Start node
sudo systemctl start xai
```

### Disk Full

**Symptom**: Write errors, node stops

**Solutions**:
```bash
# Check disk usage
df -h
du -sh ~/xai/data/*

# Prune old data (if supported)
# Or move to larger disk
```

## Memory Issues

### Out of Memory

**Symptom**: Node killed by OOM killer

**Check**:
```bash
dmesg | grep -i "out of memory"
journalctl -u xai | grep -i "killed"
```

**Solutions**:
- Increase RAM
- Add swap space:
  ```bash
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```
- Reduce cache size in configuration

## Mining Issues

### Mining Not Producing Blocks

**Symptom**: Mining enabled but no blocks mined

**Check**:
```bash
journalctl -u xai | grep -i "mining"
curl -s http://localhost:8545/stats | jq '{mining_enabled, difficulty}'
```

**Solutions**:
1. Verify mining is enabled:
   ```bash
   export XAI_MINING_ENABLED=true
   export XAI_MINER_ADDRESS=your_address
   ```

2. For testnet, ensure fast mining is enabled (auto on testnet)

3. Check if synced:
   ```bash
   curl -s http://localhost:8545/stats | jq '.synced'
   ```

## Getting Help

If issues persist:

1. **Check logs**: `journalctl -u xai --since "1 hour ago"`
2. **Search issues**: https://github.com/xai-blockchain/xai/issues
3. **Discord**: Join community Discord for support
4. **Create issue**: https://github.com/xai-blockchain/xai/issues/new
