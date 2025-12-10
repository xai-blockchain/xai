import time

from xai.core.aixn_blockchain.atomic_swap_11_coins import (
    AtomicSwapHTLC,
    CoinType,
    SwapStateMachine,
    SwapState,
    SwapEvent,
    SwapRefundPlanner,
    SwapRecoveryService,
    SwapClaimRecoveryService,
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


def test_claim_recovery_transitions_failed_swap(tmp_path):
    sm = SwapStateMachine(storage_dir=tmp_path / "claim_swaps")
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(
        axn_amount=5,
        other_coin_amount=0.1,
        counterparty_address="recipient-pubkey",
        timelock_hours=2,
    )
    contract.update(
        {
            "coin": "BTC",
            "funding_txid": "tx123",
            "failure_reason": "claim_failed",
        }
    )
    swap_id = "swap-claim"
    sm.create_swap(swap_id, contract)
    sm.transition(swap_id, SwapState.FAILED, SwapEvent.FAIL, data={"failure_reason": "claim_failed"})

    claim_recovery = SwapClaimRecoveryService(sm, max_attempts=1, now_fn=lambda: time.time())
    recovered = claim_recovery.recover_failed_claims()

    assert recovered == [swap_id]
    assert sm.get_swap_state(swap_id) == SwapState.CLAIMED
    swap_record = sm.get_swap(swap_id)
    assert swap_record["data"].get("auto_recovered") is True
    assert swap_record["data"].get("recovery_claim") is not None


def test_claim_recovery_refunds_when_timelock_expired(tmp_path):
    sm = SwapStateMachine(storage_dir=tmp_path / "claim_swaps_refund")
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(
        axn_amount=10,
        other_coin_amount=0.2,
        counterparty_address="recipient",
        timelock_hours=0,
    )
    contract.update(
        {
            "coin": "BTC",
            "funding_txid": "tx456",
            "failure_reason": "claim_failed",
            "timelock": time.time() - 60,
        }
    )
    swap_id = "swap-refund"
    sm.create_swap(swap_id, contract)
    sm.transition(swap_id, SwapState.FAILED, SwapEvent.FAIL, data={"failure_reason": "claim_failed"})

    claim_recovery = SwapClaimRecoveryService(sm, max_attempts=1, now_fn=lambda: time.time())
    recovered = claim_recovery.recover_failed_claims()

    assert recovered == [swap_id]
    assert sm.get_swap_state(swap_id) == SwapState.REFUNDED
