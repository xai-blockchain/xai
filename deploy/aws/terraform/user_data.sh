#!/bin/bash
# XAI Blockchain Node Bootstrap Script
# This script runs on EC2 instance launch

set -e

# Logging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== XAI Blockchain Node Bootstrap Starting ==="
echo "Node: ${node_name}"
echo "Region: ${region}"
echo "Timestamp: $(date)"

# Update system
apt-get update
apt-get upgrade -y

# Install dependencies (DEFECT-009 fix: python3.11-venv for Python 3.11)
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    docker.io \
    docker-compose \
    awscli \
    jq \
    curl \
    wget \
    htop \
    net-tools

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Create application directory
mkdir -p /opt/xai
cd /opt/xai

# FIX DEFECT-002 & DEFECT-004: Download code from S3 and run directly
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="xai-testnet-deploy-artifacts-$AWS_ACCOUNT_ID"
aws s3 cp "s3://$S3_BUCKET/xai-blockchain-v1.0.0.tar.gz" /tmp/xai-blockchain.tar.gz
tar -xzf /tmp/xai-blockchain.tar.gz -C /opt/xai
rm /tmp/xai-blockchain.tar.gz

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies directly (skip pip install -e .) - FIX DEFECT-007
pip install --upgrade pip
pip install flask flask-cors flask-sock requests cryptography pyyaml prometheus-client

# Create blockchain data directory
mkdir -p /var/lib/xai/blockchain_data
chown -R ubuntu:ubuntu /var/lib/xai

# Configure node (FIX DEFECT-005 & DEFECT-006: Port + Host binding)
cat > /opt/xai/.env <<EOF
NODE_NAME=${node_name}
REGION=${region}
P2P_PORT=8333
XAI_DEFAULT_HOST=0.0.0.0
XAI_DEFAULT_PORT=5000
XAI_API_PORT=5000
DATA_DIR=/var/lib/xai/blockchain_data
XAI_NETWORK=testnet
LOG_LEVEL=INFO
ENABLE_MINING=true
ENABLE_API=true
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
EOF

# Create systemd service for blockchain node
cat > /etc/systemd/system/xai-node.service <<EOF
[Unit]
Description=XAI Blockchain Node
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/xai
Environment=PATH=/opt/xai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/xai/src
EnvironmentFile=/opt/xai/.env
ExecStart=/opt/xai/venv/bin/python3.11 -m xai.core.node
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=xai-node

[Install]
WantedBy=multi-user.target
EOF

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/xai/*.log",
            "log_group_name": "/aws/ec2/xai-testnet",
            "log_stream_name": "${node_name}-{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "XAI/Testnet",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# Get bootstrap peers from Parameter Store (if available)
BOOTSTRAP_PEERS=$(aws ssm get-parameter --name "/xai/testnet/bootstrap-peers" --query "Parameter.Value" --output text 2>/dev/null || echo "")

if [ -n "$BOOTSTRAP_PEERS" ]; then
    echo "BOOTSTRAP_PEERS=$BOOTSTRAP_PEERS" >> /opt/xai/.env
fi

# Set ownership
chown -R ubuntu:ubuntu /opt/xai

# Enable and start the service
systemctl daemon-reload
systemctl enable xai-node
systemctl start xai-node

# Wait for node to start
sleep 10

# Check node status
systemctl status xai-node --no-pager

# Get node info and register with Parameter Store
NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Store node information
aws ssm put-parameter \
    --name "/xai/testnet/nodes/${node_name}" \
    --value "{\"ip\":\"$NODE_IP\",\"instance_id\":\"$INSTANCE_ID\",\"region\":\"${region}\"}" \
    --type String \
    --overwrite \
    --region ${region}

echo "=== XAI Blockchain Node Bootstrap Complete ==="
echo "Node IP: $NODE_IP"
echo "Instance ID: $INSTANCE_ID"
echo "Check status: systemctl status xai-node"
echo "View logs: journalctl -u xai-node -f"
