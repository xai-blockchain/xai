"""
Atomic swap artifact helpers shared by CLI tooling and tests.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xai.core import htlc_p2wsh
from xai.core.aixn_blockchain.atomic_swap_11_coins import (
    AtomicSwapHTLC,
    CoinType,
    MeshDEXPairManager,
    SwapStateMachine,
)
from xai.core.htlc_deployer import compile_htlc_contract


class AtomicSwapArtifactError(Exception):
    """Raised when artifact generation cannot be completed."""

@dataclass
class UTXOParams:
    sender_pubkey: str
    recipient_pubkey: str
    hrp: str = "bc"
    network: str = "bitcoin"
    decimals: int = 8
    change_address: str | None = None
    suggested_fee_sats: int | None = None

@dataclass
class EthereumParams:
    sender: str
    provider: str | None = None
    auto_deploy: bool = False
    value_wei: int | None = None
    gas: int | None = None
    max_fee_per_gas: int | None = None
    max_priority_fee_per_gas: int | None = None
    solc_version: str = "0.8.21"

def _resolve_atomic_swap(pair: str) -> AtomicSwapHTLC:
    manager = MeshDEXPairManager()
    normalized = pair.strip()
    if normalized not in manager.supported_pairs:
        raise AtomicSwapArtifactError(f"Unsupported trading pair: {pair}")
    return manager.supported_pairs[normalized]["atomic_swap"]

def generate_swap_artifacts(
        pair: str,
        axn_amount: float,
        other_amount: float,
        counterparty: str,
        *,
        timelock_hours: int = 24,
        utxo: UTXOParams | None = None,
        eth: EthereumParams | None = None,
        web3_factory=None,
) -> dict[str, Any]:
    """
    Create a swap contract for the requested pair and return deployable artifacts.
    """
    atomic_swap = _resolve_atomic_swap(pair)
    deployment_config: dict[str, Any] = {}

    if utxo:
        deployment_config["utxo"] = {
            "sender_pubkey": utxo.sender_pubkey,
            "recipient_pubkey": utxo.recipient_pubkey,
            "hrp": utxo.hrp,
            "network": utxo.network,
            "decimals": utxo.decimals,
            "change_address": utxo.change_address,
            "suggested_fee_sats": utxo.suggested_fee_sats,
        }

    if eth:
        eth_cfg: dict[str, Any] = {
            "sender": eth.sender,
            "auto_deploy": eth.auto_deploy,
            "value_wei": eth.value_wei,
            "gas": eth.gas,
            "max_fee_per_gas": eth.max_fee_per_gas,
            "max_priority_fee_per_gas": eth.max_priority_fee_per_gas,
            "solc_version": eth.solc_version,
        }
        if eth.provider and eth.auto_deploy:
            if web3_factory is None:
                from web3 import Web3  # type: ignore

                web3_factory = lambda url: Web3(Web3.HTTPProvider(url))
            eth_cfg["web3"] = web3_factory(eth.provider)
        deployment_config["ethereum"] = eth_cfg

    swap = atomic_swap.create_swap_contract(
        axn_amount=axn_amount,
        other_coin_amount=other_amount,
        counterparty_address=counterparty,
        timelock_hours=timelock_hours,
        deployment_config=deployment_config if deployment_config else None,
    )

    abi, bytecode = compile_htlc_contract()
    artifact = {
        "pair": pair,
        "generated_at": time.time(),
        "swap": swap,
        "ethereum_contract": {
            "abi": abi,
            "bytecode": bytecode,
        },
    }
    return artifact

def build_btc_refund_witness(sender_signature_hex: str, redeem_script_hex: str) -> dict[str, str]:
    """
    Construct the witness stack for the refund path of a P2WSH HTLC.
    """
    sig = sender_signature_hex.strip()
    redeem_script = redeem_script_hex.strip()
    if not sig or not redeem_script:
        raise AtomicSwapArtifactError("signature and redeem_script_hex are required")
    witness = htlc_p2wsh.build_refund_witness(sig, redeem_script)
    return {
        "signature": witness[0],
        "selector": witness[1],
        "redeem_script": witness[2],
    }

def write_artifacts(artifacts: dict[str, Any], output_path: Path) -> Path:
    """
    Persist artifact dictionary to disk in JSON format.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(artifacts, handle, indent=2, sort_keys=True)
    return output_path

def export_swap_state(state_machine: SwapStateMachine, output_path: Path) -> None:
    """
    Dump the current swap state machine contents for auditing or scripting.
    """
    payload = {
        "swaps": state_machine.swaps,
        "exported_at": time.time(),
    }
    write_artifacts(payload, output_path)

__all__ = [
    "AtomicSwapArtifactError",
    "UTXOParams",
    "EthereumParams",
    "generate_swap_artifacts",
    "build_btc_refund_witness",
    "write_artifacts",
    "export_swap_state",
]
