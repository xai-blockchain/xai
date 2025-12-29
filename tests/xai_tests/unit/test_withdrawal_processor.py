"""Tests for the withdrawal processing pipeline."""

import time
from pathlib import Path

import pytest

from xai.core.wallets.exchange_wallet import ExchangeWalletManager
from xai.core.wallets.withdrawal_processor import WithdrawalProcessor


@pytest.fixture()
def wallet_manager(tmp_path: Path) -> ExchangeWalletManager:
    manager = ExchangeWalletManager(data_dir=str(tmp_path / "wallets"))
    return manager


def _fund_wallet(manager: ExchangeWalletManager, user: str, amount: float) -> None:
    assert manager.deposit(user, "XAI", amount)["success"]


def test_withdrawal_completes_after_processing(wallet_manager: ExchangeWalletManager, tmp_path: Path) -> None:
    """Processor should finalize pending withdrawals and emit settlement IDs."""
    _fund_wallet(wallet_manager, "user-complete", 50_000)
    result = wallet_manager.withdraw("user-complete", "XAI", 1_000, "custodial:treasury")
    assert result["success"]

    processor = WithdrawalProcessor(
        wallet_manager,
        data_dir=str(tmp_path / "processor"),
        lock_amount_threshold=5_000,
        lock_duration_seconds=0,
    )
    stats = processor.process_queue(current_timestamp=time.time() + 5)
    assert stats["completed"] == 1

    history = wallet_manager.get_transaction_history("user-complete", limit=1)
    assert history[0]["status"] == "completed"
    assert "settlement_txid" in history[0]


def test_timelock_defers_large_withdrawal(wallet_manager: ExchangeWalletManager, tmp_path: Path) -> None:
    """Large withdrawals must respect lock duration before settlement."""
    _fund_wallet(wallet_manager, "user-lock", 80_000)
    result = wallet_manager.withdraw("user-lock", "XAI", 20_000, "custodial:cold")
    assert result["success"]
    created_at = result["transaction"]["timestamp"]

    processor = WithdrawalProcessor(
        wallet_manager,
        data_dir=str(tmp_path / "processor-lock"),
        lock_amount_threshold=5_000,
        lock_duration_seconds=3_600,
    )
    early_stats = processor.process_queue(current_timestamp=created_at + 60)
    assert early_stats["deferred"] == 1
    pending = wallet_manager.get_pending_withdrawal(result["transaction"]["id"])
    assert pending is not None

    # Advance time beyond the computed release timestamp (~4 * 3600 seconds)
    later_stats = processor.process_queue(current_timestamp=created_at + (4 * 3_600) + 120)
    assert later_stats["completed"] == 1
    assert wallet_manager.get_pending_withdrawal(result["transaction"]["id"]) is None


def test_blocked_destination_is_failed_and_refunded(wallet_manager: ExchangeWalletManager, tmp_path: Path) -> None:
    """Blocked destinations are rejected and funds are returned."""
    _fund_wallet(wallet_manager, "user-blocked", 10_000)
    result = wallet_manager.withdraw("user-blocked", "XAI", 1_500, "scam-domain")
    assert result["success"]

    processor = WithdrawalProcessor(
        wallet_manager,
        data_dir=str(tmp_path / "processor-blocked"),
        blocked_destinations={"scam-domain"},
    )
    stats = processor.process_queue(current_timestamp=time.time() + 5)
    assert stats["failed"] == 1

    history = wallet_manager.get_transaction_history("user-blocked", limit=1)[0]
    assert history["status"] == "failed"
    balances = wallet_manager.get_balance("user-blocked", "XAI")
    assert balances["available"] == pytest.approx(10_000)


def test_timelock_boundary_cannot_be_bypassed(wallet_manager: ExchangeWalletManager, tmp_path: Path) -> None:
    """Amounts just below the threshold clear immediately; at the threshold they are deferred."""
    _fund_wallet(wallet_manager, "user-boundary", 30_000)
    threshold = 5_000
    processor = WithdrawalProcessor(
        wallet_manager,
        data_dir=str(tmp_path / "processor-boundary"),
        lock_amount_threshold=threshold,
        lock_duration_seconds=600,
    )

    # Slightly under the threshold should execute immediately.
    under = wallet_manager.withdraw("user-boundary", "XAI", threshold - 0.01, "custodial:ops")
    now = under["transaction"]["timestamp"] + 5
    stats_under = processor.process_queue(current_timestamp=now)
    assert stats_under["completed"] == 1

    # Exactly at the threshold must respect the timelock.
    exact = wallet_manager.withdraw("user-boundary", "XAI", threshold, "custodial:cold")
    stats_exact = processor.process_queue(current_timestamp=exact["transaction"]["timestamp"] + 30)
    assert stats_exact["deferred"] == 1
    pending = wallet_manager.get_pending_withdrawal(exact["transaction"]["id"])
    assert pending is not None
    assert pending.get("release_timestamp") is not None
    assert pending["release_timestamp"] >= exact["transaction"]["timestamp"] + processor.lock_duration_seconds


def test_timelock_duration_caps_multiplier(wallet_manager: ExchangeWalletManager, tmp_path: Path) -> None:
    """Huge withdrawals cannot shrink the enforced release window below the 4x cap."""
    _fund_wallet(wallet_manager, "user-cap", 200_000)
    threshold = 10_000
    lock_seconds = 900
    processor = WithdrawalProcessor(
        wallet_manager,
        data_dir=str(tmp_path / "processor-cap"),
        lock_amount_threshold=threshold,
        lock_duration_seconds=lock_seconds,
    )

    result = wallet_manager.withdraw("user-cap", "XAI", threshold * 10, "custodial:vault")
    created_at = result["transaction"]["timestamp"]
    stats = processor.process_queue(current_timestamp=created_at + 60)
    assert stats["deferred"] == 1

    pending = wallet_manager.get_pending_withdrawal(result["transaction"]["id"])
    assert pending is not None
    expected_release = created_at + (lock_seconds * 4)
    assert pending["release_timestamp"] == pytest.approx(expected_release, rel=0, abs=1e-6)

    # Processing before release keeps it deferred.
    stats_again = processor.process_queue(current_timestamp=expected_release - 1)
    assert stats_again["deferred"] == 1

    # After the capped window expires the withdrawal is processed.
    stats_final = processor.process_queue(current_timestamp=expected_release + 1)
    assert stats_final["completed"] == 1


def test_exchange_wallet_status_helpers(wallet_manager: ExchangeWalletManager) -> None:
    """Helper APIs expose queue depth and status-filtered snapshots."""
    _fund_wallet(wallet_manager, "status-user", 5_000)
    result = wallet_manager.withdraw("status-user", "XAI", 500, "custodial:ops")
    tx_id = result["transaction"]["id"]
    counts = wallet_manager.get_withdrawal_counts()
    assert counts["pending"] == 1
    assert wallet_manager.get_pending_count() == 1
    pending = wallet_manager.get_withdrawals_by_status("pending")
    assert pending and pending[0]["id"] == tx_id

    wallet_manager.update_withdrawal_status(tx_id, "failed", reason="test")
    counts = wallet_manager.get_withdrawal_counts()
    assert counts["pending"] == 0
    assert counts["failed"] == 1
    with pytest.raises(ValueError):
        wallet_manager.get_withdrawals_by_status("unknown")
