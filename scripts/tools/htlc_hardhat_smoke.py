"""
Hardhat HTLC smoke test.

Prerequisites:
- Hardhat node running at http://127.0.0.1:8545 with funded accounts.

Flows:
1. Happy path: deploy AtomicSwapETH with a future timelock and claim with the secret.
2. Refund path: deploy with an expired timelock and exercise refund().

Note: This script uses unlocked accounts provided by Hardhat; for production,
integrate proper key management.
"""

from __future__ import annotations

import secrets
import time
import hashlib

from eth_utils import to_hex
from web3 import Web3

from xai.core.htlc_deployer import deploy_htlc, claim_htlc, refund_htlc


def main() -> int:
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    if not w3.is_connected():
        print("Hardhat node not reachable at http://127.0.0.1:8545")
        return 1

    accounts = w3.eth.accounts
    sender = accounts[0]
    recipient = accounts[1]

    secret = secrets.token_bytes(32)
    secret_hash_sha256 = hashlib.sha256(secret).hexdigest()
    base_time = w3.eth.get_block("latest")["timestamp"]
    timelock = int(base_time + 600)

    print("Deploying HTLC (claim path)...")
    contract = deploy_htlc(
        w3,
        secret_hash=secret_hash_sha256,
        recipient=recipient,
        timelock_unix=timelock,
        value_wei=w3.to_wei(1, "ether"),
        sender=sender,
    )
    print(f"Claim HTLC deployed at {contract.address}")

    print("Claiming HTLC...")
    result = claim_htlc(
        w3,
        contract,
        secret=to_hex(secret),
        sender=recipient,
    )
    print("Claim result:", result)

    print("Deploying HTLC (refund path)...")
    future_timelock = int(w3.eth.get_block("latest")["timestamp"] + 60)
    contract_refund = deploy_htlc(
        w3,
        secret_hash=secret_hash_sha256,
        recipient=recipient,
        timelock_unix=future_timelock,
        value_wei=w3.to_wei(0.5, "ether"),
        sender=sender,
    )
    print(f"Refund HTLC deployed at {contract_refund.address}")
    print("Waiting for timelock to expire via evm_increaseTime...")
    try:
        w3.provider.make_request("evm_increaseTime", [120])  # type: ignore[attr-defined]
        w3.provider.make_request("evm_mine", [])  # type: ignore[attr-defined]
    except Exception as exc:
        print("Failed to advance time on provider:", exc)
        return 1
    refund = refund_htlc(w3, contract_refund, sender=sender)
    print("Refund result:", refund)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
