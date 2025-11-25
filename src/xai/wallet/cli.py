#!/usr/bin/env python3
"""
Simple wallet CLI utilities.

Currently supports requesting testnet faucet funds via the public node API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import requests

from xai.core.wallet import Wallet

DEFAULT_API_URL = os.getenv("XAI_API_URL", "http://localhost:18545")


def _format_response(data: Dict[str, Any], as_json: bool) -> str:
    """Prepare CLI-friendly output."""
    if as_json:
        return json.dumps(data, indent=2, sort_keys=True)

    if data.get("success"):
        txid = data.get("txid", "pending")
        lines = [
            f"Success: {data.get('message', 'Faucet request accepted.')}",
            f"Amount: {data.get('amount', 'N/A')} XAI",
            f"Transaction ID: {txid}",
            data.get("note", ""),
        ]
        return "\n".join(filter(None, lines))

    return f"Error: {data.get('error', 'Unknown error')}"


def _request_faucet(args: argparse.Namespace) -> int:
    """Handle the request-faucet subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/faucet/claim"
    payload = {"address": args.address}

    try:
        response = requests.post(endpoint, json=payload, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"Network error contacting faucet: {exc}", file=sys.stderr)
        return 2

    try:
        data = response.json()
    except ValueError:
        print(
            f"Unexpected response ({response.status_code}): {response.text}",
            file=sys.stderr,
        )
        return 3

    success = response.ok and data.get("success") is True
    print(_format_response(data, args.json))
    return 0 if success else 1


def _generate_address(args: argparse.Namespace) -> int:
    """Handle the generate-address subcommand."""
    wallet = Wallet()
    payload = {
        "success": True,
        "address": wallet.address,
        "public_key": wallet.public_key,
        "private_key": wallet.private_key,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "\n".join(
                [
                    f"Address:     {wallet.address}",
                    f"Public Key:  {wallet.public_key}",
                    f"Private Key: {wallet.private_key}",
                    "\nSave the private key securely. It cannot be recovered.",
                ]
            )
        )

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="XAI wallet utilities")
    subparsers = parser.add_subparsers(dest="command")

    faucet = subparsers.add_parser(
        "request-faucet",
        help="Request testnet XAI via the faucet endpoint",
    )
    faucet.add_argument(
        "--address",
        required=True,
        help="Destination TXAI address",
    )
    faucet.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    faucet.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    faucet.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON response",
    )
    faucet.set_defaults(func=_request_faucet)

    generate = subparsers.add_parser(
        "generate-address",
        help="Generate a brand new wallet address",
    )
    generate.add_argument(
        "--json",
        action="store_true",
        help="Emit the generated keys as JSON",
    )
    generate.set_defaults(func=_generate_address)

    return parser


def main(argv: Any = None) -> int:
    """Program entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
