# Security Implementation Quick Reference

Quick reference guide for the security implementations completed in this session.

## Wallet Encryption (AES-256-GCM)

### Export Encrypted Wallet
```bash
python src/xai/wallet/cli.py export \
  --address TXAI123abc... \
  --private-key abc123... \
  --encrypt
```

**Security Features**:
- AES-256-GCM authenticated encryption
- PBKDF2-HMAC-SHA256 (600,000 iterations)
- 32-byte random salt per export
- 12-byte random nonce per export
- HMAC-SHA256 integrity signature
- File permissions: 0600 (owner only)

### Import Encrypted Wallet
```bash
python src/xai/wallet/cli.py import \
  --file wallet_TXAI123a.enc
```

**Validation Checks**:
- HMAC signature verification (detects tampering)
- AES-GCM authentication tag (detects corruption)
- Password verification through decryption
- Version compatibility check

### File Format (v2.0)
```json
{
  "version": "2.0",
  "algorithm": "AES-256-GCM",
  "kdf": "PBKDF2-HMAC-SHA256",
  "iterations": 600000,
  "encrypted_data": "base64-encoded-ciphertext",
  "salt": "base64-encoded-salt",
  "nonce": "base64-encoded-nonce",
  "hmac": "base64-encoded-signature"
}
```

---

## Explorer Security

### CSRF Protection

**Template Usage**:
```html
<form method="POST" action="/search">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <!-- other form fields -->
</form>
```

**API Usage**:
```python
@app.route("/api/action", methods=["POST"])
@csrf_required
def protected_action():
    # CSRF token automatically validated
    pass
```

**JavaScript/AJAX**:
```javascript
fetch('/api/action', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': getCsrfToken(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
```

### Rate Limiting

**Apply to Endpoint**:
```python
@app.route("/api/resource")
@rate_limit(max_requests=60, window=60)  # 60 req/min
def resource():
    pass
```

**Rate Limit Response (429)**:
```json
{
  "error": "Rate limit exceeded. Please try again later.",
  "retry_after": 42
}
```

**Common Limits**:
- Search endpoints: 30/minute
- API stats: 60/minute
- Health checks: 120/minute
- Dashboard: 60/minute

### Input Validation

**Search Query Validation**:
```python
# Automatic validation in search endpoint:
- Max length: 200 characters
- Allowed chars: [a-zA-Z0-9]
- Block numbers: 0 to 10,000,000
- Transaction IDs: exactly 64 hex chars
- Addresses: XAI/TXAI prefix, 10-100 chars
```

**Manual Validation Pattern**:
```python
import re

def validate_address(address: str) -> bool:
    if not address:
        return False
    if not (address.startswith("XAI") or address.startswith("TXAI")):
        return False
    if len(address) < 10 or len(address) > 100:
        return False
    return True

def validate_txid(txid: str) -> bool:
    if not txid or len(txid) != 64:
        return False
    return all(c in '0123456789abcdefABCDEF' for c in txid)
```

### Secure Session Cookies

**Configuration** (already applied):
```python
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=3600, # 1 hour
)
```

**Requirements**:
- HTTPS required for production (SESSION_COOKIE_SECURE)
- Configure reverse proxy with SSL/TLS
- Use strong secret key (256-bit random)

---

## Threshold Signature Scheme (TSS)

### Generate Distributed Keys

```python
from xai.security.tss_production import ProductionTSS

tss = ProductionTSS()

# Generate keys for 5 participants, threshold of 3
key_shares, master_public_key = tss.generate_distributed_keys(
    num_participants=5,
    threshold=3
)

# Distribute key_shares[i] to participant i (secure channel required)
```

### Create and Combine Signatures

```python
# Each participant creates partial signature
partial_sigs = []
for i in range(3):  # threshold participants
    key_share = key_shares[i]
    r, s_partial = tss.create_partial_signature(key_share, message)
    partial_sigs.append((i, key_share, (r, s_partial)))

# Combine partial signatures
combined_signature = tss.combine_partial_signatures(
    partial_sigs,
    threshold=3
)

# Verify
is_valid = tss.verify_threshold_signature(
    master_public_key,
    message,
    combined_signature
)
```

### Shamir's Secret Sharing

```python
from xai.security.tss_production import ShamirSecretSharing

sss = ShamirSecretSharing()

# Split secret into shares
secret = 12345678901234567890
shares = sss.split_secret(
    secret=secret,
    threshold=3,
    num_shares=5
)

# Reconstruct from any 3 shares
reconstructed = sss.reconstruct_secret(shares[0:3])
assert reconstructed == secret

# Any combination of threshold shares works
reconstructed2 = sss.reconstruct_secret([shares[1], shares[3], shares[4]])
assert reconstructed2 == secret
```

---

## Security Best Practices Applied

### Cryptographically Secure Random Numbers

```python
import secrets

# Generate random bytes
random_bytes = secrets.token_bytes(32)

# Generate random hex string
random_hex = secrets.token_hex(32)  # 64 hex chars

# Generate random integer
random_int = secrets.randbelow(max_value)
```

**❌ DON'T USE**:
```python
import random  # NOT cryptographically secure!
random.randint(0, 100)  # Predictable!
```

### Constant-Time Comparisons

```python
import hmac

# Prevent timing attacks
def validate_token(provided, expected):
    return hmac.compare_digest(provided, expected)
```

**❌ DON'T USE**:
```python
# Timing attack vulnerable!
if provided == expected:
    return True
```

### Password Validation

```python
import getpass

def get_password():
    password = getpass.getpass("Enter password: ")

    # Minimum length
    if len(password) < 12:
        raise ValueError("Password too short (min 12 chars)")

    # Optional: complexity requirements
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        raise ValueError("Password must contain upper, lower, and digit")

    return password
```

### Exception Handling

```python
import requests
import logging

# ✅ GOOD: Specific exceptions
def fetch_data(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Network error: {e}")
        return None
    except (ValueError, KeyError) as e:
        logging.error(f"Data format error: {e}")
        return None

# ❌ BAD: Bare except
def fetch_data_bad(url):
    try:
        response = requests.get(url)
        return response.json()
    except:  # Catches everything, including KeyboardInterrupt!
        pass
```

---

## Testing Commands

### Test Wallet Encryption
```bash
# Generate wallet
python src/xai/wallet/cli.py generate-address --json > wallet.json

# Extract credentials
ADDRESS=$(jq -r '.address' wallet.json)
PRIVKEY=$(jq -r '.private_key' wallet.json)

# Test encryption
python src/xai/wallet/cli.py export \
  --address "$ADDRESS" \
  --private-key "$PRIVKEY" \
  --encrypt

# Test import (correct password)
python src/xai/wallet/cli.py import \
  --file "wallet_${ADDRESS:0:8}.enc"

# Test tampering detection
# Manually modify .enc file, then import (should fail with integrity error)
```

### Test Rate Limiting
```bash
# Hammer endpoint (should get 429 after limit)
for i in {1..70}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8082/api/stats
  sleep 0.5
done
```

### Test CSRF Protection
```bash
# Should fail (no CSRF token)
curl -X POST http://localhost:8082/search \
  -d "query=test" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Should succeed (with valid token - need to get from session)
# See browser dev tools for session cookie and CSRF token
```

### Test Input Validation
```bash
# Valid searches
curl -X POST http://localhost:8082/search -d "query=12345"  # block number
curl -X POST http://localhost:8082/search -d "query=abc123..."  # txid (64 chars)
curl -X POST http://localhost:8082/search -d "query=XAI123abc"  # address

# Invalid searches (should fail)
curl -X POST http://localhost:8082/search -d "query=<script>"  # XSS attempt
curl -X POST http://localhost:8082/search -d "query=$(long_string_201_chars)"  # too long
curl -X POST http://localhost:8082/search -d "query='; DROP TABLE--"  # SQL injection
```

### Test TSS
```bash
# Run production TSS test suite
python src/xai/security/tss_production.py

# Expected output:
# ✓ Key generation successful
# ✓ Partial signatures created
# ✓ Shamir's Secret Sharing: 100% reconstruction accuracy
# ✓ Threshold enforcement working
# ✓ Various share combinations work
```

---

## Configuration Reference

### Required Environment Variables

```bash
# Flask secret key (generate once, keep secure!)
export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Explorer settings
export EXPLORER_HOST="127.0.0.1"  # Local only for security
export EXPLORER_PORT="8082"
export FLASK_DEBUG="False"  # ALWAYS False in production

# Node connection
export XAI_NODE_URL="http://localhost:12001"
```

### Nginx Reverse Proxy (for HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name explorer.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Security Monitoring

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/xai/explorer.log'),
        logging.StreamHandler()
    ]
)
```

### Key Metrics to Monitor

1. **Rate Limiting**:
   - Requests hitting rate limits
   - IPs with repeated limit violations
   - Peak request rates

2. **Authentication**:
   - Failed decryption attempts
   - Invalid CSRF tokens
   - Session expiration events

3. **Input Validation**:
   - Invalid input attempts
   - XSS/SQL injection attempts
   - Unusual query patterns

4. **Errors**:
   - Network failures
   - Data format errors
   - Unexpected exceptions

---

## Incident Response

### Suspected Wallet Compromise

1. Immediately rotate all keys
2. Export wallet with new encryption
3. Transfer funds to new address
4. Review system logs for unauthorized access
5. Check file modification times

### Rate Limit Bypass Attempt

1. Identify attacker IP from logs
2. Add to firewall block list
3. Review rate limit configuration
4. Consider implementing IP reputation checking

### CSRF Attack Detected

1. Review session logs for suspicious patterns
2. Invalidate all active sessions
3. Force users to re-authenticate
4. Review CSRF token generation/validation code

### Data Integrity Failure

1. Compare backups with current state
2. Check HMAC signatures on all encrypted files
3. Verify no unauthorized file modifications
4. Review access logs for unauthorized access

---

## Quick Troubleshooting

### "Invalid CSRF token" Error
- Check session cookie is being set
- Verify HTTPS is enabled (SESSION_COOKIE_SECURE)
- Ensure form includes csrf_token field
- Check browser isn't blocking cookies

### "Rate limit exceeded"
- Wait for rate limit window to reset
- Check client IP isn't being shared (NAT)
- Increase limits if legitimate use case
- Implement authentication for higher limits

### Wallet Decryption Fails
- Verify password is correct (case-sensitive)
- Check file wasn't corrupted
- Verify file format version compatibility
- Check HMAC signature (tampering detection)

### TSS Signature Combination Fails
- Ensure minimum threshold participants
- Verify all shares use same master public key
- Check share indices are unique
- Verify message hash matches across all participants

---

## Additional Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **NIST Cryptographic Standards**: https://csrc.nist.gov/
- **Flask Security**: https://flask.palletsprojects.com/en/latest/security/
- **Python Cryptography**: https://cryptography.io/

---

**Last Updated**: 2025-11-25
**Version**: 1.0
