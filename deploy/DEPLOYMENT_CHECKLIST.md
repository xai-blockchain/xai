# XAI Node Deployment Checklist

Use this checklist to ensure a successful production deployment.

## Pre-Deployment

### Requirements
- [ ] Choose deployment platform (AWS/GCP/Azure/DigitalOcean/Kubernetes)
- [ ] Have cloud account with billing enabled
- [ ] Have SSH key pair ready
- [ ] Have API credentials/tokens configured
- [ ] Reviewed cost estimates for chosen platform

### Configuration Decisions
- [ ] Decided on network mode (testnet or mainnet)
- [ ] Determined resource sizing (instance type, storage)
- [ ] Chosen deployment region/zone
- [ ] Prepared environment variables (if customizing)
- [ ] Generated secure passwords for production

### Security Review
- [ ] Reviewed firewall rules
- [ ] Prepared IP whitelist for SSH access
- [ ] Have SSL/TLS certificates ready (if using custom domain)
- [ ] Reviewed security best practices for platform
- [ ] Backup strategy planned

## Deployment

### Run Deployment Script
- [ ] Downloaded/executed one-liner script
- [ ] Provided all required parameters
- [ ] Waited for completion (5-15 minutes)
- [ ] Saved deployment outputs (IP, URLs, credentials)

### Initial Verification
- [ ] SSH access working
- [ ] API endpoint responding: `curl http://<ip>:8080/health`
- [ ] Block Explorer accessible: `http://<ip>:3000`
- [ ] Metrics endpoint working: `http://<ip>:9090/metrics`
- [ ] Node is syncing blocks

### Service Checks
```bash
# Docker deployments
docker ps | grep xai
docker logs xai-node --tail 50

# Kubernetes deployments
kubectl get pods -n xai-blockchain
kubectl logs -f deployment/xai-node -n xai-blockchain
```

## Post-Deployment Configuration

### Security Hardening
- [ ] Changed default database password
- [ ] Restricted SSH access to specific IPs
- [ ] Configured firewall rules
- [ ] Enabled automatic security updates
- [ ] Reviewed and adjusted security groups/NSGs

### Monitoring Setup
- [ ] Verified Prometheus metrics accessible
- [ ] Set up monitoring dashboards (optional)
- [ ] Configured alerting (optional)
- [ ] Tested health check endpoint
- [ ] Verified log collection

### Backup Configuration
- [ ] Set up automated backups
- [ ] Tested backup process
- [ ] Verified backup storage location
- [ ] Documented restore procedure
- [ ] Scheduled regular backup tests

### Documentation
- [ ] Documented server IP/hostname
- [ ] Saved SSH keys securely
- [ ] Documented any custom configuration
- [ ] Shared access details with team (securely)
- [ ] Created runbook for common operations

## Production Readiness

### Performance Testing
- [ ] Verified sync performance
- [ ] Tested API response times
- [ ] Checked resource utilization
- [ ] Confirmed peer connections working
- [ ] Validated database performance

### High Availability (Optional)
- [ ] Deployed multiple nodes (if required)
- [ ] Set up load balancer (if required)
- [ ] Configured database replication
- [ ] Tested failover procedures
- [ ] Documented HA architecture

### Mainnet Preparation (If Applicable)
- [ ] Changed XAI_NETWORK to mainnet
- [ ] Updated genesis file
- [ ] Configured bootstrap nodes
- [ ] Increased resource allocation (if needed)
- [ ] Reviewed mainnet-specific security

## Ongoing Operations

### Daily Checks
- [ ] Monitor blockchain sync status
- [ ] Check resource utilization
- [ ] Review logs for errors
- [ ] Verify peer connections
- [ ] Check backup status

### Weekly Maintenance
- [ ] Review security logs
- [ ] Check disk space
- [ ] Update system packages
- [ ] Review performance metrics
- [ ] Test backup restore

### Monthly Tasks
- [ ] Security audit
- [ ] Cost review and optimization
- [ ] Update documentation
- [ ] Review and rotate credentials
- [ ] Test disaster recovery procedures

## Troubleshooting Reference

### Node Won't Start
```bash
# Check logs
docker logs xai-node
journalctl -u xai-node -f

# Common fixes:
# - Port already in use: Change XAI_API_PORT
# - Database connection: Check POSTGRES_PASSWORD
# - Disk space: Increase volume size
```

### Sync Issues
```bash
# Check peers
curl http://localhost:8080/peers

# Check sync status
curl http://localhost:8080/status

# Force resync (testnet only)
docker exec xai-node rm -rf /data/blockchain
docker restart xai-node
```

### Performance Issues
```bash
# Check resource usage
docker stats xai-node

# Check database connections
docker exec xai-postgres psql -U xai_testnet -c "SELECT count(*) FROM pg_stat_activity;"

# Review slow queries
docker exec xai-postgres psql -U xai_testnet -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## Emergency Procedures

### Node Failure
1. Check logs for errors
2. Attempt restart: `docker restart xai-node`
3. If restart fails, restore from backup
4. If backup fails, redeploy from scratch
5. Document incident and root cause

### Data Corruption
1. Stop node immediately
2. Restore from latest backup
3. Verify data integrity
4. Restart node and monitor
5. Update backup procedures if needed

### Security Incident
1. Isolate affected systems
2. Review security logs
3. Rotate all credentials
4. Apply security patches
5. Document incident
6. Update security procedures

## Rollback Procedure

If deployment fails or issues discovered:

```bash
# AWS
aws cloudformation delete-stack --stack-name xai-node

# GCP
gcloud deployment-manager deployments delete xai-node

# Azure
az group delete --name xai-node-rg --yes

# DigitalOcean
cd /tmp/xai-do && terraform destroy

# Kubernetes
kubectl delete namespace xai-blockchain

# Docker
cd /opt/xai && docker-compose down -v
```

## Sign-Off

### Deployment Sign-Off
- [ ] All checklist items completed
- [ ] Deployment verified by: ________________
- [ ] Date deployed: ________________
- [ ] Environment: ________________
- [ ] Version: ________________

### Production Approval (Mainnet Only)
- [ ] Security review completed
- [ ] Performance testing passed
- [ ] Backup/restore tested
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Approved by: ________________
- [ ] Date approved: ________________

## Quick Reference

### Important URLs
- API: `http://<ip>:8080`
- Explorer: `http://<ip>:3000`
- Metrics: `http://<ip>:9090/metrics`
- Health: `http://<ip>:8080/health`

### Important Commands
```bash
# View logs
docker logs -f xai-node

# Check status
curl http://localhost:8080/status

# Restart node
docker restart xai-node

# Backup data
docker run --rm --volumes-from xai-node -v $(pwd):/backup ubuntu tar czf /backup/xai-backup.tar.gz /data
```

### Support Contacts
- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://docs.xai-blockchain.io
- Community: https://discord.gg/xai-blockchain
- Emergency: [Your team's escalation procedure]
