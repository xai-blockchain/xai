#!/usr/bin/env python3
"""
CLI tooling for generating HTLC artifacts and running refund helpers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from xai.core.htlc_deployer import refund_htlc
from xai.tools.atomic_swap_cli import (
    EthereumParams,
    UTXOParams,
    build_btc_refund_witness,
    generate_swap_artifacts,
    write_artifacts,
)

try:
    from web3 import Web3  # type: ignore
except Exception:  # pragma: no cover
    Web3 = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atomic swap artifact tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate HTLC artifacts for a trading pair")
    gen.add_argument("--pair", required=True, help="Trading pair (e.g., XAI/BTC)")
    gen.add_argument("--axn-amount", type=float, required=True, help="Amount of XAI offered")
    gen.add_argument("--other-amount", type=float, required=True, help="Amount of counterparty asset")
    gen.add_argument("--counterparty", required=True, help="Counterparty address or pubkey")
    gen.add_argument("--timelock-hours", type=int, default=24, help="Timelock horizon in hours")
    gen.add_argument("--output", type=Path, default=Path("swap_artifacts.json"), help="Output file path")
    gen.add_argument("--sender-pubkey", help="Sender pubkey (BTC/LTC, etc.)")
    gen.add_argument("--recipient-pubkey", help="Recipient pubkey (BTC/LTC, etc.)")
    gen.add_argument("--hrp", default="bc", help="Bech32 human readable prefix (default: bc)")
    gen.add_argument("--network", default="bitcoin", help="Network label for metadata")
    gen.add_argument("--eth-provider", help="Ethereum RPC endpoint (HTTP)")
    gen.add_argument("--eth-sender", help="Ethereum sender address for deployment/refund")
    gen.add_argument("--eth-auto-deploy", action="store_true", help="Deploy contract immediately via RPC")
    gen.add_argument("--eth-value-wei", type=int, help="Override ETH value in wei")

    refund_eth = sub.add_parser("refund-eth", help="Execute refund() on an Ethereum HTLC")
    refund_eth.add_argument("--provider", required=True, help="Ethereum RPC endpoint")
    refund_eth.add_argument("--contract", required=True, help="Deployed HTLC contract address")
    refund_eth.add_argument("--sender", required=True, help="Sender address (deploying wallet)")
    refund_eth.add_argument("--abi", type=Path, help="ABI JSON file (defaults to HTLC ABI)")

    refund_btc = sub.add_parser("refund-btc", help="Generate P2WSH refund witness stack")
    refund_btc.add_argument("--signature", required=True, help="Sender signature hex")
    refund_btc.add_argument("--redeem-script", required=True, help="Redeem script hex")

    return parser.parse_args()


def _build_utxo_params(args: argparse.Namespace) -> UTXOParams | None:
    if not args.sender_pubkey or not args.recipient_pubkey:
        return None
    return UTXOParams(
        sender_pubkey=args.sender_pubkey,
        recipient_pubkey=args.recipient_pubkey,
        hrp=args.hrp,
        network=args.network,
    )


def _build_eth_params(args: argparse.Namespace) -> EthereumParams | None:
    if not args.eth_sender:
        return None
    return EthereumParams(
        sender=args.eth_sender,
        provider=args.eth_provider,
        auto_deploy=args.eth_auto_deploy,
        value_wei=args.eth_value_wei,
    )


def cmd_generate(args: argparse.Namespace) -> None:
    artifacts = generate_swap_artifacts(
        pair=args.pair,
        axn_amount=args.axn_amount,
        other_amount=args.other_amount,
        counterparty=args.counterparty,
        timelock_hours=args.timelock_hours,
        utxo=_build_utxo_params(args),
        eth=_build_eth_params(args),
        web3_factory=(lambda url: Web3(Web3.HTTPProvider(url))) if Web3 else None,
    )
    path = write_artifacts(artifacts, args.output)
    print(f"[+] Artifacts written to {path}")


def cmd_refund_eth(args: argparse.Namespace) -> None:
    if Web3 is None:
        raise SystemExit("web3.py is required for Ethereum refund operations")
    w3 = Web3(Web3.HTTPProvider(args.provider))
    if args.abi and args.abi.exists():
        abi = json.loads(args.abi.read_text(encoding="utf-8"))
    else:
        from xai.core.htlc_deployer import compile_htlc_contract

        abi, _ = compile_htlc_contract()
    contract = w3.eth.contract(address=w3.to_checksum_address(args.contract), abi=abi)
    result = refund_htlc(w3, contract, sender=w3.to_checksum_address(args.sender))
    print(json.dumps(result, indent=2))


def cmd_refund_btc(args: argparse.Namespace) -> None:
    witness = build_btc_refund_witness(args.signature, args.redeem_script)
    print(json.dumps(witness, indent=2))


def main() -> None:
    args = _parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "refund-eth":
        cmd_refund_eth(args)
    elif args.command == "refund-btc":
        cmd_refund_btc(args)
    else:  # pragma: no cover
        raise SystemExit(f"Unknown command {args.command}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
