# XAI Blockchain - Deployment Index

Quick reference for all deployment options.

## One-Line Deployments

### Docker (Universal)
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
```
Works on any system with Docker. Perfect for local development and testing.

### AWS
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
```
Deploys using CloudFormation. Creates EC2, RDS, and networking automatically.

### GCP
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deploy.sh | bash
```
Deploys using Deployment Manager. Creates Compute Engine VM with all dependencies.

### Azure
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/deploy.sh | bash
```
Deploys using ARM templates. Creates VM, managed disks, and networking.

### DigitalOcean
```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/deploy.sh | bash
```
Deploys using Terraform. Most cost-effective cloud option (~$35/month).

### Kubernetes
```bash
kubectl apply -f https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/kubernetes/deployment.yaml
```
Full Kubernetes deployment with StatefulSets and PVCs.

## File Structure

```
deploy/
├── docker-one-liner.sh          # Universal Docker deployment
├── CLOUD_DEPLOYMENT.md          # Main cloud deployment guide
├── INDEX.md                     # This file
│
├── aws/
│   ├── cloudformation.yaml      # AWS infrastructure template
│   ├── deploy.sh                # Automated deployment script
│   └── README.md                # AWS-specific documentation
│
├── gcp/
│   ├── deployment-manager.yaml  # GCP infrastructure template
│   ├── xai-node.jinja          # GCP template
│   ├── deploy.sh                # Automated deployment script
│   └── README.md                # GCP-specific documentation
│
├── azure/
│   ├── azuredeploy.json         # ARM template
│   ├── deploy.sh                # Automated deployment script
│   └── README.md                # Azure-specific documentation
│
├── digitalocean/
│   ├── main.tf                  # Terraform infrastructure
│   ├── app.yaml                 # App Platform spec
│   ├── deploy.sh                # Automated deployment script
│   └── README.md                # DigitalOcean documentation
│
├── kubernetes/
│   ├── deployment.yaml          # Full K8s deployment
│   ├── helm/
│   │   ├── Chart.yaml          # Helm chart definition
│   │   └── values.yaml         # Configurable values
│   └── README.md                # Kubernetes documentation
│
├── terraform/                   # Advanced Terraform configs
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
├── ansible/                     # Configuration management
│   ├── site.yml
│   ├── inventory/
│   └── roles/
│
└── scripts/                     # Utility scripts
    ├── deploy.sh
    ├── health-check.sh
    └── rollback.sh
```

## Quick Comparison

| Platform | Cost/Month | Setup Time | Difficulty |
|----------|-----------|------------|------------|
| Docker | Free | 5 min | Easy |
| DigitalOcean | $35 | 5 min | Easy |
| AWS | $70 | 10 min | Medium |
| GCP | $70 | 10 min | Medium |
| Azure | $90 | 10 min | Medium |
| Kubernetes | Variable | 15 min | Hard |

## Components Deployed

All deployments include:

1. **XAI Blockchain Node** - Core blockchain with consensus
2. **PostgreSQL Database** - Transaction and state storage
3. **Redis Cache** - Performance optimization
4. **Block Explorer** - Web interface
5. **Metrics Endpoint** - Prometheus-compatible monitoring

## Port Reference

- **8080** - API endpoint
- **8333** - P2P networking
- **9090** - Metrics
- **3000** - Block Explorer (12080 in testnet)

## Documentation

- **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** - Main deployment guide
- **[README.md](README.md)** - Production deployment (Terraform/Ansible)
- **Platform READMEs** - Detailed guides in each platform directory

## Support

- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://docs.xai-blockchain.io
- Community: https://discord.gg/xai-blockchain
