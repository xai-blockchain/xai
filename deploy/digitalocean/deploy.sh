#!/bin/bash
#
# XAI Blockchain Node - DigitalOcean One-Liner Deployment
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/deploy.sh | bash
#

set -e

echo "========================================"
echo "XAI Node - DigitalOcean Deployment"
echo "========================================"
echo ""

# Check for doctl
if ! command -v doctl &> /dev/null; then
    echo "Installing doctl..."
    cd /tmp
    wget https://github.com/digitalocean/doctl/releases/latest/download/doctl-$(uname -s | tr '[:upper:]' '[:lower:]')-amd64.tar.gz
    tar xf doctl-*.tar.gz
    sudo mv doctl /usr/local/bin
    rm doctl-*.tar.gz
fi

# Check authentication
if ! doctl account get &> /dev/null; then
    echo ""
    echo "Not authenticated with DigitalOcean"
    read -p "Enter your DigitalOcean API token: " DO_TOKEN
    doctl auth init --access-token $DO_TOKEN
fi

# Check for Terraform
if ! command -v terraform &> /dev/null; then
    echo ""
    echo "Terraform not found. Installing..."
    cd /tmp
    wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
    unzip terraform_1.6.0_linux_amd64.zip
    sudo mv terraform /usr/local/bin/
    rm terraform_1.6.0_linux_amd64.zip
fi

# Get parameters
read -p "Region [nyc3]: " REGION
REGION=${REGION:-nyc3}

read -p "Droplet Size [s-2vcpu-4gb]: " DROPLET_SIZE
DROPLET_SIZE=${DROPLET_SIZE:-s-2vcpu-4gb}

read -p "Volume Size (GB) [100]: " VOLUME_SIZE
VOLUME_SIZE=${VOLUME_SIZE:-100}

read -p "Network Mode (testnet/mainnet) [testnet]: " NETWORK_MODE
NETWORK_MODE=${NETWORK_MODE:-testnet}

# Get SSH keys
echo ""
echo "Available SSH keys:"
doctl compute ssh-key list --format ID,Name --no-header

read -p "Enter SSH key ID (comma-separated if multiple): " SSH_KEYS
if [ -z "$SSH_KEYS" ]; then
    echo "Error: SSH key ID required"
    exit 1
fi

# Convert to array format
SSH_KEY_ARRAY="[\"$(echo $SSH_KEYS | sed 's/,/\",\"/g')\"]"

# Confirm
echo ""
echo "Deployment Configuration:"
echo "  Region:         $REGION"
echo "  Droplet Size:   $DROPLET_SIZE"
echo "  Volume Size:    ${VOLUME_SIZE}GB"
echo "  Network:        $NETWORK_MODE"
echo "  SSH Keys:       $SSH_KEYS"
echo ""
read -p "Deploy? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Download Terraform files
echo ""
echo "Downloading Terraform configuration..."
mkdir -p /tmp/xai-do
cd /tmp/xai-do

curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/digitalocean/main.tf -o main.tf

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
do_token     = "$(doctl auth list --format Token --no-header)"
region       = "$REGION"
droplet_size = "$DROPLET_SIZE"
volume_size  = $VOLUME_SIZE
network_mode = "$NETWORK_MODE"
ssh_keys     = $SSH_KEY_ARRAY
EOF

# Initialize and deploy
echo ""
echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning deployment..."
terraform plan

echo ""
echo "Deploying infrastructure..."
terraform apply -auto-approve

# Get outputs
DROPLET_IP=$(terraform output -raw droplet_ip)
API_URL=$(terraform output -raw api_url)
EXPLORER_URL=$(terraform output -raw explorer_url)

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Node Details:"
echo "  Droplet IP:     $DROPLET_IP"
echo "  API:            $API_URL"
echo "  Explorer:       $EXPLORER_URL"
echo ""
echo "SSH Access:"
echo "  ssh root@$DROPLET_IP"
echo ""
echo "The node is starting. Wait 2-3 minutes before accessing."
echo ""
echo "Monitor logs:"
echo "  ssh root@$DROPLET_IP 'docker logs -f xai-testnet-bootstrap'"
echo ""
echo "To destroy:"
echo "  cd /tmp/xai-do && terraform destroy"
echo ""
