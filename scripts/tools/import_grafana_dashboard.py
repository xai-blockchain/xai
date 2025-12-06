#!/usr/bin/env python3
"""
Import a Grafana dashboard JSON via the HTTP API.

Example:
    python scripts/tools/import_grafana_dashboard.py \
        --grafana-url https://grafana.staging.example.com \
        --api-token $(cat ~/.grafana/token) \
        --dashboard-file monitoring/dashboards/grafana/aixn_security_operations.json \
        --folder-uid security-ops
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Grafana dashboard JSON via API.")
    parser.add_argument("--grafana-url", required=True, help="Base Grafana URL, e.g. https://grafana.example.com")
    parser.add_argument(
        "--api-token",
        help="Grafana API token with dashboard write permissions. Defaults to GRAFANA_API_TOKEN env var.",
        default=os.environ.get("GRAFANA_API_TOKEN"),
    )
    parser.add_argument(
        "--dashboard-file",
        required=True,
        help="Path to the dashboard JSON file (e.g. monitoring/dashboards/grafana/aixn_security_operations.json)",
    )
    parser.add_argument(
        "--folder-uid",
        required=True,
        help="Target Grafana folder UID (use Grafana UI → Folder settings → JSON to find UID).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing dashboard with same UID.",
    )
    parser.add_argument(
        "--message",
        default="CLI import",
        help="Optional message stored with the dashboard version.",
    )
    return parser.parse_args()


def load_dashboard(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dashboard file '{path}' not found.")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def import_dashboard(args: argparse.Namespace) -> dict:
    dashboard_json = load_dashboard(args.dashboard_file)
    payload = {
        "dashboard": dashboard_json,
        "folderUid": args.folder_uid,
        "overwrite": bool(args.overwrite),
        "message": args.message,
    }
    url = args.grafana_url.rstrip("/") + "/api/dashboards/db"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.api_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(
            f"Grafana API returned HTTP {exc.code}: {body}"
        ) from exc


def main() -> None:
    args = parse_args()
    if not args.api_token:
        print("ERROR: Provide --api-token or set GRAFANA_API_TOKEN.", file=sys.stderr)
        sys.exit(2)
    try:
        result = import_dashboard(args)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    print("Dashboard import succeeded.")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
