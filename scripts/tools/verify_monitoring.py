#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
XAI Blockchain - Monitoring Verification Script

Verifies that all monitoring components are properly installed and configured.
"""

import sys
import os
import requests
import time
from pathlib import Path
import argparse
import json
import subprocess
import shlex

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

class Colors:
    """ANSI color codes"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_header(text):
    """Print a colored header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print("=" * 60)

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")

def check_python_packages():
    """Check if required Python packages are installed"""
    print_header("Checking Python Packages")

    packages = {
        "prometheus_client": "prometheus-client",
        "grafana_api": "grafana-api",
        "pythonjsonlogger": "python-json-logger",
        "psutil": "psutil",
    }

    all_installed = True
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print_success(f"{package_name} is installed")
        except ImportError:
            print_error(f"{package_name} is NOT installed")
            print_info(f"  Install with: pip install {package_name}")
            all_installed = False

    return all_installed

def check_file_structure():
    """Check if monitoring files exist"""
    print_header("Checking File Structure")

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    required_files = [
        "src/xai/core/prometheus_metrics.py",
        "prometheus/prometheus.yml",
        "prometheus/alerts/blockchain_alerts.yml",
        "prometheus/recording_rules/blockchain_rules.yml",
        "prometheus/docker-compose.yml",
        "prometheus/README.md",
        "dashboards/grafana/aixn_blockchain_overview.json",
        "dashboards/grafana/aixn_network_health.json",
        "dashboards/grafana/aixn_api_performance.json",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_success(f"{file_path}")
        else:
            print_error(f"{file_path} NOT FOUND")
            all_exist = False

    return all_exist

def check_metrics_endpoint(port=8000, timeout=2):
    """Check if metrics endpoint is accessible"""
    print_header("Checking Metrics Endpoint")

    url = f"http://localhost:{port}/metrics"

    try:
        print_info(f"Attempting to connect to {url}...")
        response = requests.get(url, timeout=timeout)

        if response.status_code == 200:
            print_success(f"Metrics endpoint is accessible at {url}")

            # Check for XAI-specific metrics
            content = response.text
            xai_metrics = [
                "xai_block_height",
                "xai_peers_connected",
                "xai_transactions_total",
            ]

            metrics_found = []
            for metric in xai_metrics:
                if metric in content:
                    metrics_found.append(metric)

            if metrics_found:
                print_success(f"Found {len(metrics_found)} XAI metrics")
                for metric in metrics_found:
                    print(f"  • {metric}")
            else:
                print_warning("No XAI-specific metrics found yet")
                print_info("  Metrics will appear once the node is running")

            return True
        else:
            print_error(f"Metrics endpoint returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Metrics endpoint is not accessible")
        print_info("  This is normal if the XAI node is not running")
        print_info(f"  The endpoint will be available at {url} when the node starts")
        return None
    except requests.exceptions.Timeout:
        print_error(f"Connection to {url} timed out")
        return False
    except Exception as e:
        print_error(f"Error checking metrics endpoint: {e}")
        return False

def check_prometheus(port=9090):
    """Check if Prometheus is running"""
    print_header("Checking Prometheus")

    url = f"http://localhost:{port}"

    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print_success(f"Prometheus is running at {url}")

            # Check targets
            targets_url = f"{url}/api/v1/targets"
            targets_response = requests.get(targets_url, timeout=2)
            if targets_response.status_code == 200:
                data = targets_response.json()
                active_targets = data.get("data", {}).get("activeTargets", [])
                print_success(f"Found {len(active_targets)} active targets")
            return True
        else:
            print_error(f"Prometheus returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Prometheus is not running")
        print_info("  Start with: docker compose up -d (in prometheus/ directory)")
        print_info(f"  Or visit {url} to check status")
        return None
    except Exception as e:
        print_error(f"Error checking Prometheus: {e}")
        return False

def check_grafana(port=3000):
    """Check if Grafana is running"""
    print_header("Checking Grafana")

    url = f"http://localhost:{port}"

    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print_success(f"Grafana is running at {url}")
            print_info("  Default credentials: admin/admin")
            return True
        else:
            print_error(f"Grafana returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Grafana is not running")
        print_info("  Start with: docker compose up -d (in prometheus/ directory)")
        print_info(f"  Or visit {url} to check status")
        return None
    except Exception as e:
        print_error(f"Error checking Grafana: {e}")
        return False

def check_alertmanager(port=9093):
    """Check if Alertmanager is running"""
    print_header("Checking Alertmanager")

    url = f"http://localhost:{port}"

    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print_success(f"Alertmanager is running at {url}")
            return True
        else:
            print_error(f"Alertmanager returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Alertmanager is not running")
        print_info("  Start with: docker compose up -d (in prometheus/ directory)")
        return None
    except Exception as e:
        print_error(f"Error checking Alertmanager: {e}")
        return False

def check_withdrawal_history(env: str, history_path: Path, max_entries: int, loki_url: str | None, loki_token: str | None) -> bool:
    """Check that withdrawal threshold history is populated and, optionally, query Loki."""
    print_header("Checking Withdrawal Threshold History")
    if not history_path.exists():
        print_warning(f"{history_path} not found")
        print_info("  Run threshold_artifact_ingest.py or ensure the workflow artifacts were synced.")
        return False

    lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        print_warning("History file exists but contains no entries")
        return False

    print_success(f"History file contains {len(lines)} entries (showing latest {max_entries})")
    for entry in lines[-max_entries:]:
        try:
            payload = json.loads(entry)
        except json.JSONDecodeError:
            print_warning(f"  (invalid JSON line skipped: {entry[:60]}...)")
            continue
        summary = (
            f"  - {payload.get('generated_at')} env={payload.get('environment')} "
            f"recommended_rate={payload.get('recommended_rate')} "
            f"current_rate={payload.get('current_rate_threshold')} "
            f"alert_required={payload.get('alert_required')}"
        )
        print_info(summary)

    if loki_url:
        query = '{job="withdrawal_threshold_history",environment="%s"}' % env
        params = {
            "query": query,
            "limit": 5,
        }
        headers = {}
        if loki_token:
            headers["Authorization"] = f"Bearer {loki_token}"
        try:
            response = requests.get(
                f"{loki_url.rstrip('/')}/loki/api/v1/query",
                params=params,
                headers=headers,
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("data", {}).get("result", [])
            if result:
                print_success(f"Loki query returned {len(result)} streams for environment={env}")
            else:
                print_warning("Loki query returned no streams; ensure promtail is shipping the JSONL file.")
        except Exception as exc:
            print_warning(f"Unable to query Loki: {exc}")
    return True

def check_remote_withdrawal_history(
    hosts: list[str],
    user: str,
    ssh_key: str | None,
    remote_path: str,
    max_entries: int,
    timeout: int,
):
    """Pull withdrawal threshold history from remote hosts via SSH."""
    if not hosts:
        return True

    overall_success = True
    for host in hosts:
        print_header(f"Remote Withdrawal Threshold History: {host}")
        ssh_command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            f"ConnectTimeout={timeout}",
        ]
        if ssh_key:
            ssh_command.extend(["-i", ssh_key])
        ssh_command.append(f"{user}@{host}")
        remote_cmd = (
            f"if [ -f {shlex.quote(remote_path)} ]; then tail -n {max_entries} {shlex.quote(remote_path)}; "
            f"else echo '__MISSING__'; fi"
        )
        ssh_command.append(remote_cmd)

        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            print_error(f"SSH to {host} failed: {exc}")
            overall_success = False
            continue

        if result.returncode != 0:
            print_error(
                f"SSH command on {host} returned {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
            overall_success = False
            continue

        output = result.stdout.strip()
        if output == "__MISSING__":
            print_warning(f"{remote_path} not found on {host}")
            overall_success = False
            continue

        lines = [line for line in output.splitlines() if line.strip()]
        if not lines:
            print_warning(f"{host}: file exists but returned no content")
            overall_success = False
            continue

        print_success(f"{host}: received {len(lines)} entries (tail {max_entries})")
        for entry in lines:
            try:
                payload = json.loads(entry)
            except json.JSONDecodeError:
                print_warning(f"  (invalid JSON from {host}: {entry[:60]}...)")
                continue
            print_info(
                "  - {generated_at} env={environment} recommended_rate={recommended_rate} current_rate={current_rate_threshold} alert_required={alert_required}".format(
                    **payload
                )
            )

    return overall_success

def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description="Verify XAI monitoring stack.")
    parser.add_argument(
        "--environment",
        default=os.environ.get("DEPLOY_ENVIRONMENT", "staging"),
        help="Environment label used when querying Loki or history files.",
    )
    parser.add_argument(
        "--skip-withdrawal-history",
        action="store_true",
        help="Skip the withdrawal threshold history check.",
    )
    parser.add_argument(
        "--history-dir",
        default=os.environ.get("WITHDRAWAL_HISTORY_DIR", "/var/lib/xai/monitoring"),
        help="Directory that contains withdrawal_threshold_history.jsonl (defaults to /var/lib/xai/monitoring or WITHDRAWAL_HISTORY_DIR env).",
    )
    parser.add_argument(
        "--history-file",
        default=None,
        help="Explicit path to withdrawal_threshold_history.jsonl (overrides --history-dir).",
    )
    parser.add_argument(
        "--history-max-entries",
        type=int,
        default=5,
        help="Number of history entries to show when verifying the file.",
    )
    parser.add_argument(
        "--remote-host",
        action="append",
        help="SSH host (or IP) to check withdrawal history on. Can be specified multiple times.",
    )
    parser.add_argument(
        "--remote-history-path",
        default=os.environ.get("REMOTE_WITHDRAWAL_HISTORY_PATH", "/var/lib/xai/monitoring/withdrawal_threshold_history.jsonl"),
        help="Path to withdrawal_threshold_history.jsonl on remote hosts (default /var/lib/xai/monitoring/withdrawal_threshold_history.jsonl).",
    )
    parser.add_argument(
        "--ssh-user",
        default=os.environ.get("WITHDRAWAL_SSH_USER", "ubuntu"),
        help="SSH user for remote checks (default ubuntu or WITHDRAWAL_SSH_USER).",
    )
    parser.add_argument(
        "--ssh-key",
        default=os.environ.get("WITHDRAWAL_SSH_KEY"),
        help="Optional path to SSH private key for remote checks (default uses SSH agent).",
    )
    parser.add_argument(
        "--ssh-timeout",
        type=int,
        default=10,
        help="SSH connection timeout in seconds (default 10).",
    )
    args = parser.parse_args()
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 60)
    print("XAI Blockchain - Monitoring Verification")
    print("=" * 60)
    print(f"{Colors.RESET}")

    results = {}

    # Run all checks
    results["packages"] = check_python_packages()
    results["files"] = check_file_structure()
    results["metrics"] = check_metrics_endpoint()
    results["prometheus"] = check_prometheus()
    results["grafana"] = check_grafana()
    results["alertmanager"] = check_alertmanager()
    if not args.skip_withdrawal_history:
        history_path = Path(args.history_file) if args.history_file else Path(args.history_dir) / "withdrawal_threshold_history.jsonl"
        loki_url = os.environ.get("LOKI_URL")
        loki_token = os.environ.get("LOKI_BEARER_TOKEN")
        results["withdrawal_history"] = check_withdrawal_history(
            env=args.environment,
            history_path=history_path,
            max_entries=args.history_max_entries,
            loki_url=loki_url,
            loki_token=loki_token,
        )
        if args.remote_host:
            remote_result = check_remote_withdrawal_history(
                hosts=args.remote_host,
                user=args.ssh_user,
                ssh_key=args.ssh_key,
                remote_path=args.remote_history_path,
                max_entries=args.history_max_entries,
                timeout=args.ssh_timeout,
            )
            results["remote_withdrawal_history"] = remote_result

    # Summary
    print_header("Verification Summary")

    total_checks = len(results)
    passed = sum(1 for v in results.values() if v is True)
    warnings = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)

    print(f"\nTotal Checks: {total_checks}")
    print_success(f"Passed: {passed}")
    if warnings > 0:
        print_warning(f"Warnings: {warnings}")
    if failed > 0:
        print_error(f"Failed: {failed}")

    # Overall status
    print("\n" + "=" * 60)
    if failed == 0 and warnings == 0:
        print_success("All checks passed! Monitoring is fully set up.")
        return 0
    elif failed == 0:
        print_warning("Setup is partially complete. Some services are not running.")
        print_info("This is normal if you haven't started the monitoring stack yet.")
        return 0
    else:
        print_error("Some checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(1)
