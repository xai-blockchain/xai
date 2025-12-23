# Flask Secret Key Management

## Overview

The XAI blockchain node uses Flask for its API endpoints. Flask requires a secret key for session management and CSRF protection. This document explains how the secret key is managed securely.

## Implementation

The `FlaskSecretManager` class (`src/xai/core/flask_secret_manager.py`) provides:

1. **Environment variable override** (for production)
2. **Persistent file storage** (for development)
3. **Automatic generation** (secure fallback)
4. **Proper file permissions** (0600 - owner read/write only)
5. **Security warnings** (when using auto-generated keys)

## Priority Order

The secret key is loaded in this order:

1. `XAI_SECRET_KEY` environment variable (highest priority)
2. `FLASK_SECRET_KEY` environment variable (compatibility)
3. `~/.xai/.secret_key` file (persistent storage)
4. Auto-generate and persist new key (secure fallback)

## Production Deployment

**ALWAYS set the secret key via environment variable in production:**

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set environment variable (add to your .env or systemd service)
export XAI_SECRET_KEY=your_generated_key_here

# Or use FLASK_SECRET_KEY for compatibility
export FLASK_SECRET_KEY=your_generated_key_here
```

## Development Usage

For development, the secret key is automatically generated and persisted to `~/.xai/.secret_key`:

```python
from xai.core.flask_secret_manager import get_flask_secret_key

# Get or generate secret key
secret_key = get_flask_secret_key()
app.secret_key = secret_key
```

The key persists across restarts, preventing session invalidation.

## Security Features

### Cryptographically Secure Generation
- Uses `secrets.token_hex(32)` for 256-bit security
- 64-character hex string (32 bytes)

### File Permissions
- Secret key file has `0600` permissions (owner read/write only)
- Prevents unauthorized access

### No Key Logging
- The actual key value is never logged
- Only the source (env var or file) is logged

### Key Rotation
```python
from xai.core.flask_secret_manager import FlaskSecretManager

manager = FlaskSecretManager()
new_key = manager.rotate_secret_key()
# WARNING: This invalidates all existing sessions
```

## Verification

Check if secret key is properly configured:

```bash
# Verify file exists and has correct permissions
ls -la ~/.xai/.secret_key

# Should show: -rw------- (0600 permissions)
# Should be 64 bytes (64 hex characters)

# Test the manager
python3 -c "from xai.core.flask_secret_manager import get_flask_secret_key; print('OK' if len(get_flask_secret_key()) == 64 else 'FAIL')"
```

## Configuration

Add to `.env` file:

```bash
# Flask secret key for session management
# For production, ALWAYS set this to a secure value
# Alternative names: FLASK_SECRET_KEY (XAI_SECRET_KEY takes precedence)
XAI_SECRET_KEY=your_secret_key_here
```

## Security Warnings

If the key is auto-generated, you'll see a warning in the logs:

```
WARNING: Generated new Flask secret key and saved to ~/.xai/.secret_key.
For production, set XAI_SECRET_KEY or FLASK_SECRET_KEY environment variable instead.
```

**This is expected for development but should be addressed in production.**
