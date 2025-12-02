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
from typing import List

from xai.core.api_auth import APIAuthManager, APIKeyStore
from xai.core.config import Config
from xai.core.security_validation import log_security_event

RATE_WINDOW_SEC = 60
RATE_LIMIT = 20
RATE_STATE_PATH = Path(os.getenv("XAI_API_KEY_RATE_PATH", Path.home() / ".xai" / "api_key_cli_rate.json"))


def _load_rate_state() -> List[float]:
    try:
        RATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if RATE_STATE_PATH.exists():
            return [float(x) for x in json.loads(RATE_STATE_PATH.read_text())]
    except Exception:
        return []
    return []


def _persist_rate_state(stamps: List[float]) -> None:
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

    rotate = sub.add_parser("rotate", help="Rotate an existing key id")
    rotate.add_argument("key_id", help="Key id (hash) to rotate")
    rotate.add_argument("--label", default="", help="Label for new key")
    rotate.add_argument("--scope", default="user", choices=["user", "admin"], help="Scope for the new key")

    revoke = sub.add_parser("revoke", help="Revoke an existing key id")
    revoke.add_argument("key_id", help="Key id (hash) to revoke")

    return parser


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    enforce_rate_limit(time.time())

    store = APIKeyStore(args.store_path)
    manager = APIAuthManager(required=False, store=store)

    if args.command == "issue":
        key, key_id = manager.issue_key(label=args.label, scope=args.scope)
        if args.scope == "admin":
            log_security_event("api_key_issue_admin", {"key_id": key_id, "label": args.label}, severity="WARNING")
        print(f"PLAINTEXT={key}\nKEY_ID={key_id}")
        return 0

    if args.command == "rotate":
        new_plain, new_id = manager.rotate_key(args.key_id, label=args.label, scope=args.scope)
        print(f"NEW_PLAINTEXT={new_plain}\nNEW_KEY_ID={new_id}")
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
