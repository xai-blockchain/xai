"""
Unit tests for sweep/recovery planning hooks in atomic swap manager.
"""

from decimal import Decimal

import pytest

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier, SwapRefundPlanner, SwapState


def test_cross_chain_verifier_rejects_replay(monkeypatch):
    """Sanity check verifier cache prevents repeated HTTP calls (recovery/sweep uses it)."""
    verifier = CrossChainVerifier()
    called = {"count": 0}

    def _fake_fetch(provider, coin, tx_hash):
        called["count"] += 1
        return {
            "confirmations": 5,
            "outputs": [
                {"address": "addr", "amount": 1},
                {"address": "other", "amount": 0.5},
            ],
        }

    monkeypatch.setattr(verifier, "_fetch_transaction", _fake_fetch)

    ok1, _, _ = verifier.verify_transaction_on_chain(
        "BTC", "a" * 64, expected_amount=1, recipient="addr", min_confirmations=1
    )
    ok2, _, _ = verifier.verify_transaction_on_chain(
        "BTC", "a" * 64, expected_amount=1, recipient="addr", min_confirmations=1
    )
    assert ok1 and ok2
    assert called["count"] == 1  # cache hit prevents replayed HTTP


def test_calculate_fee_guardrails():
    """Refund/sweep logic relies on guardrails; ensure bounds hold."""
    fee = CrossChainVerifier.calculate_atomic_swap_fee(amount=5, fee_rate_per_byte=0.00000002, tx_size_bytes=250)
    assert fee >= Decimal("0.0001")
    assert fee <= Decimal("0.25")


def test_refund_planner_uses_spv_and_timelock(monkeypatch):
    class StubVerifier:
        def __init__(self):
            self.calls = []

        def verify_minimum_confirmations(self, coin_type, tx_hash, min_confirmations):
            self.calls.append((coin_type, tx_hash, min_confirmations))
            # Approve only matching txhash
            if tx_hash == "goodtx":
                return True, 12
            return False, 1

    verifier = StubVerifier()
    planner = SwapRefundPlanner(verifier, now_fn=lambda: 2000)

    swaps = [
        {
            "swap_id": "refundable",
            "coin": "BTC",
            "funding_txid": "goodtx",
            "timelock": 1000,
            "min_confirmations": 6,
            "state": SwapState.FUNDED,
        },
        {
            "swap_id": "not_expired",
            "coin": "BTC",
            "funding_txid": "goodtx",
            "timelock": 3000,
            "min_confirmations": 6,
            "state": SwapState.FUNDED,
        },
        {
            "swap_id": "low_conf",
            "coin": "BTC",
            "funding_txid": "badtx",
            "timelock": 1000,
            "min_confirmations": 6,
            "state": SwapState.COUNTERPARTY_FUNDED.value,
        },
        {
            "swap_id": "wrong_state",
            "coin": "BTC",
            "funding_txid": "goodtx",
            "timelock": 1000,
            "min_confirmations": 6,
            "state": SwapState.CLAIMED,
        },
    ]

    refundable = planner.plan_refunds(swaps)
    assert [s["swap_id"] for s in refundable] == ["refundable"]
    assert refundable[0]["confirmations"] == 12
    assert ("BTC", "goodtx", 6) in verifier.calls
    assert ("BTC", "badtx", 6) in verifier.calls
