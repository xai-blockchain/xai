#!/usr/bin/env python3
"""
CLI for managing encrypted API keys with migration support.

This tool extends the basic manage_api_keys.py with encryption-specific features:
- Generate encryption keys
- Migrate hashed keys to encrypted storage
- Re-encrypt keys with new encryption version
- Audit encryption status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xai.core.encrypted_api_key_store import EncryptedAPIKeyStore
from xai.core.api_key_encryption import APIKeyEncryptionManager
from xai.core.config import API_KEY_STORE_PATH, Config


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Manage encrypted API keys with migration support"
    )
    parser.add_argument(
        "--store",
        default=API_KEY_STORE_PATH,
        help=f"Path to API key store (default: {API_KEY_STORE_PATH})",
    )
    parser.add_argument(
        "--encryption-key",
        default=None,
        help="Encryption key (overrides XAI_API_KEY_ENCRYPTION_KEY)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # List keys
    sub.add_parser("list", help="List stored API keys")

    # Statistics
    sub.add_parser("stats", help="Show key storage statistics")

    # Events
    events = sub.add_parser("events", help="Show recent key audit events")
    events.add_argument("--limit", type=int, default=50, help="Number of events")

    # Issue key
    issue = sub.add_parser("issue", help="Issue a new API key")
    issue.add_argument("--label", default="", help="Label for tracking")
    issue.add_argument(
        "--scope",
        choices=["user", "admin", "operator", "auditor"],
        default="user",
        help="Key scope",
    )
    issue.add_argument("--ttl-days", type=float, help="TTL in days")
    issue.add_argument("--ttl-hours", type=float, help="TTL in hours")
    issue.add_argument("--permanent", action="store_true", help="Non-expiring key")
    issue.add_argument(
        "--no-encryption",
        action="store_true",
        help="Issue hashed key (legacy mode)",
    )

    # Revoke key
    revoke = sub.add_parser("revoke", help="Revoke an API key")
    revoke.add_argument("key_id", help="Key ID to revoke")

    # Rotate key
    rotate = sub.add_parser("rotate", help="Rotate an API key")
    rotate.add_argument("key_id", help="Old key ID to rotate")
    rotate.add_argument("--label", default="", help="Label for new key")
    rotate.add_argument("--scope", default="user", help="Scope for new key")
    rotate.add_argument("--ttl-days", type=float, help="TTL in days")
    rotate.add_argument("--ttl-hours", type=float, help="TTL in hours")

    # Migration commands
    migrate = sub.add_parser("migrate", help="Migrate hashed key to encrypted")
    migrate.add_argument("api_key", help="Plaintext API key to migrate")

    migrate_all = sub.add_parser(
        "migrate-all", help="Migrate all hashed keys (requires plaintext keys)"
    )
    migrate_all.add_argument(
        "--keys-file",
        required=True,
        help="JSON file with plaintext keys: {key_id: plaintext}",
    )

    # Re-encrypt command
    reencrypt = sub.add_parser("re-encrypt", help="Re-encrypt key with new version")
    reencrypt.add_argument("key_id", help="Key ID to re-encrypt")
    reencrypt.add_argument("--target-version", type=int, help="Target version")

    # Encryption key commands
    sub.add_parser("generate-key", help="Generate new Fernet encryption key")

    derive = sub.add_parser("derive-key", help="Derive encryption key from secret")
    derive.add_argument("secret", help="Secret passphrase")
    derive.add_argument("--salt", help="Custom salt (hex)")

    # Validate command
    validate = sub.add_parser("validate", help="Validate an API key")
    validate.add_argument("api_key", help="API key to validate")

    # Bootstrap admin
    bootstrap = sub.add_parser(
        "bootstrap-admin", help="Create admin key from pre-shared secret"
    )
    bootstrap.add_argument("--label", default="bootstrap-admin", help="Label")
    bootstrap.add_argument("--secret", help="Admin secret (or set XAI_BOOTSTRAP_ADMIN_KEY)")
    bootstrap.add_argument("--ttl-days", type=float, help="TTL in days")

    return parser


def _ttl_seconds(ttl_days: float | None, ttl_hours: float | None) -> int | None:
    """Convert TTL arguments to seconds."""
    if ttl_days is not None:
        return max(1, int(ttl_days * 86400))
    if ttl_hours is not None:
        return max(1, int(ttl_hours * 3600))
    return None


def cmd_list(store: EncryptedAPIKeyStore) -> None:
    """List all API keys."""
    keys = store.list_keys()
    print(json.dumps(keys, indent=2) or "{}")


def cmd_stats(store: EncryptedAPIKeyStore) -> None:
    """Show key storage statistics."""
    stats = store.get_statistics()
    print(json.dumps(stats, indent=2))


def cmd_events(store: EncryptedAPIKeyStore, limit: int) -> None:
    """Show recent audit events."""
    events = store.get_events(limit=limit)
    print(json.dumps(events, indent=2))


def cmd_issue(
    store: EncryptedAPIKeyStore,
    label: str,
    scope: str,
    ttl_seconds: int | None,
    permanent: bool,
    no_encryption: bool,
) -> None:
    """Issue a new API key."""
    use_encryption = not no_encryption

    try:
        api_key, key_id = store.issue_key(
            label=label,
            scope=scope,
            ttl_seconds=ttl_seconds,
            permanent=permanent,
            use_encryption=use_encryption,
        )

        metadata = store.get_key_metadata(key_id)

        result = {
            "api_key": api_key,
            "key_id": key_id,
            "scope": scope,
            "label": label,
            "storage_type": metadata.get("storage_type") if metadata else None,
            "expires_at": metadata.get("expires_at") if metadata else None,
            "permanent": metadata.get("permanent") if metadata else False,
        }

        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_revoke(store: EncryptedAPIKeyStore, key_id: str) -> int:
    """Revoke an API key."""
    if store.revoke_key(key_id):
        print(json.dumps({"revoked": True, "key_id": key_id}))
        return 0

    print(json.dumps({"revoked": False, "key_id": key_id, "error": "not_found"}))
    return 1


def cmd_rotate(
    store: EncryptedAPIKeyStore,
    key_id: str,
    label: str,
    scope: str,
    ttl_seconds: int | None,
) -> None:
    """Rotate an API key."""
    try:
        new_key, new_id = store.rotate_key(
            key_id,
            label=label,
            scope=scope,
            ttl_seconds=ttl_seconds,
        )

        metadata = store.get_key_metadata(new_id)

        result = {
            "api_key": new_key,
            "key_id": new_id,
            "replaced": key_id,
            "scope": scope,
            "label": label,
            "storage_type": metadata.get("storage_type") if metadata else None,
            "expires_at": metadata.get("expires_at") if metadata else None,
        }

        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_migrate(store: EncryptedAPIKeyStore, api_key: str) -> int:
    """Migrate a hashed key to encrypted storage."""
    if not store.encryption_enabled:
        print(json.dumps({"error": "Encryption not enabled"}), file=sys.stderr)
        return 1

    success, result = store.migrate_to_encrypted(api_key)

    if success:
        print(
            json.dumps(
                {
                    "migrated": True,
                    "new_key_id": result,
                    "message": "Key migrated to encrypted storage",
                }
            )
        )
        return 0

    print(json.dumps({"migrated": False, "error": result}), file=sys.stderr)
    return 1


def cmd_migrate_all(store: EncryptedAPIKeyStore, keys_file: str) -> int:
    """Migrate all hashed keys using plaintext keys file."""
    if not store.encryption_enabled:
        print(json.dumps({"error": "Encryption not enabled"}), file=sys.stderr)
        return 1

    # Load plaintext keys
    try:
        with open(keys_file, "r", encoding="utf-8") as f:
            keys_map = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Failed to load keys file: {e}"}), file=sys.stderr)
        return 1

    results = []
    for old_key_id, plaintext in keys_map.items():
        success, result = store.migrate_to_encrypted(plaintext)
        results.append(
            {
                "old_key_id": old_key_id,
                "success": success,
                "new_key_id": result if success else None,
                "error": result if not success else None,
            }
        )

    print(json.dumps({"migrations": results}, indent=2))

    failed = [r for r in results if not r["success"]]
    return 1 if failed else 0


def cmd_validate(store: EncryptedAPIKeyStore, api_key: str) -> int:
    """Validate an API key."""
    is_valid, key_id, metadata = store.validate_key(api_key)

    result = {
        "valid": is_valid,
        "key_id": key_id,
        "metadata": metadata,
    }

    print(json.dumps(result, indent=2))
    return 0 if is_valid else 1


def cmd_generate_key() -> None:
    """Generate a new Fernet encryption key."""
    key = APIKeyEncryptionManager.generate_key()
    result = {
        "encryption_key": key,
        "usage": "Set XAI_API_KEY_ENCRYPTION_KEY environment variable",
        "warning": "Store this key securely - keys cannot be recovered without it",
    }
    print(json.dumps(result, indent=2))


def cmd_derive_key(secret: str, salt: str | None) -> None:
    """Derive encryption key from secret."""
    salt_bytes = bytes.fromhex(salt) if salt else None
    key = APIKeyEncryptionManager.derive_key_from_secret(secret, salt=salt_bytes)

    result = {
        "encryption_key": key,
        "derived_from": "secret (PBKDF2, 480000 iterations)",
        "usage": "Set XAI_API_KEY_ENCRYPTION_KEY environment variable",
        "warning": "Store this key securely - keys cannot be recovered without it",
    }
    print(json.dumps(result, indent=2))


def cmd_bootstrap_admin(
    store: EncryptedAPIKeyStore,
    label: str,
    secret: str | None,
    ttl_seconds: int | None,
) -> int:
    """Bootstrap admin key from pre-shared secret."""
    secret_value = (secret or os.getenv("XAI_BOOTSTRAP_ADMIN_KEY", "")).strip()

    if not secret_value:
        print(
            json.dumps(
                {
                    "error": "No secret provided",
                    "message": "Provide --secret or set XAI_BOOTSTRAP_ADMIN_KEY",
                }
            ),
            file=sys.stderr,
        )
        return 1

    try:
        _, key_id = store.issue_key(
            label=label,
            scope="admin",
            plaintext=secret_value,
            ttl_seconds=ttl_seconds,
        )

        fingerprint = hashlib.sha256(secret_value.encode("utf-8")).hexdigest()[:12]

        result = {
            "operation": "bootstrap_admin",
            "key_id": key_id,
            "label": label,
            "fingerprint": fingerprint,
        }

        print(json.dumps(result, indent=2))
        return 0
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Initialize store
    store = EncryptedAPIKeyStore(
        args.store,
        default_ttl_days=getattr(Config, "API_KEY_DEFAULT_TTL_DAYS", 90),
        max_ttl_days=getattr(Config, "API_KEY_MAX_TTL_DAYS", 365),
        allow_permanent=getattr(Config, "API_KEY_ALLOW_PERMANENT", False),
        encryption_key=args.encryption_key,
        enable_encryption=getattr(Config, "API_KEY_ENABLE_ENCRYPTION", True),
    )

    # Execute command
    if args.command == "list":
        cmd_list(store)
        return 0

    if args.command == "stats":
        cmd_stats(store)
        return 0

    if args.command == "events":
        cmd_events(store, args.limit)
        return 0

    if args.command == "issue":
        ttl = _ttl_seconds(args.ttl_days, args.ttl_hours)
        cmd_issue(store, args.label, args.scope, ttl, args.permanent, args.no_encryption)
        return 0

    if args.command == "revoke":
        return cmd_revoke(store, args.key_id)

    if args.command == "rotate":
        ttl = _ttl_seconds(args.ttl_days, args.ttl_hours)
        cmd_rotate(store, args.key_id, args.label, args.scope, ttl)
        return 0

    if args.command == "migrate":
        return cmd_migrate(store, args.api_key)

    if args.command == "migrate-all":
        return cmd_migrate_all(store, args.keys_file)

    if args.command == "validate":
        return cmd_validate(store, args.api_key)

    if args.command == "generate-key":
        cmd_generate_key()
        return 0

    if args.command == "derive-key":
        cmd_derive_key(args.secret, args.salt)
        return 0

    if args.command == "bootstrap-admin":
        ttl = _ttl_seconds(args.ttl_days, None)
        return cmd_bootstrap_admin(store, args.label, args.secret, ttl)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
