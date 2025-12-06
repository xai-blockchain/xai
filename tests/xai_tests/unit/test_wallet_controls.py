import json
from datetime import datetime, timezone

import pytest

from xai.core.monitoring import MetricsCollector
from xai.wallet.daily_withdrawal_limits import DailyWithdrawalLimitManager
from xai.wallet.time_locked_withdrawals import TimeLockedWithdrawalManager


def ts(year, month, day, hour=0, minute=0, second=0):
    return int(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp())


@pytest.fixture
def metrics_collector(tmp_path):
    collector = MetricsCollector.instance()
    log_path = tmp_path / "withdrawals_events.jsonl"
    collector.withdrawal_event_log_path = str(log_path)
    reset_targets = {
        "xai_withdrawals_daily_total",
        "xai_withdrawals_time_locked_total",
        "xai_withdrawal_processor_completed_total",
        "xai_withdrawal_processor_flagged_total",
        "xai_withdrawal_processor_failed_total",
    }
    gauge_targets = {
        "xai_withdrawals_rate_per_minute",
        "xai_withdrawals_time_locked_backlog",
        "xai_withdrawal_pending_queue",
    }
    for metric_name in reset_targets:
        metric = collector.get_metric(metric_name)
        if metric:
            metric.reset()
    for metric_name in gauge_targets:
        metric = collector.get_metric(metric_name)
        if metric:
            metric.set(0)
    collector.withdrawal_events.clear()
    collector.recent_withdrawal_events.clear()
    if log_path.exists():
        log_path.unlink()
    return collector


def test_daily_withdrawal_limits_enforce_and_reset(metrics_collector):
    manager = DailyWithdrawalLimitManager(daily_limit=100.0)
    base = int(datetime.now(timezone.utc).timestamp())

    assert manager.check_and_record_withdrawal("userA", 60, current_timestamp=base)
    assert not manager.check_and_record_withdrawal("userA", 50, current_timestamp=base)

    next_day = base + 86400 + 1
    assert manager.check_and_record_withdrawal("userA", 90, current_timestamp=next_day)


def test_time_locked_withdrawal_persistence(metrics_collector, tmp_path):
    storage = tmp_path / "locks.json"
    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=100,
        time_lock_seconds=10,
        storage_path=str(storage),
    )

    start = ts(2025, 1, 1, 12)
    withdrawal = manager.request_withdrawal("userA", 150, current_timestamp=start)
    assert withdrawal.status == "pending"
    assert storage.exists()
    with storage.open() as handle:
        contents = json.load(handle)
        assert contents[0]["withdrawal_id"] == withdrawal.withdrawal_id

    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=100,
        time_lock_seconds=10,
        storage_path=str(storage),
    )
    assert len(manager.pending_withdrawals) == 1
    released = manager.process_releasable_withdrawals(start + 11)
    assert released == 1
    assert len(manager.pending_withdrawals) == 0
    with storage.open() as handle:
        assert json.load(handle) == []


def test_daily_withdrawal_metrics_update(metrics_collector):
    manager = DailyWithdrawalLimitManager(daily_limit=200.0, metrics_collector=metrics_collector)
    base = ts(2025, 2, 1, 9)

    assert manager.check_and_record_withdrawal("user-metrics", 120, current_timestamp=base)

    total_counter = metrics_collector.get_metric("xai_withdrawals_daily_total")
    rate_gauge = metrics_collector.get_metric("xai_withdrawals_rate_per_minute")
    assert total_counter.value == 1
    assert rate_gauge.value == 1
    recent = metrics_collector.get_recent_withdrawals()
    assert recent and recent[0]["user"] == "user-metrics"


def test_time_locked_backlog_metrics(metrics_collector, tmp_path):
    storage = tmp_path / "locks.json"
    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=100,
        time_lock_seconds=10,
        storage_path=str(storage),
    )

    pending = manager.request_withdrawal(
        "user-metrics", 500, current_timestamp=ts(2025, 3, 1, 10)
    )
    assert pending.status == "pending"
    locked_total = metrics_collector.get_metric("xai_withdrawals_time_locked_total")
    backlog = metrics_collector.get_metric("xai_withdrawals_time_locked_backlog")
    assert locked_total.value == 1
    assert backlog.value == 1

    assert manager.cancel_withdrawal(pending.withdrawal_id, "user-metrics")
    assert backlog.value == 0


def test_time_locked_withdrawal_cancel(metrics_collector, tmp_path):
    storage = tmp_path / "locks.json"
    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=100,
        time_lock_seconds=10,
        storage_path=str(storage),
    )
    start = ts(2025, 1, 1, 12)
    withdrawal = manager.request_withdrawal("userB", 500, current_timestamp=start)
    assert manager.cancel_withdrawal(withdrawal.withdrawal_id, "userB")
    assert withdrawal.withdrawal_id not in manager.pending_withdrawals
    with storage.open() as handle:
        assert json.load(handle) == []


def test_withdrawal_processor_metrics_recording(metrics_collector):
    stats = {"completed": 2, "flagged": 1, "failed": 1}
    metrics_collector.record_withdrawal_processor_stats(stats, queue_depth=3)
    completed = metrics_collector.get_metric("xai_withdrawal_processor_completed_total")
    flagged = metrics_collector.get_metric("xai_withdrawal_processor_flagged_total")
    failed = metrics_collector.get_metric("xai_withdrawal_processor_failed_total")
    queue = metrics_collector.get_metric("xai_withdrawal_pending_queue")
    assert completed.value == 2
    assert flagged.value == 1
    assert failed.value == 1
    assert queue.value == 3
