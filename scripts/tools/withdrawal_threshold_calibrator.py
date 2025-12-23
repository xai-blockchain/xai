#!/usr/bin/env python3
"""
Recommend withdrawal alert thresholds based on persisted telemetry.

Examples:
    python scripts/tools/withdrawal_threshold_calibrator.py \
        --events-log monitoring/withdrawals_events.jsonl \
        --locks-file data/wallet/time_locked_withdrawals.json \
        --percentile 0.95 \
        --headroom 0.25 \
        --backlog-headroom 0.5
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from xai.tools.withdrawal_calibrator import (
    analyze_events,
    load_events,
    load_time_lock_snapshot,
    recommend_backlog_threshold,
    recommend_rate_threshold,
)

def _format_top_users(top_users: list[tuple[str, int, float]]) -> str:
    if not top_users:
        return "No withdrawal activity recorded."
    lines = []
    for user, count, volume in top_users:
        lines.append(f" - {user}: {count} withdrawals, {volume:.2f} total")
    return "\n".join(lines)

def _build_details(
    *,
    analysis,
    backlog: int,
    recommended_rate: int,
    recommended_backlog: int,
    args,
) -> dict:
    timestamp = datetime.now(tz=timezone.utc).isoformat()
    details = {
        "generated_at": timestamp,
        "analysis": {
            "events_analyzed": analysis.total_events,
            "unique_users": analysis.unique_users,
            "total_volume": round(analysis.total_volume, 6),
            "max_rate_per_minute": analysis.max_rate,
            "p95_rate_per_minute": round(analysis.p95_rate, 6),
            "current_backlog": backlog,
            "top_users": [
                {"user": user, "count": count, "total_volume": round(volume, 6)}
                for user, count, volume in analysis.top_users
            ],
        },
        "recommendations": {
            "rate_per_minute": recommended_rate,
            "time_lock_backlog": recommended_backlog,
        },
        "inputs": {
            "events_log": str(args.events_log),
            "locks_file": str(args.locks_file),
            "percentile": args.percentile,
            "headroom": args.headroom,
            "backlog_headroom": args.backlog_headroom,
            "window_seconds": args.window,
        },
        "current_thresholds": {
            "rate_per_minute": args.current_rate_threshold,
            "time_lock_backlog": args.current_backlog_threshold,
        },
    }
    alert_required = False
    if (
        args.current_rate_threshold is not None
        and recommended_rate > args.current_rate_threshold
    ):
        alert_required = True
    if (
        args.current_backlog_threshold is not None
        and recommended_backlog > args.current_backlog_threshold
    ):
        alert_required = True
    details["alert_required"] = alert_required
    return details

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate withdrawal alert thresholds.")
    parser.add_argument("--events-log", type=Path, default=Path("monitoring/withdrawals_events.jsonl"))
    parser.add_argument("--locks-file", type=Path, default=Path("data/wallet/time_locked_withdrawals.json"))
    parser.add_argument("--percentile", type=float, default=0.95, help="Percentile used for rate recommendation.")
    parser.add_argument("--headroom", type=float, default=0.25, help="Additional headroom multiplier for rate threshold.")
    parser.add_argument(
        "--backlog-headroom",
        type=float,
        default=0.5,
        help="Additional headroom multiplier for backlog threshold.",
    )
    parser.add_argument("--window", type=int, default=60, help="Sliding window size in seconds.")
    parser.add_argument("--json-output", type=Path, help="Optional path for structured JSON output.")
    parser.add_argument(
        "--current-rate-threshold",
        type=int,
        default=None,
        help="Current configured withdrawal rate threshold for alerting.",
    )
    parser.add_argument(
        "--current-backlog-threshold",
        type=int,
        default=None,
        help="Current configured time-lock backlog threshold for alerting.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    events = load_events(args.events_log)
    analysis = analyze_events(events, window_seconds=args.window)
    backlog = load_time_lock_snapshot(args.locks_file)

    recommended_rate = recommend_rate_threshold(
        analysis, percentile=args.percentile, headroom=args.headroom
    )
    recommended_backlog = recommend_backlog_threshold(backlog, headroom=args.backlog_headroom)

    print("=== Withdrawal Threshold Calibration ===")
    print(f"Events analyzed: {analysis.total_events}")
    print(f"Unique users: {analysis.unique_users}")
    print(f"Total volume: {analysis.total_volume:.2f}")
    print(f"Max 1m rate: {analysis.max_rate}/min")
    print(f"{int(args.percentile * 100)}th percentile 1m rate: {analysis.p95_rate:.2f}/min")
    print()
    print("Top actors:")
    print(_format_top_users(analysis.top_users))
    print()
    print("=== Recommendations ===")
    print(
        f"Suggested withdrawal rate threshold: {recommended_rate}/min "
        f"(percentile={args.percentile}, headroom={args.headroom})"
    )
    print(
        f"Suggested time-lock backlog threshold: {recommended_backlog} "
        f"(current backlog={backlog}, headroom={args.backlog_headroom})"
    )
    print()
    print("Update GitHub repo variables WITHDRAWAL_RATE_THRESHOLD / TIMELOCK_BACKLOG_THRESHOLD or")
    print("adjust prometheus/alerts/security_operations.yml to use the recommended values.")
    if args.json_output:
        details = _build_details(
            analysis=analysis,
            backlog=backlog,
            recommended_rate=recommended_rate,
            recommended_backlog=recommended_backlog,
            args=args,
        )
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(details, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
