# XAI Blockchain Node - Cloud Deployment

One-command deployment templates for running XAI blockchain nodes on major cloud providers.

## Quick Deploy

Choose your platform and run one command:

### Docker (Any System)

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
```

**Best for**: Quick testing, development, any system with Docker

### AWS

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
```

**Best for**: Enterprise deployments, AWS infrastructure

### GCP (Google Cloud)

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deploy.sh | bash
```

**Best for**: Google Cloud users, global scalability

### Azure

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/deploy.sh | bash
```

**Best for**: Microsoft ecosystem, enterprise Windows integration

### DigitalOcean

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/deploy.sh | bash
```

**Best for**: Cost-effective, simple deployments, developers

### Kubernetes

```bash
kubectl apply -f https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/kubernetes/deployment.yaml
```

**Best for**: Container orchestration, multi-cloud, production scale

## Deployment Comparison

| Platform | Monthly Cost | Setup Time | Complexity | Best For |
|----------|--------------|------------|------------|----------|
| Docker | $0 (self-hosted) | 5 min | Low | Local development |
| DigitalOcean | ~$35 | 5 min | Low | Cost-conscious users |
| AWS | ~$70 | 10 min | Medium | Enterprise deployments |
| GCP | ~$70 | 10 min | Medium | Google Cloud users |
| Azure | ~$90 | 10 min | Medium | Microsoft ecosystem |
| Kubernetes | Variable | 15 min | High | Production scale |

## What Gets Deployed

All deployments include:

- **XAI Blockchain Node**: Full node with API
- **PostgreSQL Database**: Chain state storage
- **Redis Cache**: Performance optimization
- **Block Explorer**: Web UI for viewing blockchain
- **Metrics Endpoint**: Prometheus-compatible monitoring

## Ports

- **8080**: API endpoint
- **8333**: P2P networking
- **9090**: Metrics
- **3000**: Block Explorer (mapped to 12080 in testnet)

## Configuration

All deployments support environment variables:

```bash
XAI_NETWORK=testnet          # or mainnet
XAI_API_PORT=8080
XAI_NODE_PORT=8333
XAI_METRICS_PORT=9090
```

## Platform-Specific Guides

Detailed instructions for each platform:

- [AWS](aws/README.md) - CloudFormation template
- [GCP](gcp/README.md) - Deployment Manager
- [Azure](azure/README.md) - ARM template
- [DigitalOcean](digitalocean/README.md) - Terraform
- [Kubernetes](kubernetes/README.md) - Helm chart

## Manual Deployment

If you prefer manual control:

1. Clone repository:
```bash
git clone https://github.com/xai-blockchain/xai.git
cd xai
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Deploy:
```bash
cd docker/testnet
docker-compose up -d
```

## Security Considerations

### Production Checklist

- [ ] Change default database password
- [ ] Enable firewall (restrict SSH to known IPs)
- [ ] Use HTTPS (setup reverse proxy with SSL)
- [ ] Enable automatic security updates
- [ ] Configure log monitoring/alerts
- [ ] Setup automated backups
- [ ] Use strong API authentication
- [ ] Keep secrets in environment variables, never in code

### Network Security

All templates open these ports:
- 22 (SSH) - Restrict to your IP
- 8080 (API) - Public
- 8333 (P2P) - Public
- 9090 (Metrics) - Consider restricting
- 3000 (Explorer) - Public

## Monitoring

### Health Check

```bash
curl http://<node-ip>:8080/health
```

### View Logs

```bash
# Docker
docker logs -f xai-node

# Kubernetes
kubectl logs -f deployment/xai-node -n xai-blockchain

# SSH to cloud instance
ssh user@<ip> 'docker logs -f xai-testnet-bootstrap'
```

### Metrics

Access Prometheus metrics at: `http://<node-ip>:9090/metrics`

## Upgrading

### Docker

```bash
cd /opt/xai
git pull
docker-compose down
docker-compose up -d --build
```

### Cloud Deployments

Most use Docker internally, so SSH and run upgrade commands above.

### Kubernetes

```bash
helm upgrade xai-node ./helm
```

## Backup and Recovery

### Backup Blockchain Data

```bash
# Docker
docker run --rm --volumes-from xai-node -v $(pwd):/backup \
  ubuntu tar czf /backup/xai-backup.tar.gz /data

# Kubernetes
kubectl exec deployment/xai-node -n xai-blockchain -- \
  tar czf - /data > xai-backup.tar.gz
```

### Restore

```bash
# Docker
docker run --rm --volumes-from xai-node -v $(pwd):/backup \
  ubuntu bash -c "cd /data && tar xzf /backup/xai-backup.tar.gz --strip 1"
```

## Troubleshooting

### Node Won't Start

```bash
# Check logs
docker logs xai-node

# Common issues:
# - Port already in use: Change XAI_API_PORT
# - Database connection failed: Check POSTGRES_PASSWORD
# - Out of disk space: Increase volume size
```

### Can't Connect to API

```bash
# Check if service is running
curl http://localhost:8080/health

# Check firewall
sudo ufw status

# Check if port is open
netstat -tuln | grep 8080
```

### Sync Issues

```bash
# Check peer connections
curl http://localhost:8080/peers

# Force resync (testnet only)
docker exec xai-node rm -rf /data/blockchain
docker restart xai-node
```

## Cost Optimization

### Reduce Costs

1. **Use smaller instances** for testnet
2. **Enable pruning** (set XAI_PRUNE_BLOCKS)
3. **Reduce volume size** if not storing full history
4. **Use spot/preemptible instances** for non-critical nodes
5. **Schedule shutdown** during off-hours for dev nodes

### Cost Examples (Testnet vs Mainnet)

| Component | Testnet | Mainnet |
|-----------|---------|---------|
| Instance | t3.medium | t3.large |
| Storage | 50GB | 200GB |
| Bandwidth | Low | High |
| **Monthly** | **~$40** | **~$120** |

## Support

- **Documentation**: https://docs.xai-blockchain.io
- **GitHub Issues**: https://github.com/xai-blockchain/xai/issues
- **Community**: https://discord.gg/xai-blockchain

## Contributing

Found a bug or want to improve these templates?

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details
