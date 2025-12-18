# XAI Node - GCP Deployment

Deploy a production XAI blockchain node on Google Cloud Platform with one command.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deploy.sh | bash
```

## Prerequisites

- gcloud CLI installed and authenticated
- GCP project with Compute Engine API enabled
- Billing enabled on project

## Manual Deployment

1. Download templates:
```bash
wget https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deployment-manager.yaml
wget https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/xai-node.jinja
```

2. Deploy:
```bash
gcloud deployment-manager deployments create xai-node \
  --config deployment-manager.yaml
```

## Resources Created

- **Compute Instance**: Ubuntu 22.04 with Docker
- **Persistent Disk**: 100GB SSD
- **Firewall Rules**: Ports 22, 8080, 8333, 9090, 3000
- **External IP**: Ephemeral (can upgrade to static)

## Costs

Estimated monthly cost (us-central1):
- n1-standard-2: ~$50
- 100GB SSD: ~$17
- Network egress: Variable

**Total: ~$70-90/month**

## Access

```bash
# SSH
gcloud compute ssh xai-node-instance --zone=us-central1-a

# API
curl http://<external-ip>:8080/health

# Explorer
http://<external-ip>:3000
```

## Monitoring

GCP Console > Compute Engine > VM instances > xai-node-instance

View logs:
```bash
gcloud compute ssh xai-node-instance --command='docker logs -f xai-testnet-bootstrap'
```

## Cleanup

```bash
gcloud deployment-manager deployments delete xai-node
```

## Custom Configuration

Edit `deployment-manager.yaml` properties:
- zone: GCP zone
- machineType: Instance size
- diskSizeGb: Storage size
- networkMode: testnet or mainnet
