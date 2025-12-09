"""
Tests for amount parsing to recipient in CrossChainVerifier.
"""

from decimal import Decimal

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


def test_calculate_amount_from_outputs_or_vout():
    verifier = CrossChainVerifier()
    tx = {"outputs": [{"address": "addr", "amount": Decimal("1.5")}]}  # pre-parsed
    amt = verifier._calculate_amount_to_recipient(tx, "addr", "BTC")
    assert amt == Decimal("1.5")

    # Fallback to vout parsing
    tx2 = {
        "vout": [
            {"scriptpubkey_address": "addr", "value": 200000000},
            {"scriptpubkey_address": "other", "value": 100000000},
        ]
    }
    amt2 = verifier._calculate_amount_to_recipient(tx2, "addr", "BTC")
    # 2 BTC when value_is_base_units=True with 8 decimals
    assert amt2 == Decimal("2")
