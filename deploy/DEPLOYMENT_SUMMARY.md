# XAI Blockchain - Cloud Deployment Summary

Complete cloud deployment infrastructure created for XAI blockchain nodes.

## What Was Created

### One-Liner Deployments

Six platform-specific one-command deployments, each creating a complete production-ready XAI node:

1. **Docker Universal** (`docker-one-liner.sh`)
   - Works on any system with Docker
   - Creates standalone node with all dependencies
   - Perfect for local development

2. **AWS** (`aws/deploy.sh` + `cloudformation.yaml`)
   - CloudFormation template
   - EC2 instance with EBS storage
   - Security groups, Elastic IP
   - IAM roles for CloudWatch
   - Estimated cost: $70/month

3. **GCP** (`gcp/deploy.sh` + `deployment-manager.yaml`)
   - Deployment Manager configuration
   - Compute Engine VM with persistent disk
   - Firewall rules
   - Stackdriver monitoring
   - Estimated cost: $70/month

4. **Azure** (`azure/deploy.sh` + `azuredeploy.json`)
   - ARM template deployment
   - Virtual Machine with managed disk
   - Network security group
   - Static public IP with DNS
   - Estimated cost: $90/month

5. **DigitalOcean** (`digitalocean/deploy.sh` + `main.tf`)
   - Terraform infrastructure
   - Droplet with block storage
   - Firewall rules
   - Most cost-effective option
   - Estimated cost: $35/month

6. **Kubernetes** (`kubernetes/deployment.yaml` + Helm chart)
   - Full K8s deployment
   - StatefulSets for database
   - PersistentVolumeClaims
   - LoadBalancer services
   - Helm chart for easy customization

### What Each Deployment Includes

Every deployment creates:

- **XAI Blockchain Node**: Full consensus node
- **PostgreSQL Database**: Transaction storage (15-alpine)
- **Redis Cache**: Performance optimization (7-alpine)
- **Block Explorer**: Web interface for viewing blockchain
- **Monitoring**: Prometheus-compatible metrics endpoint

### Port Mappings

Standard ports across all deployments:
- `8080` - REST API endpoint
- `8333` - P2P networking
- `9090` - Metrics (Prometheus format)
- `3000` - Block Explorer UI (12080 in testnet)

## Directory Structure

```
deploy/
├── docker-one-liner.sh              # Universal Docker deployment
├── INDEX.md                         # Quick reference guide
├── QUICK_START.md                   # 2-minute quick start
├── CLOUD_DEPLOYMENT.md              # Comprehensive cloud guide
│
├── aws/
│   ├── cloudformation.yaml          # AWS CloudFormation template
│   ├── deploy.sh                    # Automated deployment script
│   └── README.md                    # AWS-specific documentation
│
├── gcp/
│   ├── deployment-manager.yaml      # GCP Deployment Manager config
│   ├── xai-node.jinja              # Jinja2 template
│   ├── deploy.sh                    # Automated deployment script
│   └── README.md                    # GCP-specific documentation
│
├── azure/
│   ├── azuredeploy.json             # Azure ARM template
│   ├── deploy.sh                    # Automated deployment script
│   └── README.md                    # Azure-specific documentation
│
├── digitalocean/
│   ├── main.tf                      # Terraform infrastructure
│   ├── app.yaml                     # App Platform spec (alternative)
│   ├── deploy.sh                    # Automated deployment script
│   └── README.md                    # DigitalOcean documentation
│
└── kubernetes/
    ├── deployment.yaml              # Complete K8s deployment
    ├── helm/
    │   ├── Chart.yaml              # Helm chart metadata
    │   └── values.yaml             # Configurable values
    └── README.md                    # Kubernetes documentation
```

## Usage Examples

### Deploy to AWS
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
```

The script will:
1. Prompt for configuration (region, instance type, network mode)
2. Create CloudFormation stack
3. Wait for completion (5-10 minutes)
4. Output connection details (IP, URLs, SSH command)

### Deploy to Docker (Local)
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
```

The script will:
1. Install Docker and Docker Compose (if needed)
2. Clone XAI repository
3. Configure environment
4. Start all services
5. Verify deployment

### Deploy to Kubernetes
```bash
kubectl apply -f https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/kubernetes/deployment.yaml
```

Or with Helm:
```bash
cd deploy/kubernetes/helm
helm install xai-node . --namespace xai-blockchain --create-namespace
```

## Features

### Automatic Installation
- All prerequisites installed automatically
- Docker, Docker Compose, cloud CLIs
- No manual setup required

### Security Defaults
- Firewall configuration included
- Encrypted storage (cloud providers)
- Random secure passwords generated
- Non-root containers

### Production-Ready
- Health checks configured
- Auto-restart on failure
- Persistent storage
- Log management

### Monitoring
- Prometheus metrics endpoint
- Health check API
- Container logs accessible
- Cloud provider monitoring integrated

## Configuration

### Environment Variables

All deployments support customization via environment variables:

```bash
XAI_NETWORK=testnet              # or mainnet
XAI_API_PORT=8080
XAI_NODE_PORT=8333
XAI_METRICS_PORT=9090
XAI_DATA_DIR=/data
XAI_LOG_DIR=/logs
POSTGRES_PASSWORD=<random-generated>
```

### Network Modes

- **Testnet**: Default, for testing and development
- **Mainnet**: Production blockchain (requires configuration)

## Post-Deployment

### Verify Installation
```bash
# Health check
curl http://<node-ip>:8080/health

# Blockchain status
curl http://<node-ip>:8080/status

# View explorer
http://<node-ip>:3000
```

### View Logs
```bash
# Docker
docker logs -f xai-node

# Kubernetes
kubectl logs -f deployment/xai-node -n xai-blockchain

# Cloud VM (SSH)
ssh user@<ip> 'docker logs -f xai-testnet-bootstrap'
```

### Monitor Resources
```bash
# Prometheus metrics
curl http://<node-ip>:9090/metrics

# Docker stats
docker stats xai-node

# Kubernetes
kubectl top pods -n xai-blockchain
```

## Cost Comparison

| Platform | Instance | Storage | Monthly Cost |
|----------|----------|---------|--------------|
| Docker (Self-hosted) | Your hardware | Your disk | $0 |
| DigitalOcean | s-2vcpu-4gb | 100GB | ~$35 |
| AWS | t3.large | 100GB gp3 | ~$70 |
| GCP | n1-standard-2 | 100GB SSD | ~$70 |
| Azure | Standard_D2s_v3 | 100GB Premium | ~$90 |
| Kubernetes | Variable | Variable | Variable |

## Maintenance

### Upgrade Node
```bash
cd /opt/xai
git pull
docker-compose down
docker-compose up -d --build
```

### Backup Data
```bash
docker run --rm --volumes-from xai-node \
  -v $(pwd):/backup ubuntu \
  tar czf /backup/xai-backup.tar.gz /data
```

### Cleanup
```bash
# AWS
aws cloudformation delete-stack --stack-name xai-node

# GCP
gcloud deployment-manager deployments delete xai-node

# Azure
az group delete --name xai-node-rg

# DigitalOcean
terraform destroy

# Kubernetes
kubectl delete namespace xai-blockchain
```

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - 2-minute deployment guide
- **[INDEX.md](INDEX.md)** - Quick reference index
- **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** - Comprehensive cloud guide
- **Platform READMEs** - Detailed guides in each directory

## Testing

All templates have been designed following these principles:

1. **Idempotent**: Can be run multiple times safely
2. **Self-contained**: No external dependencies
3. **Well-documented**: Clear instructions and examples
4. **Secure by default**: Strong security configuration
5. **Production-ready**: Suitable for real deployments

## Support

- **GitHub Issues**: https://github.com/xai-blockchain/xai/issues
- **Documentation**: https://docs.xai-blockchain.io
- **Community**: https://discord.gg/xai-blockchain

## Next Steps

1. Choose your platform
2. Run the one-liner deployment
3. Verify the node is syncing
4. Configure monitoring/alerts
5. Set up automated backups
6. Review security settings
7. Switch to mainnet (for production)

## License

MIT License - All deployment templates are open source
