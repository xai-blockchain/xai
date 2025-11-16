#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIXN Blockchain - Monitoring Verification Script

Verifies that all monitoring components are properly installed and configured.
"""

import sys
import os
import requests
import time
from pathlib import Path

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
        "src/aixn/core/prometheus_metrics.py",
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

            # Check for AIXN-specific metrics
            content = response.text
            aixn_metrics = [
                "aixn_block_height",
                "aixn_peers_connected",
                "aixn_transactions_total",
            ]

            metrics_found = []
            for metric in aixn_metrics:
                if metric in content:
                    metrics_found.append(metric)

            if metrics_found:
                print_success(f"Found {len(metrics_found)} AIXN metrics")
                for metric in metrics_found:
                    print(f"  • {metric}")
            else:
                print_warning("No AIXN-specific metrics found yet")
                print_info("  Metrics will appear once the node is running")

            return True
        else:
            print_error(f"Metrics endpoint returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Metrics endpoint is not accessible")
        print_info("  This is normal if the AIXN node is not running")
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


def main():
    """Main verification function"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 60)
    print("AIXN Blockchain - Monitoring Verification")
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
