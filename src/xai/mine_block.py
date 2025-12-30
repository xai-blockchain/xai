"""
Ask the running XAI node to mine a block with the current mempool.

Usage:
  python mine_block.py --miner XAI1MinerAddress
"""

import argparse

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Trigger the node to mine a block.")
    parser.add_argument("--miner", required=True, help="Miner address (XAI1...)")
    parser.add_argument("--node-url", default="http://127.0.0.1:5000", help="Node RPC base URL")
    return parser.parse_args()


def main():
    args = parse_args()
    url = f"{args.node_url.rstrip('/')}/mine"
    response = requests.post(url, json={"miner_address": args.miner}, timeout=30)
    print("Status:", response.status_code)
    print(response.text)


if __name__ == "__main__":
    main()
