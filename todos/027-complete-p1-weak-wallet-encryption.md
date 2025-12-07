# Weak Legacy Wallet Encryption - Private Key Exposure

---
status: pending
priority: p1
issue_id: 027
tags: [security, wallet, encryption, cryptography, code-review]
dependencies: []
---

## Problem Statement

Legacy wallet encryption uses weak SHA256-only key derivation (no salt, single iteration), making it vulnerable to brute force attacks. While deprecated, old wallets remain at risk and the weak methods are still exposed.

## Findings

### Location
**File:** `src/xai/core/wallet.py` (Lines 293-322, 600-607)

### Evidence

```python
def _encrypt(self, data: str, password: str) -> str:
    """SECURITY NOTE: This method uses weak key derivation (SHA256 only, no salt,
    single iteration). It is DEPRECATED..."""
    # WEAK: No salt, no iterations, no key stretching
    key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data.decode()
```

### Vulnerability Analysis

| Property | Current (Legacy) | Required | Status |
|----------|-----------------|----------|--------|
| Key Derivation | SHA256 | PBKDF2/Argon2 | ❌ FAIL |
| Salt | None | 16+ bytes | ❌ FAIL |
| Iterations | 1 | 100,000+ | ❌ FAIL |
| Time to Crack | ~1 second | ~1 year | ❌ FAIL |

### Attack Scenario

1. Attacker obtains encrypted wallet file (backup, cloud sync, etc.)
2. Brute force password with GPU: 10 billion SHA256/sec
3. Common 8-char password cracked in < 1 minute
4. Private keys extracted, funds stolen

### Impact

- **Private Key Exposure**: All legacy wallets vulnerable
- **Fund Theft**: Attacker can drain wallet after cracking password
- **No Recovery**: Stolen cryptocurrency cannot be recovered

## Proposed Solutions

### Option A: Forced Migration with Secure Encryption (Recommended)
**Effort:** Medium | **Risk:** Low

```python
class WalletMigrator:
    """Force migration from legacy to secure encryption."""

    @staticmethod
    def needs_migration(wallet_file: str) -> bool:
        """Check if wallet uses legacy weak encryption."""
        with open(wallet_file, "r") as f:
            data = json.load(f)

        # Legacy wallets don't have version field
        return "version" not in data or data.get("version", 0) < 2

    @staticmethod
    def migrate_wallet(wallet_file: str, password: str) -> None:
        """Migrate wallet to secure encryption."""
        # Load with legacy method
        wallet = Wallet._legacy_load(wallet_file, password)

        # Create backup
        backup_path = wallet_file + f".backup.{int(time.time())}"
        shutil.copy2(wallet_file, backup_path)

        try:
            # Re-save with secure encryption
            wallet.save_to_file(wallet_file, password)

            logger.security(
                "Wallet migrated to secure encryption",
                extra={
                    "event": "wallet.migration.success",
                    "address": wallet.address[:16] + "...",
                    "backup": backup_path
                }
            )
        except Exception as e:
            # Restore backup on failure
            shutil.move(backup_path, wallet_file)
            raise RuntimeError(f"Migration failed: {e}") from e
```

### Option B: Deprecation with Hard Deadline
**Effort:** Small | **Risk:** Medium

```python
class Wallet:
    LEGACY_ENCRYPTION_DEADLINE = datetime(2025, 3, 1)  # 3 months to migrate

    @classmethod
    def load_from_file(cls, filename: str, password: str) -> "Wallet":
        with open(filename, "r") as f:
            data = json.load(f)

        if cls._is_legacy_encryption(data):
            if datetime.now() > cls.LEGACY_ENCRYPTION_DEADLINE:
                raise SecurityError(
                    "Legacy wallet encryption no longer supported. "
                    "Please migrate using: xai-wallet migrate --file wallet.json"
                )

            logger.critical(
                "SECURITY WARNING: Wallet uses deprecated weak encryption!",
                extra={
                    "event": "wallet.legacy_encryption",
                    "deadline": cls.LEGACY_ENCRYPTION_DEADLINE.isoformat()
                }
            )
            # Continue loading but warn loudly

        # ... rest of loading logic
```

### Option C: Remove Legacy Methods Entirely
**Effort:** Small | **Risk:** High (breaks existing wallets)

Remove `_encrypt()` and `_decrypt()` methods entirely. Users must migrate manually.

## Recommended Action

Implement Option A with Option B as enforcement. Provide CLI tool for migration.

## Technical Details

**Secure Encryption Already Exists:**
The wallet already has `_encrypt_payload()` using PBKDF2 with 100k iterations:
```python
def _encrypt_payload(self, plaintext: str, password: str) -> Dict[str, str]:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,  # Strong key derivation
    )
    # ... AES-GCM encryption
```

**Migration CLI:**
```bash
# Check if migration needed
xai-wallet check-encryption --file wallet.json

# Migrate wallet
xai-wallet migrate --file wallet.json --password

# Batch migrate all wallets in directory
xai-wallet migrate-all --dir ~/.xai/wallets/
```

## Acceptance Criteria

- [ ] Migration tool implemented and tested
- [ ] Warning on legacy wallet load
- [ ] Hard deadline for legacy support
- [ ] Unit tests for migration
- [ ] Documentation for migration process
- [ ] Remove legacy methods after deadline

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by python-reviewer agent | Critical security vulnerability |

## Resources

- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [PBKDF2 Recommendation](https://www.nist.gov/publications/recommendation-password-based-key-derivation-part-1-storage-applications)
