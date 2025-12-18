# XAI Node - Azure Deployment

Deploy a production XAI blockchain node on Microsoft Azure with one command.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/deploy.sh | bash
```

## Prerequisites

- Azure CLI installed and authenticated
- Azure subscription
- SSH key pair

## Manual Deployment

1. Download template:
```bash
wget https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/azuredeploy.json
```

2. Deploy via Azure Portal:
   - Go to Portal > Create a resource > Template deployment
   - Build your own template in editor
   - Paste contents of azuredeploy.json
   - Fill parameters and deploy

3. Or deploy via CLI:
```bash
az group create --name xai-node-rg --location eastus

az deployment group create \
  --resource-group xai-node-rg \
  --template-file azuredeploy.json \
  --parameters \
    vmName=xai-node \
    vmSize=Standard_D2s_v3 \
    adminUsername=xaiuser \
    diskSizeGB=100 \
    networkMode=testnet \
    sshPublicKey="$(cat ~/.ssh/id_rsa.pub)"
```

## Resources Created

- **Virtual Machine**: Ubuntu 22.04 with Docker
- **Managed Disk**: 100GB Premium SSD
- **Network Security Group**: Ports 22, 8080, 8333, 9090, 3000
- **Public IP**: Static IP with DNS label
- **Virtual Network**: Isolated network

## Costs

Estimated monthly cost (East US):
- Standard_D2s_v3: ~$70
- 100GB Premium SSD: ~$15
- Public IP: ~$3
- Network egress: Variable

**Total: ~$90-110/month**

## Access

```bash
# SSH
ssh xaiuser@<public-ip>

# API
curl http://<public-ip>:8080/health

# Explorer
http://<public-ip>:3000
```

## Monitoring

Azure Portal > Virtual Machines > xai-node > Monitoring

View logs:
```bash
ssh xaiuser@<ip> 'docker logs -f xai-testnet-bootstrap'
```

## Cleanup

```bash
az group delete --name xai-node-rg --yes
```

## Custom Configuration

Edit azuredeploy.json parameters section or pass via CLI.
