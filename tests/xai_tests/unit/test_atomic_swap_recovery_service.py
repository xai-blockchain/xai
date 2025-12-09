import time

from xai.core.aixn_blockchain.atomic_swap_11_coins import (
    SwapStateMachine,
    SwapState,
    SwapEvent,
    SwapRefundPlanner,
    SwapRecoveryService,
)


class StubVerifier:
    def __init__(self, good_tx="goodtx"):
        self.good_tx = good_tx
        self.calls = 0

    def verify_minimum_confirmations(self, coin_type, tx_hash, min_confirmations):
        self.calls += 1
        if tx_hash == self.good_tx:
            return True, 12
        return False, 0


def test_recovery_service_surfaces_refundable_swaps(tmp_path):
    sm = SwapStateMachine(storage_dir=tmp_path / "swaps")
    swap_id = "swap1"
    timelock = time.time() - 10
    sm.create_swap(
        swap_id,
        {
            "coin": "BTC",
            "funding_txid": "goodtx",
            "timelock": timelock,
            "min_confirmations": 6,
        },
    )
    sm.transition(swap_id, SwapState.FUNDED, SwapEvent.FUND)

    verifier = StubVerifier()
    planner = SwapRefundPlanner(verifier, now_fn=lambda: timelock + 100)
    recovery = SwapRecoveryService(sm, planner)

    refundable = recovery.find_refundable_swaps()
    assert [r["swap_id"] for r in refundable] == [swap_id]
    assert refundable[0]["confirmations"] == 12
    assert verifier.calls >= 1
