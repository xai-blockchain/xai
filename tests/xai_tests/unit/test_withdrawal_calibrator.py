import json
import subprocess
import sys
from pathlib import Path

from xai.tools.withdrawal_calibrator import (
    analyze_events,
    recommend_backlog_threshold,
    recommend_rate_threshold,
)


def test_analysis_produces_expected_rates():
    events = [
        {"timestamp": 0, "user": "userA", "amount": 50.0},
        {"timestamp": 10, "user": "userB", "amount": 25.0},
        {"timestamp": 20, "user": "userB", "amount": 10.0},
        {"timestamp": 80, "user": "userC", "amount": 5.0},
    ]
    analysis = analyze_events(events, window_seconds=60)
    assert analysis.total_events == 4
    assert analysis.unique_users == 3
    assert analysis.max_rate == 3  # first three in same minute
    assert analysis.p95_rate >= 2.8

    rate_threshold = recommend_rate_threshold(analysis, percentile=0.9, headroom=0.1)
    assert rate_threshold >= analysis.max_rate

    backlog_threshold = recommend_backlog_threshold(4, headroom=0.5)
    assert backlog_threshold >= 6


def test_cli_outputs_recommendations(tmp_path):
    events_log = tmp_path / "events.jsonl"
    events = [
        {"timestamp": 0, "user": "user1", "amount": 100.0},
        {"timestamp": 5, "user": "user1", "amount": 50.0},
        {"timestamp": 65, "user": "user2", "amount": 25.0},
    ]
    with events_log.open("w", encoding="utf-8") as handle:
        for entry in events:
            handle.write(json.dumps(entry))
            handle.write("\n")

    locks_file = tmp_path / "locks.json"
    locks_file.write_text(json.dumps([{"status": "pending"}, {"status": "pending"}]))

    json_output = tmp_path / "details.json"
    cmd = [
        sys.executable,
        "scripts/tools/withdrawal_threshold_calibrator.py",
        "--events-log",
        str(events_log),
        "--locks-file",
        str(locks_file),
        "--percentile",
        "0.9",
        "--headroom",
        "0.2",
        "--json-output",
        str(json_output),
        "--current-rate-threshold",
        "10",
        "--current-backlog-threshold",
        "2",
    ]
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=repo_root)
    assert "Suggested withdrawal rate threshold" in result.stdout
    assert "Suggested time-lock backlog threshold" in result.stdout
    payload = json.loads(json_output.read_text())
    assert payload["recommendations"]["rate_per_minute"] >= 1
    assert payload["analysis"]["events_analyzed"] == 3
