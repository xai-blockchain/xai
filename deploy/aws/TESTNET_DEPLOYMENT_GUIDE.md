# XAI Blockchain Testnet - AWS Deployment Guide

## Overview

This guide walks you through deploying the XAI blockchain testnet on AWS infrastructure using Terraform.

## Architecture

### Multi-Region Deployment
- **Primary Region (us-east-1)**: 2 nodes
- **EU Region (eu-west-1)**: 1 node
- **Asia Region (ap-southeast-1)**: 1 node

### Components
1. **Blockchain Nodes** - EC2 instances running blockchain software
2. **Application Load Balancer** - Distributes API traffic
3. **VPC Network** - Isolated network per region
4. **Monitoring Stack** - Prometheus + Grafana + CloudWatch
5. **Block Explorer** - Web interface for blockchain data
6. **Faucet Service** - Dispenses test tokens

## Prerequisites

### Required Tools
- AWS CLI (v2.x)
- Terraform (v1.5+)
- jq (for JSON processing)

### AWS Account Setup
1. **Create IAM user** with these permissions:
   - EC2 Full Access
   - VPC Full Access
   - IAM Full Access
   - CloudWatch Full Access
   - Systems Manager Full Access
   - S3 Access (for Terraform state)

2. **Configure AWS CLI**:
   ```bash
   aws configure
   ```

3. **Verify access**:
   ```bash
   aws sts get-caller-identity
   ```

## Deployment Steps

### 1. Clone Repository
```bash
cd xai-blockchain/deploy/aws
```

### 2. Review Configuration
Edit `terraform/variables.tf` to customize:
- Instance types
- Region selection
- SSH access IPs
- Cost optimization settings

### 3. Initialize Terraform
```bash
cd terraform
terraform init
```

### 4. Plan Deployment
```bash
terraform plan -out=tfplan
```

Review the plan carefully. Expected resources:
- 4 EC2 instances (nodes)
- 3 VPCs (multi-region)
- 1 Application Load Balancer
- Security groups, IAM roles, etc.

### 5. Deploy Infrastructure
```bash
terraform apply tfplan
```

This takes ~10-15 minutes.

### 6. Alternative: Automated Deployment
```bash
chmod +x deploy-testnet.sh
./deploy-testnet.sh
```

## Post-Deployment

### Verify Deployment

1. **Check API Health**:
   ```bash
   API_ENDPOINT=$(terraform output -raw api_endpoint)
   curl $API_ENDPOINT/health
   ```

2. **View Blockchain Info**:
   ```bash
   curl $API_ENDPOINT/blockchain/info | jq .
   ```

3. **List Connected Peers**:
   ```bash
   curl $API_ENDPOINT/peers | jq .
   ```

### Access Services

```bash
# Get all endpoints
terraform output deployment_info

# Services available:
API_ENDPOINT=$(terraform output -raw api_endpoint)
echo "Block Explorer: $API_ENDPOINT/explorer"
echo "Faucet: $API_ENDPOINT/faucet"
echo "Metrics: $API_ENDPOINT/metrics"
echo "API Docs: $API_ENDPOINT/docs"
```

### Monitor Nodes

1. **CloudWatch Logs**:
   ```bash
   aws logs tail /aws/ec2/xai-testnet --follow
   ```

2. **SSH to Node** (if needed):
   ```bash
   # Get instance ID
   aws ec2 describe-instances \
       --filters "Name=tag:Name,Values=xai-node-primary" \
       --query "Reservations[].Instances[].InstanceId" \
       --output text

   # Connect via SSM (no SSH key needed)
   aws ssm start-session --target i-xxxxxxxxxxxxx

   # Or traditional SSH
   ssh -i your-key.pem ubuntu@<node-ip>
   ```

3. **View Node Logs**:
   ```bash
   # After SSH'ing to node
   sudo journalctl -u xai-node -f
   ```

### Using the Testnet

#### Request Test Tokens
```bash
curl -X POST $API_ENDPOINT/faucet \
    -H "Content-Type: application/json" \
    -d '{"address": "YOUR_WALLET_ADDRESS", "amount": 100}'
```

#### Create Wallet
```bash
curl -X POST $API_ENDPOINT/wallet/create | jq .
```

#### Send Transaction
```bash
curl -X POST $API_ENDPOINT/transaction \
    -H "Content-Type: application/json" \
    -d '{
      "sender": "SENDER_ADDRESS",
      "receiver": "RECEIVER_ADDRESS",
      "amount": 10.0,
      "private_key": "YOUR_PRIVATE_KEY"
    }'
```

#### Mine Blocks
```bash
curl -X POST $API_ENDPOINT/mining/start \
    -H "Content-Type: application/json" \
    -d '{"miner_address": "YOUR_ADDRESS", "intensity": "medium"}'
```

## Cost Estimates

### Monthly Costs (Approximate)

| Resource | Quantity | Unit Cost | Total |
|----------|----------|-----------|-------|
| t3.medium EC2 (On-Demand) | 4 | $30/month | $120 |
| t3.medium EC2 (Spot) | 4 | $10/month | $40 |
| EBS Storage (50GB) | 4 | $5/month | $20 |
| Data Transfer | - | $5/month | $5 |
| Load Balancer | 1 | $20/month | $20 |
| **Total (On-Demand)** | | | **$165/month** |
| **Total (Spot)** | | | **$85/month** |

### Cost Optimization Tips
1. Enable spot instances in `variables.tf`
2. Use smaller instance types for low-traffic testing
3. Stop nodes when not needed:
   ```bash
   aws autoscaling set-desired-capacity \
       --auto-scaling-group-name xai-nodes-primary-asg \
       --desired-capacity 0
   ```
4. Delete unused EBS snapshots
5. Use CloudWatch billing alarms

## Troubleshooting

### Nodes Not Starting
```bash
# Check user-data execution
aws ec2 get-console-output --instance-id i-xxxxx

# View bootstrap logs
ssh ubuntu@<node-ip>
sudo cat /var/log/user-data.log
```

### Nodes Not Syncing
```bash
# Check P2P connectivity
telnet <node-ip> 8333

# Verify bootstrap peers
curl $API_ENDPOINT/peers
```

### API Not Responding
```bash
# Check load balancer health
aws elbv2 describe-target-health \
    --target-group-arn <tg-arn>

# Check security groups
aws ec2 describe-security-groups \
    --group-ids <sg-id>
```

### High Costs
```bash
# View current spending
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost

# Set billing alarm
aws cloudwatch put-metric-alarm \
    --alarm-name xai-billing-alarm \
    --alarm-description "Alert if spending exceeds $100" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 21600 \
    --evaluation-periods 1 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold
```

## Maintenance

### Update Node Software
```bash
# SSH to each node
ssh ubuntu@<node-ip>

# Pull latest code
cd /opt/xai

# Restart service
sudo systemctl restart xai-node
```

### Backup Blockchain Data
```bash
# Create EBS snapshot
aws ec2 create-snapshot \
    --volume-id vol-xxxxx \
    --description "XAI blockchain backup $(date +%Y%m%d)"
```

### Scale Nodes
```bash
# Increase node count
aws autoscaling set-desired-capacity \
    --auto-scaling-group-name xai-nodes-primary-asg \
    --desired-capacity 3
```

## Teardown

### Destroy Infrastructure
```bash
cd terraform
terraform destroy
```

**Warning**: This deletes all resources including blockchain data!

### Preserve Blockchain Data
Before destroying:
1. Create EBS snapshots
2. Export blockchain data:
   ```bash
   ssh ubuntu@<node-ip>
   tar -czf blockchain-backup.tar.gz /var/lib/xai/blockchain_data
   aws s3 cp blockchain-backup.tar.gz s3://your-backup-bucket/
   ```

## Security Best Practices

1. **Restrict SSH Access**: Update `ssh_allowed_ips` in variables.tf
2. **Enable Encryption**: EBS volumes encrypted by default
3. **Use IAM Roles**: No hardcoded credentials
4. **Enable VPC Flow Logs**: Monitor network traffic
5. **Regular Updates**: Keep OS and dependencies updated
6. **Monitoring**: Set up CloudWatch alarms
7. **Backup Strategy**: Regular EBS snapshots

## Support

### Documentation
- Main Docs: `../../docs/`
- API Reference: `../../docs/API_REFERENCE.md`
- Architecture: `../../docs/ARCHITECTURE.md`

### Getting Help
- Discord: https://discord.gg/xai-blockchain
- Email: support@xai.io

## Next Steps

1. ✅ Deploy testnet
2. 📝 Read [Testnet User Guide](../../docs/TESTNET_USER_GUIDE.md)
3. 🧪 Run integration tests
4. 📊 Monitor performance metrics
5. 🐛 Report issues
6. 🚀 Prepare for mainnet

---

**Deployed**: $(date)
**Version**: 1.0.0-testnet
**Network**: XAI Testnet
