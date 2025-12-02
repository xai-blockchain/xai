# JWT Token Expiration Security

## Overview

The XAI blockchain API authentication implements production-grade JWT token expiration verification to minimize the attack window for stolen tokens.

## Security Features

### 1. Explicit Expiration Verification

**Setting:** `verify_exp=True` (explicitly enabled)

All JWT tokens are validated with explicit expiration checking. This ensures that expired tokens are immediately rejected, even if they have valid signatures.

```python
payload = jwt.decode(
    token,
    secret_key,
    algorithms=["HS256"],
    options={
        "verify_exp": True,  # CRITICAL: Verify expiration
        "verify_signature": True,
        "verify_iat": True,
    }
)
```

### 2. Clock Skew Tolerance

**Default:** 30 seconds

To handle minor clock drift between servers and clients, the system implements a 30-second leeway period. This prevents legitimate requests from failing due to small timing differences while maintaining security.

```python
manager = JWTAuthManager(
    secret_key="your-secret",
    clock_skew_seconds=30  # Configurable
)
```

**How it works:**
- Token expires at time T
- Token is still valid until T + 30 seconds
- After T + 30 seconds, token is rejected

### 3. Required Claims Validation

**Required claims:**
- `exp`: Expiration timestamp
- `sub`: Subject (user ID)
- `iat`: Issued-at timestamp

Tokens missing any required claim are rejected:

```python
options={
    "require": ["exp", "sub", "iat"],
}
```

### 4. Token Expiry Configuration

**Default values:**
- Access token: 1 hour
- Refresh token: 30 days

These can be configured per environment:

```python
# Development: Shorter expiry for testing
manager = JWTAuthManager(
    secret_key="dev-secret",
    token_expiry_hours=0.5,  # 30 minutes
    refresh_expiry_days=1     # 1 day
)

# Production: Standard expiry
manager = JWTAuthManager(
    secret_key="prod-secret",
    token_expiry_hours=1,     # 1 hour
    refresh_expiry_days=30    # 30 days
)
```

## Security Logging

All token validation failures are logged as security events for monitoring and auditing.

### Logged Events

1. **Expired Token Attempts**
   ```python
   {
       "event": "jwt_expired_token_attempt",
       "remote_addr": "192.168.1.100",
       "timestamp": "2025-12-01T12:00:00Z",
       "severity": "WARNING"
   }
   ```

2. **Invalid Token Attempts**
   ```python
   {
       "event": "jwt_invalid_token_attempt",
       "remote_addr": "192.168.1.100",
       "error": "Signature verification failed",
       "timestamp": "2025-12-01T12:00:00Z",
       "severity": "WARNING"
   }
   ```

3. **Revoked Token Attempts**
   ```python
   {
       "event": "jwt_revoked_token_attempt",
       "remote_addr": "192.168.1.100",
       "timestamp": "2025-12-01T12:00:00Z",
       "severity": "WARNING"
   }
   ```

4. **Insufficient Permissions**
   ```python
   {
       "event": "jwt_insufficient_permissions",
       "remote_addr": "192.168.1.100",
       "required_scope": "admin",
       "token_scope": "user",
       "timestamp": "2025-12-01T12:00:00Z",
       "severity": "WARNING"
   }
   ```

## Token Refresh Flow

To maintain continuous access without requiring re-authentication:

1. **Client** requests access with username/password
2. **Server** returns access token (1 hour) + refresh token (30 days)
3. **Client** uses access token for API requests
4. **Access token expires** after 1 hour
5. **Client** sends refresh token to `/auth/refresh` endpoint
6. **Server** validates refresh token and issues new access token
7. **Client** continues with new access token

### Example Flow

```python
# Initial authentication
access_token, refresh_token = manager.generate_token("user-123", scope="user")

# Use access token
request = make_request(headers={"Authorization": f"Bearer {access_token}"})
authorized, payload, error = manager.authorize_request(request)

# After 1 hour, access token expires
# Use refresh token to get new access token
success, new_access_token, error = manager.refresh_access_token(refresh_token)

# Continue with new access token
request = make_request(headers={"Authorization": f"Bearer {new_access_token}"})
authorized, payload, error = manager.authorize_request(request)
```

## Blacklist Management

Revoked tokens are added to an in-memory blacklist. For production:

### Current Implementation (In-Memory)

```python
manager.revoke_token(access_token)  # Add to blacklist
manager.cleanup_expired_tokens()    # Remove expired tokens from blacklist
```

### Production Recommendation

For distributed systems, use Redis with TTL:

```python
# Pseudo-code for Redis-based blacklist
redis_client.setex(
    f"blacklist:{token_hash}",
    token_remaining_ttl,  # Expires when token would expire anyway
    "revoked"
)
```

## Testing

Comprehensive test coverage ensures expiration verification works correctly:

```bash
pytest tests/xai_tests/unit/test_jwt_expiration.py -v
```

Test cases include:
- Valid token acceptance
- Expired token rejection
- Clock skew tolerance
- Missing required claims
- Security event logging
- Signature verification
- Algorithm validation
- Refresh token expiration
- Blacklist functionality

## Security Best Practices

### 1. Short Access Token Expiry
Keep access tokens short-lived (1 hour or less) to minimize the window of opportunity for attackers using stolen tokens.

### 2. Long Refresh Token Expiry
Use longer-lived refresh tokens (30 days) for user convenience, but implement proper rotation on use.

### 3. Secure Token Storage
- **Never** store tokens in localStorage (vulnerable to XSS)
- **Use** httpOnly cookies or secure session storage
- **Implement** CSRF protection for cookie-based auth

### 4. Token Rotation
Rotate refresh tokens on use to detect token theft:

```python
# On refresh, issue new refresh token
new_access, new_refresh = manager.generate_token(user_id, scope)
# Revoke old refresh token
manager.revoke_token(old_refresh_token)
```

### 5. Rate Limiting
Implement rate limiting on authentication endpoints to prevent brute force attacks.

### 6. Monitoring
Set up alerts for:
- High volume of expired token attempts (possible replay attack)
- Failed token validations from single IP
- Unusual refresh token usage patterns

## Error Messages

Clear, actionable error messages help with debugging while maintaining security:

- `"Token has expired"` - Token is past expiration time
- `"Token has been revoked"` - Token is in blacklist
- `"Invalid token: Signature verification failed"` - Wrong secret or tampered token
- `"Invalid token: Missing required claim: exp"` - Token missing expiration
- `"No JWT token provided"` - Authorization header missing
- `"Insufficient permissions. Required: admin"` - Scope validation failed

## Migration Guide

If upgrading from a system without expiration verification:

1. **Backup** existing tokens and blacklist
2. **Deploy** new code with `verify_exp=True`
3. **Monitor** logs for expired token attempts
4. **Notify** users if mass logout occurs
5. **Issue** new tokens with proper expiration

## References

- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
