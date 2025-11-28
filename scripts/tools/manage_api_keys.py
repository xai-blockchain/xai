#!/usr/bin/env python3
"""CLI for managing API keys via the on-disk APIKeyStore."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xai.core.api_auth import APIKeyStore  # noqa: E402
from xai.core.config import API_KEY_STORE_PATH  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage API keys in the store")
    parser.add_argument(
        "--store",
        default=API_KEY_STORE_PATH,
        help=f"Path to api key store (default: {API_KEY_STORE_PATH})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List stored API keys (hashes + metadata)")
    events = sub.add_parser("events", help="Show recent key issuance/revocation events")
    events.add_argument("--limit", type=int, default=50, help="Number of events to display")

    issue = sub.add_parser("issue", help="Issue a new API key")
    issue.add_argument("--label", default="", help="Human friendly label for tracking")
    issue.add_argument(
        "--scope",
        choices=["user", "admin"],
        default="user",
        help="Scope of the key (user: API auth, admin: /admin endpoints)",
    )

    revoke = sub.add_parser("revoke", help="Revoke an API key by key_id")
    revoke.add_argument("key_id", help="SHA256 key id to revoke")

    watch = sub.add_parser("watch-events", help="Stream audit log entries as they happen")
    watch.add_argument("--limit", type=int, default=10, help="Initial events to replay before streaming")
    watch.add_argument("--interval", type=float, default=0.5, help="Polling interval while waiting for new events")

    bootstrap = sub.add_parser("bootstrap-admin", help="Promote a pre-shared secret into an admin API key")
    bootstrap.add_argument("--label", default="bootstrap-admin", help="Label for the bootstrap key entry")
    bootstrap.add_argument(
        "--secret",
        default=None,
        help="Admin secret to persist (falls back to XAI_BOOTSTRAP_ADMIN_KEY)",
    )

    return parser


def cmd_list(store: APIKeyStore) -> None:
    keys = store.list_keys()
    print(json.dumps(keys, indent=2) or "{}")


def cmd_events(store: APIKeyStore, limit: int) -> None:
    events = store.get_events(limit=limit)
    print(json.dumps(events, indent=2))


def cmd_issue(store: APIKeyStore, label: str, scope: str) -> None:
    api_key, key_id = store.issue_key(label=label, scope=scope)
    payload = {"api_key": api_key, "key_id": key_id, "scope": scope, "label": label}
    print(json.dumps(payload, indent=2))


def cmd_revoke(store: APIKeyStore, key_id: str) -> int:
    if store.revoke_key(key_id):
        print(json.dumps({"revoked": True, "key_id": key_id}))
        return 0
    print(json.dumps({"revoked": False, "key_id": key_id, "error": "not_found"}))
    return 1


def cmd_watch_events(store: APIKeyStore, limit: int, interval: float) -> int:
    """Stream the audit log so ops teams can tail issuance/revocation events."""
    events = store.get_events(limit=limit)
    for event in events:
        print(json.dumps(event, indent=2))

    log_path = Path(store.audit_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure the log file exists before tailing
    log_path.touch(exist_ok=True)

    print(json.dumps({"watching": str(log_path), "interval": interval}))

    with log_path.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        try:
            while True:
                line = handle.readline()
                if not line:
                    time.sleep(max(interval, 0.1))
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                print(json.dumps(event, indent=2))
        except KeyboardInterrupt:
            return 0


def cmd_bootstrap_admin(store: APIKeyStore, label: str, secret: Optional[str]) -> int:
    """Issue an admin key using a pre-provisioned secret (env or CLI)."""
    secret_value = (secret or os.getenv("XAI_BOOTSTRAP_ADMIN_KEY", "")).strip()
    if not secret_value:
        print(json.dumps({"error": "missing_secret", "message": "Provide --secret or XAI_BOOTSTRAP_ADMIN_KEY"}))
        return 1

    _, key_id = store.issue_key(label=label, scope="admin", plaintext=secret_value)
    fingerprint = hashlib.sha256(secret_value.encode("utf-8")).hexdigest()[:12]
    payload = {
        "operation": "bootstrap_admin",
        "key_id": key_id,
        "label": label,
        "fingerprint": fingerprint,
    }
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store = APIKeyStore(args.store)

    if args.command == "list":
        cmd_list(store)
        return 0
    if args.command == "events":
        cmd_events(store, args.limit)
        return 0
    if args.command == "issue":
        cmd_issue(store, args.label, args.scope)
        return 0
    if args.command == "revoke":
        return cmd_revoke(store, args.key_id)
    if args.command == "watch-events":
        return cmd_watch_events(store, args.limit, args.interval)
    if args.command == "bootstrap-admin":
        return cmd_bootstrap_admin(store, args.label, args.secret)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
