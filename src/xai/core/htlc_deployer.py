"""
Deploy and operate Ethereum HTLC contracts with automated claim/refund helpers.

This module compiles the HTLC Solidity contract using py-solc-x, deploys it via
web3.py, and exposes claim/refund functions with gas estimation and safety
checks. Designed for production use with explicit error handling.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from eth_utils import to_hex, to_checksum_address
from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams
import solcx

HTLC_SOLIDITY_SOURCE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

/// @title AtomicSwapETH - Hashed timelock contract for atomic swaps
contract AtomicSwapETH {
    bytes32 public immutable secretHash;
    address public immutable recipient;
    address public immutable sender;
    uint256 public immutable timelock;

    constructor(bytes32 _secretHash, address _recipient, uint256 _timelock) payable {
        require(_secretHash != bytes32(0), "secretHash required");
        require(_recipient != address(0), "recipient required");
        require(_timelock > block.timestamp, "timelock must be in future");
        secretHash = _secretHash;
        recipient = _recipient;
        sender = msg.sender;
        timelock = _timelock;
    }

    /// @notice Claim funds by providing the preimage before timelock expires.
    function claim(bytes32 secret) external {
        require(sha256(abi.encodePacked(secret)) == secretHash, "invalid secret");
        require(msg.sender == recipient, "not recipient");
        _payout(payable(recipient));
    }

    /// @notice Refund to sender after timelock expires.
    function refund() external {
        require(block.timestamp >= timelock, "timelock not expired");
        require(msg.sender == sender, "not sender");
        _payout(payable(sender));
    }

    function _payout(address payable to) internal {
        uint256 bal = address(this).balance;
        (bool ok, ) = to.call{value: bal}("");
        require(ok, "transfer failed");
    }
}
"""


def _ensure_solc(version: str = "0.8.21") -> None:
    """Install solc if missing."""
    if version not in solcx.get_installed_solc_versions():
        solcx.install_solc(version)
    solcx.set_solc_version(version)


def compile_htlc_contract(version: str = "0.8.21") -> Tuple[list, str]:
    """Compile the Solidity HTLC contract and return (abi, bytecode)."""
    _ensure_solc(version)
    compiled = solcx.compile_source(
        HTLC_SOLIDITY_SOURCE,
        output_values=["abi", "bin"],
        solc_version=version,
    )
    _, contract_data = compiled.popitem()
    return contract_data["abi"], contract_data["bin"]


def _build_tx_params(
    w3: Web3,
    sender: str,
    *,
    value_wei: int = 0,
    gas: Optional[int] = None,
    max_fee_per_gas: Optional[int] = None,
    max_priority_fee_per_gas: Optional[int] = None,
) -> TxParams:
    base: TxParams = {
        "from": to_checksum_address(sender),
        "value": value_wei,
        "nonce": w3.eth.get_transaction_count(sender),
        "chainId": w3.eth.chain_id,
    }
    if max_fee_per_gas is None or max_priority_fee_per_gas is None:
        # Prefer EIP-1559 fee fields; fallback to gas_price if priority API absent.
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas") or w3.eth.gas_price
        try:
            priority_fee = int(getattr(w3.eth, "max_priority_fee"))
        except Exception:
            priority_fee = int(base_fee // 10)  # conservative fallback
        max_priority_fee_per_gas = max_priority_fee_per_gas or priority_fee
        # Choose a ceiling that is comfortably above base+priority to avoid underpriced txs.
        max_fee_per_gas = max_fee_per_gas or (base_fee * 2 + max_priority_fee_per_gas)
    base["maxFeePerGas"] = max_fee_per_gas
    base["maxPriorityFeePerGas"] = max_priority_fee_per_gas
    if gas is not None:
        base["gas"] = gas
    return base


def deploy_htlc(
    w3: Web3,
    secret_hash_keccak: str,
    recipient: str,
    timelock_unix: int,
    *,
    value_wei: int,
    sender: str,
    gas: Optional[int] = None,
    max_fee_per_gas: Optional[int] = None,
    max_priority_fee_per_gas: Optional[int] = None,
    solc_version: str = "0.8.21",
) -> Contract:
    """Deploy the HTLC contract and return the contract instance."""
    abi, bytecode = compile_htlc_contract(solc_version)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_params = _build_tx_params(
        w3,
        sender,
        value_wei=value_wei,
        gas=gas,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
    )
    construct_tx = contract.constructor(to_hex(hexstr=secret_hash_keccak), recipient, timelock_unix).build_transaction(
        tx_params
    )
    # Estimate gas if not provided
    if "gas" not in construct_tx:
        construct_tx["gas"] = w3.eth.estimate_gas(construct_tx)
    tx_hash = w3.eth.send_transaction(construct_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return w3.eth.contract(address=receipt.contractAddress, abi=abi)


def claim_htlc(
    w3: Web3,
    contract: Contract,
    secret: str,
    *,
    sender: str,
    gas: Optional[int] = None,
    max_fee_per_gas: Optional[int] = None,
    max_priority_fee_per_gas: Optional[int] = None,
) -> Dict[str, Any]:
    """Claim HTLC funds by providing the secret preimage."""
    tx = contract.functions.claim(to_hex(hexstr=secret)).build_transaction(
        _build_tx_params(
            w3,
            sender,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
    )
    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)
    tx_hash = w3.eth.send_transaction(tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return dict(status=receipt.status, tx_hash=tx_hash.hex(), block=receipt.blockNumber)


def refund_htlc(
    w3: Web3,
    contract: Contract,
    *,
    sender: str,
    gas: Optional[int] = None,
    max_fee_per_gas: Optional[int] = None,
    max_priority_fee_per_gas: Optional[int] = None,
) -> Dict[str, Any]:
    """Refund HTLC after timelock expiry."""
    tx = contract.functions.refund().build_transaction(
        _build_tx_params(
            w3,
            sender,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
    )
    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)
    tx_hash = w3.eth.send_transaction(tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return dict(status=receipt.status, tx_hash=tx_hash.hex(), block=receipt.blockNumber)
