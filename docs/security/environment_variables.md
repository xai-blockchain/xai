# Environment Variables and API Key Security

## Overview

All API keys and sensitive credentials in the XAI blockchain project **MUST** be loaded from environment variables. Hardcoding credentials in source code is a critical security vulnerability and is strictly forbidden.

## Security Policy

### ✅ Required Practice

```python
import os

# Load API key from environment
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

# Use the key
client = anthropic.Client(api_key=api_key)
```

### ❌ Forbidden Practice

```python
# NEVER DO THIS - Security violation!
api_key = "sk-ant-api03-xxxxxxxxxxxxx"  # FORBIDDEN
user_api_key = "YOUR_API_KEY_HERE"      # FORBIDDEN
```

## Environment Variables

### Required for AI Features

| Variable | Purpose | Where to Get It |
|----------|---------|-----------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API access | https://console.anthropic.com/ |
| `OPENAI_API_KEY` | OpenAI GPT API access (optional) | https://platform.openai.com/ |
| `GOOGLE_AI_API_KEY` | Google Gemini API access (optional) | https://makersuite.google.com/ |

### Configuration

```bash
# Set environment variable (Linux/Mac)
export ANTHROPIC_API_KEY='sk-ant-api03-your-actual-key-here'

# Set environment variable (Windows PowerShell)
$env:ANTHROPIC_API_KEY='sk-ant-api03-your-actual-key-here'

# Or create a .env file (see .env.example)
cp .env.example .env
# Edit .env with your actual values
```

### Using .env Files

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual credentials:
   ```bash
   # .env
   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
   OPENAI_API_KEY=sk-proj-your-openai-key-here
   ```

3. **CRITICAL**: Never commit `.env` to git!
   - `.env` is already in `.gitignore`
   - Only commit `.env.example` (template with no real keys)

## Running Demo Scripts

Demo scripts in `if __name__ == "__main__"` blocks require environment variables:

```bash
# Set API key first
export ANTHROPIC_API_KEY='your-key-here'

# Then run the demo
python -m xai.core.ai_trading_bot
python -m xai.core.secure_api_key_manager
python -m xai.core.ai_pool_with_strict_limits
```

If the environment variable is not set, you'll see:

```
⚠️  ERROR: ANTHROPIC_API_KEY environment variable not set
   Set your API key: export ANTHROPIC_API_KEY='your-key-here'
   Get your API key from: https://console.anthropic.com/
```

## Security Testing

A comprehensive security test suite ensures no credentials are hardcoded:

```bash
# Run security tests
pytest tests/xai_tests/security/test_no_hardcoded_credentials.py -v
```

The test suite checks for:
- Hardcoded API keys in source files
- Placeholder strings used as actual values
- `.env` files accidentally committed
- Proper environment variable usage in critical files
- API key validation functions exist

## API Key Validation

The project includes built-in validation to reject demo/placeholder keys:

```python
# From ai_trading_bot.py
INVALID_DEMO_KEYS = [
    "sk-ant-demo-key",
    "YOUR_ANTHROPIC_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "DEMO_KEY",
    "TEST_KEY",
    "PLACEHOLDER",
]

def validate_api_key(api_key: str) -> bool:
    """Validate that the API key is not a known demo/placeholder key."""
    if not api_key or not isinstance(api_key, str):
        raise ValueError("API key must be a non-empty string")

    if api_key in INVALID_DEMO_KEYS:
        raise ValueError(f"Invalid demo API key: {api_key}")

    # Additional validation...
```

## Best Practices

1. **Never hardcode credentials** - Always use `os.environ.get()`
2. **Use .env files locally** - Keep credentials out of source control
3. **Validate keys at runtime** - Reject demo/placeholder keys
4. **Fail securely** - Clear error messages when keys are missing
5. **Run security tests** - Before commits and in CI/CD
6. **Rotate keys regularly** - Update credentials periodically
7. **Use different keys per environment** - Development, staging, production

## Error Handling

Proper error handling when keys are missing:

```python
import os
import logging

logger = logging.getLogger(__name__)

def get_api_key(key_name: str, required: bool = True) -> str | None:
    """
    Get API key from environment with proper error handling.

    Args:
        key_name: Name of environment variable
        required: If True, raise error when missing

    Returns:
        API key or None

    Raises:
        ValueError: If required=True and key not found
    """
    api_key = os.environ.get(key_name)

    if not api_key:
        if required:
            raise ValueError(
                f"{key_name} environment variable is required. "
                f"Set it with: export {key_name}='your-key-here'"
            )
        else:
            logger.warning(f"{key_name} not set - AI features will be disabled")
            return None

    return api_key
```

## Production Deployment

For production deployments:

1. **Use secret management systems**:
   - Kubernetes Secrets
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault

2. **Never log API keys**:
   ```python
   # Bad - logs the key
   logger.info(f"Using API key: {api_key}")

   # Good - logs that key exists
   logger.info(f"API key configured: {bool(api_key)}")
   ```

3. **Audit access**:
   - Log when keys are accessed
   - Monitor for unusual usage patterns
   - Rotate keys on security events

## Compliance

This security practice ensures compliance with:
- OWASP Top 10 (A07:2021 - Identification and Authentication Failures)
- CWE-798: Use of Hard-coded Credentials
- SOC 2 credential management requirements
- Industry best practices for secret management

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [CWE-798: Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)
- [NIST SP 800-63B: Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
