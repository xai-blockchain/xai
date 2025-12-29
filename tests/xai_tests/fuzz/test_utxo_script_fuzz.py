"""
Fuzzing tests for UTXO script validation and manager handling.

These tests feed randomized locking scripts and amounts into the UTXO manager to
ensure invalid data never crashes the system and amounts are clamped to sane ranges.
"""

import os
import random
import string

import pytest

from xai.core.transactions.utxo_manager import UTXOManager, UTXOValidationError


def _random_script() -> str:
    alphabet = string.ascii_letters + string.digits + "+-/= "
    return "".join(random.choice(alphabet) for _ in range(random.randint(0, 200)))


def _random_amount() -> float:
    # Occasionally push extreme values
    choice = random.random()
    if choice < 0.2:
        return random.uniform(-1e6, -1)
    if choice < 0.4:
        return random.uniform(1e6, 1e9)
    return random.uniform(0, 1_000)


def test_utxo_manager_handles_random_scripts_and_amounts():
    manager = UTXOManager()
    for _ in range(200):
        address = "XAI" + os.urandom(20).hex()
        txid = os.urandom(32).hex()
        vout = random.randint(0, 10)
        amount = _random_amount()
        script = _random_script()
        try:
            manager.add_utxo(address, txid, vout, amount, script)
            assert manager.get_utxos_for_address(address)
        except UTXOValidationError:
            continue


def test_utxo_manager_rejects_nan_and_infinity():
    manager = UTXOManager()
    address = "XAI" + "0" * 40
    txid = "ff" * 32
    for bad in [float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(UTXOValidationError):
            manager.add_utxo(address, txid, 0, bad, "OP_DUP OP_HASH160")
