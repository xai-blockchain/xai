# Encryption at Rest Requirements

## Overview

XAI stores sensitive blockchain data including:
- **Block index** (SQLite database)
- **UTXO store** (LevelDB) - contains all address balances
- **Checkpoints** - contains full UTXO snapshots
- **WAL files** - transaction logs

## Security Requirement

**Full disk encryption (FDE) is REQUIRED for all production deployments.**

Without encryption at rest, disk compromise exposes:
- Complete blockchain state
- All address balances
- Transaction history

## Recommended Solutions

### Linux: LUKS (Recommended)
```bash
# Create encrypted partition
cryptsetup luksFormat /dev/sdb1
cryptsetup open /dev/sdb1 xai-data

# Format and mount
mkfs.ext4 /dev/mapper/xai-data
mount /dev/mapper/xai-data /var/lib/xai
```

### macOS: FileVault
Enable FileVault in System Preferences > Security & Privacy.

### Windows: BitLocker
Enable BitLocker for the drive containing XAI data.

### Cloud Deployments
- AWS: Use encrypted EBS volumes
- GCP: Enable disk encryption for persistent disks
- Azure: Enable Azure Disk Encryption

## Application-Level Encryption

XAI provides additional defense-in-depth via checkpoint encryption:

```bash
# Generate encryption key
python3 -c "from xai.core.security.checkpoint_encryption import CheckpointEncryption; print(CheckpointEncryption.generate_key())"

# Set environment variable
export XAI_CHECKPOINT_ENCRYPTION_KEY="<generated-key>"
```

Checkpoint UTXO data is encrypted with AES-128-CBC + HMAC-SHA256 (Fernet).

## Verification

Check encryption status:
```bash
# Linux - verify LUKS
lsblk -o NAME,FSTYPE,MOUNTPOINT | grep crypt

# Check XAI checkpoint encryption
grep "_encrypted" /var/lib/xai/data/checkpoints/*.json
```

## Compliance Notes

- PCI-DSS: Requires encryption of stored cardholder data
- GDPR: Recommends encryption for personal data protection
- SOC 2: Encryption at rest is a common control
