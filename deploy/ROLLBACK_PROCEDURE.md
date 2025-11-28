# XAI Blockchain - Rollback Procedure

Critical rollback procedures for emergency deployment failures.

## Quick Reference

### Decision Matrix

| Severity | Time to Rollback | Action |
|----------|------------------|--------|
| Critical (API Down) | < 5 minutes | Immediate rollback |
| High (Errors > 1%) | < 15 minutes | Immediate rollback |
| Medium (Degraded) | < 1 hour | Investigate first |
| Low (Non-critical) | < 24 hours | Monitor and plan |

## Automated Rollback

### GitHub Actions Rollback

```bash
# Trigger rollback via GitHub CLI
gh workflow run rollback.yml \
  -f environment=production \
  -f backup_directory=/var/backups/pre-deployment
```

### Shell Script Rollback

```bash
# Execute rollback with backups
bash deploy/scripts/rollback.sh /var/backups/pre-deployment

# Monitor rollback
tail -f rollback.log
```

## Manual Rollback

### Step 1: Notify Team

```bash
# Send alert to on-call
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:xai-alerts \
  --subject "Deployment Rollback Initiated" \
  --message "Rolling back XAI deployment to previous stable version"

# Post to Slack
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Deployment Rollback Initiated",
    "attachments": [{
      "color": "danger",
      "title": "XAI Blockchain Rollback",
      "text": "Rolling back to previous stable version"
    }]
  }'
```

### Step 2: Stop Current Services

```bash
# Stop blockchain node
systemctl stop xai-node
docker-compose down

# Wait for graceful shutdown
sleep 10

# Verify services stopped
systemctl is-active xai-node || echo "Service stopped"
```

### Step 3: Restore Database

```bash
# List available backups
ls -la /var/backups/pre-deployment/database-*.sql.gz

# Select latest backup
BACKUP_FILE=$(ls -t /var/backups/pre-deployment/database-*.sql.gz | head -1)

# Restore database
gunzip -c "$BACKUP_FILE" | psql \
  -h xai-db.internal \
  -U xaiadmin \
  -d xai_blockchain

# Verify restore
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c \
  "SELECT COUNT(*) FROM blockchain WHERE 1=1;"
```

### Step 4: Restore Blockchain Data

```bash
# List available backups
ls -la /var/backups/pre-deployment/blockchain-*.tar.gz

# Select latest backup
BLOCKCHAIN_BACKUP=$(ls -t /var/backups/pre-deployment/blockchain-*.tar.gz | head -1)

# Restore blockchain data
tar -xzf "$BLOCKCHAIN_BACKUP" -C /

# Verify permissions
chown -R xai:xai /var/lib/xai
chmod -R 755 /var/lib/xai
```

### Step 5: Restore Configuration

```bash
# List available backups
ls -la /var/backups/pre-deployment/config-*.tar.gz

# Select latest backup
CONFIG_BACKUP=$(ls -t /var/backups/pre-deployment/config-*.tar.gz | head -1)

# Restore configuration
tar -xzf "$CONFIG_BACKUP" -C /

# Reload configuration
systemctl daemon-reload
```

### Step 6: Restart Services

```bash
# Start blockchain node
systemctl start xai-node

# Wait for startup
sleep 30

# Verify status
systemctl status xai-node

# Check logs
journalctl -u xai-node -n 20 --no-pager
```

### Step 7: Verify Rollback

```bash
# Health check
bash deploy/scripts/health-check.sh

# Test API
curl -v http://localhost:8080/health
curl -s http://localhost:8080/api/v1/network/info | jq .

# Verify blockchain state
curl -s http://localhost:8080/api/v1/blockchain/info | jq '.block_height, .is_synced'

# Check database consistency
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -f \
  /var/lib/xai/verify-consistency.sql
```

## Rollback via Terraform

### Complete Infrastructure Rollback

```bash
cd deploy/terraform

# Show current state
terraform show

# Plan destruction
terraform plan -destroy -var-file="environments/production.tfvars" -out=destroy.tfplan

# Review destruction plan
terraform show destroy.tfplan | less

# Apply destruction
terraform apply destroy.tfplan

# Redeploy from backups (if needed)
terraform apply -var-file="environments/production.tfvars"
```

### Partial Resource Rollback

```bash
# Rollback RDS only
terraform destroy \
  -target=aws_rds_cluster.main \
  -target=aws_rds_cluster_instance.main \
  -var-file="environments/production.tfvars"

# Recreate RDS from backup
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier xai-blockchain-restored \
  --snapshot-identifier <snapshot-id> \
  --engine aurora-postgresql
```

## Rollback via Docker

### Container-Level Rollback

```bash
# Stop current containers
docker-compose down

# List available images
docker images | grep xai

# Tag previous stable image
docker tag xai-blockchain:v0.9.9 xai-blockchain:latest
docker tag xai-explorer:v0.9.9 xai-explorer:latest

# Start with previous version
docker-compose up -d

# Monitor startup
docker-compose logs -f
```

### Registry-Level Rollback

```bash
# Pull previous image from registry
docker pull ghcr.io/your-org/xai-blockchain:v0.9.9

# Update docker-compose.yml to use specific version
sed -i 's/image: xai-blockchain:latest/image: xai-blockchain:v0.9.9/g' docker-compose.yml

# Restart services
docker-compose up -d --force-recreate

# Verify rollback
docker ps | grep xai
```

## Rollback via Ansible

### Orchestrated Rollback

```bash
cd deploy/ansible

# Create rollback playbook
cat > rollback-playbook.yml << 'EOF'
---
- name: XAI Rollback
  hosts: blockchain-nodes
  become: yes
  
  tasks:
    - name: Stop services
      systemd:
        name: "{{ item }}"
        state: stopped
      loop:
        - xai-node
        - prometheus
        - grafana-server
    
    - name: Restore from backup
      shell: |
        tar -xzf /var/backups/pre-deployment/blockchain-*.tar.gz -C /
        gunzip -c /var/backups/pre-deployment/database-*.sql.gz | psql -h {{ postgres_host }} -U {{ postgres_user }}
    
    - name: Start services
      systemd:
        name: "{{ item }}"
        state: started
      loop:
        - xai-node
        - prometheus
        - grafana-server
    
    - name: Verify services
      uri:
        url: http://localhost:8080/health
        status_code: 200
      retries: 5
      delay: 10
EOF

# Execute rollback
ansible-playbook rollback-playbook.yml \
  -i inventory/production.yml \
  -e "postgres_host=xai-db.internal" \
  -e "postgres_user=xaiadmin"
```

## Post-Rollback Verification

### Health Checks

```bash
# System health
bash deploy/scripts/health-check.sh

# Database integrity
psql -h xai-db.internal -U xaiadmin -d xai_blockchain << SQL
  SELECT 
    COUNT(*) as total_blocks,
    MAX(height) as latest_block,
    COUNT(DISTINCT miner_address) as unique_miners
  FROM blockchain;
SQL

# Blockchain sync status
curl -s http://localhost:8080/api/v1/blockchain/info | jq '.is_synced, .block_height'

# Peer connectivity
curl -s http://localhost:8080/api/v1/network/info | jq '.peer_count'
```

### Data Consistency

```bash
# Verify blockchain consistency
curl -s http://localhost:8080/api/v1/blockchain/verify | jq '.is_valid, .errors'

# Check transaction backlog
curl -s http://localhost:8080/api/v1/mempool/info | jq '.transaction_count, .total_size'

# Validate wallet state
curl -s http://localhost:8080/api/v1/wallets/verify | jq '.total_wallets, .total_balance'
```

## Communication Template

### Slack Notification

```
:warning: DEPLOYMENT ROLLBACK EXECUTED

**Service**: XAI Blockchain
**Environment**: production
**Initiated At**: 2024-01-15 14:32:00 UTC
**Initiated By**: @devops-engineer
**Reason**: High error rate (>5%)

**Status**: COMPLETE
**Verification**: PASSED
**Impact**: ~2 minutes of downtime

**Next Steps**:
1. RCA scheduled for 15:00 UTC
2. Investigate root cause
3. Plan deployment fixes
4. Resume normal operations

@on-call please review logs and prepare summary.
```

### Email Notification

```
Subject: CRITICAL - XAI Deployment Rollback Completed

Hi Team,

A deployment rollback has been executed for XAI Blockchain production environment.

Timeline:
- 14:30 UTC: Deployment completed
- 14:32 UTC: High error rate detected (>5%)
- 14:35 UTC: Rollback initiated
- 14:37 UTC: Rollback completed
- 14:38 UTC: Health checks passed

Impact:
- Downtime: ~2 minutes
- Data Loss: None
- User Impact: Minimal

Root Cause: [To be determined]

Action Items:
- [ ] Complete RCA by 2024-01-15 18:00 UTC
- [ ] Implement fixes
- [ ] Deploy to staging for testing
- [ ] Plan re-deployment

For questions, contact: devops@company.internal
```

## Prevention and Learning

### Post-Incident Review

```bash
# Collect logs for analysis
mkdir -p incident-reports/2024-01-15

# Gather deployment logs
cp deploy.log incident-reports/2024-01-15/
journalctl -u xai-node --since "2024-01-15 14:00:00" > incident-reports/2024-01-15/service-logs.txt

# Gather metrics
curl -s 'http://localhost:9091/api/v1/query_range?query=rate(http_requests_total[5m])&start=<timestamp>&end=<timestamp>' \
  > incident-reports/2024-01-15/metrics.json

# Create incident document
cat > incident-reports/2024-01-15/INCIDENT_REPORT.md << 'EOF'
# Incident Report: XAI Deployment Rollback

## Summary
Brief description of what happened and why rollback was necessary.

## Timeline
- 14:30 UTC: Event occurred
- 14:35 UTC: Rollback initiated
- 14:37 UTC: Rollback completed

## Root Cause
Analysis of what caused the deployment failure.

## Impact
Description of user impact and data loss (if any).

## Resolution
How the issue was resolved and services restored.

## Prevention
Steps to prevent similar incidents in the future.

## Follow-ups
Required actions and owners.
EOF
```

### Lessons Learned

Document improvements:
- Update deployment procedures
- Add additional validation checks
- Improve monitoring/alerting
- Update runbooks
- Schedule team training
