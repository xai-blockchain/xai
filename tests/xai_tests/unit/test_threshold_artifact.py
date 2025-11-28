import json
import os
import subprocess
import sys
from pathlib import Path

from xai.tools.threshold_artifact import (
    ThresholdDetails,
    append_history_entry,
    load_history,
)


def _sample_details_payload():
    return {
        "generated_at": "2024-01-01T00:00:00Z",
        "analysis": {
            "events_analyzed": 5,
            "unique_users": 3,
            "total_volume": 120.5,
            "max_rate_per_minute": 4,
            "p95_rate_per_minute": 3.5,
            "current_backlog": 2,
            "top_users": [
                {"user": "user-a", "count": 3, "total_volume": 75.0},
                {"user": "user-b", "count": 2, "total_volume": 45.5},
            ],
        },
        "recommendations": {
            "rate_per_minute": 12,
            "time_lock_backlog": 6,
        },
        "inputs": {
            "percentile": 0.95,
            "headroom": 0.25,
            "backlog_headroom": 0.5,
            "window_seconds": 60,
            "events_log": "monitoring/events.jsonl",
            "locks_file": "data/locks.json",
        },
        "current_thresholds": {"rate_per_minute": 10, "time_lock_backlog": 4},
        "alert_required": True,
    }


def test_threshold_details_roundtrip(tmp_path):
    details_file = tmp_path / "threshold_details.json"
    details_file.write_text(json.dumps(_sample_details_payload()), encoding="utf-8")
    details = ThresholdDetails.from_path(details_file)
    assert details.recommendations.rate_per_minute == 12
    history_path = tmp_path / "history.jsonl"
    entry = details.to_history_entry(environment="staging", commit="abc123")
    append_history_entry(history_path, entry)
    history = load_history(history_path)
    assert len(history) == 1
    assert history[0].environment == "staging"
    assert history[0].alert_required is True


def test_threshold_artifact_ingest_cli(tmp_path):
    details_file = tmp_path / "threshold_details.json"
    details_file.write_text(json.dumps(_sample_details_payload()), encoding="utf-8")
    history_file = tmp_path / "history.jsonl"
    markdown_file = tmp_path / "summary.md"
    cmd = [
        sys.executable,
        "scripts/tools/threshold_artifact_ingest.py",
        "--details",
        str(details_file),
        "--history-file",
        str(history_file),
        "--environment",
        "staging",
        "--commit",
        "abc123",
        "--markdown-output",
        str(markdown_file),
        "--print-markdown",
    ]
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=repo_root)
    assert "**Environment**" in result.stdout
    history_lines = [line for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(history_lines) == 1
    payload = json.loads(history_lines[0])
    assert payload["environment"] == "staging"
    assert payload["recommended_rate"] == 12
    assert "Recommended rate threshold" in markdown_file.read_text(encoding="utf-8")


def test_threshold_artifact_ingest_prunes_history(tmp_path):
    history_file = tmp_path / "history.jsonl"
    repo_root = Path(__file__).resolve().parents[3]
    for idx in range(3):
        payload = _sample_details_payload()
        payload["generated_at"] = f"2024-01-01T00:00:0{idx}Z"
        details_file = tmp_path / f"details_{idx}.json"
        details_file.write_text(json.dumps(payload), encoding="utf-8")
        cmd = [
            sys.executable,
            "scripts/tools/threshold_artifact_ingest.py",
            "--details",
            str(details_file),
            "--history-file",
            str(history_file),
            "--environment",
            "staging",
            "--max-history-entries",
            "2",
        ]
        subprocess.run(cmd, check=True, cwd=repo_root)
    history_lines = [line for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(history_lines) == 2
    assert '"generated_at": "2024-01-01T00:00:02Z"' in history_lines[-1]


def test_threshold_artifact_publish_dry_run(tmp_path):
    details_file = tmp_path / "threshold_details.json"
    details_file.write_text(json.dumps(_sample_details_payload()), encoding="utf-8")
    markdown_file = tmp_path / "summary.md"
    markdown_file.write_text("**Environment**: staging\n\n- Recommended rate threshold: 12", encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/tools/threshold_artifact_publish.py",
        "--details",
        str(details_file),
        "--markdown",
        str(markdown_file),
        "--environment",
        "staging",
        "--dry-run",
    ]
    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=repo_root, env=env)
    assert "Withdrawal threshold calibration" in result.stdout


def test_threshold_artifact_publish_requires_target(tmp_path):
    details_file = tmp_path / "threshold_details.json"
    details_file.write_text(json.dumps(_sample_details_payload()), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[3]
    cmd = [
        sys.executable,
        "scripts/tools/threshold_artifact_publish.py",
        "--details",
        str(details_file),
        "xai/test",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
    assert result.returncode != 0
    assert "No publish target configured" in result.stderr
