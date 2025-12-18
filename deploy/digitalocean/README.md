# XAI Node - DigitalOcean Deployment

Deploy a production XAI blockchain node on DigitalOcean with one command.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/deploy.sh | bash
```

## Prerequisites

- DigitalOcean account
- API token (generate at: https://cloud.digitalocean.com/account/api/tokens)
- SSH key uploaded to DigitalOcean

## Deployment Options

### Option 1: Terraform (Recommended)

```bash
# Install doctl and terraform (script does this automatically)
doctl auth init
cd deploy/digitalocean
terraform init
terraform apply
```

### Option 2: One-Click App Platform

1. Click: [![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/xai-blockchain/xai/tree/main)
2. Configure environment variables
3. Deploy

### Option 3: Manual Droplet

```bash
# Create droplet
doctl compute droplet create xai-node \
  --region nyc3 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --ssh-keys <your-key-id>

# SSH and install
ssh root@<droplet-ip>
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/docker-one-liner.sh | bash
```

## Resources Created

- **Droplet**: 2 vCPU, 4GB RAM
- **Block Storage**: 100GB volume
- **Firewall**: Ports 22, 8080, 8333, 9090, 3000

## Costs

Estimated monthly cost:
- s-2vcpu-4gb: $24/month
- 100GB volume: $10/month
- Bandwidth: 4TB included

**Total: ~$35/month**

## Access

```bash
# SSH
ssh root@<droplet-ip>

# API
curl http://<droplet-ip>:8080/health

# Explorer
http://<droplet-ip>:3000
```

## Monitoring

DigitalOcean Console > Droplets > xai-blockchain-node

View logs:
```bash
ssh root@<ip> 'docker logs -f xai-testnet-bootstrap'
```

## Cleanup

```bash
# Terraform
terraform destroy

# Or via doctl
doctl compute droplet delete xai-blockchain-node
doctl compute volume delete xai-node-data
```

## Custom Configuration

Edit `main.tf` variables or pass via `-var` flags:
```bash
terraform apply -var="droplet_size=s-4vcpu-8gb" -var="network_mode=mainnet"
```
