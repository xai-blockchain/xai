#!/bin/bash
#
# XAI Blockchain Node - AWS One-Liner Deployment
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
#   OR
#   bash deploy.sh
#

set -e

echo "========================================"
echo "XAI Blockchain Node - AWS Deployment"
echo "========================================"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not installed"
    echo "Install: https://aws.amazon.com/cli/"
    exit 1
fi

# Check for credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

# Get parameters
read -p "Stack name [xai-node]: " STACK_NAME
STACK_NAME=${STACK_NAME:-xai-node}

read -p "AWS Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

read -p "EC2 Instance Type [t3.large]: " INSTANCE_TYPE
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.large}

read -p "EBS Volume Size (GB) [100]: " VOLUME_SIZE
VOLUME_SIZE=${VOLUME_SIZE:-100}

read -p "Network Mode (testnet/mainnet) [testnet]: " NETWORK_MODE
NETWORK_MODE=${NETWORK_MODE:-testnet}

# SSH Key
echo ""
echo "Available SSH keys:"
aws ec2 describe-key-pairs --region $AWS_REGION --query 'KeyPairs[*].KeyName' --output table

read -p "SSH Key Name: " KEY_NAME
if [ -z "$KEY_NAME" ]; then
    echo "Error: SSH key name required"
    exit 1
fi

# Confirm
echo ""
echo "Deployment Configuration:"
echo "  Stack Name:     $STACK_NAME"
echo "  Region:         $AWS_REGION"
echo "  Instance Type:  $INSTANCE_TYPE"
echo "  Volume Size:    ${VOLUME_SIZE}GB"
echo "  Network:        $NETWORK_MODE"
echo "  SSH Key:        $KEY_NAME"
echo ""
read -p "Deploy? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Download CloudFormation template
echo ""
echo "Downloading CloudFormation template..."
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/cloudformation.yaml -o /tmp/xai-cf.yaml

# Deploy stack
echo ""
echo "Creating CloudFormation stack..."
aws cloudformation create-stack \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --template-body file:///tmp/xai-cf.yaml \
    --parameters \
        ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE \
        ParameterKey=KeyName,ParameterValue=$KEY_NAME \
        ParameterKey=VolumeSize,ParameterValue=$VOLUME_SIZE \
        ParameterKey=NetworkMode,ParameterValue=$NETWORK_MODE \
    --capabilities CAPABILITY_IAM

echo ""
echo "Stack creation initiated. Waiting for completion..."
echo "This will take 5-10 minutes..."

aws cloudformation wait stack-create-complete \
    --stack-name $STACK_NAME \
    --region $AWS_REGION

# Get outputs
echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""

PUBLIC_IP=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIURL`].OutputValue' \
    --output text)

EXPLORER_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ExplorerURL`].OutputValue' \
    --output text)

echo "Node Details:"
echo "  Public IP:      $PUBLIC_IP"
echo "  API:            $API_URL"
echo "  Explorer:       $EXPLORER_URL"
echo ""
echo "SSH Access:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""
echo "The node is starting. Wait 2-3 minutes before accessing."
echo ""
echo "Monitor logs:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP 'docker logs -f xai-testnet-bootstrap'"
echo ""
echo "To delete:"
echo "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION"
echo ""
