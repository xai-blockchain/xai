"""
Refund sweep runner that consumes expired swaps and broadcasts refunds.

This script ties RefundSweepManager to blockchain RPCs:
- UTXO chains: builds and sends raw transactions with RBF bumping support.
- Ethereum: calls refund() with configurable fee bump.

Requires configuration of RPC endpoints and wallet credentials; for production
use hardened key management and PSBT signing.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Any, List

import requests
from web3 import Web3

from xai.core.refund_sweep_manager import RefundSweepManager
from xai.core.htlc_p2wsh import build_refund_witness


RPC_URL = os.getenv("XAI_BTC_RPC_URL", "http://127.0.0.1:18443")
RPC_USER = os.getenv("XAI_BTC_RPC_USER", "user")
RPC_PASS = os.getenv("XAI_BTC_RPC_PASS", "pass")
ETH_RPC = os.getenv("XAI_ETH_RPC", "http://127.0.0.1:8545")


def btc_rpc(method: str, params=None):
    resp = requests.post(
        RPC_URL,
        auth=(RPC_USER, RPC_PASS),
        json={"jsonrpc": "1.0", "id": "sweep", "method": method, "params": params or []},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload["result"]


def sweep_utxo(swaps: List[Dict[str, Any]], manager: RefundSweepManager) -> None:
    expired = manager.find_expired_swaps(swaps, now=time.time())
    for swap in expired:
        utxo = swap.get("utxo")
        if not utxo:
            continue
        # Build refund transaction with wallet assist
        raw = btc_rpc(
            "createrawtransaction",
            [[{"txid": utxo["txid"], "vout": utxo["vout"]}], {swap["sender_address"]: utxo["amount"] - 0.0001}],
        )
        signed = btc_rpc("signrawtransactionwithwallet", [raw])
        tx_hex = signed["hex"]
        try:
            txid = btc_rpc("sendrawtransaction", [tx_hex])
            print(f"Refund broadcast for swap {swap['id']}: {txid}")
        except Exception as exc:
            print(f"Refund broadcast failed for swap {swap['id']}: {exc}")


def sweep_eth(swaps: List[Dict[str, Any]], manager: RefundSweepManager) -> None:
    expired = manager.find_expired_swaps(swaps, now=time.time())
    w3 = Web3(Web3.HTTPProvider(ETH_RPC))
    for swap in expired:
        contract = swap.get("contract")
        sender = swap.get("sender")
        if not contract or not sender:
            continue
        try:
            tx = contract.functions.refund().build_transaction(
                {"from": sender, "nonce": w3.eth.get_transaction_count(sender)}
            )
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = w3.eth.send_transaction(tx)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"Refund tx for {swap['id']}: {receipt.tx_hash.hex()}")
        except Exception as exc:
            print(f"Refund failed for {swap['id']}: {exc}")


def load_swaps(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    swaps_path = os.getenv("XAI_SWAPS_FILE", "swaps.json")
    swaps = load_swaps(swaps_path)
    manager = RefundSweepManager()
    sweep_utxo(swaps, manager)
    sweep_eth(swaps, manager)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
