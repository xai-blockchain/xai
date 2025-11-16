import os
import sys
import json
import argparse
import requests


def main():
    parser = argparse.ArgumentParser(description="Register wallet-trade peer")
    parser.add_argument("peer_url", help="Peer host (e.g., http://node2:8545)")
    parser.add_argument(
        "--secret", default=os.getenv("XAI_WALLET_TRADE_PEER_SECRET"), help="Shared secret"
    )
    args = parser.parse_args()

    if not args.secret:
        print("Provide --secret or set XAI_WALLET_TRADE_PEER_SECRET")
        sys.exit(1)

    payload = {"host": args.peer_url, "secret": args.secret}
    url = f"{args.peer_url.rstrip('/')}/wallet-trades/peers/register"
    resp = requests.post(url, json=payload, timeout=5)
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    main()
