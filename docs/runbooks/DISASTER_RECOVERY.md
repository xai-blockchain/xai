# XAI Blockchain Disaster Recovery Runbook

**Version:** 1.0.0
**Last Updated:** 2025-12-30
**Classification:** Operations Critical

## Quick Reference

| Scenario | Severity | RTO | RPO |
|----------|----------|-----|-----|
| Chain Halt | Critical | 4h | 0 (no data loss) |
| Key Compromise | Critical | 1h | N/A |
| Consensus Failure | Critical | 2h | 0 |
| Data Corruption | High | 8h | Last checkpoint |
| DDoS Attack | Medium | 1h | 0 |

## Scenario 1: Chain Halt

### Symptoms
- No new blocks for >5 minutes
- All nodes stuck at same height
- Mining/validation stopped

### Immediate Actions (0-15 min)

```bash
# 1. Verify chain status across nodes
for node in node1 node2 node3; do
    ssh $node "curl -s localhost:12345/info | jq '.height'"
done

# 2. Check node logs for errors
journalctl -u xai-node --since "10 minutes ago" | grep -i error

# 3. Check mempool status
curl localhost:12345/mempool/stats
```

### Diagnosis (15-60 min)

| Check | Command | Expected |
|-------|---------|----------|
| Peer count | `curl /peers` | >3 |
| Mempool | `curl /mempool` | Not stuck |
| CPU/Memory | `top` | <90% |
| Disk | `df -h` | >10% free |

### Resolution

#### If: Mempool deadlock
```bash
# Clear mempool
curl -X POST localhost:12345/admin/mempool/clear

# Restart node
systemctl restart xai-node
```

#### If: Consensus stuck
```bash
# Force re-sync from checkpoint
xai-cli node resync --from-checkpoint

# If multiple nodes, restart validators
ansible validators -m command -a "systemctl restart xai-validator"
```

### Recovery Verification

```bash
# Verify blocks progressing
watch -n 10 'curl -s localhost:12345/info | jq ".height"'

# Verify transactions processing
xai-cli tx send --to test_address --amount 1 --wait
```

---

## Scenario 2: Key Compromise

### Symptoms
- Unauthorized transactions detected
- Admin key used unexpectedly
- Validator signing unauthorized blocks

### Immediate Actions (0-5 min)

```bash
# 1. EMERGENCY: Pause critical contracts
xai-cli admin emergency-pause --all

# 2. Rotate compromised keys
xai-cli admin rotate-key --key-type admin --emergency

# 3. Notify security team
./scripts/notify-security-team.sh "KEY_COMPROMISE"
```

### Containment (5-30 min)

```bash
# 1. Identify compromised key scope
xai-cli audit key-usage --key $COMPROMISED_KEY --since "7 days ago"

# 2. Revoke compromised key from all contracts
xai-cli admin revoke-key --key $COMPROMISED_KEY --all-contracts

# 3. Enable enhanced monitoring
xai-cli monitoring enable-alert --pattern "key:$COMPROMISED_KEY"
```

### Recovery (30 min - 24h)

1. **Assess Damage**
   ```bash
   # List all transactions from compromised key
   xai-cli query tx --from $COMPROMISED_KEY --format json > compromised_txs.json
   ```

2. **Revert Malicious Transactions** (if possible)
   ```bash
   # Governance proposal for reversal
   xai-cli governance propose --type emergency-reversal \
       --transactions compromised_txs.json
   ```

3. **Update All Key References**
   - Update multisig configurations
   - Rotate all related keys
   - Update documentation

### Post-Incident

- [ ] Root cause analysis
- [ ] Security audit
- [ ] Key management review
- [ ] Update procedures

---

## Scenario 3: Consensus Failure

### Symptoms
- Chain fork detected
- Validators disagreeing
- Multiple valid chains

### Immediate Actions

```bash
# 1. Identify fork
xai-cli chain analyze-fork

# 2. Check validator status
xai-cli validator list --status

# 3. Pause block production temporarily
xai-cli admin pause-mining --duration 10m
```

### Resolution

#### If: Network partition
```bash
# Identify partitioned nodes
xai-cli network analyze-partition

# Force reconnection
xai-cli peer connect --force --peers "node1,node2,node3"
```

#### If: Byzantine validator
```bash
# Slash misbehaving validator
xai-cli validator slash --address $VALIDATOR_ADDRESS \
    --reason "double_sign" --evidence evidence.json

# Remove from active set
xai-cli validator remove --address $VALIDATOR_ADDRESS
```

#### If: Conflicting checkpoints
```bash
# Determine canonical checkpoint
xai-cli checkpoint verify --all

# Force all nodes to specific checkpoint
xai-cli checkpoint force --height $CHECKPOINT_HEIGHT
```

---

## Scenario 4: Data Corruption

### Symptoms
- Merkle root mismatches
- Invalid state transitions
- Database errors

### Immediate Actions

```bash
# 1. Stop the corrupted node
systemctl stop xai-node

# 2. Backup current state (even if corrupted)
tar -czf /backup/corruption-$(date +%Y%m%d).tar.gz /data/xai

# 3. Verify corruption
xai-cli db verify --full
```

### Recovery Options

#### Option A: Restore from backup
```bash
# Find latest good backup
ls -la /backup/xai-data-*.tar.gz

# Restore
systemctl stop xai-node
rm -rf /data/xai
tar -xzf /backup/xai-data-$DATE.tar.gz -C /data
systemctl start xai-node
```

#### Option B: Sync from peers
```bash
# Clear data and resync
rm -rf /data/xai/blocks /data/xai/state
xai-cli node sync --from-genesis
```

#### Option C: Restore from checkpoint
```bash
# Download checkpoint
wget https://checkpoints.xai.io/checkpoint-$HEIGHT.tar.gz

# Restore
tar -xzf checkpoint-$HEIGHT.tar.gz -C /data/xai
xai-cli node sync --from-height $HEIGHT
```

---

## Scenario 5: DDoS Attack

### Symptoms
- High request rate
- Node unresponsive
- Network saturation

### Immediate Actions

```bash
# 1. Enable rate limiting
xai-cli admin rate-limit --enable --requests-per-second 100

# 2. Block attacking IPs
iptables -A INPUT -s $ATTACKER_IP -j DROP

# 3. Enable DDoS protection mode
xai-cli network ddos-protection --enable
```

### Mitigation

```bash
# Enable geo-blocking if needed
xai-cli network block-region --region CN,RU

# Scale up infrastructure
kubectl scale deployment xai-node --replicas=10

# Enable CDN/proxy protection
./scripts/enable-cloudflare.sh
```

---

## Recovery Verification Checklist

### Post-Recovery Checks

- [ ] Chain advancing normally
- [ ] All validators online
- [ ] P2P connections healthy
- [ ] API responding
- [ ] Transactions processing
- [ ] Monitoring active
- [ ] Alerts functioning

### Health Commands

```bash
# Full health check
xai-cli health check --full

# Expected output:
# ✓ Chain: Healthy (height: 123456)
# ✓ Consensus: Active (5/7 validators)
# ✓ P2P: Connected (42 peers)
# ✓ API: Responsive (avg: 45ms)
# ✓ Storage: OK (82% free)
```

---

## Contact Information

### Escalation Path

| Level | Role | Contact | Response Time |
|-------|------|---------|---------------|
| L1 | On-call Ops | ops-pager@xai.io | 5 min |
| L2 | Senior Ops | senior-ops@xai.io | 15 min |
| L3 | Core Team | core@xai.io | 30 min |
| L4 | Founders | founders@xai.io | 1 hour |

### External Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| AWS Support | [Support Console] | Infrastructure |
| CloudFlare | [CF Dashboard] | DDoS mitigation |
| Security Firm | security-partner@firm.com | Incident response |

---

## Appendix: Backup Procedures

### Daily Backup

```bash
# Automated daily backup (crontab)
0 0 * * * /opt/xai/scripts/backup-daily.sh
```

### Checkpoint Creation

```bash
# Create checkpoint every 10,000 blocks
xai-cli checkpoint create --interval 10000
```

### Off-site Backup

```bash
# Sync to off-site storage
aws s3 sync /backup/xai s3://xai-backups/daily/
```

---

*This runbook should be tested quarterly. Last test: [DATE]*
