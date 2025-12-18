# XAI Node - AWS Deployment

Deploy a production XAI blockchain node on AWS with one command.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/deploy.sh | bash
```

## Prerequisites

- AWS CLI installed and configured
- AWS account with EC2 permissions
- SSH key pair created in target region

## Manual Deployment

1. Download the template:
```bash
wget https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/aws/cloudformation.yaml
```

2. Deploy via AWS Console:
   - Go to CloudFormation
   - Create Stack
   - Upload `cloudformation.yaml`
   - Fill in parameters
   - Create

3. Or deploy via CLI:
```bash
aws cloudformation create-stack \
  --stack-name xai-node \
  --template-body file://cloudformation.yaml \
  --parameters \
    ParameterKey=InstanceType,ParameterValue=t3.large \
    ParameterKey=KeyName,ParameterValue=my-key \
    ParameterKey=VolumeSize,ParameterValue=100 \
    ParameterKey=NetworkMode,ParameterValue=testnet \
  --capabilities CAPABILITY_IAM
```

## Resources Created

- **EC2 Instance**: Ubuntu 22.04 with Docker
- **EBS Volume**: Encrypted gp3 storage
- **Security Group**: Ports 22, 8080, 8333, 9090, 3000
- **Elastic IP**: Static public IP
- **IAM Role**: CloudWatch and SSM access

## Costs

Estimated monthly cost (us-east-1):
- t3.large: ~$60
- 100GB gp3: ~$8
- Elastic IP: Free (when attached)
- Data transfer: Variable

**Total: ~$70-100/month**

## Access

After deployment (wait 5 minutes):
```bash
# SSH
ssh -i your-key.pem ubuntu@<public-ip>

# API
curl http://<public-ip>:8080/health

# Explorer
http://<public-ip>:3000
```

## Monitoring

```bash
# View logs
ssh ubuntu@<ip> 'docker logs -f xai-testnet-bootstrap'

# Check status
ssh ubuntu@<ip> 'docker ps'
```

## Cleanup

```bash
aws cloudformation delete-stack --stack-name xai-node
```

## Custom Configuration

Edit environment variables in UserData section of CloudFormation template.

## Support

- GitHub: https://github.com/xai-blockchain/xai
- Docs: https://docs.xai-blockchain.io
