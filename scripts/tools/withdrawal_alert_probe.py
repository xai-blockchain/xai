#!/usr/bin/env python3
"""
Utility to inspect recent withdrawals and time-lock backlog for alert calibration.

Examples:
    python scripts/tools/withdrawal_alert_probe.py \\
        --events-log monitoring/withdrawals_events.jsonl \\
        --locks-file data/wallet/time_locked_withdrawals.json \\
        --rate-threshold 15
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

def _load_events(path: Path) -> list[dict[str, float]]:
    if not path.exists():
        return []
    events: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events

def _load_time_lock_backlog(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            entries = json.load(handle)
    except json.JSONDecodeError:
        return 0
    return sum(1 for entry in entries if entry.get("status", "pending") == "pending")

def _summarize(events: list[dict[str, float]], window: int) -> dict[str, float]:
    now = time.time()
    cutoff = now - window
    window_events = [event for event in events if event.get("timestamp", 0) >= cutoff]

    rate = len(window_events)
    volume = sum(event.get("amount", 0.0) for event in window_events)
    by_user: Counter[str] = Counter()
    volume_by_user: defaultdict[str, float] = defaultdict(float)
    for event in window_events:
        user = event.get("user", "unknown")
        by_user[user] += 1
        volume_by_user[user] += float(event.get("amount", 0.0))

    recent_rates = [event.get("rate_per_minute", 0) for event in window_events]
    stats = {
        "rate": rate,
        "volume": volume,
        "unique_users": len(by_user),
        "max_window_rate": max(recent_rates) if recent_rates else 0,
        "p95_window_rate": statistics.quantiles(recent_rates, n=20)[-1] if len(recent_rates) >= 20 else max(recent_rates, default=0),
        "top_users": [(user, by_user[user], volume_by_user[user]) for user in by_user.most_common(5)],
    }
    return stats

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect withdrawal metrics for alert calibration.")
    parser.add_argument("--events-log", type=Path, default=Path("monitoring/withdrawals_events.jsonl"))
    parser.add_argument("--locks-file", type=Path, default=Path("data/wallet/time_locked_withdrawals.json"))
    parser.add_argument("--time-window", type=int, default=60, help="Window in seconds for withdrawal rate calculations.")
    parser.add_argument("--rate-threshold", type=float, default=15.0, help="Configured alert threshold for per-minute withdrawal rate.")
    parser.add_argument("--backlog-threshold", type=int, default=5, help="Configured alert threshold for time-lock backlog.")
    args = parser.parse_args(argv)

    events = _load_events(args.events_log)
    if not events:
        print(f"No withdrawal events found at {args.events_log}")
    stats = _summarize(events, args.time_window) if events else {
        "rate": 0,
        "volume": 0.0,
        "unique_users": 0,
        "max_window_rate": 0,
        "p95_window_rate": 0,
        "top_users": [],
    }

    backlog = _load_time_lock_backlog(args.locks_file)

    print("=== Withdrawal Rate Probe ===")
    print(f"Window: last {args.time_window}s")
    print(f"Observed withdrawals: {stats['rate']} (threshold {args.rate_threshold}/min)")
    print(f"Max instantaneous rate in window: {stats['max_window_rate']}/min")
    print(f"95th percentile instantaneous rate: {stats['p95_window_rate']}/min")
    print(f"Total volume in window: {stats['volume']:.2f}")
    print(f"Unique users: {stats['unique_users']}")
    print()
    if stats["top_users"]:
        print("Top actors (user, count, volume):")
        for user, count, volume in stats["top_users"]:
            vol_str = f"{volume:.2f}"
            print(f" - {user}: {count} withdrawals, {vol_str} total")
    else:
        print("No withdrawal actors recorded in the specified window.")
    print()
    print("=== Time-lock Backlog ===")
    print(f"Pending withdrawals: {backlog} (threshold {args.backlog_threshold})")
    if backlog > args.backlog_threshold:
        print(">> Backlog exceeds threshold. Investigate stuck approvals or run manual release job.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
