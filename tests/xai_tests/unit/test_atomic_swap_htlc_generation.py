"""
Tests for HTLC generation logic in atomic_swap_11_coins.
"""

import re
from decimal import Decimal

from xai.core.aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC, CoinType


def test_utxo_htlc_includes_hash_and_timelock():
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.1, counterparty_address="pubkey", timelock_hours=1)
    assert contract["contract_type"] == "HTLC_UTXO"
    assert "OP_SHA256" in contract["script_template"]
    assert str(contract["timelock"]) in contract["refund_method"]
    assert contract["secret_hash"] in contract["script_template"]


def test_eth_htlc_contains_hash_and_recipient():
    htlc = AtomicSwapHTLC(CoinType.ETH)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.2, counterparty_address="0xRecipient", timelock_hours=1)
    solidity = contract["smart_contract"]
    assert "AtomicSwapETH" in solidity
    assert contract["secret_hash_keccak"] in solidity
    assert "0xRecipient" in solidity
    # amount is embedded as ether literal
    assert str(0.2) in solidity


def test_verify_swap_claim_checks_secret_and_timelock(monkeypatch):
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.1, counterparty_address="pub", timelock_hours=1)
    secret = contract["secret"]
    secret_hash = contract["secret_hash"]

    valid, msg = htlc.verify_swap_claim(secret, secret_hash, contract)
    assert valid is True
    assert "Valid claim" in msg

    # Wrong secret fails
    valid, msg = htlc.verify_swap_claim("00" * 32, secret_hash, contract)
    assert valid is False

    # Expired timelock fails
    monkeypatch.setattr("time.time", lambda: contract["timelock"] + 1)
    valid, msg = htlc.verify_swap_claim(secret, secret_hash, contract)
    assert valid is False
    assert "Timelock expired" in msg
