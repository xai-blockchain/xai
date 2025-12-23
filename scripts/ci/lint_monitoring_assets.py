#!/usr/bin/env python3
"""
Offline lint for monitoring assets to catch missing P2P/fast-mining signals and datasource wiring
before applying Kubernetes overlays. Intended to run in CI/pre-merge and locally.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONITORING = ROOT / "monitoring"

def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)

def require_file(path: Path, errors: list[str]) -> str:
    if not path.exists():
        fail(f"Missing file: {path}", errors)
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - unexpected IO failure
        fail(f"Failed to read {path}: {exc}", errors)
        return ""

def check_substrings(path: Path, content: str, substrings: Iterable[str], errors: list[str]) -> None:
    for needle in substrings:
        if needle not in content:
            fail(f"{path}: expected to contain '{needle}'", errors)

def validate_alertmanager(errors: list[str]) -> None:
    path = MONITORING / "alertmanager.yml"
    content = require_file(path, errors)
    if not content:
        return
    check_substrings(
        path,
        content,
        substrings=["p2p", "fast_mining", "siem", "receiver"],
        errors=errors,
    )

def validate_prometheus_rules(errors: list[str]) -> None:
    path = MONITORING / "prometheus_alerts.yml"
    content = require_file(path, errors)
    if not content:
        return
    check_substrings(
        path,
        content,
        substrings=[
            "FastMiningConfigEnabled",
            "P2PQuicErrors",
            "P2PQuicDialTimeouts",
            "xai_p2p_nonce_replay_total",
            "xai_p2p_rate_limited_total",
            "xai_p2p_invalid_signature_total",
        ],
        errors=errors,
    )

def _any_uid_prometheus(node: object) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uid" and value == "prometheus":
                return True
            if _any_uid_prometheus(value):
                return True
    elif isinstance(node, list):
        return any(_any_uid_prometheus(item) for item in node)
    return False

def validate_grafana_dashboard(dashboard_path: Path, errors: list[str]) -> None:
    raw = require_file(dashboard_path, errors)
    if not raw:
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{dashboard_path}: invalid JSON ({exc})", errors)
        return

    if not _any_uid_prometheus(data):
        fail(f"{dashboard_path}: expected at least one datasource uid 'prometheus'", errors)

    # Ensure panels include critical metrics; fall back to substring search for robustness
    required_metrics = [
        "xai_p2p_quic_errors_total",
        "xai_p2p_quic_timeouts_total",
        "xai_p2p_nonce_replay_total",
        "xai_p2p_rate_limited_total",
        "xai_p2p_invalid_signature_total",
        "config.fast_mining_",
    ]
    check_substrings(dashboard_path, raw, required_metrics, errors)

    # Optional: confirm title presence to reduce false positives on mis-placed files
    title = data.get("title") or data.get("dashboard", {}).get("title")
    if not title:
        fail(f"{dashboard_path}: missing dashboard title", errors)

def main() -> int:
    errors: list[str] = []

    validate_alertmanager(errors)
    validate_prometheus_rules(errors)

    dashboards: tuple[Path, ...] = (
        MONITORING / "dashboards" / "grafana" / "aixn_security_operations.json",
        MONITORING / "dashboards" / "grafana" / "production" / "aixn_security_operations.json",
    )
    for path in dashboards:
        validate_grafana_dashboard(path, errors)

    if errors:
        sys.stderr.write("[ERROR] Monitoring asset lint failed:\n")
        for item in errors:
            sys.stderr.write(f"  - {item}\n")
        return 1

    print("[OK] Monitoring assets lint passed (Alertmanager/Prometheus/Grafana).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
