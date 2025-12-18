"""CLI helpers for AI observability"""

import argparse
import requests


def fetch_bridge_status(base_url):
    return requests.get(f"{base_url}/ai/bridge/status", timeout=5).json()


def fetch_bridge_tasks(base_url):
    return requests.get(f"{base_url}/ai/bridge/tasks", timeout=5).json()


def fetch_metrics(base_url):
    return requests.get(f"{base_url}/ai/metrics", timeout=5).json()


def dump(name, data):
    print(f"== {name} ==")
    for key, value in data.items():
        print(f"  {key}: {value}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Inspect AI bridge and metrics")
    parser.add_argument("--base-url", required=True, help="Node base URL (http://localhost:12001)")
    parser.add_argument("--watch", action="store_true", help="Refresh every 30s")

    args = parser.parse_args()

    try:
        while True:
            dump("Bridge Status", fetch_bridge_status(args.base_url))
            dump("Bridge Tasks", fetch_bridge_tasks(args.base_url))
            dump("AI Metrics", fetch_metrics(args.base_url))

            if not args.watch:
                break
            import time

            time.sleep(30)
    except KeyboardInterrupt:
        print("Stopped")
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")


if __name__ == "__main__":
    main()
