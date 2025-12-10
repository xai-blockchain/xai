"""
Integration parity test for HTLC secret hashing across BTC (P2WSH) and ETH (Solidity).

Ensures a single SHA-256 preimage is used end-to-end so BTC scripts and ETH contracts
share the same hash, matching the deployed helpers and smokes.
"""

import hashlib

from xai.core.aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC, CoinType
from xai.core.htlc_deployer import compile_htlc_contract


def test_htlc_hash_parity_sha256():
    """The same SHA-256 hash must be used for BTC and ETH HTLC legs."""
    preimage = bytes.fromhex("00" * 32)

    htlc_btc = AtomicSwapHTLC(CoinType.BTC)
    swap_btc = htlc_btc.create_swap_contract(
        axn_amount=1,
        other_coin_amount=0.1,
        counterparty_address="02abc",
        timelock_hours=1,
        secret_bytes=preimage,
    )
    # BTC path emits canonical SHA-256 hash
    sha_hash = swap_btc["secret_hash"]
    assert len(sha_hash) == 64

    # ETH path must embed the same SHA-256 hash in constructor args
    htlc_eth = AtomicSwapHTLC(CoinType.ETH)
    swap_eth = htlc_eth.create_swap_contract(
        axn_amount=1,
        other_coin_amount=0.1,
        counterparty_address="0xRecipient",
        timelock_hours=1,
        secret_bytes=preimage,
    )
    solidity_src = swap_eth["smart_contract"]
    assert sha_hash in solidity_src

    # And the contract constructor expects the SHA-256 hash (ABI compiled here)
    abi, _ = compile_htlc_contract()
    secret_param = next(x for x in abi if x.get("type") == "constructor")
    # Ensure the constructor param type matches bytes32 and the value we pass is a hex str of SHA-256
    assert secret_param["inputs"][0]["type"] == "bytes32"
    # Recompute hash to prove value matches expectation
    assert sha_hash == hashlib.sha256(bytes.fromhex(swap_eth["secret"])).hexdigest()
