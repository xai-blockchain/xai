# XAI Node - Quick Start Guide

Deploy a production-ready XAI blockchain node in minutes.

## Choose Your Platform

### Local Development
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
```

### AWS Cloud
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
```

### Google Cloud
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deploy.sh | bash
```

### Microsoft Azure
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/deploy.sh | bash
```

### DigitalOcean
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/deploy.sh | bash
```

### Kubernetes
```bash
kubectl apply -f https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/kubernetes/deployment.yaml
```

## What You Get

After deployment, you'll have:

1. **Full XAI Node** running on port 8080
2. **Block Explorer** on port 3000
3. **Metrics** on port 9090
4. **Database** (PostgreSQL + Redis)

## Verify Deployment

```bash
# Check node health
curl http://<your-ip>:8080/health

# View blockchain status
curl http://<your-ip>:8080/status

# Open explorer
http://<your-ip>:3000
```

## Default Configuration

- Network: Testnet
- API Port: 8080
- P2P Port: 8333
- Storage: 100GB

## Next Steps

1. Review platform-specific README in respective directory
2. Configure firewall (restrict SSH access)
3. Setup monitoring/alerts
4. Enable backups
5. Switch to mainnet (if production)

## Need Help?

- [Full Documentation](CLOUD_DEPLOYMENT.md)
- [Platform Index](INDEX.md)
- GitHub Issues: https://github.com/xai-blockchain/xai/issues
