# XAI Web Wallet Security Documentation

## Overview

This document provides comprehensive documentation of all security features implemented in the XAI Web Wallet, including configuration, deployment, and operational guidelines.

## Table of Contents

1. [Security Features](#security-features)
2. [Configuration](#configuration)
3. [Deployment Checklist](#deployment-checklist)
4. [Usage Examples](#usage-examples)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Security Features

### 1. Rate Limiting

Rate limiting protects the API from abuse, denial-of-service attacks, and brute force attempts.

#### Features:
- **IP-based Rate Limiting**: Tracks requests by client IP address
- **Endpoint-specific Limits**: Different rate limits for sensitive endpoints
- **Sliding Window Algorithm**: Accurate request tracking over time
- **Automatic IP Blocking**: Temporary blocks for suspicious activity
- **Configurable Thresholds**: Easy adjustment via SecurityConfig

#### Endpoints with Special Limits:
```
/wallet/create: 5 requests per hour (for account creation)
/wallet/send: 20 requests per minute (for sending transactions)
/mine: 100 requests per minute (for mining operations)
/transaction: 50 requests per minute (for transaction queries)
```

#### Configuration:
```python
from xai.core.security_middleware import SecurityConfig

config = SecurityConfig()
config.RATE_LIMIT_ENABLED = True
config.RATE_LIMIT_REQUESTS = 120
config.RATE_LIMIT_WINDOW = 60  # seconds
config.BLOCK_DURATION = 900  # 15 minutes
config.SUSPICIOUS_ACTIVITY_THRESHOLD = 5
```

#### Response on Rate Limit Exceeded:
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```
Status Code: 429 (Too Many Requests)

---

### 2. CSRF Token Protection

Cross-Site Request Forgery (CSRF) protection prevents unauthorized actions from external websites.

#### Features:
- **Token Generation**: Cryptographically secure tokens (32 bytes)
- **Session Binding**: Tokens tied to specific user sessions
- **Token Expiry**: Automatic expiration after 24 hours
- **Stateful Validation**: Server-side token validation
- **Exempt Endpoints**: GET requests and safe endpoints excluded

#### Implementation:
```python
# 1. Get CSRF Token (before form submission)
GET /csrf-token
Response: {
  "csrf_token": "a1b2c3d4e5f6...",
  "session_id": "session_123..."
}

# 2. Include Token in Request
POST /wallet/create
Headers: {
  "X-CSRF-Token": "a1b2c3d4e5f6..."
}
Body: {
  "wallet_name": "my_wallet"
}
```

#### Exempt Endpoints (read-only operations):
```
/health
/metrics
/stats
/blocks
/transaction
/balance
/peer
/csrf-token
```

#### Configuration:
```python
config.CSRF_ENABLED = True
config.CSRF_TOKEN_LENGTH = 32
config.CSRF_EXEMPT_ENDPOINTS = [...]
```

---

### 3. CORS (Cross-Origin Resource Sharing)

CORS configuration with whitelist prevents unauthorized cross-origin requests.

#### Features:
- **Origin Whitelist**: Only specified origins allowed
- **Method Restrictions**: Limited HTTP methods (GET, POST, PUT, DELETE)
- **Credential Support**: With HttpOnly cookie support
- **Preflight Handling**: Automatic OPTIONS request handling
- **Max Age Caching**: Reduce preflight requests

#### Configuration:
```python
config.CORS_ENABLED = True
config.CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "https://wallet.xai.network"
]
config.CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
config.CORS_ALLOW_CREDENTIALS = True
config.CORS_MAX_AGE = 3600  # 1 hour
```

#### Example Request:
```
Origin: http://localhost:3000
Method: POST
Path: /wallet/send

Response Headers:
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Max-Age: 3600
```

---

### 4. Security Headers

HTTP security headers protect against common web vulnerabilities.

#### Implemented Headers:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevents MIME type sniffing |
| X-Frame-Options | DENY | Prevents clickjacking attacks |
| X-XSS-Protection | 1; mode=block | Enables browser XSS protection |
| Strict-Transport-Security | max-age=31536000 | Enforces HTTPS for 1 year |
| Content-Security-Policy | (see below) | Comprehensive XSS/injection protection |
| Referrer-Policy | strict-origin-when-cross-origin | Controls referrer leakage |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | Restricts browser features |

#### Content Security Policy (CSP):
```
default-src 'self'
  - Only load resources from same origin

script-src 'self' 'unsafe-inline'
  - Allow scripts from same origin and inline

style-src 'self' 'unsafe-inline'
  - Allow stylesheets from same origin and inline

img-src 'self' data: https:
  - Allow images from same origin, data URIs, and HTTPS

font-src 'self'
  - Allow fonts from same origin only

connect-src 'self'
  - Allow AJAX/WebSocket to same origin

frame-ancestors 'none'
  - Prevent framing in any context

base-uri 'self'
  - Restrict base URL changes

form-action 'self'
  - Restrict form submissions to same origin
```

#### Configuration:
```python
config.SECURITY_HEADERS_ENABLED = True
config.CONTENT_SECURITY_POLICY = "default-src 'self'; ..."
```

---

### 5. Input Validation & Sanitization

Comprehensive input validation prevents injection attacks.

#### Features:
- **String Sanitization**: HTML escaping and length checks
- **SQL Injection Detection**: Pattern-based SQL injection detection
- **XSS Prevention**: Dangerous HTML/JavaScript detection
- **JSON Validation**: Recursive JSON structure validation
- **Type Checking**: Strict type validation
- **Depth Limiting**: Prevent deeply nested structures

#### Validation Examples:
```python
from xai.core.security_middleware import InputSanitizer

# Sanitize user input
try:
    clean_name = InputSanitizer.sanitize_string(user_name, max_length=100)
except ValueError as e:
    # Handle validation error
    print(f"Invalid input: {e}")

# Sanitize JSON data
try:
    clean_data = InputSanitizer.sanitize_json(request_json)
except ValueError as e:
    # Handle validation error
    print(f"Invalid JSON: {e}")

# Detect SQL injection
try:
    InputSanitizer.sanitize_sql_input(query_param)
except ValueError as e:
    # SQL injection detected
    print(f"Suspicious input: {e}")
```

#### Dangerous Patterns Detected:
- `<script>` tags
- `javascript:` protocol
- Event handlers (`onclick=`, `onload=`, etc.)
- `<iframe>` tags
- `<embed>` tags
- SQL keywords (UNION, DROP, DELETE, etc.)
- SQL comment syntax (--,  #, ;)

#### Configuration:
```python
config.MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
config.MAX_HEADER_SIZE = 8192  # 8KB
config.MAX_URL_LENGTH = 2048  # 2KB
```

---

### 6. Session Management

Secure session management with timeout and validation.

#### Features:
- **Secure Session Creation**: Cryptographically secure tokens
- **Session Timeout**: Automatic session expiration
- **IP Validation**: Detect session hijacking attempts
- **User Agent Tracking**: Additional session security
- **Session Revocation**: Immediate session termination

#### Usage:
```python
from xai.core.security_middleware import SecurityMiddleware

middleware = SecurityMiddleware(app)

# Create session
session_token = middleware.session_manager.create_session(
    user_id="user123",
    metadata={"login_type": "web"}
)

# Validate session
is_valid, session_data = middleware.session_manager.validate_session(session_token)
if is_valid:
    print(f"Session valid for user: {session_data['user_id']}")

# Destroy session (logout)
middleware.session_manager.destroy_session(session_token)
```

#### Session Cookie Configuration:
```python
config.SESSION_COOKIE_SECURE = True        # HTTPS only
config.SESSION_COOKIE_HTTPONLY = True      # Not accessible to JavaScript
config.SESSION_COOKIE_SAMESITE = "Strict"  # Only same-site requests
config.SESSION_COOKIE_NAME = "xai_wallet_session"
config.SESSION_TIMEOUT = 1800  # 30 minutes
```

#### Session Data Structure:
```json
{
  "user_id": "user123",
  "created_at": "2024-01-01T12:00:00Z",
  "last_activity": "2024-01-01T12:15:00Z",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "metadata": {}
}
```

---

### 7. Two-Factor Authentication (2FA) - TOTP

Time-based One-Time Password (TOTP) implementation for enhanced security.

#### Features:
- **TOTP Standard**: RFC 6238 compliant
- **QR Code Generation**: For easy authenticator app setup
- **Backup Codes**: Recovery codes for account access
- **Time Window**: Configurable time window for validation
- **Multiple Providers**: Compatible with Google Authenticator, Authy, Microsoft Authenticator

#### Installation:
```bash
pip install pyotp qrcode
```

#### Usage:
```python
from xai.core.security_middleware import TOTPManager

totp = TOTPManager()

# Generate secret for new user
if totp.AVAILABLE:
    secret_data = totp.generate_secret("user123")
    print(f"Secret: {secret_data['secret']}")
    print(f"QR URI: {secret_data['uri']}")

    # Store secret_data['secret'] in database

    # Later: verify TOTP token from authenticator
    is_valid = totp.verify_token("user123", "123456")
    if is_valid:
        print("2FA successful")

    # Generate backup codes
    backup_codes = totp.get_backup_codes("user123", count=10)
```

#### TOTP Configuration:
```python
config.TOTP_ENABLED = True
config.TOTP_WINDOW = 1  # Allow 1 TOTP step drift (±30 seconds)
config.TOTP_PERIOD = 30  # 30 second TOTP period (standard)
```

#### QR Code Example:
```
otpauth://totp/user123?secret=ABCD1234...&issuer=XAI-Wallet
```

---

## Configuration

### SecurityConfig Class

All security features are configured via the `SecurityConfig` class:

```python
from xai.core.security_middleware import SecurityConfig

# Create custom configuration
config = SecurityConfig()

# Rate limiting
config.RATE_LIMIT_ENABLED = True
config.RATE_LIMIT_REQUESTS = 120
config.RATE_LIMIT_WINDOW = 60

# CSRF
config.CSRF_ENABLED = True
config.CSRF_TOKEN_LENGTH = 32

# CORS
config.CORS_ENABLED = True
config.CORS_ORIGINS = ["http://localhost:3000"]

# Session
config.SESSION_TIMEOUT = 1800
config.SESSION_COOKIE_SECURE = True

# 2FA
config.TOTP_ENABLED = True
```

### Environment Variables

```bash
# Flask secret key
export FLASK_SECRET_KEY="your-secure-random-key"

# API configuration
export XAI_API_URL="http://localhost:5000"

# CORS origins
export CORS_ORIGINS="http://localhost:3000,https://wallet.xai.network"

# Session timeout (seconds)
export SESSION_TIMEOUT=1800

# Rate limiting
export RATE_LIMIT_REQUESTS=120
export RATE_LIMIT_WINDOW=60
```

---

## Deployment Checklist

### Pre-Deployment Security Verification

- [ ] **Secret Keys**
  - [ ] Generate strong Flask secret key: `python -c "import secrets; print(secrets.token_hex(32))"`
  - [ ] Set `FLASK_SECRET_KEY` environment variable
  - [ ] Never commit secret keys to repository

- [ ] **HTTPS/TLS**
  - [ ] Obtain valid SSL/TLS certificate
  - [ ] Configure reverse proxy (nginx/Apache) with HTTPS
  - [ ] Set `SESSION_COOKIE_SECURE = True`
  - [ ] Enable HSTS header
  - [ ] Redirect HTTP to HTTPS

- [ ] **CORS Configuration**
  - [ ] Review whitelist of allowed origins
  - [ ] Remove localhost origins for production
  - [ ] Only include trusted domains
  - [ ] Test with actual domain names

- [ ] **Rate Limiting**
  - [ ] Adjust thresholds based on expected traffic
  - [ ] Monitor for legitimate users hitting limits
  - [ ] Consider endpoint-specific adjustments
  - [ ] Test blocking mechanism

- [ ] **Security Headers**
  - [ ] Verify CSP doesn't break functionality
  - [ ] Test with actual frontend code
  - [ ] Adjust CSP if needed for third-party resources
  - [ ] Validate with security scanner

- [ ] **Session Management**
  - [ ] Set appropriate timeout duration
  - [ ] Configure secure cookie flags
  - [ ] Test session expiration
  - [ ] Verify IP consistency checks

- [ ] **2FA Setup**
  - [ ] Install pyotp: `pip install pyotp qrcode`
  - [ ] Generate backup codes for admin accounts
  - [ ] Store backup codes securely
  - [ ] Test TOTP verification flow

- [ ] **Logging & Monitoring**
  - [ ] Configure centralized logging
  - [ ] Set up security alerts
  - [ ] Monitor rate limit events
  - [ ] Track CSRF/authentication failures
  - [ ] Archive logs for audit trail

- [ ] **Database Security**
  - [ ] Use strong database passwords
  - [ ] Enable database encryption
  - [ ] Restrict database access
  - [ ] Regular backups with encryption
  - [ ] Test backup restoration

- [ ] **API Security**
  - [ ] Remove debug mode: `DEBUG = False`
  - [ ] Hide sensitive error messages
  - [ ] Implement proper error handling
  - [ ] Don't expose stack traces to users

- [ ] **Dependencies**
  - [ ] Audit all dependencies: `pip audit`
  - [ ] Keep packages updated
  - [ ] Use requirements.txt with pinned versions
  - [ ] Test updates in staging first

- [ ] **Testing**
  - [ ] Run security tests
  - [ ] Test rate limiting
  - [ ] Test CSRF protection
  - [ ] Test input validation
  - [ ] Test CORS restrictions
  - [ ] Test session management

- [ ] **Infrastructure**
  - [ ] Configure firewall rules
  - [ ] Enable WAF (Web Application Firewall)
  - [ ] Set up DDoS protection
  - [ ] Configure load balancer
  - [ ] Test failover mechanisms

---

## Usage Examples

### Example 1: Basic Flask Integration

```python
from flask import Flask
from xai.core.security_middleware import setup_security_middleware, SecurityConfig

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Setup security middleware
security_config = SecurityConfig()
security_config.CORS_ORIGINS = ["http://localhost:3000"]
security_middleware = setup_security_middleware(app, config=security_config)

@app.route("/wallet/create", methods=["POST"])
def create_wallet():
    # CSRF protection automatic
    # Rate limiting automatic
    # Input validation available
    return {"status": "wallet_created"}

if __name__ == "__main__":
    app.run(ssl_context="adhoc")  # Use HTTPS in production
```

### Example 2: Protected Endpoint with Authentication

```python
from flask import request, jsonify

@app.route("/wallet/send", methods=["POST"])
@security_middleware.require_auth
def send_transaction():
    # Session automatically validated by decorator
    user_id = request.session_data["user_id"]

    # Get CSRF token from request (middleware validates)
    data = request.get_json()

    # Process transaction
    return jsonify({"transaction_id": "tx123"})
```

### Example 3: Login Endpoint

```python
# Use the built-in login endpoint
# POST /login
# {
#   "user_id": "user123",
#   "password": "secure_password"
# }

# Response:
# {
#   "session_token": "abc123...",
#   "user_id": "user123",
#   "timeout": 1800
# }

# Use token in Authorization header
# Authorization: Bearer abc123...
```

### Example 4: CSRF Token Workflow

```javascript
// 1. Get CSRF token before form submission
async function getCsrfToken() {
  const response = await fetch('/csrf-token');
  const data = await response.json();
  return data.csrf_token;
}

// 2. Include token in form submission
async function submitForm() {
  const csrfToken = await getCsrfToken();

  const response = await fetch('/wallet/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken
    },
    body: JSON.stringify({
      wallet_name: 'my_wallet'
    })
  });

  return response.json();
}
```

### Example 5: TOTP Setup Flow

```python
# Step 1: Generate TOTP secret
secret_data = security_middleware.totp_manager.generate_secret("user123")
# Display QR code to user: secret_data['uri']
# Show secret: secret_data['secret']

# Step 2: User adds to authenticator app (Google Authenticator, Authy, etc.)

# Step 3: Verify TOTP token from user
user_token = "123456"  # 6-digit code from authenticator
if security_middleware.totp_manager.verify_token("user123", user_token):
    # Enable 2FA for user
    enable_2fa("user123")
    # Generate backup codes
    backup_codes = security_middleware.totp_manager.get_backup_codes("user123")
    # Show backup codes to user
    display_backup_codes(backup_codes)

# Step 4: Verify on login
if security_middleware.totp_manager.verify_token("user123", login_token):
    # Create session
    session_token = security_middleware.session_manager.create_session("user123")
    return {"session_token": session_token}
```

---

## Monitoring & Logging

### Security Logger

The security middleware provides detailed logging of security events:

```python
import logging
from xai.core.security_middleware import security_logger

# Configure logging level
security_logger.setLevel(logging.INFO)

# Log entries are in structured JSON format
# Example:
# {
#   "timestamp": "2024-01-01T12:00:00Z",
#   "event_type": "csrf_mismatch",
#   "severity": "WARNING",
#   "details": {...}
# }
```

### Key Events Logged

| Event | Severity | Details |
|-------|----------|---------|
| Rate limit exceeded | WARNING | IP address, endpoint, timestamp |
| CSRF token mismatch | WARNING | Session ID, IP address |
| CSRF token invalid | WARNING | IP address, attempt count |
| IP blocked | WARNING | IP address, reason, duration |
| Failed attempts | INFO | IP address, endpoint, count |
| Session created | INFO | User ID, IP address |
| Session expired | INFO | User ID, session duration |
| Input validation failure | WARNING | Field name, violation type |
| SQL injection attempt | CRITICAL | Pattern matched, user input |
| XSS attempt | CRITICAL | Dangerous pattern, field name |

### Monitoring Dashboard

Monitor these metrics:

```
- Requests per second (RPS)
- Rate limit violations per minute
- CSRF failures per hour
- Session count
- Active IP addresses
- Blocked IP addresses
- Average response time
- Error rate
```

### Alerting Rules

Configure alerts for:

1. **Rate Limit Spikes**: > 10 violations per minute
2. **CSRF Failures**: > 5 failures from same IP
3. **Multiple Login Failures**: > 3 failed attempts
4. **Unusual Access Patterns**: Access at unusual times/frequencies
5. **Security Header Violations**: Missing/invalid headers
6. **Session Anomalies**: Unusual session counts or durations

---

## Troubleshooting

### Common Issues

#### Issue: CSRF Token Missing

**Error**: `CSRFTokenInvalid("CSRF token missing")`

**Solution**:
1. Call `/csrf-token` endpoint first
2. Include `X-CSRF-Token` header in requests
3. Check header spelling and case

```javascript
// Correct
headers: {
  'X-CSRF-Token': token
}

// Incorrect (wrong case)
headers: {
  'X-csrf-token': token  // Will fail
}
```

#### Issue: Rate Limit Exceeded

**Error**: 429 Too Many Requests

**Solution**:
1. Wait for rate limit window to pass
2. Reduce request frequency
3. Check for application retry loops
4. Contact support if legitimate user

```python
# Debug rate limiting
client_ip = request.remote_addr
is_blocked = security_middleware.rate_limiter.is_blocked(client_ip)
if is_blocked:
    # IP is temporarily blocked
    pass
```

#### Issue: CORS Error in Browser

**Error**: `Cross-Origin Request Blocked`

**Solution**:
1. Add origin to `CORS_ORIGINS` whitelist
2. Verify origin matches exactly (protocol, domain, port)
3. Include credentials in fetch:

```javascript
// Include credentials
fetch(url, {
  credentials: 'include',
  headers: {
    'X-CSRF-Token': csrfToken
  }
})
```

#### Issue: Session Expiration During Use

**Error**: `Invalid or expired session`

**Solution**:
1. Increase `SESSION_TIMEOUT` if needed
2. Implement session refresh mechanism
3. Monitor session activity
4. Prompt user before expiration

```python
# Refresh session
is_valid, session_data = session_manager.validate_session(token)
if is_valid:
    # Update last_activity
    session_data['last_activity'] = datetime.now(timezone.utc)
```

#### Issue: TOTP Not Available

**Error**: `TOTP not available - pyotp not installed`

**Solution**:
```bash
# Install TOTP dependencies
pip install pyotp qrcode

# Verify installation
python -c "import pyotp; print('TOTP available')"
```

#### Issue: Security Headers Missing

**Solution**:
1. Verify `SECURITY_HEADERS_ENABLED = True`
2. Check middleware is registered
3. Verify headers in response:

```bash
# Check response headers
curl -I https://localhost:5000/api/endpoint

# Should include:
# Strict-Transport-Security: max-age=31536000
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# etc.
```

---

## Security Best Practices

### 1. Secret Key Management

```python
# Good: Generate strong key
import secrets
secret_key = secrets.token_hex(32)  # 256-bit key

# Good: Use environment variable
import os
secret_key = os.environ.get('FLASK_SECRET_KEY')

# Bad: Hardcoded secret
app.secret_key = "my-secret-key"  # Insecure!

# Bad: Weak secret
app.secret_key = "password123"  # Too weak
```

### 2. HTTPS/TLS Configuration

```nginx
# nginx configuration
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Use modern TLS versions only
    ssl_protocols TLSv1.2 TLSv1.3;

    # Strong ciphers
    ssl_ciphers HIGH:!aNULL:!MD5;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

### 3. Password Storage

```python
# Never store plain passwords!

# Good: Use bcrypt for password hashing
from werkzeug.security import generate_password_hash, check_password_hash

# Hash password on registration
hashed = generate_password_hash(password, method='pbkdf2:sha256')

# Verify password on login
if check_password_hash(hashed, password):
    # Password is correct
    pass
```

### 4. Rate Limiting Best Practices

```python
# Adjust limits based on traffic
config.ENDPOINT_LIMITS = {
    "/wallet/create": (5, 3600),      # 5/hour for registrations
    "/wallet/send": (20, 60),         # 20/minute for sends
    "/wallet/balance": (100, 60),     # 100/minute for queries
}

# Monitor and adjust
# If legitimate users hit limits, increase threshold
# If abuse occurs, decrease threshold
```

### 5. CORS Whitelist Management

```python
# Maintain whitelist in configuration file
# config.yml or environment variable

CORS_ORIGINS = [
    "https://wallet.xai.network",       # Production
    "https://app.xai.network",
    "https://staging.xai.network",      # Staging
]

# Never include:
# - localhost in production
# - *  (wildcard)
# - Untrusted origins
```

### 6. CSP Policy Tuning

```python
# Start with strict policy
CSP = "default-src 'self'"

# Add resources as needed
# Example for Google Fonts:
CSP = "default-src 'self'; font-src 'self' fonts.googleapis.com"

# Never use 'unsafe-eval' or 'unsafe-inline' if possible
# Use nonces for inline scripts if necessary
```

### 7. Session Security

```python
# Always:
- Use HTTPS for session transmission
- Set HttpOnly flag (prevents JavaScript access)
- Set Secure flag (HTTPS only)
- Set SameSite attribute (Strict or Lax)
- Implement reasonable timeout
- Validate session IP
- Regenerate session ID on login

# Configuration:
SESSION_COOKIE_SECURE = True          # HTTPS only
SESSION_COOKIE_HTTPONLY = True        # No JavaScript access
SESSION_COOKIE_SAMESITE = "Strict"    # Same-site only
SESSION_TIMEOUT = 1800                # 30 minutes
```

### 8. Logging Security

```python
# What to log:
- Failed authentication attempts
- Rate limit violations
- CSRF failures
- Suspicious input patterns
- Session creation/destruction
- Privilege escalation attempts
- Error conditions

# What NOT to log:
- Passwords
- Private keys
- Credit card numbers
- Personal information
- Session tokens
- API keys

# Configure log rotation
import logging.handlers
handler = logging.handlers.RotatingFileHandler(
    'security.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)

# Encrypt log files
# Store logs securely
# Retain logs for audit trail
```

### 9. Dependency Management

```bash
# Audit dependencies for vulnerabilities
pip audit

# Use pip-audit for continuous checking
pip install pip-audit
pip-audit

# Pin versions in requirements.txt
werkzeug==2.3.0          # Good
werkzeug>=2.0            # Bad: unpredictable
werkzeug                  # Worst: always latest

# Regularly update
pip list --outdated
pip install --upgrade package-name
```

### 10. Incident Response

```python
# On security incident:
1. Log detailed information
2. Alert security team
3. Block suspicious actors
4. Review access logs
5. Check for data breaches
6. Notify affected users
7. Implement remediation
8. Update security measures
9. Document incident
10. Post-incident review
```

---

## Support & Contact

For security issues or questions:

- Email: security@xai.network
- Security Advisory: SECURITY.md
- Bug Bounty: https://xai.network/security/bounty

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Flask Security](https://flask.palletsprojects.com/en/latest/security/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)

---

Last Updated: 2024-01-01
Version: 1.0.0
Status: Production Ready
