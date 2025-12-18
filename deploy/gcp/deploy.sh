#!/bin/bash
#
# XAI Blockchain Node - GCP One-Liner Deployment
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deploy.sh | bash
#

set -e

echo "========================================"
echo "XAI Blockchain Node - GCP Deployment"
echo "========================================"
echo ""

# Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not installed"
    echo "Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get parameters
read -p "Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "Error: Project ID required"
    exit 1
fi

read -p "Deployment name [xai-node]: " DEPLOYMENT_NAME
DEPLOYMENT_NAME=${DEPLOYMENT_NAME:-xai-node}

read -p "Zone [us-central1-a]: " ZONE
ZONE=${ZONE:-us-central1-a}

read -p "Machine Type [n1-standard-2]: " MACHINE_TYPE
MACHINE_TYPE=${MACHINE_TYPE:-n1-standard-2}

read -p "Disk Size (GB) [100]: " DISK_SIZE
DISK_SIZE=${DISK_SIZE:-100}

read -p "Network Mode (testnet/mainnet) [testnet]: " NETWORK_MODE
NETWORK_MODE=${NETWORK_MODE:-testnet}

# Confirm
echo ""
echo "Deployment Configuration:"
echo "  Project:        $PROJECT_ID"
echo "  Name:           $DEPLOYMENT_NAME"
echo "  Zone:           $ZONE"
echo "  Machine Type:   $MACHINE_TYPE"
echo "  Disk Size:      ${DISK_SIZE}GB"
echo "  Network:        $NETWORK_MODE"
echo ""
read -p "Deploy? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set project
gcloud config set project $PROJECT_ID

# Download templates
echo ""
echo "Downloading deployment templates..."
mkdir -p /tmp/xai-gcp
cd /tmp/xai-gcp

curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/deployment-manager.yaml -o deployment-manager.yaml
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/gcp/xai-node.jinja -o xai-node.jinja

# Update parameters
cat > deployment-manager.yaml <<EOF
imports:
- path: xai-node.jinja

resources:
- name: xai-blockchain-node
  type: xai-node.jinja
  properties:
    zone: $ZONE
    machineType: $MACHINE_TYPE
    diskSizeGb: $DISK_SIZE
    networkMode: $NETWORK_MODE
EOF

# Deploy
echo ""
echo "Creating deployment..."
gcloud deployment-manager deployments create $DEPLOYMENT_NAME \
    --config deployment-manager.yaml

echo ""
echo "Deployment initiated. Waiting for completion..."
sleep 5

# Get outputs
INSTANCE_NAME=$(gcloud deployment-manager deployments describe $DEPLOYMENT_NAME \
    --format='value(resources[0].name)')

EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Node Details:"
echo "  Instance:       $INSTANCE_NAME"
echo "  External IP:    $EXTERNAL_IP"
echo "  API:            http://$EXTERNAL_IP:8080"
echo "  Explorer:       http://$EXTERNAL_IP:3000"
echo ""
echo "SSH Access:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "The node is starting. Wait 2-3 minutes before accessing."
echo ""
echo "Monitor logs:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='docker logs -f xai-testnet-bootstrap'"
echo ""
echo "To delete:"
echo "  gcloud deployment-manager deployments delete $DEPLOYMENT_NAME"
echo ""
