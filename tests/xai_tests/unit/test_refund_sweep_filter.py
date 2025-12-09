import time

from scripts.tools import refund_sweep_runner
from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


class StubVerifier(CrossChainVerifier):
    def __init__(self, ok_tx="ok"):
        super().__init__()
        self.ok_tx = ok_tx

    def verify_minimum_confirmations(self, coin_type: str, tx_hash: str, min_confirmations: int = 6):
        if tx_hash == self.ok_tx:
            return True, 5
        return False, 0


def test_filter_refundable_swaps_respects_timelock_and_conf():
    now = time.time()
    swaps = [
        {"funding_txid": "ok", "coin": "BTC", "timelock": now - 4000, "sender_address": "sender"},
        {"funding_txid": "lowconf", "coin": "BTC", "timelock": now - 4000},
        {"funding_txid": "ok", "coin": "BTC", "timelock": now + 10},  # not expired
    ]
    verifier = StubVerifier()
    filtered = refund_sweep_runner.filter_refundable_swaps(swaps, verifier, min_confirmations=3, safety_margin_seconds=0, now=now)
    assert len(filtered) == 1
    assert filtered[0]["funding_txid"] == "ok"
    assert filtered[0]["confirmations"] == 5
