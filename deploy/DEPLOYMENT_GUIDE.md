# XAI Blockchain Deployment Guide

Complete guide for deploying XAI Blockchain to production, staging, and development environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Application Deployment](#application-deployment)
5. [Verification and Health Checks](#verification-and-health-checks)
6. [Rollback Procedures](#rollback-procedures)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# Terraform (>= 1.5.0)
terraform --version

# Ansible (>= 2.10)
ansible --version

# AWS CLI (>= 2.0)
aws --version

# Docker (>= 20.10)
docker --version

# kubectl (for Kubernetes deployments)
kubectl version --client
```

### AWS Account Setup

1. Create AWS account with appropriate IAM permissions
2. Configure AWS credentials:
   ```bash
   aws configure
   ```
3. Create S3 bucket for Terraform state:
   ```bash
   aws s3 mb s3://xai-terraform-state-$(aws sts get-caller-identity --query Account --output text)
   ```
4. Create DynamoDB table for Terraform locks:
   ```bash
   aws dynamodb create-table \
     --table-name terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

### Network Configuration

- VPC CIDR: 10.0.0.0/16
- Public Subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
- Private Subnets: 10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24
- Database Port: 5432
- Redis Port: 6379
- Node P2P Port: 8333
- API Port: 8080

## Environment Setup

### 1. Clone Repository

```bash
cd xai-blockchain
```

### 2. Configure Environment Variables

#### Production Environment

```bash
# Create production environment file
cp .env.example .env.production

# Edit with production values
cat > .env.production << EOF
# Environment
ENVIRONMENT=production
DEPLOYMENT_VERSION=1.0.0

# P2P Security (mainnet validator profile)
XAI_NETWORK=mainnet
XAI_PEER_REQUIRE_CLIENT_CERT=1
# sha256 fingerprints (hex, comma-separated)
XAI_TRUSTED_PEER_CERT_FPS=abc123...,def456...
# hex secp256k1 pubkeys (compressed form)
XAI_TRUSTED_PEER_PUBKEYS=02abcd...,03ef01...
XAI_PEER_NONCE_TTL_SECONDS=90
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Database
POSTGRES_HOST=xai-db.c5rp6z8qq8ql.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=xai_blockchain
POSTGRES_USER=xaiadmin
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis
REDIS_HOST=xai-redis.abcdefg.ng.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=$(openssl rand -base64 32)

# Blockchain Network
NETWORK_ID=0x5841
NETWORK_NAME=mainnet
MIN_PEERS=10
MAX_PEERS=500

# P2P Security (mainnet validator profile)
XAI_PEER_REQUIRE_CLIENT_CERT=1
XAI_TRUSTED_PEER_CERT_FPS=abc123...,def456...   # sha256 fingerprints
XAI_TRUSTED_PEER_PUBKEYS=02abcd...,03ef01...    # hex secp256k1 pubkeys
XAI_PEER_NONCE_TTL_SECONDS=90
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt

# Monitoring
MONITORING_ENABLED=true
ALERT_EMAIL=ops-team@company.internal
EOF
```

#### Staging Environment

```bash
cp .env.example .env.staging

cat > .env.staging << EOF
ENVIRONMENT=staging
DEPLOYMENT_VERSION=1.0.0-rc.1
AWS_REGION=us-east-1
POSTGRES_HOST=staging-db.internal
NETWORK_ID=0xABCD
NETWORK_NAME=testnet
MIN_PEERS=3
MAX_PEERS=50

# P2P Security (public seeder/testnet)
XAI_PEER_REQUIRE_CLIENT_CERT=0
XAI_TRUSTED_PEER_CERT_FPS=
XAI_TRUSTED_PEER_PUBKEYS=
XAI_PEER_NONCE_TTL_SECONDS=180
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
EOF
```

### 3. Configure Terraform Variables

```bash
cd deploy/terraform

# Copy environment-specific tfvars
cp terraform.tfvars.example environments/production.tfvars

# Edit production.tfvars
cat > environments/production.tfvars << EOF
aws_region = "us-east-1"
project_name = "xai-blockchain"
environment = "production"

vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

postgres_db_name = "xai_blockchain"
postgres_username = "xaiadmin"
postgres_password = "your-secure-password"
postgres_engine_version = "15.3"
rds_instance_class = "db.r6g.xlarge"
rds_instance_count = 2

redis_node_type = "cache.r6g.xlarge"
redis_cluster_size = 3
redis_engine_version = "7.0"

ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/your-cert-id"
alert_email = "ops-team@company.internal"

tags = {
  Project = "XAI Blockchain"
  Owner = "Platform Team"
  CostCenter = "Engineering"
}
EOF
```

## Infrastructure Deployment

### 1. Terraform Plan

```bash
cd deploy/terraform

# Initialize Terraform
terraform init \
  -backend-config="bucket=xai-terraform-state-123456789012" \
  -backend-config="key=production/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=terraform-locks"

# Review plan
terraform plan \
  -var-file="environments/production.tfvars" \
  -out=tfplan

# Show plan details
terraform show tfplan
```

### 2. Terraform Apply

```bash
# Apply infrastructure changes
terraform apply tfplan

# Save outputs
terraform output -json > ../infrastructure-outputs.json

# Display key outputs
terraform output -json | jq '.alb_dns_name, .rds_endpoint, .redis_endpoint'
```

### 3. Verify Infrastructure

```bash
# Check VPC creation
aws ec2 describe-vpcs --filters Name=tag:Project,Values=XAI | jq '.Vpcs[0].VpcId'

# Check RDS cluster
aws rds describe-db-clusters --db-cluster-identifier xai-blockchain-db-cluster

# Check ElastiCache
aws elasticache describe-replication-groups --replication-group-id xai-blockchain-redis-cluster

# Check ALB
aws elbv2 describe-load-balancers --names xai-blockchain-alb
```

## Application Deployment

### 1. Prepare Ansible Inventory

```bash
cd deploy/ansible

# Update inventory with actual IP addresses
cat > inventory/production.yml << EOF
all:
  vars:
    environment: production
    deployment_version: "1.0.0"
    postgres_host: "$(terraform output -raw rds_endpoint)"
    redis_host: "$(terraform output -raw redis_endpoint)"

  children:
    blockchain-nodes:
      hosts:
        blockchain-node-1:
          ansible_host: 10.0.1.10
        blockchain-node-2:
          ansible_host: 10.0.2.10
        blockchain-node-3:
          ansible_host: 10.0.3.10
EOF
```

### 2. Run Ansible Deployment

```bash
# Validate playbook syntax
ansible-playbook --syntax-check site.yml -i inventory/production.yml

# Run in check mode (dry run)
ansible-playbook site.yml -i inventory/production.yml --check -v

# Execute deployment
ansible-playbook site.yml \
  -i inventory/production.yml \
  -e "environment=production" \
  -e "deployment_version=1.0.0" \
  -v \
  --extra-vars @/path/to/.env.production
```

### 3. Automated Deployment Script

```bash
# Run complete deployment with error handling
bash deploy/scripts/deploy.sh production 1.0.0

# Monitor deployment
tail -f deploy.log
```

## Verification and Health Checks

### 1. Post-Deployment Health Checks

```bash
# Run comprehensive health checks
bash deploy/scripts/health-check.sh

# Expected output:
# ✓ Disk space: 500GB available
# ✓ Memory: 32GB available
# ✓ Blockchain node is running
# ✓ API endpoint is responding
# ✓ PostgreSQL database is accessible
# ✓ Redis is accessible
# ✓ All health checks passed!
```

### 2. Manual Verification

```bash
# Test API endpoint
curl -v http://localhost:8080/health
curl -s http://localhost:8080/api/v1/network/info | jq .

# Check blockchain status
curl -s http://localhost:8080/api/v1/blockchain/info | jq '.is_synced, .block_height'

# Verify database
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c "SELECT version();"

# Check Redis connectivity
redis-cli -h xai-redis.internal ping

# Monitor logs
docker logs xai-node -f
journalctl -u xai-node -f
```

### 3. Smoke Tests

```bash
# Run quick validation tests
pytest tests/smoke -v

# Load testing
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

## Rollback Procedures

### Automatic Rollback

```bash
# Execute rollback script with pre-deployment backups
bash deploy/scripts/rollback.sh /var/backups/pre-deployment

# Verify rollback completion
bash deploy/scripts/health-check.sh
```

### Manual Rollback via Terraform

```bash
cd deploy/terraform

# Show current state
terraform show

# Destroy specific resources
terraform destroy -target=aws_rds_cluster.main
terraform destroy -target=aws_elasticache_replication_group.main

# Full infrastructure rollback
terraform destroy -var-file="environments/production.tfvars"
```

### Manual Rollback via Docker

```bash
# Stop current containers
docker-compose down

# Restore previous image
docker tag xai-blockchain:v0.9.9 xai-blockchain:latest

# Start previous version
docker-compose up -d

# Verify
docker-compose logs xai-node
```


Trigger rollback workflow:

```bash
gh workflow run rollback.yml \
  -f environment=production \
  -f backup_directory=/var/backups/pre-deployment
```

## Monitoring and Maintenance

### Prometheus Monitoring

```bash
# Access Prometheus
open http://localhost:9091

# Query blockchain metrics
curl -s 'http://localhost:9091/api/v1/query?query=blockchain_height'

# Create alert rule
cat > /opt/prometheus/alert-rules.yml << EOF
groups:
  - name: blockchain
    rules:
      - alert: BlockHeightNotIncreasing
        expr: increase(blockchain_height[5m]) == 0
        for: 10m
        annotations:
          summary: "Block height not increasing"
EOF
```

### Grafana Dashboards

1. Navigate to http://localhost:3000
2. Login with default credentials (admin/admin)
3. Add Prometheus datasource
4. Import XAI dashboards from `deploy/ansible/roles/monitoring/files/dashboards/`

### Database Maintenance

```bash
# Backup database
pg_dump -h xai-db.internal -U xaiadmin xai_blockchain | \
  gzip > backup-$(date +%Y%m%d).sql.gz

# Restore database
gunzip -c backup-20231125.sql.gz | \
  psql -h xai-db.internal -U xaiadmin xai_blockchain

# Optimize tables
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c "VACUUM ANALYZE;"
```

### Cache Management

```bash
# Check Redis memory
redis-cli -h xai-redis.internal info memory

# Clear cache (if needed)
redis-cli -h xai-redis.internal FLUSHDB

# Monitor slow queries
redis-cli -h xai-redis.internal slowlog get 10
```

## Troubleshooting

### Issue: Blockchain Node Not Starting

```bash
# Check service status
systemctl status xai-node

# View logs
journalctl -u xai-node -n 50 --no-pager

# Check network connectivity
netstat -tuln | grep 8333
ss -tuln | grep 8080

# Verify database connection
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c "SELECT 1;"
```

### Issue: API Endpoints Not Responding

```bash
# Check if service is running
curl -v http://localhost:8080/health

# Inspect Docker container
docker logs xai-node

# Check resource limits
docker stats xai-node

# Restart service
systemctl restart xai-node
docker restart xai-node
```

### Issue: Database Connection Failures

```bash
# Test RDS connectivity
psql -h <rds-endpoint> -U xaiadmin -d xai_blockchain -c "SELECT version();"

# Check RDS instance status
aws rds describe-db-clusters --query "DBClusters[0].Status"

# Monitor RDS events
aws rds describe-events --source-type db-cluster --max-records 10
```

### Issue: High Resource Usage

```bash
# Check system resources
free -h
df -h
top

# Check Docker resource usage
docker stats --no-stream

# Monitor application metrics
curl -s http://localhost:9090/api/v1/query?query=process_resident_memory_bytes | jq .

# Scale up if needed
terraform apply -var="rds_instance_count=3"
```

## Additional Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Ansible Documentation](https://docs.ansible.com)
- [AWS Documentation](https://docs.aws.amazon.com)
- [XAI Blockchain Documentation](../docs)
- [Security Best Practices](./SECURITY.md)
- [Disaster Recovery Plan](./DISASTER_RECOVERY.md)

## Support and Escalation

For deployment issues:

1. **Check logs**: Review deployment logs in `deploy.log`
2. **Review backup**: Ensure backups were created successfully
3. **Contact on-call**: Escalate to infrastructure team if needed
5. **Rollback if necessary**: Execute rollback procedures

## Change Log

- **2024-01-XX**: Initial deployment guide created
- **2024-02-XX**: Added Kubernetes deployment examples
- **2024-03-XX**: Added disaster recovery procedures
