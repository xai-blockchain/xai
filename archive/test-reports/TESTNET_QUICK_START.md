# PAW/XAI Testnet - Quick Start Guide

**Deploy a testnet node in 30 minutes**

This is the absolute fastest way to get a PAW/XAI testnet node running. Perfect for testing and development.

---

## Prerequisites

- VPS server (4 CPU, 16GB RAM, 200GB SSD) - **$17-80/month**
- Ubuntu 20.04+ or Debian 11+
- Root access
- 30 minutes of time

**Recommended Providers**:
- Hetzner CX41: $17/month - [https://www.hetzner.com/cloud](https://www.hetzner.com/cloud)
- Linode Dedicated 8GB: $60/month - [https://www.linode.com/](https://www.linode.com/)
- DigitalOcean Droplet: $80/month - [https://www.digitalocean.com/](https://www.digitalocean.com/)

---

## Installation (Copy & Paste)

### Step 1: Install Docker (5 minutes)

```bash
# SSH into your server
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Verify
docker --version
docker compose version
```

### Step 2: Clone & Configure (10 minutes)

```bash
# Clone repository
cd /opt
cd xai-blockchain

# Create environment file
cp .env.example .env

# Generate secure passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)
export GRAFANA_PASSWORD=$(openssl rand -base64 16)
export XAI_API_KEY=$(openssl rand -hex 32)
export XAI_JWT_SECRET=$(openssl rand -hex 64)

# Save passwords to file (IMPORTANT: Save these!)
cat > /root/xai-passwords.txt << EOF
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
XAI_API_KEY=$XAI_API_KEY
XAI_JWT_SECRET=$XAI_JWT_SECRET
EOF

# Make passwords file secure
chmod 600 /root/xai-passwords.txt

echo "IMPORTANT: Passwords saved to /root/xai-passwords.txt"
echo "Copy these to a password manager NOW!"
cat /root/xai-passwords.txt

# Update .env file with minimal configuration
cat > .env << EOF
# Environment
XAI_ENV=testnet
XAI_NETWORK_ID=2

# Ports
XAI_NODE_PORT=8333
XAI_API_PORT=8080
XAI_WS_PORT=8081
XAI_METRICS_PORT=9090

# Mining
XAI_ENABLE_MINING=true
XAI_MINING_THREADS=2

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=xai_testnet
POSTGRES_USER=xai
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# Security
XAI_API_KEY=$XAI_API_KEY
XAI_JWT_SECRET=$XAI_JWT_SECRET

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_USER=admin
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# Logging
LOG_LEVEL=INFO
EOF

echo ".env file created successfully"
```

### Step 3: Configure Firewall (2 minutes)

```bash
# Install and configure firewall
apt install -y ufw

# Allow necessary ports
ufw allow 22/tcp      # SSH
ufw allow 8080/tcp    # API
ufw allow 8333/tcp    # P2P
ufw allow 3000/tcp    # Grafana

# Enable firewall
ufw --force enable

# Verify
ufw status
```

### Step 4: Deploy (10 minutes)

```bash
# Build and start services
docker compose build
docker compose up -d

# Wait for services to start (about 2 minutes)
echo "Waiting for services to start..."
sleep 120

# Check status
docker compose ps

# View logs
docker compose logs -f
# Press Ctrl+C to exit logs
```

### Step 5: Verify (3 minutes)

```bash
# Get your server IP
SERVER_IP=$(curl -s ifconfig.me)

echo "=========================================="
echo "PAW/XAI Testnet Node Deployed!"
echo "=========================================="
echo ""
echo "Server IP: $SERVER_IP"
echo ""
echo "Access Points:"
echo "  API:        http://$SERVER_IP:8080"
echo "  WebSocket:  ws://$SERVER_IP:8081"
echo "  Grafana:    http://$SERVER_IP:3000"
echo "  Prometheus: http://$SERVER_IP:9091"
echo "  Explorer:   http://$SERVER_IP:8082"
echo ""
echo "Credentials:"
echo "  View passwords: cat /root/xai-passwords.txt"
echo ""
echo "Health Check:"
curl -s http://localhost:8080/health | python3 -m json.tool
echo ""
echo "=========================================="

# Test API
echo "Testing API..."
curl -s http://localhost:8080/api/blockchain/status | python3 -m json.tool
```

---

## Quick Commands

### View Status
```bash
cd /opt/xai-blockchain
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Just blockchain node
docker compose logs -f xai-node
```

### Check Health
```bash
curl http://localhost:8080/health
```

### Check Blockchain Status
```bash
curl http://localhost:8080/api/blockchain/status | python3 -m json.tool
```

### Stop Services
```bash
docker compose stop
```

### Start Services
```bash
docker compose start
```

### Restart Services
```bash
docker compose restart
```

---

## Access Your Node

Replace `YOUR_SERVER_IP` with your actual server IP from step 5.

### API Endpoints

**Get Blockchain Status**:
```bash
curl http://YOUR_SERVER_IP:8080/api/blockchain/status
```

**Get Latest Block**:
```bash
curl http://YOUR_SERVER_IP:8080/api/blocks/latest
```

**Get Network Peers**:
```bash
curl http://YOUR_SERVER_IP:8080/api/network/peers
```

**Create Wallet**:
```bash
curl -X POST http://YOUR_SERVER_IP:8080/api/wallet/create
```

### Monitoring Dashboards

**Grafana** (Blockchain Metrics):
- URL: `http://YOUR_SERVER_IP:3000`
- Username: `admin`
- Password: See `/root/xai-passwords.txt`

**Prometheus** (Raw Metrics):
- URL: `http://YOUR_SERVER_IP:9091`

**Block Explorer** (Web UI):
- URL: `http://YOUR_SERVER_IP:8082`

---

## What's Running?

Your testnet node includes:

1. **Blockchain Node** - Core consensus and P2P
2. **PostgreSQL** - Transaction storage
3. **Redis** - Caching layer
4. **Prometheus** - Metrics collection
5. **Grafana** - Metrics visualization
6. **Block Explorer** - Web interface
7. **Wallet Service** - Wallet management

All services are connected and monitored.

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker compose logs <service-name>

# Restart service
docker compose restart <service-name>

# Rebuild if needed
docker compose up -d --build
```

### API Not Responding

```bash
# Check if node is running
docker compose ps xai-node

# Check logs
docker compose logs xai-node | tail -50

# Restart node
docker compose restart xai-node
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a

# Check logs size
du -sh /var/lib/docker/containers/*/

# Rotate logs
docker compose logs --tail=1000 > /tmp/logs.txt
```

### Need to Reset Everything

```bash
# WARNING: This deletes all blockchain data!
cd /opt/xai-blockchain
docker compose down -v
docker compose up -d
```

---

## Next Steps

### After 24 Hours

1. **Check Performance**:
   ```bash
   docker stats
   ```

2. **Review Logs**:
   ```bash
   docker compose logs | grep ERROR
   ```

3. **Check Blockchain Growth**:
   ```bash
   curl http://localhost:8080/api/blockchain/height
   ```

### After 1 Week

1. **Set Up Automated Backups**:
   - See: `TESTNET_DEPLOYMENT_CHECKLIST.md` - "Set Up Backups" section

2. **Configure Alerts**:
   - Open Grafana
   - Set up email/Slack notifications

3. **Enable SSL/TLS** (if using domain):
   - See: `TESTNET_DEPLOYMENT_CHECKLIST.md` - "SSL/TLS Setup" section

### Production Considerations

Before mainnet:
- [ ] Professional security audit
- [ ] Load testing
- [ ] Backup/restore testing
- [ ] Multi-region deployment
- [ ] DDoS protection
- [ ] Monitoring alerts
- [ ] Incident response plan

---

## Backup Your Node

### Manual Backup

```bash
# Backup blockchain data
docker compose exec -T xai-node tar czf - /data/blockchain > /opt/backups/blockchain_$(date +%Y%m%d).tar.gz

# Backup database
docker compose exec -T postgres pg_dump -U xai xai_testnet | gzip > /opt/backups/database_$(date +%Y%m%d).sql.gz
```

### Automated Daily Backups

```bash
# Create backup directory
mkdir -p /opt/backups

# Create backup script
cat > /opt/backups/backup-daily.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

cd /opt/xai-blockchain

# Backup blockchain
docker compose exec -T xai-node tar czf - /data/blockchain > $BACKUP_DIR/blockchain_$DATE.tar.gz

# Backup database
docker compose exec -T postgres pg_dump -U xai xai_testnet | gzip > $BACKUP_DIR/database_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $DATE" >> /var/log/xai-backup.log
EOF

# Make executable
chmod +x /opt/backups/backup-daily.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backups/backup-daily.sh") | crontab -

echo "Daily backups scheduled at 2 AM"
```

---

## Maintenance Commands

### Update Docker Images

```bash
cd /opt/xai-blockchain

# Pull latest changes

# Rebuild and restart
docker compose up -d --build
```

### View Resource Usage

```bash
# Real-time stats
docker stats

# Disk usage
df -h

# Memory usage
free -h

# Container disk usage
docker system df
```

### Clean Up Logs

```bash
# Truncate logs (keeps last 1000 lines per service)
cd /opt/xai-blockchain
for service in $(docker compose ps --services); do
  docker compose logs $service --tail=1000 > /tmp/${service}_logs.txt
done

# Restart to clear old logs
docker compose restart
```

---

## API Examples

### Check Node Status
```bash
curl http://YOUR_SERVER_IP:8080/api/node/info | python3 -m json.tool
```

### Get Blockchain Height
```bash
curl http://YOUR_SERVER_IP:8080/api/blockchain/height
```

### Get Block by Number
```bash
curl http://YOUR_SERVER_IP:8080/api/blocks/0 | python3 -m json.tool
```

### Create Transaction (Example)
```bash
curl -X POST http://YOUR_SERVER_IP:8080/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "XAI1234...",
    "recipient": "XAI5678...",
    "amount": 10.0
  }' | python3 -m json.tool
```

### Get Mining Status
```bash
curl http://YOUR_SERVER_IP:8080/api/mining/status | python3 -m json.tool
```

---

## Getting Help

### Documentation
- **Full Assessment**: `TESTNET_DEPLOYMENT_READINESS_ASSESSMENT.md`
- **Detailed Checklist**: `TESTNET_DEPLOYMENT_CHECKLIST.md`
- **Kubernetes Guide**: `k8s/00-START-HERE.md`

### Logs
```bash
# View all logs
docker compose logs -f

# Search for errors
docker compose logs | grep -i error

# View specific service
docker compose logs -f xai-node
```

### Status Check Script

Save this as `/root/check-status.sh`:

```bash
#!/bin/bash
echo "PAW/XAI Testnet Status"
echo "======================"
echo ""
echo "Containers:"
docker compose ps
echo ""
echo "Health:"
curl -s http://localhost:8080/health | python3 -m json.tool
echo ""
echo "Blockchain:"
curl -s http://localhost:8080/api/blockchain/status | python3 -m json.tool
echo ""
echo "Peers:"
curl -s http://localhost:8080/api/network/peers | python3 -m json.tool
echo ""
echo "Mining:"
curl -s http://localhost:8080/api/mining/status | python3 -m json.tool
echo ""
echo "Resource Usage:"
docker stats --no-stream
```

Make executable:
```bash
chmod +x /root/check-status.sh
```

Run anytime:
```bash
/root/check-status.sh
```

---

## Success!

If you can access these URLs and they return valid data, your testnet node is working:

- ✅ `http://YOUR_SERVER_IP:8080/health` - Returns health status
- ✅ `http://YOUR_SERVER_IP:8080/api/blockchain/status` - Returns blockchain info
- ✅ `http://YOUR_SERVER_IP:3000` - Grafana loads
- ✅ `http://YOUR_SERVER_IP:8082` - Block explorer loads

**Congratulations! Your PAW/XAI testnet node is live!** 🎉

---

## Important Notes

1. **Save Your Passwords**: Passwords are in `/root/xai-passwords.txt` - copy to a password manager!

2. **Backups**: Set up automated backups (see above)

3. **Monitoring**: Check Grafana regularly at `http://YOUR_SERVER_IP:3000`

4. **Security**: This is a testnet setup. For production/mainnet, additional security is required.


---

## Cost Estimate

**Monthly Costs** (Testnet):
- VPS: $17-80/month (depending on provider)
- Domain: $1/month (optional)
- Backups: $1-5/month (optional)
- **Total: $18-85/month**

**Total Deployment Time**: ~30 minutes

---

## Questions?

- Check logs: `docker compose logs -f`
- Review full documentation: `TESTNET_DEPLOYMENT_READINESS_ASSESSMENT.md`
- Run status check: `/root/check-status.sh`

---

**Happy Testing! 🚀**
