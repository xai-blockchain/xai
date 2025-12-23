#!/usr/bin/env python3
"""
API key rotation/issuance/revocation CLI with simple rate limiting and admin-scope alerting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from xai.core.api_auth import APIAuthManager, APIKeyStore
from xai.core.config import Config
from xai.core.security_validation import log_security_event

RATE_WINDOW_SEC = 60
RATE_LIMIT = 20
RATE_STATE_PATH = Path(os.getenv("XAI_API_KEY_RATE_PATH", Path.home() / ".xai" / "api_key_cli_rate.json"))

def _load_rate_state() -> list[float]:
    try:
        RATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if RATE_STATE_PATH.exists():
            return [float(x) for x in json.loads(RATE_STATE_PATH.read_text())]
    except Exception:
        return []
    return []

def _persist_rate_state(stamps: list[float]) -> None:
    try:
        RATE_STATE_PATH.write_text(json.dumps(stamps))
    except Exception:
        pass

def enforce_rate_limit(now: float) -> None:
    stamps = _load_rate_state()
    stamps = [ts for ts in stamps if now - ts <= RATE_WINDOW_SEC]
    if len(stamps) >= RATE_LIMIT:
        raise SystemExit(f"Rate limit exceeded ({len(stamps)} actions in last {RATE_WINDOW_SEC}s)")
    stamps.append(now)
    _persist_rate_state(stamps)

def default_store_path() -> str:
    return os.getenv(
        "XAI_API_KEY_STORE_PATH",
        getattr(Config, "API_KEY_STORE_PATH", os.path.join(os.getcwd(), "secure_keys", "api_keys.json")),
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage API keys (issue/rotate/revoke) with audit logging.")
    parser.add_argument("--store-path", default=default_store_path(), help="Path to API key store JSON file.")

    sub = parser.add_subparsers(dest="command", required=True)

    issue = sub.add_parser("issue", help="Issue a new API key")
    issue.add_argument("--label", default="", help="Label for the key")
    issue.add_argument("--scope", default="user", choices=["user", "admin"], help="Scope for the key")
    issue.add_argument("--ttl-days", type=float, default=None, help="Override default TTL in days")
    issue.add_argument("--ttl-hours", type=float, default=None, help="Override default TTL in hours")
    issue.add_argument("--permanent", action="store_true", help="Issue a non-expiring key (if allowed)")

    rotate = sub.add_parser("rotate", help="Rotate an existing key id")
    rotate.add_argument("key_id", help="Key id (hash) to rotate")
    rotate.add_argument("--label", default="", help="Label for new key")
    rotate.add_argument("--scope", default="user", choices=["user", "admin"], help="Scope for the new key")
    rotate.add_argument("--ttl-days", type=float, default=None, help="Override default TTL in days")
    rotate.add_argument("--ttl-hours", type=float, default=None, help="Override default TTL in hours")
    rotate.add_argument("--permanent", action="store_true", help="Issue a non-expiring key (if allowed)")

    revoke = sub.add_parser("revoke", help="Revoke an existing key id")
    revoke.add_argument("key_id", help="Key id (hash) to revoke")

    return parser

def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    enforce_rate_limit(time.time())

    store = APIKeyStore(
        args.store_path,
        default_ttl_days=getattr(Config, "API_KEY_DEFAULT_TTL_DAYS", 90),
        max_ttl_days=getattr(Config, "API_KEY_MAX_TTL_DAYS", 365),
        allow_permanent=getattr(Config, "API_KEY_ALLOW_PERMANENT", False),
    )
    manager = APIAuthManager(required=False, store=store)

    def ttl_seconds_from_args(ttl_days: float | None, ttl_hours: float | None) -> int | None:
        if ttl_days is not None:
            return max(1, int(ttl_days * 86400))
        if ttl_hours is not None:
            return max(1, int(ttl_hours * 3600))
        return None

    if args.command == "issue":
        ttl_seconds = ttl_seconds_from_args(args.ttl_days, args.ttl_hours)
        try:
            key, key_id = manager.issue_key(
                label=args.label,
                scope=args.scope,
                ttl_seconds=ttl_seconds,
                permanent=args.permanent,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        metadata = store.list_keys().get(key_id, {})
        if args.scope == "admin":
            log_security_event("api_key_issue_admin", {"key_id": key_id, "label": args.label}, severity="WARNING")
        expires_at = metadata.get("expires_at")
        permanent = metadata.get("permanent", False)
        print(f"PLAINTEXT={key}\nKEY_ID={key_id}\nEXPIRES_AT={expires_at}\nPERMANENT={permanent}")
        return 0

    if args.command == "rotate":
        ttl_seconds = ttl_seconds_from_args(args.ttl_days, args.ttl_hours)
        try:
            new_plain, new_id = manager.rotate_key(
                args.key_id,
                label=args.label,
                scope=args.scope,
                ttl_seconds=ttl_seconds,
                permanent=args.permanent,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        metadata = store.list_keys().get(new_id, {})
        expires_at = metadata.get("expires_at")
        permanent = metadata.get("permanent", False)
        print(f"NEW_PLAINTEXT={new_plain}\nNEW_KEY_ID={new_id}\nEXPIRES_AT={expires_at}\nPERMANENT={permanent}")
        return 0

    if args.command == "revoke":
        if manager.revoke_key(args.key_id):
            log_security_event("api_key_revoked", {"key_id": args.key_id}, severity="WARNING")
            print("revoked")
            return 0
        print("not_found")
        return 1

    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
