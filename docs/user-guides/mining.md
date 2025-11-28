# Mining Guide

Complete guide to mining XAI tokens using the Proof-of-Work consensus mechanism.

## Table of Contents

- [Introduction](#introduction)
- [Mining Basics](#mining-basics)
- [Getting Started](#getting-started)
- [Mining Configuration](#mining-configuration)
- [Mining Operations](#mining-operations)
- [Mining Pools](#mining-pools)
- [Profitability and Economics](#profitability-and-economics)
- [Optimization](#optimization)
- [Troubleshooting](#troubleshooting)

## Introduction

Mining is the process of validating transactions and creating new blocks on the XAI blockchain. Miners compete to solve cryptographic puzzles, and the first to solve it receives the block reward plus transaction fees.

### What You'll Learn

- How XAI mining works
- Setting up a mining operation
- Optimizing mining performance
- Understanding mining profitability
- Troubleshooting mining issues

### Prerequisites

- XAI node installed and synchronized
- Wallet address for receiving rewards
- Computer with adequate resources (CPU/GPU)
- Understanding of blockchain basics
- Patience (mining requires time and resources)

## Mining Basics

### How XAI Mining Works

XAI uses Proof-of-Work (PoW) consensus with SHA-256 hashing algorithm:

1. **Block Creation**: Miner collects pending transactions from mempool
2. **Puzzle Solving**: Miner searches for nonce that produces valid hash
3. **Block Validation**: Valid block is broadcast to network
4. **Reward Distribution**: Miner receives block reward + transaction fees
5. **Difficulty Adjustment**: Network adjusts difficulty to maintain ~2 min block time

### Block Rewards

**Current Block Reward Structure:**

| Block Range | Reward per Block | Era |
|-------------|-----------------|------|
| 0 - 1,050,000 | 100 XAI | Era 1 |
| 1,050,001 - 2,100,000 | 50 XAI | Era 2 |
| 2,100,001 - 3,150,000 | 25 XAI | Era 3 |
| 3,150,001+ | 12.5 XAI | Era 4 |

**Total Supply:** Capped at 121,000,000 XAI

**Halving Schedule:** Every 1,050,000 blocks (~4 years at 2-minute block time)

### Mining Requirements

**Minimum Requirements:**
- **CPU**: Dual-core processor
- **RAM**: 4GB
- **Storage**: 50GB available space
- **Network**: Stable internet connection (10 Mbps+)
- **OS**: Linux, macOS, or Windows

**Recommended Requirements:**
- **CPU**: Quad-core or higher (or GPU)
- **RAM**: 8GB+
- **Storage**: 100GB+ SSD
- **Network**: Fast, stable connection (100 Mbps+)
- **Power**: Reliable power supply

### SHA-256 Algorithm

XAI uses SHA-256 for mining:
- **Same as Bitcoin**: Compatible with Bitcoin mining hardware
- **ASIC Compatible**: Can use specialized mining hardware
- **GPU Efficient**: NVIDIA/AMD GPUs perform well
- **CPU Mining**: Possible but less competitive

## Getting Started

### Step 1: Prepare Your Wallet

```bash
# Generate mining wallet address (if you don't have one)
python src/xai/wallet/cli.py generate-address

# Save the address - you'll need it for mining rewards
# Example: XAI1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0
```

**Important:** Back up your wallet immediately! See [Wallet Setup Guide](wallet-setup.md).

### Step 2: Synchronize Your Node

```bash
# Start node and sync with network
export XAI_NETWORK=mainnet  # or testnet for practice
python src/xai/core/node.py

# Wait for full synchronization (may take hours for mainnet)
# Monitor sync status:
python src/xai/wallet/cli.py node-status
```

### Step 3: Configure Mining

```bash
# Set your mining address
export MINER_ADDRESS=YOUR_XAI_ADDRESS

# Optional: Set mining threads (default: auto-detect)
export MINING_THREADS=4

# Optional: Set mining intensity (1-10, default: 5)
export MINING_INTENSITY=7
```

### Step 4: Start Mining

```bash
# Start mining with configured address
python src/xai/core/node.py --miner $MINER_ADDRESS

# Or start node and mining together
python src/xai/core/node.py --miner $MINER_ADDRESS --mining-threads 4
```

### Quick Start (Testnet)

Practice mining on testnet first:

```bash
# Set testnet environment
export XAI_NETWORK=testnet
export MINER_ADDRESS=YOUR_TESTNET_ADDRESS

# Start testnet mining
python src/xai/core/node.py --miner $MINER_ADDRESS

# Testnet has lower difficulty - easier to mine blocks
```

## Mining Configuration

### Environment Variables

Configure mining behavior with environment variables:

```bash
# Network Configuration
export XAI_NETWORK=mainnet              # Network: mainnet or testnet
export XAI_PORT=8545                    # P2P port
export XAI_RPC_PORT=8546               # RPC port

# Mining Configuration
export MINER_ADDRESS=YOUR_XAI_ADDRESS   # Address for rewards
export MINING_THREADS=4                 # Number of CPU threads
export MINING_INTENSITY=5               # Intensity 1-10
export MINING_ALGORITHM=sha256          # Hashing algorithm
export ENABLE_GPU_MINING=false         # Enable GPU mining

# Performance
export MEMPOOL_SIZE=1000               # Max transactions per block
export BLOCK_SIZE_LIMIT=1048576        # Max block size (bytes)
export REFRESH_INTERVAL=10             # Seconds between work updates

# Monitoring
export MINING_STATS_INTERVAL=60        # Stats update interval
export ENABLE_PROMETHEUS=true          # Enable metrics export
```

### Configuration File

Create `~/.xai/mining.yaml`:

```yaml
# Mining Configuration
mining:
  enabled: true
  miner_address: "YOUR_XAI_ADDRESS"
  threads: 4
  intensity: 5

  # Hardware
  use_gpu: false
  gpu_devices: [0]  # GPU device IDs if using GPU

  # Performance
  refresh_interval: 10
  max_block_size: 1048576
  mempool_size: 1000

# Network
network:
  mainnet: true
  port: 8545
  rpc_port: 8546
  peers:
    - "node1.xai.io:8545"
    - "node2.xai.io:8545"

# Monitoring
monitoring:
  stats_interval: 60
  log_level: INFO
  prometheus:
    enabled: true
    port: 9090
```

### Network Selection

**Mainnet Mining:**
- Real XAI rewards
- Higher difficulty
- Requires significant resources
- Competitive environment

**Testnet Mining:**
- Practice mining
- Lower difficulty
- Test XAI (no real value)
- Learning environment

```bash
# Switch networks
export XAI_NETWORK=mainnet  # or testnet
python src/xai/core/node.py --miner $MINER_ADDRESS
```

## Mining Operations

### Starting Mining

```bash
# Start mining (basic)
python src/xai/core/node.py --miner YOUR_ADDRESS

# Start with specific configuration
python src/xai/core/node.py \
  --miner YOUR_ADDRESS \
  --mining-threads 8 \
  --mining-intensity 7 \
  --network mainnet

# Start as background service
nohup python src/xai/core/node.py --miner YOUR_ADDRESS > miner.log 2>&1 &
```

### Monitoring Mining

```bash
# Check mining status
python src/xai/wallet/cli.py mining-status

# Output:
# Status: Mining
# Address: XAI1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0
# Hashrate: 125.5 MH/s
# Blocks Found: 3
# Last Block: 2 hours ago
# Estimated Time to Block: 6 hours

# View detailed statistics
python src/xai/wallet/cli.py mining-stats --detailed

# Monitor in real-time
python src/xai/wallet/cli.py watch-mining
```

### Checking Rewards

```bash
# Check mining rewards balance
python src/xai/wallet/cli.py balance --address YOUR_MINING_ADDRESS

# View mining transaction history
python src/xai/wallet/cli.py transactions \
  --address YOUR_MINING_ADDRESS \
  --type coinbase

# Calculate total mining earnings
python src/xai/wallet/cli.py mining-earnings --address YOUR_MINING_ADDRESS
```

### Stopping Mining

```bash
# Graceful shutdown
python src/xai/wallet/cli.py stop-mining

# Or kill the node process
# Find process ID
ps aux | grep "node.py"

# Stop process
kill -SIGTERM <PID>

# Force stop if needed
kill -SIGKILL <PID>
```

## Mining Pools

### What are Mining Pools?

Mining pools combine hashpower from multiple miners to find blocks more consistently:

**Benefits:**
- More consistent rewards
- Lower variance
- Suitable for smaller miners
- Professional infrastructure

**Drawbacks:**
- Pool fees (typically 1-3%)
- Trust required in pool operator
- Less decentralized

### Solo Mining vs Pool Mining

| Aspect | Solo Mining | Pool Mining |
|--------|-------------|-------------|
| **Setup** | Simple | Requires pool connection |
| **Rewards** | Irregular, all-or-nothing | Regular, proportional |
| **Variance** | Very high | Low |
| **Returns** | 100% (when finding block) | 97-99% (after fees) |
| **Best For** | Large hashpower | Small/medium miners |

### Connecting to Mining Pool

```bash
# Configure pool connection
export MINING_POOL_URL=stratum+tcp://pool.xai.io:3333
export MINING_POOL_USER=YOUR_XAI_ADDRESS
export MINING_POOL_PASSWORD=x

# Start pool mining
python src/xai/core/pool_miner.py \
  --pool $MINING_POOL_URL \
  --user $MINING_POOL_USER \
  --password $MINING_POOL_PASSWORD \
  --threads 4
```

### Recommended Mining Pools

**Public Pools (Example - verify current availability):**
- pool.xai.io - Official pool, 1% fee
- xai-mining.org - Community pool, 2% fee
- mineXAI.com - Large pool, 1.5% fee

**Pool Selection Criteria:**
- Fee structure (lower is better)
- Pool hashrate (balanced - not too large)
- Geographic location (closer = lower latency)
- Payout threshold and frequency
- Reputation and uptime

### Setting Up Your Own Pool

For advanced users wanting to run a mining pool:

```bash
# Install pool software (example using standard pool software)
cd pool-software

# Configure pool
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

# Start pool
python pool_server.py
```

See [Pool Setup Guide](../advanced/pool-setup.md) for detailed instructions.

## Profitability and Economics

### Calculating Profitability

**Factors affecting profitability:**
- Your hashrate
- Network hashrate (difficulty)
- Block reward
- Transaction fees
- Electricity costs
- Hardware costs

**Basic Formula:**
```
Daily Earnings = (Your Hashrate / Network Hashrate) × Blocks per Day × Block Reward

Daily Profit = Daily Earnings - Electricity Cost
```

### Profitability Calculator

```bash
# Calculate mining profitability
python src/xai/tools/mining_calculator.py \
  --hashrate 100 \
  --power-consumption 500 \
  --electricity-cost 0.12

# Output:
# Daily Earnings: 5.2 XAI
# Daily Electricity Cost: $1.44
# Daily Profit: ~$X.XX (depends on XAI price)
# Break-even XAI Price: $0.XX
```

### Online Calculators

Check current profitability online:
- xai.mining-calculator.com (example)
- Calculate with current difficulty and price
- Compare with other cryptocurrencies

### Hardware Efficiency

**Hash Rate per Watt (efficiency metric):**

| Hardware Type | Hashrate | Power | Efficiency |
|--------------|----------|-------|------------|
| CPU (4-core) | 1 MH/s | 65W | 15 KH/W |
| GPU (Mid-range) | 25 MH/s | 150W | 167 KH/W |
| GPU (High-end) | 50 MH/s | 250W | 200 KH/W |
| ASIC (Entry) | 14 TH/s | 1400W | 10 GH/W |
| ASIC (Advanced) | 100 TH/s | 3250W | 31 GH/W |

*Note: Values are examples - check specific hardware specifications*

### When to Mine

**Mining makes sense when:**
- Your electricity costs are low
- You have efficient hardware
- XAI price is favorable
- Network difficulty is reasonable
- You value supporting the network

**Consider alternatives when:**
- Electricity costs are very high
- Hardware is outdated/inefficient
- Simply buying XAI is more cost-effective
- Environmental concerns

## Optimization

### CPU Mining Optimization

```bash
# Use all available cores
export MINING_THREADS=$(nproc)

# Or leave some cores for system
export MINING_THREADS=$(($(nproc) - 2))

# Set process priority (Linux)
nice -n -20 python src/xai/core/node.py --miner $MINER_ADDRESS

# Enable CPU optimizations
export ENABLE_CPU_OPTIMIZATIONS=true
export USE_AVX2=true  # If your CPU supports it
```

### GPU Mining Optimization

```bash
# Enable GPU mining
export ENABLE_GPU_MINING=true

# Specify GPU devices
export GPU_DEVICES=0,1  # Use GPUs 0 and 1

# GPU optimization flags
export GPU_THREADS=256
export GPU_BLOCKS=64

# Start GPU mining
python src/xai/core/gpu_miner.py \
  --miner-address $MINER_ADDRESS \
  --devices 0,1
```

### System Optimization

**Linux:**
```bash
# Disable CPU frequency scaling
sudo cpupower frequency-set -g performance

# Increase file descriptor limits
ulimit -n 65536

# Disable swap (if enough RAM)
sudo swapoff -a
```

**Cooling:**
- Ensure adequate cooling
- Monitor temperatures
- Keep hardware dust-free
- Consider additional fans

### Network Optimization

```bash
# Add peer nodes for better connectivity
export XAI_PEERS="node1.xai.io:8545,node2.xai.io:8545,node3.xai.io:8545"

# Increase max connections
export MAX_PEERS=50

# Reduce latency
# Connect to geographically close nodes
```

### Monitoring and Maintenance

```bash
# Monitor system resources
htop  # CPU and memory
nvidia-smi  # GPU stats (NVIDIA)
iotop  # Disk I/O

# Monitor mining logs
tail -f miner.log

# Check for errors
grep -i error miner.log

# Regular maintenance schedule:
# - Daily: Check mining status and earnings
# - Weekly: Review logs for errors
# - Monthly: Clean hardware, update software
```

## Troubleshooting

### Low Hashrate

**Symptoms:** Hashrate lower than expected

**Solutions:**
1. Check CPU/GPU utilization
   ```bash
   htop  # Should show high CPU usage
   nvidia-smi  # Check GPU utilization
   ```
2. Increase mining threads
3. Check for thermal throttling
4. Update drivers and software
5. Verify no other processes competing for resources

### No Blocks Found

**Symptoms:** Mining for extended period without finding blocks

**This is normal!**
- Solo mining is probabilistic
- Average time between blocks depends on your hashrate vs network hashrate
- Consider joining a mining pool for consistent rewards

**Verify mining is working:**
```bash
# Check you're actively mining
python src/xai/wallet/cli.py mining-status

# Verify node is synchronized
python src/xai/wallet/cli.py node-status

# Check network connectivity
python src/xai/wallet/cli.py peer-status
```

### High Rejection Rate

**Symptoms:** Many submitted solutions rejected

**Causes & Solutions:**
- **Stale work:** Reduce work refresh interval
- **Network latency:** Connect to closer nodes
- **Wrong difficulty:** Ensure node is fully synced
- **Software bug:** Update to latest version

### System Overheating

**Symptoms:** System crashes, thermal throttling

**Solutions:**
1. Improve cooling (fans, ventilation)
2. Reduce mining intensity
3. Underclock hardware slightly
4. Clean dust from hardware
5. Apply new thermal paste (GPU/CPU)

### High Memory Usage

**Symptoms:** System running out of memory

**Solutions:**
```bash
# Reduce mempool size
export MEMPOOL_SIZE=500

# Limit peer connections
export MAX_PEERS=25

# Increase swap space (temporary)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Mining Software Crashes

**Symptoms:** Mining process terminates unexpectedly

**Solutions:**
1. Check logs for error messages
   ```bash
   tail -100 miner.log
   ```
2. Update to latest version
3. Verify hardware stability (run stress tests)
4. Check for disk space issues
5. Monitor system resources

### Not Receiving Rewards

**Symptoms:** Mined blocks but no rewards received

**Checks:**
```bash
# Verify mining address is correct
echo $MINER_ADDRESS

# Check blockchain for your mined blocks
python src/xai/wallet/cli.py blocks-mined --address $MINER_ADDRESS

# Verify coinbase transactions
python src/xai/wallet/cli.py transactions \
  --address $MINER_ADDRESS \
  --type coinbase

# Check wallet is synchronized
python src/xai/wallet/cli.py node-status
```

## Mining Best Practices

### Security

- [ ] Use dedicated mining address
- [ ] Back up wallet immediately
- [ ] Secure mining machine (firewall, updates)
- [ ] Monitor for unauthorized access
- [ ] Use secure RPC connections

### Economics

- [ ] Calculate profitability before starting
- [ ] Account for all costs (electricity, hardware depreciation)
- [ ] Consider pool mining for consistent income
- [ ] Monitor XAI price and adjust accordingly
- [ ] Have exit strategy if unprofitable

### Operations

- [ ] Start on testnet to learn
- [ ] Monitor system health regularly
- [ ] Keep software updated
- [ ] Maintain cooling and hardware
- [ ] Have backup power (for serious operations)

### Environment

- [ ] Consider energy efficiency
- [ ] Use renewable energy if possible
- [ ] Proper e-waste disposal for old hardware
- [ ] Balance mining with environmental impact

## Additional Resources

- [Wallet Setup Guide](wallet-setup.md) - Secure your mining rewards
- [Transaction Guide](transactions.md) - Managing your mined XAI
- [FAQ](faq.md) - Common mining questions
- [Technical Documentation](../../WHITEPAPER.md) - Mining algorithm details

## Community

**Mining Forums:**
- Share tips and strategies with other miners

**Support:**
- Email: mining@xai.io

---

**Last Updated**: January 2025

**Disclaimer:** Mining cryptocurrency requires significant investment in hardware and electricity. Always calculate profitability and consider risks before starting mining operations. Past performance does not guarantee future results.
