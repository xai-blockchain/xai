# XAI Blockchain - Operations Runbook

Quick reference guide for common operational tasks and procedures.

## Table of Contents

1. [Service Management](#service-management)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Database Operations](#database-operations)
4. [Scaling Operations](#scaling-operations)
5. [Security Operations](#security-operations)
6. [Troubleshooting](#troubleshooting)

## Service Management

### Viewing Service Status

```bash
# Systemd services
systemctl status xai-node
systemctl status prometheus
systemctl status grafana-server

# Docker services
docker ps | grep xai
docker-compose ps

# Detailed service info
journalctl -u xai-node --no-pager -n 100
```

### Starting Services

```bash
# Single service
systemctl start xai-node

# All services
systemctl start xai-node prometheus grafana-server

# Using docker-compose
docker-compose up -d
```

### Stopping Services

```bash
# Graceful stop
systemctl stop xai-node
# Wait for graceful shutdown
sleep 10

# Force stop if necessary
systemctl kill -s SIGKILL xai-node

# Stop all
docker-compose down
```

### Restarting Services

```bash
# Restart service
systemctl restart xai-node

# Restart with new configuration
systemctl restart xai-node

# Full restart sequence
systemctl restart xai-node prometheus grafana-server
```

### View Service Logs

```bash
# Last 100 lines
journalctl -u xai-node -n 100

# Follow logs
journalctl -u xai-node -f

# Logs for specific time range
journalctl -u xai-node --since "2024-01-15 10:00:00" --until "2024-01-15 11:00:00"

# Docker logs
docker logs xai-node --tail 100 -f
```

## Monitoring and Alerting

### Prometheus Queries

```bash
# Blockchain height
curl 'http://localhost:9091/api/v1/query?query=blockchain_height'

# Network peers
curl 'http://localhost:9091/api/v1/query?query=network_peers'

# CPU usage
curl 'http://localhost:9091/api/v1/query?query=process_resident_memory_bytes'

# Query with range
curl 'http://localhost:9091/api/v1/query_range?query=blockchain_height&start=1705334400&end=1705420800&step=300'
```

### Grafana Dashboards

**Access**: http://localhost:12030

Default login: admin/admin

Available dashboards:
- Blockchain Node
- Network Status
- Database Performance
- System Resources
- Application Metrics

### Alert Thresholds

| Alert | Threshold | Severity |
|-------|-----------|----------|
| High CPU | >80% for 5 minutes | Critical |
| Low Disk | <10% available | Critical |
| High Memory | >85% | High |
| API Errors | >1% error rate | High |
| Database Connection | >80% pool utilization | High |
| Peer Count | <3 peers | Medium |
| Block Height | Not increasing for 30m | High |
| Sync Lag | >10 blocks behind | Medium |

### Manual Alert Testing

```bash
# Trigger CPU alert
stress --cpu 8 --timeout 300s

# Trigger memory alert
python3 -c "import os; a = [0] * (2**26)" &

# Trigger disk alert
dd if=/dev/zero of=/tmp/fillup bs=1M count=10000

# Check alert status in Prometheus
curl 'http://localhost:9091/api/v1/alerts'
```

## Database Operations

### Connect to Database

```bash
# Using psql
psql -h xai-db.internal -U xaiadmin -d xai_blockchain

# Using AWS RDS Proxy
psql -h xai-db-proxy.internal -U xaiadmin -d xai_blockchain

# Connection string
postgresql://xaiadmin:password@xai-db.internal:5432/xai_blockchain
```

### Database Maintenance

```bash
# Check database size
psql -c "SELECT pg_size_pretty(pg_database_size('xai_blockchain'));"

# Vacuum database
psql -c "VACUUM ANALYZE;"

# Reindex tables
psql -c "REINDEX DATABASE xai_blockchain;"

# Check table sizes
psql -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname != 'pg_catalog' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
```

### Backup and Restore

```bash
# Create backup
pg_dump -h xai-db.internal -U xaiadmin xai_blockchain | gzip > backup.sql.gz

# Restore backup
gunzip -c backup.sql.gz | psql -h xai-db.internal -U xaiadmin xai_blockchain

# Backup with WAL archiving
pg_basebackup -h xai-db.internal -U xaiadmin -D /var/backups/base_backup -F tar -z -P

# Point-in-time recovery
psql -c "SELECT pg_start_backup('label');"
# Copy data files
psql -c "SELECT pg_stop_backup();"
```

### Connection Management

```bash
# View active connections
psql -c "SELECT pid, usename, state, query FROM pg_stat_activity;"

# Terminate connection
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid();"

# Monitor connections
watch -n 5 'psql -c "SELECT count(*) FROM pg_stat_activity;"'
```

## Scaling Operations

### Horizontal Scaling

```bash
# Add more blockchain nodes
cd deploy/terraform
terraform apply -var="instance_count=4"

# Add blockchain node to network
ansible-playbook -i inventory/production.yml site.yml --tags blockchain-node
```

### Database Scaling

```bash
# Upgrade RDS instance type
aws rds modify-db-instance \
  --db-instance-identifier xai-db-instance \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately

# Add read replicas
aws rds create-db-instance-read-replica \
  --db-instance-identifier xai-db-replica-1 \
  --source-db-instance-identifier xai-db-instance
```

### Cache Scaling

```bash
# Scale Redis cluster
aws elasticache increase-replica-count \
  --replication-group-id xai-blockchain-redis \
  --new-replica-count 5 \
  --apply-immediately

# Monitor scaling
watch -n 5 'aws elasticache describe-replication-groups --replication-group-id xai-blockchain-redis'
```

### Load Balancer Scaling

```bash
# Increase ALB target group capacity
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --health-check-timeout-seconds 10

# Monitor ALB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Security Operations

### Key Rotation

```bash
# Rotate database password
aws rds modify-db-cluster \
  --db-cluster-identifier xai-blockchain-db-cluster \
  --master-user-password "$(openssl rand -base64 32)" \
  --apply-immediately

# Rotate Redis password
aws elasticache modify-replication-group \
  --replication-group-id xai-blockchain-redis \
  --auth-token "$(openssl rand -base64 32)" \
  --apply-immediately

# Rotate API keys
kubectl create secret generic xai-api-keys \
  --from-literal=api-key="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### SSL Certificate Management

```bash
# Check certificate expiration
openssl x509 -enddate -noout -in /etc/ssl/certs/xai.crt

# Renew certificate
certbot renew --cert-name xai-blockchain.com

# Update ALB with new certificate
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/new-cert-id
```

### Security Auditing

```bash
# Review IAM policies
aws iam list-policies --scope Local

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-12345678

# Audit CloudTrail logs
aws cloudtrail lookup-events --max-results 100

# Run security scan
bandit -r src/ -f json -o bandit-report.json
```

## Troubleshooting

### High CPU Usage

```bash
# Identify process
top -b -n 1 | head -20

# Check Docker container
docker stats --no-stream xai-node

# Kubernetes pod
kubectl top pod xai-node

# Profile process
perf record -p $(pgrep -f "python.*xai")
perf report

# Potential solutions
# 1. Increase CPU resources
# 2. Optimize slow queries
# 3. Increase cache size
# 4. Scale horizontally
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Find memory hogs
ps aux --sort=-%mem | head

# Docker memory
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Potential solutions
# 1. Increase memory allocation
# 2. Configure memory limits
# 3. Optimize queries
# 4. Clear cache if safe
```

### Slow API Response

```bash
# Check application logs
journalctl -u xai-node -n 50 | grep -i "slow\|timeout\|error"

# Monitor API metrics
curl 'http://localhost:9091/api/v1/query?query=http_request_duration_seconds'

# Check database performance
psql -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Potential solutions
# 1. Add database indexes
# 2. Increase cache TTL
# 3. Scale horizontally
# 4. Optimize slow queries
```

### Blockchain Sync Issues

```bash
# Check sync status
curl -s http://localhost:8080/api/v1/blockchain/info | jq '.is_synced, .block_height'

# Compare with network
curl -s https://mainnet-api.example.com/api/v1/blockchain/info | jq '.block_height'

# Check peer connectivity
curl -s http://localhost:8080/api/v1/network/info | jq '.peer_count, .peers'

# Potential solutions
# 1. Check network connectivity
# 2. Restart blockchain node
# 3. Increase peer connections
# 4. Restore from backup if corrupted
```

### Database Connection Errors

```bash
# Check database status
pg_isready -h xai-db.internal -U xaiadmin

# View connection pool status
psql -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Increase pool size
# Update connection string: pool_size=100

# Potential solutions
# 1. Increase max connections
# 2. Scale read replicas
# 3. Implement connection pooling
# 4. Identify connection leaks
```

## Quick Decision Tree

```
Issue: Service Down
├─ Is it systemd service? → systemctl status <service>
├─ Is it Docker container? → docker logs <container>
├─ Is it network issue? → ping, nc, nslookup
└─ Is it resource issue? → top, free -h, df -h

Issue: Slow Performance
├─ High CPU? → top, profile, optimize
├─ High memory? → ps aux, memory optimization
├─ Slow database? → EXPLAIN, indexes, VACUUM
└─ Network bottleneck? → ifstat, nethogs, tcpdump

Issue: Data Problems
├─ Missing data? → Check backups, restore if needed
├─ Corrupted data? → REINDEX, REPAIR TABLE, consistency check
├─ Lost transactions? → Check transaction log, point-in-time recovery
└─ Sync lag? → Restart node, check peer connectivity
```

## Emergency Contacts

- **On-Call Engineer**: Check Pagerduty
- **Platform Team**: platform-team@company.internal
- **Security Team**: security@company.internal
- **DevOps Lead**: devops-lead@company.internal

## Additional Resources

- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Disaster Recovery Plan](./DISASTER_RECOVERY.md)
- [Rollback Procedures](./ROLLBACK_PROCEDURE.md)
- [XAI Documentation](../docs)
