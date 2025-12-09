"""
Tests for redeem script/witness hash helpers.
"""

import hashlib

from xai.core.aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC


def test_build_redeem_script_and_hash():
    secret_hash = "aa" * 32
    recipient = "02abcd"
    sender = "03cdef"
    timelock = 12345
    script = AtomicSwapHTLC.build_utxo_redeem_script(secret_hash, recipient, sender, timelock)
    assert "OP_SHA256" in script
    assert secret_hash in script
    assert str(timelock) in script
    assert recipient in script and sender in script

    witness_hash = AtomicSwapHTLC.witness_script_hash(script)
    expected = hashlib.sha256(script.encode("utf-8")).hexdigest()
    assert witness_hash == expected
    assert len(witness_hash) == 64
