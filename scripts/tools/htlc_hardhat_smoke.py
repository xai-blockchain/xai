"""
Hardhat HTLC smoke test.

Prerequisites:
- Hardhat node running at http://127.0.0.1:8545 with funded accounts.

Flow:
1. Compile/deploy AtomicSwapETH with a future timelock and 1 ETH value.
2. Claim funds using generated secret before timelock.

Note: This script uses unlocked accounts provided by Hardhat; for production,
integrate proper key management.
"""

from __future__ import annotations

import secrets
import time
import hashlib

from eth_utils import to_hex
from web3 import Web3

from xai.core.htlc_deployer import deploy_htlc, claim_htlc


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
    timelock = int(time.time()) + 600

    print("Deploying HTLC...")
    contract = deploy_htlc(
        w3,
        secret_hash_keccak=secret_hash_sha256,
        recipient=recipient,
        timelock_unix=timelock,
        value_wei=w3.to_wei(1, "ether"),
        sender=sender,
    )
    print(f"Contract deployed at {contract.address}")

    print("Claiming HTLC...")
    result = claim_htlc(
        w3,
        contract,
        secret=to_hex(secret),
        sender=recipient,
    )
    print("Claim result:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
