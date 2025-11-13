# XAI Blockchain - Deployment Guide

**⚠️ INTERNAL USE ONLY - DELETE THIS FILE BEFORE PUBLIC RELEASE ⚠️**

---

## Quick Start

### Linux/Mac
```bash
chmod +x deploy/install_node.sh
./deploy/install_node.sh
cd ~/xai-blockchain
source venv/bin/activate
python core/node.py
```

### Windows
```cmd
deploy\install_node.bat
cd %USERPROFILE%\xai-blockchain
venv\Scripts\activate.bat
python core\node.py
```

### Docker
```bash
docker-compose up -d
```

---

## Installation Methods

### Method 1: Docker (Recommended for Production)

**Single Node:**
```bash
docker build -t xai-node .
docker run -d -p 5000:5000 --name xai-node xai-node
```

**Multi-Node Network:**
```bash
docker-compose up -d
```

**View Logs:**
```bash
docker logs -f xai-node
```

### Method 2: System Service (Linux)

**Install:**
```bash
./deploy/install_node.sh
sudo cp deploy/xai-node.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xai-node
sudo systemctl start xai-node
```

**Manage:**
```bash
sudo systemctl status xai-node
sudo systemctl stop xai-node
sudo systemctl restart xai-node
sudo journalctl -u xai-node -f
```

### Method 3: Manual Installation

**Clone/Extract:**
```bash
cd /opt
git clone [repository] xai-blockchain
cd xai-blockchain
```

**Setup:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configure:**
```bash
cp deploy/config.template.env config.env
nano config.env  # Edit configuration
```

**Run:**
```bash
python core/node.py
```

---

## Node Management

### Using Node Manager Script (Linux/Mac)

**Start:**
```bash
./deploy/node_manager.sh start
```

**Stop:**
```bash
./deploy/node_manager.sh stop
```

**Status:**
```bash
./deploy/node_manager.sh status
```

**View Logs:**
```bash
./deploy/node_manager.sh logs
```

**Get Stats:**
```bash
./deploy/node_manager.sh stats
```

---

## Configuration

### Environment Variables

```bash
# Network
XAI_HOST=0.0.0.0
XAI_PORT=5000
XAI_NETWORK=mainnet

# Mining
XAI_MINER_ADDRESS=your_address
XAI_AUTO_MINE=true

# Peers
XAI_BOOTSTRAP_PEERS=http://peer1:5000,http://peer2:5000
```

### Genesis Block Setup

**Generate Genesis (DO ONCE FOR ENTIRE NETWORK):**
```bash
python generate_premine.py
```

**Distribute:**
- Copy `genesis_mainnet.json` to all nodes
- Keep `premine_wallets_ENCRYPTED.json` secure (password-protected)

---

## Monitoring

### Basic Monitoring
```bash
./deploy/monitor_node.sh
```

### API Health Check
```bash
curl http://localhost:5000/stats
```

### Log Monitoring
```bash
tail -f logs/xai_node.log
```

---

## Security Checklist

- [ ] Firewall configured (allow port 5000 only from trusted sources)
- [ ] SSL/TLS enabled for API (use reverse proxy)
- [ ] Wallet private keys encrypted
- [ ] Genesis block validated (hash matches network)
- [ ] Rate limiting enabled
- [ ] Log rotation configured
- [ ] Backups automated (data/, logs/)
- [ ] Monitoring alerts configured
- [ ] Keep Python and dependencies updated

---

## Troubleshooting

### Node Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check dependencies
pip list

# Check logs
cat logs/xai_node.log
```

### No Peers Connecting
```bash
# Verify bootstrap peers
curl http://peer-address:5000/stats

# Check firewall
sudo ufw status

# Test connectivity
nc -zv peer-address 5000
```

### Genesis Block Mismatch
```bash
# Delete local chain
rm -rf data/*

# Copy correct genesis
cp genesis_mainnet.json .

# Restart node
```

### High Memory Usage
```bash
# Check stats
curl http://localhost:5000/stats

# Restart node periodically
./deploy/node_manager.sh restart
```

---

## Ports and Networking

**Required Ports:**
- 5000: Node API (TCP)

**Firewall Rules:**
```bash
# Linux (ufw)
sudo ufw allow 5000/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

---

## Backup and Recovery

### Backup Data
```bash
tar -czf xai-backup-$(date +%Y%m%d).tar.gz data/ logs/ config.env
```

### Restore Data
```bash
tar -xzf xai-backup-YYYYMMDD.tar.gz
```

---

## Upgrading

### Stop Node
```bash
./deploy/node_manager.sh stop
```

### Backup
```bash
cp -r data/ data.backup/
cp -r logs/ logs.backup/
```

### Update Code
```bash
git pull
# or extract new release
```

### Update Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Start Node
```bash
./deploy/node_manager.sh start
```

---

## Multi-Node Deployment

### Bootstrap Node
```bash
# Node 1 (bootstrap)
XAI_HOST=0.0.0.0 XAI_PORT=5000 python core/node.py
```

### Additional Nodes
```bash
# Node 2
XAI_BOOTSTRAP_PEERS=http://node1:5000 XAI_PORT=5001 python core/node.py

# Node 3
XAI_BOOTSTRAP_PEERS=http://node1:5000,http://node2:5001 XAI_PORT=5002 python core/node.py
```

---

## Performance Tuning

### Increase File Descriptors
```bash
ulimit -n 65536
```

### Optimize Python
```bash
# Use PyPy for better performance
pypy3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Contact

**Issues:** Report to internal team only
**Updates:** Check internal repository
**Documentation:** All files in deploy/ directory

---

**⚠️ REMEMBER: DELETE ALL DEPLOYMENT DOCUMENTATION BEFORE PUBLIC RELEASE ⚠️**
