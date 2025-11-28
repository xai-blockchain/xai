# XAI Blockchain - Disaster Recovery Plan

Comprehensive disaster recovery procedures for XAI Blockchain production environment.

## Recovery Point Objective (RPO) and Recovery Time Objective (RTO)

| Service Component | RTO | RPO |
|------------------|-----|-----|
| Blockchain Node | 30 minutes | 5 minutes |
| PostgreSQL Database | 15 minutes | 1 minute |
| Redis Cache | 10 minutes | N/A (non-persistent) |
| Block Explorer | 30 minutes | 1 hour |
| Monitoring | 1 hour | N/A |

## Backup Strategy

### Backup Schedule

```
Database: Every 1 hour (transaction logs every 10 minutes)
Blockchain: Every 6 hours
Configuration: On every deployment
```

### Backup Storage

**Primary Backup Location**: AWS S3
- Bucket: `xai-backups-production`
- Encryption: KMS (AES-256)
- Versioning: Enabled
- Retention: 30 days (lifecycle policies)

**Secondary Backup Location**: On-premise (for critical data)
- Location: `/var/backups/off-site`
- Frequency: Daily via rsync
- Retention: 90 days

### Backup Verification

```bash
# Daily backup verification script
cat > /usr/local/bin/verify-backups.sh << 'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/pre-deployment"
LOG_FILE="/var/log/backup-verification.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Verify database backup
if [ -f "$BACKUP_DIR/database-"*.sql.gz ]; then
    LATEST=$(ls -t "$BACKUP_DIR"/database-*.sql.gz | head -1)
    if gunzip -t "$LATEST" 2>/dev/null; then
        log "✓ Database backup verified: $LATEST"
    else
        log "✗ Database backup corrupt: $LATEST"
        exit 1
    fi
fi

# Verify blockchain backup
if [ -f "$BACKUP_DIR/blockchain-"*.tar.gz ]; then
    LATEST=$(ls -t "$BACKUP_DIR"/blockchain-*.tar.gz | head -1)
    if tar -tzf "$LATEST" > /dev/null 2>&1; then
        log "✓ Blockchain backup verified: $LATEST"
    else
        log "✗ Blockchain backup corrupt: $LATEST"
        exit 1
    fi
fi

# Verify S3 backups
if aws s3 ls s3://xai-backups-production/ &>/dev/null; then
    log "✓ S3 backup location accessible"
else
    log "✗ S3 backup location not accessible"
    exit 1
fi

log "All backup verifications passed"
EOF

chmod +x /usr/local/bin/verify-backups.sh

# Schedule daily verification
crontab -e
# Add: 0 4 * * * /usr/local/bin/verify-backups.sh
```

## Disaster Scenarios

### Scenario 1: Database Corruption

#### Detection

```bash
# Monitor for database errors
systemctl is-active --quiet postgresql || echo "Database is down"

# Check database integrity
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c \
  "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC LIMIT 5;"

# Run REINDEX if corruption detected
psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c "REINDEX DATABASE xai_blockchain;"
```

#### Recovery Steps

1. **Stop dependent services**
   ```bash
   systemctl stop xai-node
   systemctl stop xai-explorer
   ```

2. **Restore from latest backup**
   ```bash
   LATEST_BACKUP=$(ls -t /var/backups/pre-deployment/database-*.sql.gz | head -1)
   gunzip -c "$LATEST_BACKUP" | psql -h xai-db.internal -U xaiadmin -d xai_blockchain
   ```

3. **Verify restored data**
   ```bash
   psql -h xai-db.internal -U xaiadmin -d xai_blockchain -c \
     "SELECT COUNT(*) FROM blockchain; SELECT MAX(height) FROM blockchain;"
   ```

4. **Restart services**
   ```bash
   systemctl start xai-node
   systemctl start xai-explorer
   ```

### Scenario 2: Blockchain Data Loss

#### Detection

```bash
# Check blockchain state
curl -s http://localhost:8080/api/v1/blockchain/info | jq '.block_height'

# Verify against network
curl -s "https://mainnet-rpc.example.com/api/v1/blockchain/info" | jq '.block_height'

# If height is significantly lower, blockchain is out of sync or corrupted
```

#### Recovery Steps

1. **Backup current blockchain state**
   ```bash
   tar -czf /var/backups/corrupted-blockchain-$(date +%s).tar.gz /var/lib/xai/blockchain
   ```

2. **Restore from backup**
   ```bash
   LATEST_BLOCKCHAIN=$(ls -t /var/backups/pre-deployment/blockchain-*.tar.gz | head -1)
   tar -xzf "$LATEST_BLOCKCHAIN" -C /
   chown -R xai:xai /var/lib/xai
   ```

3. **Resync blockchain**
   ```bash
   systemctl restart xai-node
   # Monitor sync progress
   watch -n 5 'curl -s http://localhost:8080/api/v1/blockchain/info | jq ".block_height, .is_synced"'
   ```

4. **Verify integrity**
   ```bash
   curl -s http://localhost:8080/api/v1/blockchain/verify | jq '.is_valid'
   ```

### Scenario 3: Complete Data Center Failure

#### Preparation (Before Disaster)

1. **Multi-region setup**
   ```bash
   # Deploy standby in different region
   cd deploy/terraform
   cp environments/production.tfvars environments/production-dr.tfvars
   
   # Edit DR tfvars with different region
   sed -i 's/us-east-1/us-west-2/g' environments/production-dr.tfvars
   
   # Deploy DR infrastructure
   terraform apply -var-file="environments/production-dr.tfvars"
   ```

2. **Cross-region replication**
   ```bash
   # Enable S3 cross-region replication
   aws s3api put-bucket-replication \
     --bucket xai-backups-production \
     --replication-configuration '{
       "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
       "Rules": [{
         "Status": "Enabled",
         "Priority": 1,
         "Destination": {
           "Bucket": "arn:aws:s3:::xai-backups-dr-us-west-2",
           "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
           "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
         }
       }]
     }'
   ```

3. **Database replication**
   ```bash
   # Configure RDS multi-AZ deployment
   aws rds modify-db-cluster \
     --db-cluster-identifier xai-blockchain-db-cluster \
     --multi-az \
     --apply-immediately
   ```

#### Recovery Steps (After Disaster)

1. **Activate DR infrastructure**
   ```bash
   # Update DNS to point to DR region
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z1234567890ABC \
     --change-batch file://dr-failover.json
   ```

2. **Restore from cross-region backups**
   ```bash
   # Copy backups from DR S3 bucket
   aws s3 sync s3://xai-backups-dr-us-west-2 /var/backups/restore --region us-west-2
   
   # Restore database and blockchain
   cd deploy/scripts
   bash restore.sh /var/backups/restore
   ```

3. **Verify service availability**
   ```bash
   bash deploy/scripts/health-check.sh
   ```

4. **Monitor for data consistency**
   ```bash
   curl -s http://localhost:8080/api/v1/blockchain/verify | jq '.'
   ```

### Scenario 4: Network Partition / Consensus Failure

#### Detection

```bash
# Check peer connectivity
curl -s http://localhost:8080/api/v1/network/info | jq '.peer_count'

# Monitor transaction acceptance
curl -s http://localhost:8080/api/v1/mempool/info | jq '.transaction_count'

# Check if node is mining
curl -s http://localhost:8080/api/v1/node/status | jq '.is_mining'
```

#### Recovery Steps

1. **Wait for network healing** (usually 10-15 minutes)
   ```bash
   while true; do
     PEERS=$(curl -s http://localhost:8080/api/v1/network/info | jq '.peer_count')
     SYNCED=$(curl -s http://localhost:8080/api/v1/blockchain/info | jq '.is_synced')
     echo "Peers: $PEERS, Synced: $SYNCED"
     
     if [ "$SYNCED" = "true" ] && [ "$PEERS" -gt 5 ]; then
       echo "Network recovered"
       break
     fi
     
     sleep 10
   done
   ```

2. **If partition persists, perform manual consensus recovery**
   ```bash
   # Connect to largest partition
   curl -X POST http://localhost:8080/api/v1/network/rejoin \
     -H "Content-Type: application/json" \
     -d '{"peer_addresses": ["10.0.1.11:8333", "10.0.2.11:8333"]}'
   ```

3. **Verify consensus state**
   ```bash
   curl -s http://localhost:8080/api/v1/blockchain/info | jq '.consensus_state'
   ```

### Scenario 5: Security Breach

#### Immediate Actions

```bash
# 1. Isolate affected systems
aws ec2 modify-instance-attribute \
  --instance-id i-0123456789abcdef0 \
  --source-dest-check

# 2. Revoke compromised credentials
aws iam list-access-keys --user-name compromised-user
aws iam delete-access-key --user-name compromised-user --access-key-id AKIAIOSFODNN7EXAMPLE

# 3. Enable forensics logging
aws cloudtrail start-logging --name xai-blockchain-trail

# 4. Create forensic snapshot
aws ec2 create-image \
  --instance-id i-0123456789abcdef0 \
  --name "forensic-snapshot-$(date +%s)" \
  --no-reboot
```

#### Recovery Steps

1. **Terminate compromised instances**
   ```bash
   aws ec2 terminate-instances --instance-ids i-0123456789abcdef0
   ```

2. **Redeploy from known-good state**
   ```bash
   bash deploy/scripts/deploy.sh production
   ```

3. **Rotate all credentials and secrets**
   ```bash
   # Update database password
   aws rds modify-db-cluster \
     --db-cluster-identifier xai-blockchain-db-cluster \
     --master-user-password "$(openssl rand -base64 32)" \
     --apply-immediately
   
   # Update Redis password
   aws elasticache modify-replication-group \
     --replication-group-id xai-blockchain-redis \
     --auth-token "$(openssl rand -base64 32)"
   
   # Update application secrets
   kubectl create secret generic xai-secrets \
     --from-literal=db-password="$(openssl rand -base64 32)" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

4. **Investigate root cause**
   ```bash
   # Review CloudTrail logs
   aws cloudtrail lookup-events --max-results 100
   
   # Analyze security logs
   grep -i "unauthorized\|failed\|error" /var/log/auth.log /var/log/audit/audit.log
   
   # Review network traffic
   tcpdump -i eth0 -w /var/tmp/traffic.pcap 'not port 22'
   ```

## Testing Disaster Recovery

### DR Drill Schedule

- Monthly: Database restore test
- Quarterly: Full system failover test
- Annually: Complete DR exercise

### DR Test Checklist

```bash
# Create test environment
cat > tests/disaster-recovery/test-dr.sh << 'EOF'
#!/bin/bash
set -euo pipefail

TEST_DIR="/tmp/dr-test-$(date +%s)"
mkdir -p "$TEST_DIR"

echo "=== Database Restore Test ==="
# Test database restore
latest_backup=$(ls -t /var/backups/pre-deployment/database-*.sql.gz | head -1)
gunzip -c "$latest_backup" | psql -h localhost -U xaiadmin -d xai_test
psql -h localhost -U xaiadmin -d xai_test -c "SELECT COUNT(*) FROM blockchain;" || exit 1

echo "=== Blockchain Restore Test ==="
# Test blockchain restore
latest_blockchain=$(ls -t /var/backups/pre-deployment/blockchain-*.tar.gz | head -1)
tar -xzf "$latest_blockchain" -C "$TEST_DIR"
[ -f "$TEST_DIR/var/lib/xai/blockchain/chain.db" ] || exit 1

echo "=== Health Check Test ==="
bash deploy/scripts/health-check.sh || exit 1

echo "=== All DR Tests Passed ==="
rm -rf "$TEST_DIR"
EOF

chmod +x tests/disaster-recovery/test-dr.sh
```

## Disaster Recovery Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| DR Lead | John Doe | john.doe@company.com | +1-555-0100 |
| Infrastructure Lead | Jane Smith | jane.smith@company.com | +1-555-0101 |
| Database Lead | Bob Johnson | bob.johnson@company.com | +1-555-0102 |
| Security Lead | Alice Williams | alice.williams@company.com | +1-555-0103 |

## Disaster Recovery Documentation

Required documents should be maintained:

1. **Runbooks**: Step-by-step recovery procedures
2. **Architecture Diagrams**: Current infrastructure layout
3. **Inventory**: All systems, credentials, and dependencies
4. **Procedures**: Backup, restore, and failover procedures
5. **Contact List**: All relevant personnel and vendors
6. **Test Results**: Records of DR drill outcomes

All documentation should be stored:
- Primary: GitHub Wiki (encrypted)
- Secondary: AWS Secrets Manager
- Tertiary: Printed copy in secure location

## Recovery Metrics

Track and monitor:

```bash
# Backup success rate
TOTAL_BACKUPS=$(aws s3 ls s3://xai-backups-production/ | wc -l)
RECENT_BACKUPS=$(aws s3 ls s3://xai-backups-production/ --recursive | grep -c "$(date +%Y-%m-%d)")

# Restore success rate
echo "Backup success rate: $((RECENT_BACKUPS * 100 / 24))%"

# Average recovery time
# Measured in DR drills and actual incidents
```

## Continuous Improvement

Post-incident (or drill):
1. Review all actions taken
2. Document lessons learned
3. Update procedures based on findings
4. Conduct team debriefing
5. Schedule follow-up training
6. Update recovery time objectives if needed
