import pytest
import xai.blockchain.front_running_protection as fr_module

from pathlib import Path

from xai.blockchain.front_running_protection import FrontRunningProtectionManager
from xai.blockchain.mev_mitigation import MEVMitigationManager
from xai.core.consensus.advanced_consensus import TransactionOrdering
from xai.core.transaction import Transaction


RECIPIENT = "XAI00000000000000000000000000000000000000AA"
COINBASE_RECIPIENT = "XAI00000000000000000000000000000000000000BB"
SENDER_A = "XAI1111111111111111111111111111111111111111"
SENDER_B = "XAI2222222222222222222222222222222222222222"
SENDER_C = "XAI3333333333333333333333333333333333333333"


def _make_tx(sender: str, nonce: int, fee: float, timestamp: float, amount: float = 1.0) -> Transaction:
    tx = Transaction(
        sender=sender,
        recipient=RECIPIENT,
        amount=amount,
        fee=fee,
        nonce=nonce,
    )
    tx.timestamp = timestamp
    tx.txid = f"{sender[-4:]}_{nonce}_{int(fee * 1000)}"
    return tx


def _make_coinbase(timestamp: float) -> Transaction:
    coinbase = Transaction(
        sender="COINBASE",
        recipient=COINBASE_RECIPIENT,
        amount=50.0,
        fee=0.0,
        tx_type="coinbase",
    )
    coinbase.timestamp = timestamp
    coinbase.txid = f"coinbase_{int(timestamp)}"
    return coinbase


@pytest.fixture
def mev_managers(tmp_path: Path):
    fr_manager = FrontRunningProtectionManager()
    mev_manager = MEVMitigationManager(tmp_path / "mev_state.db", fr_manager)
    return fr_manager, mev_manager


def test_commit_reveal_and_slippage():
    manager = FrontRunningProtectionManager()
    tx = {"type": "swap", "amount": 10}
    salt = "salt"
    commit_hash = manager._hash_transaction_with_salt(tx, salt)

    manager.commit_transaction("0xUser", commit_hash)
    with pytest.raises(ValueError):
        manager.commit_transaction("0xUser", commit_hash)

    manager.reveal_transaction("0xUser", tx, salt)
    with pytest.raises(ValueError):
        manager.reveal_transaction("0xUser", tx, salt)

    manager.process_mempool_with_fair_ordering()
    assert manager.revealed_transactions == {}

    assert manager.check_slippage(100.0, 99.5, max_slippage_percent=1.0) is True
    assert manager.check_slippage(100.0, 95.0, max_slippage_percent=1.0) is False


def test_mev_private_and_bundle_processing(mev_managers):
    fr_manager, mev_manager = mev_managers

    mev_manager.submit_private_transaction({"type": "swap"}, "0xUser")
    assert len(mev_manager.private_transactions_queue) == 1
    mev_manager.process_private_transactions()
    assert len(mev_manager.private_transactions_queue) == 0

    mev_manager.submit_transaction_bundle([{"type": "approve"}, {"type": "swap"}], "0xUser")
    assert len(mev_manager.transaction_bundles) == 1
    mev_manager.process_transaction_bundles()
    assert len(mev_manager.transaction_bundles) == 0


def test_mev_sandwich_detection(mev_managers):
    fr_manager, mev_manager = mev_managers
    target_tx = {"type": "swap", "token": "ETH"}

    assert (
        mev_manager.detect_sandwich_attack(target_tx, pre_tx_price=100.0, post_tx_price=100.5, current_mempool_transactions=[])
        is False
    )

    mempool = [
        {"type": "buy", "token": "ETH"},
        target_tx,
        {"type": "sell", "token": "ETH"},
    ]
    assert (
        mev_manager.detect_sandwich_attack(target_tx, pre_tx_price=100.0, post_tx_price=102.0, current_mempool_transactions=mempool)
        is True
    )


def test_transaction_order_validation_rejects_nonce_gap():
    """Missing nonces indicate reordered execution and must be rejected."""
    coinbase = _make_coinbase(timestamp=5)
    attacker_first = _make_tx(SENDER_A, nonce=5, fee=4.0, timestamp=15)
    attacker_skip = _make_tx(SENDER_A, nonce=7, fee=6.0, timestamp=16)

    invalid_order = [coinbase, attacker_first, attacker_skip]
    assert TransactionOrdering.validate_transaction_order(invalid_order) is False


def test_transaction_order_validation_rejects_nonce_shuffle():
    """Nonce reordering in a block is rejected to stop MEV-driven reshuffles."""
    coinbase = _make_coinbase(timestamp=5)
    victim_first = _make_tx(SENDER_C, nonce=1, fee=2.0, timestamp=20)
    attacker_reordered = _make_tx(SENDER_C, nonce=0, fee=5.0, timestamp=19)

    invalid_order = [coinbase, victim_first, attacker_reordered]
    assert TransactionOrdering.validate_transaction_order(invalid_order) is False


def test_commit_reveal_uses_secure_shuffle(monkeypatch):
    """Fair ordering leverages secure randomness so attackers cannot predict placement."""
    manager = FrontRunningProtectionManager()
    salts = ["salt-a", "salt-b", "salt-c"]
    txs = [
        {"type": "swap", "amount": 25, "sender": "0xVictim"},
        {"type": "swap", "amount": 30, "sender": "0xAttackerFront"},
        {"type": "swap", "amount": 35, "sender": "0xAttackerBack"},
    ]

    for idx, tx in enumerate(txs):
        commit_hash = manager._hash_transaction_with_salt(tx, salts[idx])
        manager.commit_transaction(f"0xUser{idx}", commit_hash)
        manager.reveal_transaction(f"0xUser{idx}", tx, salts[idx])

    class DeterministicShuffle:
        def __init__(self):
            self.calls = 0
            self.last_order = None

        def shuffle(self, seq):
            self.calls += 1
            seq.sort(key=lambda h: h[::-1])
            self.last_order = tuple(seq)

    fake_random = DeterministicShuffle()
    monkeypatch.setattr(fr_module.secrets, "SystemRandom", lambda: fake_random)

    manager.process_mempool_with_fair_ordering()

    assert fake_random.calls == 1
    assert fake_random.last_order is not None
    assert manager.revealed_transactions == {}
    assert manager.committed_transactions == {}
