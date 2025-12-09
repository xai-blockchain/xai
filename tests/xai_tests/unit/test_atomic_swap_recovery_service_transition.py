import time

from xai.core.aixn_blockchain.atomic_swap_11_coins import (
    SwapStateMachine,
    SwapState,
    SwapEvent,
    SwapRefundPlanner,
    SwapRecoveryService,
)


class StubVerifier:
    def verify_minimum_confirmations(self, coin_type, tx_hash, min_confirmations):
        return True, 10


def test_recovery_service_transitions_refunds(tmp_path):
    sm = SwapStateMachine(storage_dir=tmp_path / "swaps2")
    swap_id = "swap2"
    timelock = time.time() - 5
    sm.create_swap(
        swap_id,
        {
            "coin": "BTC",
            "funding_txid": "tx",
            "timelock": timelock,
            "min_confirmations": 1,
        },
    )
    sm.transition(swap_id, SwapState.FUNDED, SwapEvent.FUND)

    planner = SwapRefundPlanner(StubVerifier(), now_fn=lambda: timelock + 100)
    recovery = SwapRecoveryService(sm, planner)
    transitioned = recovery.auto_transition_refunds()

    assert transitioned == [swap_id]
    assert sm.get_swap_state(swap_id) == SwapState.REFUNDED
