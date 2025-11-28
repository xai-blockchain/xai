from datetime import datetime, timezone

import pytest

from xai.core.monitoring import MetricsCollector
from xai.wallet.daily_withdrawal_limits import DailyWithdrawalLimitManager
from xai.wallet.time_locked_withdrawals import TimeLockedWithdrawalManager


def ts(year, month, day, hour=0, minute=0, second=0):
    return int(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp())


@pytest.fixture
def reset_metrics(tmp_path):
    collector = MetricsCollector.instance()
    log_path = tmp_path / "withdrawals_events.jsonl"
    collector.withdrawal_event_log_path = str(log_path)
    for name in {
        "xai_withdrawals_daily_total",
        "xai_withdrawals_time_locked_total",
    }:
        metric = collector.get_metric(name)
        if metric:
            metric.reset()
    for name in {
        "xai_withdrawals_rate_per_minute",
        "xai_withdrawals_time_locked_backlog",
    }:
        metric = collector.get_metric(name)
        if metric:
            metric.set(0)
    collector.withdrawal_events.clear()
    collector.recent_withdrawal_events.clear()
    if log_path.exists():
        log_path.unlink()
    return collector


def test_withdrawal_rate_window_rollover(monkeypatch, reset_metrics):
    collector = reset_metrics
    manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
    current = 1_700_000_000.0

    def fake_time():
        return current

    monkeypatch.setattr("xai.core.monitoring.time.time", lambda: fake_time())

    assert manager.check_and_record_withdrawal("user-1", 200, current_timestamp=int(current))
    assert collector.get_metric("xai_withdrawals_daily_total").value == 1
    assert collector.get_metric("xai_withdrawals_rate_per_minute").value == 1

    current += 30
    assert manager.check_and_record_withdrawal("user-2", 150, current_timestamp=int(current))
    assert collector.get_metric("xai_withdrawals_rate_per_minute").value == 2

    current += 45
    assert manager.check_and_record_withdrawal("user-3", 150, current_timestamp=int(current))
    # First withdrawal is now older than 60 seconds and should roll out of the window
    assert collector.get_metric("xai_withdrawals_daily_total").value == 3
    assert collector.get_metric("xai_withdrawals_rate_per_minute").value == 2
    recent = collector.get_recent_withdrawals(3)
    assert len(recent) == 3


def test_time_locked_backlog_releases_update_metrics(reset_metrics, tmp_path):
    collector = reset_metrics
    storage = tmp_path / "locks.json"
    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=100,
        time_lock_seconds=30,
        storage_path=str(storage),
    )

    start = ts(2025, 4, 1, 12)
    w1 = manager.request_withdrawal("user-lock-1", 200, current_timestamp=start)
    w2 = manager.request_withdrawal("user-lock-2", 400, current_timestamp=start + 1)
    assert w1.status == "pending" and w2.status == "pending"

    backlog = collector.get_metric("xai_withdrawals_time_locked_backlog")
    assert backlog.value == 2

    # Processing before release time should keep backlog unchanged
    manager.process_releasable_withdrawals(start + 10)
    assert backlog.value == 2

    released = manager.process_releasable_withdrawals(start + 40)
    assert released == 2
    assert backlog.value == 0
