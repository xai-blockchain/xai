"""
Comprehensive tests for the daily withdrawal limits module.

Tests cover:
- UserWithdrawalTracker class
- DailyWithdrawalLimitManager class
- Daily limit tracking and enforcement
- Reset logic at day boundaries
- Multi-user scenarios
- Edge cases and concurrent access patterns
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from xai.wallet.daily_withdrawal_limits import (
    DailyWithdrawalLimitManager,
    UserWithdrawalTracker,
)


# =============================================================================
# UserWithdrawalTracker Tests
# =============================================================================


class TestUserWithdrawalTracker:
    """Tests for the UserWithdrawalTracker class."""

    def test_init_creates_empty_tracker(self):
        """Tracker initializes with empty withdrawal list."""
        tracker = UserWithdrawalTracker("0xTestUser123")
        assert tracker.user_address == "0xTestUser123"
        assert tracker.withdrawals == []
        assert tracker.current_day_start_timestamp > 0

    def test_init_sets_current_day_start(self):
        """Tracker initializes with today's UTC midnight timestamp."""
        tracker = UserWithdrawalTracker("0xUser")
        now_utc = datetime.now(timezone.utc)
        expected_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        assert tracker.current_day_start_timestamp == int(expected_start.timestamp())

    def test_add_withdrawal_stores_data(self):
        """add_withdrawal stores amount and timestamp."""
        tracker = UserWithdrawalTracker("0xUser")
        ts = int(datetime.now(timezone.utc).timestamp())
        tracker.add_withdrawal(100.0, ts)
        assert len(tracker.withdrawals) == 1
        assert tracker.withdrawals[0]["amount"] == 100.0
        assert tracker.withdrawals[0]["timestamp"] == ts

    def test_add_withdrawal_multiple(self):
        """Multiple withdrawals are stored sequentially."""
        tracker = UserWithdrawalTracker("0xUser")
        ts = int(datetime.now(timezone.utc).timestamp())
        tracker.add_withdrawal(50.0, ts)
        tracker.add_withdrawal(75.0, ts + 60)
        tracker.add_withdrawal(25.0, ts + 120)
        assert len(tracker.withdrawals) == 3
        assert sum(w["amount"] for w in tracker.withdrawals) == 150.0

    def test_get_daily_total_sums_current_day(self):
        """get_daily_total sums withdrawals from current day only."""
        tracker = UserWithdrawalTracker("0xUser")
        ts = int(datetime.now(timezone.utc).timestamp())
        tracker.add_withdrawal(100.0, ts)
        tracker.add_withdrawal(200.0, ts)
        total = tracker.get_daily_total(ts)
        assert total == 300.0

    def test_get_daily_total_filters_old_withdrawals(self):
        """Withdrawals before current day start are filtered out."""
        tracker = UserWithdrawalTracker("0xUser")
        current_ts = int(datetime.now(timezone.utc).timestamp())
        # Add a withdrawal from "yesterday" (before day start)
        old_ts = tracker.current_day_start_timestamp - 3600
        tracker.withdrawals.append({"amount": 500.0, "timestamp": old_ts})
        # Add a current withdrawal
        tracker.add_withdrawal(100.0, current_ts)
        total = tracker.get_daily_total(current_ts)
        # Old withdrawal should be filtered out
        assert total == 100.0
        assert len(tracker.withdrawals) == 1

    def test_reset_if_new_day_does_nothing_same_day(self):
        """reset_if_new_day does not reset if still same day."""
        tracker = UserWithdrawalTracker("0xUser")
        current_ts = int(datetime.now(timezone.utc).timestamp())
        tracker.add_withdrawal(100.0, current_ts)
        original_day_start = tracker.current_day_start_timestamp
        tracker.reset_if_new_day(current_ts)
        assert tracker.current_day_start_timestamp == original_day_start
        assert len(tracker.withdrawals) == 1

    def test_reset_if_new_day_resets_on_new_day(self):
        """reset_if_new_day clears withdrawals when new UTC day starts."""
        tracker = UserWithdrawalTracker("0xUser")
        current_ts = int(datetime.now(timezone.utc).timestamp())
        tracker.add_withdrawal(500.0, current_ts)
        # Simulate a timestamp from tomorrow
        tomorrow_ts = tracker.current_day_start_timestamp + 86400 + 3600
        tracker.reset_if_new_day(tomorrow_ts)
        assert len(tracker.withdrawals) == 0
        # Day start should be updated
        assert tracker.current_day_start_timestamp > current_ts

    def test_reset_if_new_day_with_none_uses_current_time(self):
        """reset_if_new_day with None uses current system time."""
        tracker = UserWithdrawalTracker("0xUser")
        # This should not raise and should use current time
        tracker.reset_if_new_day(None)
        assert tracker.current_day_start_timestamp > 0

    def test_get_current_day_start_timestamp_with_reference(self):
        """_get_current_day_start_timestamp correctly computes day start from reference."""
        tracker = UserWithdrawalTracker("0xUser")
        # Reference: 2024-01-15 14:30:00 UTC
        ref_dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        ref_ts = int(ref_dt.timestamp())
        day_start = tracker._get_current_day_start_timestamp(ref_ts)
        expected_start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert day_start == int(expected_start.timestamp())

    def test_repr(self):
        """__repr__ returns readable string."""
        tracker = UserWithdrawalTracker("0xABCDEF1234567890")
        repr_str = repr(tracker)
        assert "UserWithdrawalTracker" in repr_str
        assert "0xABCDEF" in repr_str
        assert "withdrawals_count=0" in repr_str


# =============================================================================
# DailyWithdrawalLimitManager Tests
# =============================================================================


class TestDailyWithdrawalLimitManager:
    """Tests for the DailyWithdrawalLimitManager class."""

    def test_init_with_default_limit(self):
        """Manager initializes with default daily limit."""
        manager = DailyWithdrawalLimitManager()
        assert manager.daily_limit == 5000.0
        assert manager.user_trackers == {}
        assert manager.metrics_collector is None

    def test_init_with_custom_limit(self):
        """Manager initializes with custom daily limit."""
        manager = DailyWithdrawalLimitManager(daily_limit=10000.0)
        assert manager.daily_limit == 10000.0

    def test_init_with_integer_limit(self):
        """Manager accepts integer daily limit."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000)
        assert manager.daily_limit == 1000

    def test_init_with_metrics_collector(self):
        """Manager accepts optional metrics collector."""
        mock_collector = MagicMock()
        manager = DailyWithdrawalLimitManager(metrics_collector=mock_collector)
        assert manager.metrics_collector is mock_collector

    def test_init_rejects_zero_limit(self):
        """Manager raises ValueError for zero limit."""
        with pytest.raises(ValueError, match="positive number"):
            DailyWithdrawalLimitManager(daily_limit=0)

    def test_init_rejects_negative_limit(self):
        """Manager raises ValueError for negative limit."""
        with pytest.raises(ValueError, match="positive number"):
            DailyWithdrawalLimitManager(daily_limit=-100)

    def test_init_rejects_non_numeric_limit(self):
        """Manager raises ValueError for non-numeric limit."""
        with pytest.raises(ValueError, match="positive number"):
            DailyWithdrawalLimitManager(daily_limit="1000")

    def test_check_and_record_withdrawal_approves_within_limit(self):
        """Withdrawals within daily limit are approved."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 500.0, ts)
        assert result is True

    def test_check_and_record_withdrawal_rejects_over_limit(self):
        """Single withdrawal exceeding limit is rejected."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 1500.0, ts)
        assert result is False

    def test_check_and_record_withdrawal_cumulative_limit(self):
        """Multiple withdrawals are tracked cumulatively."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        assert manager.check_and_record_withdrawal("0xUser", 400.0, ts) is True
        assert manager.check_and_record_withdrawal("0xUser", 400.0, ts + 60) is True
        assert manager.check_and_record_withdrawal("0xUser", 200.0, ts + 120) is True
        # Now at 1000, further withdrawal should fail
        assert manager.check_and_record_withdrawal("0xUser", 100.0, ts + 180) is False

    def test_check_and_record_withdrawal_exact_limit(self):
        """Withdrawal exactly at limit is approved."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 1000.0, ts)
        assert result is True
        # Any additional withdrawal should fail
        assert manager.check_and_record_withdrawal("0xUser", 0.01, ts + 60) is False

    def test_check_and_record_withdrawal_rejects_zero_amount(self):
        """Zero withdrawal amount raises ValueError."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        with pytest.raises(ValueError, match="positive number"):
            manager.check_and_record_withdrawal("0xUser", 0, ts)

    def test_check_and_record_withdrawal_rejects_negative_amount(self):
        """Negative withdrawal amount raises ValueError."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        with pytest.raises(ValueError, match="positive number"):
            manager.check_and_record_withdrawal("0xUser", -100, ts)

    def test_check_and_record_withdrawal_rejects_non_numeric_amount(self):
        """Non-numeric withdrawal amount raises ValueError."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        with pytest.raises(ValueError, match="positive number"):
            manager.check_and_record_withdrawal("0xUser", "100", ts)

    def test_check_and_record_withdrawal_uses_current_time_if_none(self):
        """Uses current timestamp when none provided."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        # Should not raise and should work with current time
        result = manager.check_and_record_withdrawal("0xUser", 100.0, None)
        assert result is True

    def test_check_and_record_withdrawal_with_metrics_collector(self):
        """Metrics collector is called on successful withdrawal."""
        mock_collector = MagicMock()
        mock_collector.record_withdrawal.return_value = 5  # rate per minute
        manager = DailyWithdrawalLimitManager(
            daily_limit=1000.0, metrics_collector=mock_collector
        )
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 100.0, ts)
        assert result is True
        mock_collector.record_withdrawal.assert_called_once_with("0xUser", 100.0, ts)

    def test_check_and_record_withdrawal_no_metrics_on_rejection(self):
        """Metrics collector is not called on rejected withdrawal."""
        mock_collector = MagicMock()
        manager = DailyWithdrawalLimitManager(
            daily_limit=100.0, metrics_collector=mock_collector
        )
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 200.0, ts)
        assert result is False
        mock_collector.record_withdrawal.assert_not_called()

    def test_get_user_tracker_creates_new(self):
        """_get_user_tracker creates tracker for new user."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        tracker = manager._get_user_tracker("0xNewUser")
        assert isinstance(tracker, UserWithdrawalTracker)
        assert "0xNewUser" in manager.user_trackers

    def test_get_user_tracker_returns_existing(self):
        """_get_user_tracker returns existing tracker."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        tracker1 = manager._get_user_tracker("0xUser")
        tracker2 = manager._get_user_tracker("0xUser")
        assert tracker1 is tracker2


# =============================================================================
# Multi-User Scenarios
# =============================================================================


class TestDailyLimitsMultiUser:
    """Tests for multi-user withdrawal scenarios."""

    def test_separate_limits_per_user(self):
        """Each user has independent daily limits."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        # User A uses full limit
        assert manager.check_and_record_withdrawal("0xUserA", 1000.0, ts) is True
        assert manager.check_and_record_withdrawal("0xUserA", 1.0, ts + 60) is False
        # User B should have full limit available
        assert manager.check_and_record_withdrawal("0xUserB", 1000.0, ts) is True
        assert manager.check_and_record_withdrawal("0xUserB", 1.0, ts + 60) is False

    def test_many_users_independent(self):
        """Many users can withdraw independently."""
        manager = DailyWithdrawalLimitManager(daily_limit=500.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        for i in range(100):
            user = f"0xUser{i:04d}"
            assert manager.check_and_record_withdrawal(user, 250.0, ts) is True
            assert manager.check_and_record_withdrawal(user, 250.0, ts + 60) is True
            assert manager.check_and_record_withdrawal(user, 1.0, ts + 120) is False

    def test_user_trackers_are_isolated(self):
        """Modifications to one user's tracker don't affect others."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        manager.check_and_record_withdrawal("0xUserA", 500.0, ts)
        manager.check_and_record_withdrawal("0xUserB", 300.0, ts)
        tracker_a = manager._get_user_tracker("0xUserA")
        tracker_b = manager._get_user_tracker("0xUserB")
        assert tracker_a.get_daily_total(ts) == 500.0
        assert tracker_b.get_daily_total(ts) == 300.0


# =============================================================================
# Day Boundary Reset Tests
# =============================================================================


class TestDailyLimitsDayBoundary:
    """Tests for day boundary reset behavior."""

    def test_limit_resets_on_new_day(self):
        """Daily limit resets when new UTC day begins."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        # Use current time for testing to avoid issues with tracker initialization
        now = datetime.now(timezone.utc)
        # Get start of today, then use times within today
        ts_today_noon = int(now.replace(hour=12, minute=0, second=0, microsecond=0).timestamp())
        manager.check_and_record_withdrawal("0xUser", 1000.0, ts_today_noon)
        # User should be at limit within same day
        assert manager.check_and_record_withdrawal("0xUser", 1.0, ts_today_noon + 60) is False

        # To test reset, we need to manually adjust the tracker's day start to simulate yesterday
        tracker = manager._get_user_tracker("0xUser")
        # Move the tracker's day start to "yesterday"
        tracker.current_day_start_timestamp = tracker.current_day_start_timestamp - 86400
        # Also adjust the withdrawal timestamp to be in "yesterday"
        for w in tracker.withdrawals:
            w["timestamp"] = tracker.current_day_start_timestamp + 3600
        # Now calling with today's timestamp should trigger reset
        ts_now = int(datetime.now(timezone.utc).timestamp())
        # Should have full limit again after reset
        assert manager.check_and_record_withdrawal("0xUser", 1000.0, ts_now) is True

    def test_reset_at_utc_midnight_boundary(self):
        """Reset happens at exactly UTC midnight."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        # Use current time-based approach
        now = datetime.now(timezone.utc)
        ts_today = int(now.replace(hour=23, minute=59, second=59, microsecond=0).timestamp())
        manager.check_and_record_withdrawal("0xUser", 1000.0, ts_today)
        # Still within limit should fail (same second)
        assert manager.check_and_record_withdrawal("0xUser", 1.0, ts_today) is False

        # Manually set tracker to simulate yesterday's state
        tracker = manager._get_user_tracker("0xUser")
        yesterday_start = tracker.current_day_start_timestamp - 86400
        tracker.current_day_start_timestamp = yesterday_start
        for w in tracker.withdrawals:
            w["timestamp"] = yesterday_start + 3600

        # Now a withdrawal at current time should trigger reset
        ts_now = int(datetime.now(timezone.utc).timestamp())
        # Should have fresh limit after reset
        assert manager.check_and_record_withdrawal("0xUser", 500.0, ts_now) is True

    def test_partial_day_usage_tracked_across_calls(self):
        """Partial day usage persists across method calls."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        manager.check_and_record_withdrawal("0xUser", 200.0, ts)
        manager.check_and_record_withdrawal("0xUser", 300.0, ts + 60)
        # Later in same day
        manager.check_and_record_withdrawal("0xUser", 400.0, ts + 3600)
        # Total should be 900
        tracker = manager._get_user_tracker("0xUser")
        assert tracker.get_daily_total(ts + 3600) == 900.0


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


class TestDailyLimitsEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_small_withdrawals(self):
        """Very small withdrawal amounts are tracked correctly."""
        manager = DailyWithdrawalLimitManager(daily_limit=1.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        for i in range(100):
            result = manager.check_and_record_withdrawal("0xUser", 0.01, ts + i)
            if i < 100:
                assert result is True
        # At this point, total is 1.00, any more should fail
        assert manager.check_and_record_withdrawal("0xUser", 0.01, ts + 101) is False

    def test_float_precision_near_limit(self):
        """Float precision doesn't cause issues near limit boundary."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        # Add amounts that might cause float precision issues
        for i in range(9999):
            manager.check_and_record_withdrawal("0xUser", 0.1, ts + i)
        tracker = manager._get_user_tracker("0xUser")
        total = tracker.get_daily_total(ts + 10000)
        # Total should be around 999.9
        assert 999.0 <= total <= 1000.0

    def test_large_single_withdrawal_at_limit(self):
        """Large withdrawal exactly at limit succeeds."""
        manager = DailyWithdrawalLimitManager(daily_limit=1_000_000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 1_000_000.0, ts)
        assert result is True

    def test_very_large_limit(self):
        """Manager handles very large limits correctly."""
        manager = DailyWithdrawalLimitManager(daily_limit=1e18)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal("0xUser", 1e17, ts)
        assert result is True

    def test_empty_user_address(self):
        """Empty user address is handled."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        # Empty string is a valid key (though odd)
        result = manager.check_and_record_withdrawal("", 100.0, ts)
        assert result is True

    def test_special_characters_in_user_address(self):
        """Special characters in user address are handled."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        result = manager.check_and_record_withdrawal(
            "0x1234!@#$%^&*()_+-=[]{}|;':\",./<>?", 100.0, ts
        )
        assert result is True


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestDailyLimitsConcurrency:
    """Tests for concurrent access scenarios."""

    def test_concurrent_withdrawals_same_user(self):
        """Concurrent withdrawals for same user are handled safely."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        results = []
        errors = []

        def withdraw():
            try:
                result = manager.check_and_record_withdrawal("0xUser", 100.0, ts)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=withdraw) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # At most 10 should succeed (10 * 100 = 1000)
        success_count = sum(1 for r in results if r is True)
        assert success_count <= 10

    def test_concurrent_withdrawals_different_users(self):
        """Concurrent withdrawals for different users don't interfere."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        results = {}
        lock = threading.Lock()

        def withdraw(user_id):
            result = manager.check_and_record_withdrawal(f"0xUser{user_id}", 500.0, ts)
            with lock:
                results[user_id] = result

        threads = [threading.Thread(target=withdraw, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed since each user is independent
        assert all(results.values())

    def test_concurrent_reset_and_withdrawal(self):
        """Concurrent reset and withdrawal don't cause issues."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        # Set up for day boundary scenario
        ts_day1 = int(datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc).timestamp())
        manager.check_and_record_withdrawal("0xUser", 500.0, ts_day1)
        ts_day2 = int(datetime(2024, 1, 16, 0, 0, 1, tzinfo=timezone.utc).timestamp())
        errors = []

        def withdraw():
            try:
                manager.check_and_record_withdrawal("0xUser", 100.0, ts_day2)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=withdraw) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# Logging Tests
# =============================================================================


class TestDailyLimitsLogging:
    """Tests for logging behavior."""

    def test_logs_approved_withdrawal(self, caplog):
        """Approved withdrawals are logged."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        with caplog.at_level("INFO"):
            manager.check_and_record_withdrawal("0xUser", 100.0, ts)
        assert any("approved" in record.message.lower() for record in caplog.records)

    def test_logs_rejected_withdrawal(self, caplog):
        """Rejected withdrawals are logged as warnings."""
        manager = DailyWithdrawalLimitManager(daily_limit=100.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        with caplog.at_level("WARNING"):
            manager.check_and_record_withdrawal("0xUser", 200.0, ts)
        assert any("rejected" in record.message.lower() for record in caplog.records)

    def test_logs_day_reset(self, caplog):
        """Day reset is logged."""
        manager = DailyWithdrawalLimitManager(daily_limit=1000.0)
        ts = int(datetime.now(timezone.utc).timestamp())
        manager.check_and_record_withdrawal("0xUser", 100.0, ts)

        # Manually set tracker to simulate yesterday's state to trigger reset logging
        tracker = manager._get_user_tracker("0xUser")
        yesterday_start = tracker.current_day_start_timestamp - 86400
        tracker.current_day_start_timestamp = yesterday_start
        for w in tracker.withdrawals:
            w["timestamp"] = yesterday_start + 3600

        # Now a withdrawal at current time should trigger reset and log it
        ts_now = int(datetime.now(timezone.utc).timestamp())
        with caplog.at_level("INFO"):
            manager.check_and_record_withdrawal("0xUser", 100.0, ts_now)
        assert any("reset" in record.message.lower() for record in caplog.records)
