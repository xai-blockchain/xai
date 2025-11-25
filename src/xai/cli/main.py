"""Primary command line interface for the XAI blockchain."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Sequence

import requests

from xai.core.blockchain import Blockchain
from xai.core.node import BlockchainNode
from xai.core.node_utils import DEFAULT_HOST, DEFAULT_PORT

DEFAULT_API_URL = os.getenv("XAI_API_URL", "http://localhost:18545")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _node_status(args: argparse.Namespace) -> int:
    url = f"{args.base_url.rstrip('/')}/health"
    try:
        response = requests.get(url, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"Failed to reach node: {exc}", file=sys.stderr)
        return 2

    try:
        data = response.json()
    except ValueError:
        print(f"Invalid response ({response.status_code}): {response.text}", file=sys.stderr)
        return 3

    if args.json:
        _print_json(data)
    else:
        status = data.get("status", "unknown")
        uptime = data.get("services", {}).get("api", "n/a")
        height = data.get("blockchain", {}).get("height", "-")
        print(f"Status : {status}\nAPI    : {uptime}\nHeight : {height}")

    return 0 if response.ok else 1


def _node_sync(args: argparse.Namespace) -> int:
    url = f"{args.base_url.rstrip('/')}/sync"
    try:
        response = requests.post(url, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"Failed to contact node: {exc}", file=sys.stderr)
        return 2

    try:
        data = response.json()
    except ValueError:
        print(f"Invalid response ({response.status_code}): {response.text}", file=sys.stderr)
        return 3

    if args.json:
        _print_json(data)
    else:
        synced = "yes" if data.get("synced") else "no"
        length = data.get("chain_length", "-")
        print(f"Synced: {synced}\nLength: {length}")

    return 0 if response.ok else 1


def _node_run(args: argparse.Namespace) -> int:
    blockchain = Blockchain()
    node = BlockchainNode(
        blockchain=blockchain,
        host=args.host,
        port=args.port,
        miner_address=args.miner,
    )

    for peer in args.peer or []:
        node.add_peer(peer)

    try:
        node.run(debug=args.debug)
    except KeyboardInterrupt:
        print("\nNode shutdown requested. Goodbye!")
        return 0

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XAI blockchain utilities")
    subparsers = parser.add_subparsers(dest="command")

    node_parser = subparsers.add_parser("node", help="Manage or inspect nodes")
    node_sub = node_parser.add_subparsers(dest="node_command")

    run_parser = node_sub.add_parser("run", help="Start a standalone node")
    run_parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host (default: %(default)s)")
    run_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP/API port")
    run_parser.add_argument("--miner", help="Address to receive mining rewards")
    run_parser.add_argument(
        "--peer",
        action="append",
        help="Optional peer URL to connect to (repeatable)",
    )
    run_parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    run_parser.set_defaults(func=_node_run)

    status_parser = node_sub.add_parser("status", help="Query /health from a running node")
    status_parser.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    status_parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout")
    status_parser.add_argument("--json", action="store_true", help="Emit raw JSON")
    status_parser.set_defaults(func=_node_status)

    sync_parser = node_sub.add_parser("sync", help="Trigger /sync on a running node")
    sync_parser.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    sync_parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout")
    sync_parser.add_argument("--json", action="store_true", help="Emit raw JSON")
    sync_parser.set_defaults(func=_node_sync)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
