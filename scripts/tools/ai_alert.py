"""Simple alert helper that pushes AI metrics alerts."""

import argparse
import json
import os
import requests
import sys


def fetch_metrics(base_url):
    resp = requests.get(f"{base_url}/ai/metrics", timeout=5)
    resp.raise_for_status()
    return resp.json()


def trigger_webhook(url, payload):
    headers = {"Content-Type": "application/json"}
    requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)


def main():
    parser = argparse.ArgumentParser(description="AI metrics alert helper")
    parser.add_argument("--base-url", required=True, help="Node base URL (http://localhost:8545)")
    parser.add_argument(
        "--token-threshold",
        type=int,
        default=100000,
        help="Trigger when tokens consumed exceeds this",
    )
    parser.add_argument("--webhook", help="Optional webhook URL to POST alerts")
    args = parser.parse_args()

    metrics = fetch_metrics(args.base_url)
    tokens = metrics.get("tokens_consumed", 0)

    print(f"Tokens consumed: {tokens}")

    if tokens >= args.token_threshold:
        message = {
            "text": f"⚠️ AI bridge consumed {tokens} tokens (threshold {args.token_threshold})"
        }
        print(message["text"])
        if args.webhook:
            try:
                trigger_webhook(args.webhook, message)
                print("Webhook alerted successfully")
            except Exception as exc:
                print(f"Webhook failed: {exc}", file=sys.stderr)
    else:
        print("Token usage below threshold, no alert.")


if __name__ == "__main__":
    main()
