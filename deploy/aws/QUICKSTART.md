# XAI Testnet - AWS Quick Start Guide

## 🚀 Deploy in 5 Minutes

### Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install Terraform
wget https://releases.hashicorp.com/terraform/1.6.4/terraform_1.6.4_linux_amd64.zip
unzip terraform_1.6.4_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Configure AWS credentials
aws configure
```

### Deploy Testnet
```bash
# Clone repository
cd xai-blockchain/deploy/aws

# Run automated deployment
chmod +x deploy-testnet.sh
./deploy-testnet.sh
```

That's it! The script will:
1. ✅ Initialize Terraform
2. ✅ Create AWS infrastructure
3. ✅ Deploy 4 blockchain nodes across 3 regions
4. ✅ Configure load balancer and monitoring
5. ✅ Run health checks

### Get Your Endpoints
```bash
cd terraform
terraform output deployment_info
```

### Test the Testnet
```bash
# Set your API endpoint
export API_ENDPOINT=$(cd terraform && terraform output -raw api_endpoint)

# Create a wallet
curl -X POST $API_ENDPOINT/wallet/create

# Request test tokens
curl -X POST $API_ENDPOINT/faucet \
  -H "Content-Type: application/json" \
  -d '{"address": "YOUR_ADDRESS", "amount": 100}'

# Start mining
curl -X POST $API_ENDPOINT/mining/start \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "YOUR_ADDRESS", "intensity": "medium"}'
```

### Access Block Explorer
```bash
echo "Block Explorer: $API_ENDPOINT/explorer"
```

Open the URL in your browser!

### Monitor Your Testnet
```bash
# View real-time logs
aws logs tail /aws/ec2/xai-testnet --follow

# Check node health
curl $API_ENDPOINT/health | jq .

# View metrics
curl $API_ENDPOINT/metrics
```

### Teardown (When Done)
```bash
cd terraform
terraform destroy
```

## 📊 What You Get

- **4 Blockchain Nodes** across 3 AWS regions
- **Load-Balanced API** for high availability
- **Block Explorer** web interface
- **Faucet Service** for test tokens
- **Monitoring Dashboard** with Prometheus/Grafana
- **CloudWatch Integration** for logs and metrics
- **Multi-Region Setup** for realistic network testing

## 💰 Cost Estimate

- **With Spot Instances**: ~$85/month
- **With On-Demand**: ~$165/month

## 📚 Next Steps

1. Read full guide: [TESTNET_DEPLOYMENT_GUIDE.md](TESTNET_DEPLOYMENT_GUIDE.md)
2. API documentation: `../../docs/API_REFERENCE.md`
3. Join community: https://discord.gg/xai-blockchain

## ❓ Need Help?

- Discord: https://discord.gg/xai-blockchain
- Email: support@xai.io

---

**Ready to deploy?** Run `./deploy-testnet.sh` now!
