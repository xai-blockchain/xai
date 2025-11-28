"""
Daemon that iterates over pending wallet claims and emits reminders.

This can be scheduled daily (e.g., via cron or Task Scheduler) to ensure
every eligible miner/node hears about their pre-loaded wallet until they claim it.
"""

import json
import os

try:
    import requests  # type: ignore
except ImportError:
    requests = None

from core.wallet_claiming_api import WalletClaimingTracker


def _dispatch_webhook(url: str, payload: dict):
    if not url or requests is None:
        return
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[WEBHOOK] Failed to notify endpoint: {exc}")


def main():
    tracker = WalletClaimingTracker()
    pending = tracker.pending_claims_summary()
    webhook_url = os.getenv("XAI_NOTIFICATION_WEBHOOK", "").strip()

    if pending:
        summary_msg = f"[SUMMARY] {len(pending)} unclaimed wallets tracked; next reminders scheduled at per-identifier cadence."
        print(summary_msg)
        _dispatch_webhook(
            webhook_url,
            {
                "type": "wallet_reminder_summary",
                "pending_count": len(pending),
                "pending": pending[:10],
            },
        )
    else:
        print("[SUMMARY] No pending wallet claims right now.")

    for identifier in list(tracker.pending_claims.keys()):
        note = tracker.get_unclaimed_notification(identifier)
        if note:
            print(f"[REMINDER] {identifier}: {note['message']}")
            print(f"  Details: {note['details']}")
            print(f"  Try: {note['action']}")
            payload = {"type": "wallet_reminder", "identifier": identifier, "notification": note}
            if webhook_url:
                _dispatch_webhook(webhook_url, payload)
            elif os.getenv("XAI_NOTIFICATION_LOG_JSON") == "1":
                print(json.dumps(payload))


if __name__ == "__main__":
    main()
