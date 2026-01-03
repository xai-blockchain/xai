# XAI Testnet Incident Response Runbook

## Contacts
| Role | Name | Contact |
|------|------|---------|
| Primary On-Call | TBD | TBD |
| Secondary On-Call | TBD | TBD |

## Severity Levels
| Level | Description | Response | Escalation |
|-------|-------------|----------|------------|
| P1 | Chain halted, security breach | Immediate | All hands |
| P2 | Node down, degraded | 15 min | Primary + Secondary |
| P3 | Performance issues | 1 hour | Primary |
| P4 | Non-urgent | Next day | Ticket |

## Quick Reference
- **Server**: `ssh xai-testnet` (54.39.129.11, VPN: 10.10.0.3)
- **Service**: `sudo systemctl {status|restart|stop} xai.service`
- **Logs**: `journalctl -u xai.service -f`
- **Secondary**: 10.10.0.4:8546

## Incident: Node Down
```bash
ssh xai-testnet "systemctl status xai.service"
curl -s http://54.39.129.11:8545/health
ssh xai-testnet "sudo systemctl restart xai.service"
ssh xai-testnet "journalctl -u xai.service -n 50"
```

## Incident: Chain Stalled
```bash
# Check block height (primary vs secondary)
curl -s http://54.39.129.11:8545/ -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
curl -s http://10.10.0.4:8546/ -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check peers and restart if needed
ssh xai-testnet "curl -s localhost:8545/metrics | grep peer"
ssh xai-testnet "sudo systemctl restart xai.service"
```

## Incident: High Memory/CPU
```bash
ssh xai-testnet "top -bn1 | head -15; free -h"
ssh xai-testnet "ps aux | grep node.py"
ssh xai-testnet "sudo systemctl restart xai.service"  # If memory leak
```

## Incident: Disk Full
```bash
ssh xai-testnet "df -h; du -sh ~/.xai/*"
ssh xai-testnet "journalctl --vacuum-time=3d"
ssh xai-testnet "sudo systemctl restart xai.service"
```

## Restore from Backup
```bash
ssh xai-testnet "sudo systemctl stop xai.service"
ssh xai-testnet "mv ~/.xai ~/.xai.broken.$(date +%s)"
ssh xai-testnet "~/.validator-backups/keys/xai-backup.sh restore"
ssh xai-testnet "ls -la ~/.xai/.secret_key ~/.xai/node_identity.json ~/.xai/config.json"
ssh xai-testnet "sudo systemctl start xai.service"
```

## Upgrade Procedure
```bash
# 1. Build locally
cd ~/blockchain-projects/xai && git pull

# 2. Stop and backup remote
ssh xai-testnet "sudo systemctl stop xai.service"
ssh xai-testnet "~/.validator-backups/keys/xai-backup.sh"

# 3. Deploy
rsync -avz --exclude='__pycache__' --exclude='.git' ~/blockchain-projects/xai/ xai-testnet:~/xai/
ssh xai-testnet "cd ~/xai && source venv/bin/activate && pip install -r requirements.txt"

# 4. Start and verify
ssh xai-testnet "sudo systemctl start xai.service"
curl -s http://54.39.129.11:8545/health
```

## Security Incident (P1)
1. **Isolate**: `ssh xai-testnet "sudo systemctl stop xai.service"`
2. **Preserve**: `ssh xai-testnet "sudo cp -r /var/log /tmp/incident-$(date +%s)"`
3. **Investigate**:
   ```bash
   ssh xai-testnet "last -20; who; ps aux --forest; netstat -tulpn"
   ssh xai-testnet "ls -la ~/.xai/.secret_key"  # Check modification time
   ```
4. **If keys compromised**: `ssh xai-testnet "mv ~/.xai/.secret_key ~/.xai/.secret_key.compromised"`
5. **Block attacker**: `ssh xai-testnet "sudo ufw deny from <IP>"`
6. **Document and notify team**

## Health Check All Ports
```bash
for port in 8545 8333 8765 8080; do
  echo "Port $port: $(curl -s -o /dev/null -w '%{http_code}' http://54.39.129.11:$port/)"
done
```
