# XAI Blockchain - Production Deployment


## 📋 Directory Structure

```
deploy/
├── terraform/                      # Infrastructure-as-Code
│   ├── main.tf                     # Core infrastructure definition
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # Output values
│   └── environments/               # Environment-specific configurations
│       ├── production.tfvars
│       ├── staging.tfvars
│       └── development.tfvars
│
├── ansible/                        # Configuration Management
│   ├── site.yml                    # Main playbook
│   ├── inventory/                  # Environment inventories
│   │   ├── production.yml
│   │   ├── staging.yml
│   │   └── development.yml
│   └── roles/                      # Ansible roles
│       ├── system-hardening/       # OS hardening
│       ├── docker/                 # Docker installation
│       ├── blockchain-node/        # Blockchain deployment
│       ├── explorer/               # Block explorer
│       ├── monitoring/             # Prometheus & Grafana
│       ├── backup/                 # Backup configuration
│       └── firewall/               # Firewall setup
│
├── scripts/                        # Deployment Scripts
│   ├── deploy.sh                   # Main deployment script
│   ├── rollback.sh                 # Rollback script
│   ├── health-check.sh             # Health verification
│   └── backup.sh                   # Backup utilities
│
├── DEPLOYMENT_GUIDE.md             # Complete deployment instructions
├── ROLLBACK_PROCEDURE.md           # Emergency rollback procedures
├── DISASTER_RECOVERY.md            # Disaster recovery plan
├── RUNBOOK.md                      # Operations runbook
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites

```bash
# Required tools
terraform --version          # >= 1.5.0
ansible --version           # >= 2.10
aws --version              # >= 2.0
docker --version           # >= 20.10
```

### Minimal Deployment

```bash
# 1. Clone repository
cd xai-blockchain

# 2. Configure environment
export ENVIRONMENT=production
export DEPLOYMENT_VERSION=1.0.0
source .env.production

# 3. Deploy infrastructure
cd deploy/terraform
terraform init -upgrade
terraform apply -var-file="environments/production.tfvars"

# 4. Deploy application
cd ../ansible
ansible-playbook -i inventory/production.yml site.yml

# 5. Run health checks
cd ../scripts
bash health-check.sh
```

## 📚 Documentation

### Getting Started

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete step-by-step deployment guide
  - Environment setup
  - Infrastructure deployment
  - Application deployment
  - Verification procedures

### Operations

- **[RUNBOOK.md](./RUNBOOK.md)** - Daily operations guide
  - Service management
  - Monitoring and alerting
  - Database operations
  - Scaling procedures
  - Troubleshooting

### Emergency Procedures

- **[ROLLBACK_PROCEDURE.md](./ROLLBACK_PROCEDURE.md)** - Emergency rollback
  - Automated rollback
  - Manual rollback steps
  - Verification procedures
  - Post-incident communication

- **[DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md)** - Disaster recovery
  - Recovery objectives (RTO/RPO)
  - Backup strategy
  - Disaster scenarios
  - Multi-region failover

## 🏗️ Infrastructure Components

### AWS Services

| Service | Purpose | Sizing |
|---------|---------|--------|
| **VPC** | Network isolation | 10.0.0.0/16 |
| **ALB** | Load balancing | Auto-scaling |
| **ECS Fargate** | Container orchestration | t3.large |
| **RDS Aurora** | PostgreSQL database | db.r6g.xlarge (2 instances) |
| **ElastiCache** | Redis cluster | cache.r6g.xlarge (3 nodes) |
| **S3** | Backup storage | Encrypted, versioned |
| **CloudWatch** | Monitoring | 30-day retention |
| **KMS** | Encryption | AWS managed keys |

### Application Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Blockchain Node** | Python 3.11 | Core consensus |
| **REST API** | Flask | HTTP endpoints |
| **WebSocket API** | Flask-SocketIO | Real-time updates |
| **Database** | PostgreSQL 15 | Transaction storage |
| **Cache** | Redis 7 | Session management |
| **Block Explorer** | Python/React | Web interface |
| **Monitoring** | Prometheus + Grafana | Observability |

## 🔧 Key Features

### Infrastructure-as-Code (Terraform)

```hcl
# Infrastructure is version-controlled and reproducible
terraform apply -var-file="environments/production.tfvars"

# Output connection information
terraform output -json | jq '.alb_dns_name, .rds_endpoint'

# Destroy when needed
terraform destroy -var-file="environments/production.tfvars"
```

### Configuration Management (Ansible)

```yaml
# Idempotent, replayable configurations
- name: Deploy Blockchain Node
  hosts: blockchain-nodes
  roles:
    - blockchain-node
    - monitoring
    - backup
```


```yaml
# Automated testing, building, and deployment
on:
  push:
    tags: 'v*.*.*'

jobs:
  build:
    # Build and test
  deploy-production:
    # Deploy to production
  verify-deployment:
    # Post-deployment validation
```

### Automated Backups

```bash
# Hourly database backups
0 * * * * /usr/local/bin/xai-backup-database

# 6-hourly blockchain backups
0 */6 * * * /usr/local/bin/xai-backup-blockchain

# S3 encryption and lifecycle policies
# 30-day retention in S3 standard
# Automatic archive to Glacier after 30 days
```

## 📊 Monitoring and Observability

### Prometheus Metrics

- Blockchain height and sync status
- Network peer count
- Transaction throughput
- API response times
- Database connection pool utilization
- System resources (CPU, memory, disk)

### Grafana Dashboards

- Blockchain Node Status
- Network Performance
- Database Performance
- System Resources
- Application Metrics

### Alerts

Configured for:
- High CPU/Memory usage
- Low disk space
- API errors
- Database connection issues
- Blockchain sync lag
- Network peer loss

## 🔐 Security

### Network Security

- **VPC isolation**: Private subnets for databases and caches
- **Security groups**: Fine-grained ingress/egress rules
- **ALB**: HTTPS only with SSL/TLS 1.2+
- **NAT gateway**: Secure outbound connectivity

### Data Security

- **Encryption at rest**: KMS for RDS, S3, Redis
- **Encryption in transit**: TLS for all connections
- **Database**: IAM authentication enabled
- **Backups**: Encrypted and versioned

### Access Control

- **IAM roles**: Least privilege permissions
- **SSH**: Key-based only (password auth disabled)
- **Secrets**: AWS Secrets Manager
- **Audit logging**: CloudTrail and VPC Flow Logs

### Compliance

- HIPAA-compliant backup procedures
- SOC 2 audit logging
- GDPR data retention policies
- Regular security scanning (Trivy, Checkov, Semgrep)

## 🎯 Deployment Modes

### Production

```bash
bash deploy/scripts/deploy.sh production 1.0.0

# Features:
# - Multi-AZ deployment
# - Database replication
# - Cache clustering
# - 30-day backup retention
# - CloudWatch monitoring
# - SSL certificates
```

### Staging

```bash
bash deploy/scripts/deploy.sh staging 1.0.0-rc.1

# Features:
# - Single-AZ (cost optimization)
# - Database replication
# - Cache replication
# - 7-day backup retention
# - Full monitoring
# - Testing enabled
```

### Development

```bash
bash deploy/scripts/deploy.sh development dev

# Features:
# - Minimal resources
# - Local database
# - Local cache
# - No backups
# - Debug logging
```

## 🔄 CI/CD Pipeline

### Workflows


1. **deploy-production.yml** - Production deployment on tag
   - Builds Docker images
   - Runs security scans
   - Validates infrastructure
   - Deploys to production
   - Runs smoke tests

2. **deploy-staging.yml** - Staging deployment on branch
   - Builds Docker images
   - Validates infrastructure
   - Deploys to staging
   - Runs integration tests

3. **rollback.yml** - Emergency rollback
   - Requires approval
   - Restores from backups
   - Verifies services
   - Creates incident ticket


```bash
# AWS
AWS_ROLE_TO_ASSUME
AWS_ROLE_TO_ASSUME_STAGING

# Terraform
TF_STATE_BUCKET
TF_STATE_BUCKET_STAGING

# Database
DB_HOST
DB_USER
DB_NAME

# Notifications
SLACK_WEBHOOK

# API
API_ID
```

## 📈 Scaling

### Horizontal Scaling (More Nodes)

```bash
# Add blockchain nodes
terraform apply -var="instance_count=4"

# Add read replicas
terraform apply -var="rds_instance_count=3"

# Scale cache cluster
terraform apply -var="redis_cluster_size=5"
```

### Vertical Scaling (Larger Instances)

```bash
# Upgrade RDS instance type
terraform apply -var="rds_instance_class=db.r6g.2xlarge"

# Upgrade cache node type
terraform apply -var="redis_node_type=cache.r6g.2xlarge"
```

## 🧪 Testing Deployment

### Pre-Deployment Validation

```bash
# Terraform validation
terraform plan -var-file="environments/production.tfvars"

# Ansible syntax check
ansible-playbook --syntax-check site.yml

# Configuration validation
ansible-playbook site.yml --check -v
```

### Post-Deployment Testing

```bash
# Health checks
bash scripts/health-check.sh

# Smoke tests
pytest tests/smoke -v

# Integration tests
pytest tests/integration -v

# Load testing
locust -f tests/load/locustfile.py
```

## 🆘 Troubleshooting

### Deployment Failures

```bash
# Review deployment logs
tail -f deploy.log

# Check Terraform state
terraform show

# View Ansible output
journalctl -u xai-node -f

# Check service status
systemctl status xai-node
docker-compose logs -f
```

### Service Issues

Refer to [RUNBOOK.md](./RUNBOOK.md) for:
- Service management
- Troubleshooting procedures
- Performance optimization
- Emergency escalation

### Emergency Rollback

```bash
# Automated rollback
bash scripts/rollback.sh /var/backups/pre-deployment

gh workflow run rollback.yml -f environment=production

# Manual procedures documented in
# [ROLLBACK_PROCEDURE.md](./ROLLBACK_PROCEDURE.md)
```

## 📞 Support

### Resources

- **Documentation**: See files in this directory
- **Discussions**: Technical questions and architecture
- **Wiki**: Team knowledge base

### On-Call Support

| Role | Escalation |
|------|-----------|
| Level 1 | Runbook procedures (30 min SLA) |
| Level 2 | Platform team (1 hour SLA) |
| Level 3 | Infrastructure lead (immediate) |
| Critical | All-hands (incident command) |

## 🗺️ Roadmap

Planned improvements:

- [ ] Kubernetes migration
- [ ] Multi-region active-active
- [ ] Automated capacity planning
- [ ] Enhanced security scanning
- [ ] Cost optimization
- [ ] Performance benchmarking
- [ ] Chaos engineering tests
- [ ] GraphQL API
- [ ] REST API v2

## 📄 License

MIT License - See LICENSE file in project root

## 🤝 Contributing

Contributing to deployment infrastructure:

2. Make changes and test
3. Run validation: `terraform validate`, `ansible-playbook --syntax-check`
4. Submit pull request for review
5. Deploy to staging first
6. Final approval for production

## Version History

- **1.0.0** (2024-01-XX) - Initial production-ready deployment infrastructure
- See [CHANGELOG.md](../CHANGELOG.md) for full history

---

**Last Updated**: 2024-01-XX
**Maintained By**: Platform Engineering Team
**Status**: Production Ready ✓
