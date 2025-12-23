# API Key Encryption Migration Guide

This guide covers migrating API keys from SHA256 hashing to Fernet encryption.

## Quick Start

Generate encryption key:
```bash
python3 scripts/tools/manage_encrypted_api_keys.py generate-key
export XAI_API_KEY_ENCRYPTION_KEY="your-generated-key"
```

Issue encrypted API key:
```bash
python3 scripts/tools/manage_encrypted_api_keys.py issue --label "my-key" --scope user
```

For complete documentation, see API_KEY_ENCRYPTION_SUMMARY.md

## Migration Scenarios

1. **New Deployment**: Enable encryption from start
2. **Existing Keys**: Gradual migration with backward compatibility  
3. **Key Rotation**: Multi-version support for seamless rotation

## Key Features

- Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- Multi-version key support
- Backward compatibility with hashed keys
- Migration utilities
- Comprehensive audit logging

## CLI Commands

- `generate-key` - Generate Fernet encryption key
- `issue` - Create new API key
- `migrate` - Convert hashed key to encrypted
- `rotate` - Rotate API key
- `validate` - Check API key validity
- `stats` - View storage statistics

## Security

- Constant-time comparison (timing attack prevention)
- No plaintext logging
- PBKDF2 key derivation (480K iterations)
- Audit trail for all operations

See API_KEY_ENCRYPTION_SUMMARY.md for full details.
