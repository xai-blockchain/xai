#!/bin/bash
#
# XAI Blockchain Node - Azure One-Liner Deployment
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/deploy.sh | bash
#

set -e

echo "========================================"
echo "XAI Blockchain Node - Azure Deployment"
echo "========================================"
echo ""

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI not installed"
    echo "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check login
if ! az account show &> /dev/null; then
    echo "Error: Not logged into Azure"
    echo "Run: az login"
    exit 1
fi

# Get parameters
read -p "Resource Group name [xai-node-rg]: " RG_NAME
RG_NAME=${RG_NAME:-xai-node-rg}

read -p "Location [eastus]: " LOCATION
LOCATION=${LOCATION:-eastus}

read -p "VM Name [xai-node]: " VM_NAME
VM_NAME=${VM_NAME:-xai-node}

read -p "VM Size [Standard_D2s_v3]: " VM_SIZE
VM_SIZE=${VM_SIZE:-Standard_D2s_v3}

read -p "Disk Size (GB) [100]: " DISK_SIZE
DISK_SIZE=${DISK_SIZE:-100}

read -p "Admin Username [xaiuser]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-xaiuser}

read -p "Network Mode (testnet/mainnet) [testnet]: " NETWORK_MODE
NETWORK_MODE=${NETWORK_MODE:-testnet}

# SSH Key
if [ -f ~/.ssh/id_rsa.pub ]; then
    SSH_KEY=$(cat ~/.ssh/id_rsa.pub)
    echo ""
    echo "Found SSH key: ~/.ssh/id_rsa.pub"
else
    echo ""
    echo "No SSH key found at ~/.ssh/id_rsa.pub"
    read -p "Paste your SSH public key: " SSH_KEY
fi

if [ -z "$SSH_KEY" ]; then
    echo "Error: SSH public key required"
    exit 1
fi

# Confirm
echo ""
echo "Deployment Configuration:"
echo "  Resource Group: $RG_NAME"
echo "  Location:       $LOCATION"
echo "  VM Name:        $VM_NAME"
echo "  VM Size:        $VM_SIZE"
echo "  Disk Size:      ${DISK_SIZE}GB"
echo "  Admin User:     $ADMIN_USER"
echo "  Network:        $NETWORK_MODE"
echo ""
read -p "Deploy? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Create resource group
echo ""
echo "Creating resource group..."
az group create --name $RG_NAME --location $LOCATION

# Download template
echo ""
echo "Downloading ARM template..."
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/azure/azuredeploy.json -o /tmp/azuredeploy.json

# Deploy
echo ""
echo "Deploying XAI node..."
az deployment group create \
    --resource-group $RG_NAME \
    --template-file /tmp/azuredeploy.json \
    --parameters \
        vmName=$VM_NAME \
        vmSize=$VM_SIZE \
        adminUsername=$ADMIN_USER \
        diskSizeGB=$DISK_SIZE \
        networkMode=$NETWORK_MODE \
        sshPublicKey="$SSH_KEY"

echo ""
echo "Deployment initiated. Waiting for completion..."

# Get outputs
PUBLIC_IP=$(az deployment group show \
    --resource-group $RG_NAME \
    --name azuredeploy \
    --query 'properties.outputs.publicIP.value' -o tsv)

API_URL=$(az deployment group show \
    --resource-group $RG_NAME \
    --name azuredeploy \
    --query 'properties.outputs.apiURL.value' -o tsv)

EXPLORER_URL=$(az deployment group show \
    --resource-group $RG_NAME \
    --name azuredeploy \
    --query 'properties.outputs.explorerURL.value' -o tsv)

FQDN=$(az deployment group show \
    --resource-group $RG_NAME \
    --name azuredeploy \
    --query 'properties.outputs.fqdn.value' -o tsv)

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Node Details:"
echo "  Public IP:      $PUBLIC_IP"
echo "  FQDN:           $FQDN"
echo "  API:            $API_URL"
echo "  Explorer:       $EXPLORER_URL"
echo ""
echo "SSH Access:"
echo "  ssh $ADMIN_USER@$PUBLIC_IP"
echo ""
echo "The node is starting. Wait 2-3 minutes before accessing."
echo ""
echo "Monitor logs:"
echo "  ssh $ADMIN_USER@$PUBLIC_IP 'docker logs -f xai-testnet-bootstrap'"
echo ""
echo "To delete:"
echo "  az group delete --name $RG_NAME --yes --no-wait"
echo ""
