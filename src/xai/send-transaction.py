"""
Submit a signed transaction to the running XAI node.

Usage:
  python send-transaction.py --private-key <hex> --to <address> --amount 1.2 --fee 0.01

The script builds the transaction, signs it, and POSTs to /transactions.
"""

import argparse
import json
from pathlib import Path

import requests

from xai.core.blockchain import Transaction
from xai.core.wallet import Wallet


def parse_args():
    parser = argparse.ArgumentParser(description="Create and submit a signed XAI transaction.")
    parser.add_argument("--private-key", required=True, help="Sender private key (hex)")
    parser.add_argument("--to", required=True, help="Recipient address (XAI1...)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in XAI")
    parser.add_argument("--fee", type=float, default=0.001, help="Transaction fee in XAI")
    parser.add_argument("--node-url", default="http://127.0.0.1:5000", help="Node API base URL")
    parser.add_argument("--nonce", type=int, help="Optional transaction nonce")
    return parser.parse_args()


def main():
    args = parse_args()
    wallet = Wallet(private_key=args.private_key)

    tx = Transaction(
        sender=wallet.address,
        recipient=args.to,
        amount=args.amount,
        fee=args.fee,
        public_key=wallet.public_key,
    )
    if args.nonce is not None:
        tx.nonce = args.nonce

    tx.sign_transaction(wallet.private_key)
    payload = tx.to_dict()

    url = f"{args.node_url.rstrip('/')}/transactions"
    response = requests.post(url, json=payload, timeout=15)
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)


if __name__ == "__main__":
    main()
