"""
Comprehensive tests for the time-locked withdrawals module.

Tests cover:
- PendingWithdrawal class
- TimeLockedWithdrawalManager class
- Withdrawal scheduling and execution
- Cancellation logic
- Time-based unlock conditions
- Persistence and state management
- Edge cases and concurrent access patterns
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xai.wallet.time_locked_withdrawals import (
    PendingWithdrawal,
    TimeLockedWithdrawalManager,
)


# =============================================================================
# PendingWithdrawal Tests
# =============================================================================


class TestPendingWithdrawal:
    """Tests for the PendingWithdrawal class."""

    def test_init_creates_valid_withdrawal(self):
        """PendingWithdrawal initializes with valid parameters."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser123",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        assert withdrawal.withdrawal_id == "w-123"
        assert withdrawal.user_address == "0xUser123"
        assert withdrawal.amount == 1000.0
        assert withdrawal.initiation_timestamp == 1000
        assert withdrawal.release_timestamp == 2000
        assert withdrawal.status == "pending"

    def test_init_accepts_integer_amount(self):
        """PendingWithdrawal accepts integer amount."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        assert withdrawal.amount == 1000

    def test_init_rejects_empty_withdrawal_id(self):
        """Empty withdrawal ID raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PendingWithdrawal(
                withdrawal_id="",
                user_address="0xUser",
                amount=1000.0,
                initiation_timestamp=1000,
                release_timestamp=2000,
            )

    def test_init_rejects_empty_user_address(self):
        """Empty user address raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="",
                amount=1000.0,
                initiation_timestamp=1000,
                release_timestamp=2000,
            )

    def test_init_rejects_zero_amount(self):
        """Zero amount raises ValueError."""
        with pytest.raises(ValueError, match="positive number"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=0,
                initiation_timestamp=1000,
                release_timestamp=2000,
            )

    def test_init_rejects_negative_amount(self):
        """Negative amount raises ValueError."""
        with pytest.raises(ValueError, match="positive number"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=-100.0,
                initiation_timestamp=1000,
                release_timestamp=2000,
            )

    def test_init_rejects_non_numeric_amount(self):
        """Non-numeric amount raises ValueError."""
        with pytest.raises(ValueError, match="positive number"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount="1000",
                initiation_timestamp=1000,
                release_timestamp=2000,
            )

    def test_init_rejects_zero_initiation_timestamp(self):
        """Zero initiation timestamp raises ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=1000.0,
                initiation_timestamp=0,
                release_timestamp=2000,
            )

    def test_init_rejects_negative_initiation_timestamp(self):
        """Negative initiation timestamp raises ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=1000.0,
                initiation_timestamp=-100,
                release_timestamp=2000,
            )

    def test_init_rejects_release_before_initiation(self):
        """Release timestamp before initiation raises ValueError."""
        with pytest.raises(ValueError, match="after initiation"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=1000.0,
                initiation_timestamp=2000,
                release_timestamp=1000,
            )

    def test_init_rejects_release_equal_to_initiation(self):
        """Release timestamp equal to initiation raises ValueError."""
        with pytest.raises(ValueError, match="after initiation"):
            PendingWithdrawal(
                withdrawal_id="w-123",
                user_address="0xUser",
                amount=1000.0,
                initiation_timestamp=1000,
                release_timestamp=1000,
            )

    def test_is_releasable_before_time(self):
        """is_releasable returns False before release time."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        assert withdrawal.is_releasable(1500) is False

    def test_is_releasable_at_time(self):
        """is_releasable returns True at release time."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        assert withdrawal.is_releasable(2000) is True

    def test_is_releasable_after_time(self):
        """is_releasable returns True after release time."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        assert withdrawal.is_releasable(3000) is True

    def test_is_releasable_false_when_cancelled(self):
        """is_releasable returns False when cancelled."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.cancel()
        assert withdrawal.is_releasable(3000) is False

    def test_is_releasable_false_when_confirmed(self):
        """is_releasable returns False when already confirmed."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.confirm()
        assert withdrawal.is_releasable(3000) is False

    def test_cancel_sets_status(self):
        """cancel() sets status to cancelled."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.cancel()
        assert withdrawal.status == "cancelled"

    def test_cancel_only_works_when_pending(self):
        """cancel() only changes status from pending."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.confirm()
        withdrawal.cancel()  # Should not change from confirmed
        assert withdrawal.status == "confirmed"

    def test_confirm_sets_status(self):
        """confirm() sets status to confirmed."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.confirm()
        assert withdrawal.status == "confirmed"

    def test_confirm_only_works_when_pending(self):
        """confirm() only changes status from pending."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        withdrawal.cancel()
        withdrawal.confirm()  # Should not change from cancelled
        assert withdrawal.status == "cancelled"

    def test_to_dict_returns_all_fields(self):
        """to_dict returns all fields."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-123",
            user_address="0xUser",
            amount=1500.5,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        data = withdrawal.to_dict()
        assert data["withdrawal_id"] == "w-123"
        assert data["user_address"] == "0xUser"
        assert data["amount"] == 1500.5
        assert data["initiation_timestamp"] == 1000
        assert data["release_timestamp"] == 2000
        assert data["status"] == "pending"

    def test_repr(self):
        """__repr__ returns readable string."""
        withdrawal = PendingWithdrawal(
            withdrawal_id="w-12345678-abcd",
            user_address="0xABCDEF1234567890",
            amount=1000.0,
            initiation_timestamp=1000,
            release_timestamp=2000,
        )
        repr_str = repr(withdrawal)
        assert "PendingWithdrawal" in repr_str
        assert "w-123456" in repr_str
        assert "0xABCDEF" in repr_str
        assert "pending" in repr_str


# =============================================================================
# TimeLockedWithdrawalManager Tests
# =============================================================================


class TestTimeLockedWithdrawalManager:
    """Tests for the TimeLockedWithdrawalManager class."""

    @pytest.fixture
    def temp_storage_path(self, tmp_path):
        """Provide a temporary storage path."""
        return str(tmp_path / "withdrawals.json")

    def test_init_with_defaults(self):
        """Manager initializes with default values."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector"):
            manager = TimeLockedWithdrawalManager()
        assert manager.withdrawal_threshold == 1000.0
        assert manager.time_lock_seconds == 3600
        assert manager.pending_withdrawals == {}
        assert manager.storage_path is None

    def test_init_with_custom_values(self, temp_storage_path):
        """Manager initializes with custom values."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector"):
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=5000.0,
                time_lock_seconds=7200,
                storage_path=temp_storage_path,
            )
        assert manager.withdrawal_threshold == 5000.0
        assert manager.time_lock_seconds == 7200
        assert manager.storage_path == temp_storage_path

    def test_init_rejects_zero_threshold(self):
        """Zero threshold raises ValueError."""
        with pytest.raises(ValueError, match="positive number"):
            TimeLockedWithdrawalManager(withdrawal_threshold=0)

    def test_init_rejects_negative_threshold(self):
        """Negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="positive number"):
            TimeLockedWithdrawalManager(withdrawal_threshold=-100)

    def test_init_rejects_zero_time_lock(self):
        """Zero time lock raises ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            TimeLockedWithdrawalManager(time_lock_seconds=0)

    def test_init_rejects_negative_time_lock(self):
        """Negative time lock raises ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            TimeLockedWithdrawalManager(time_lock_seconds=-60)


class TestTimeLockedWithdrawalManagerRequests:
    """Tests for withdrawal request handling."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=3600
            )
            manager._metrics_mock = mock_instance
        return manager

    def test_request_below_threshold_immediate(self, manager):
        """Withdrawal below threshold is processed immediately."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            withdrawal = manager.request_withdrawal("0xUser", 500.0, ts)
        assert withdrawal.status == "confirmed"
        # Release timestamp is ts + 1 to satisfy PendingWithdrawal validation
        assert withdrawal.release_timestamp == ts + 1

    def test_request_at_threshold_time_locked(self, manager):
        """Withdrawal at threshold is time-locked."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            withdrawal = manager.request_withdrawal("0xUser", 1000.0, ts)
        assert withdrawal.status == "pending"
        assert withdrawal.release_timestamp == ts + 3600
        assert withdrawal.withdrawal_id in manager.pending_withdrawals

    def test_request_above_threshold_time_locked(self, manager):
        """Withdrawal above threshold is time-locked."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            withdrawal = manager.request_withdrawal("0xUser", 5000.0, ts)
        assert withdrawal.status == "pending"
        assert withdrawal.release_timestamp == ts + 3600

    def test_request_generates_unique_id(self, manager):
        """Each request generates a unique withdrawal ID."""
        ts = int(datetime.now(timezone.utc).timestamp())
        ids = set()
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            for i in range(100):
                withdrawal = manager.request_withdrawal("0xUser", 500.0, ts + i)
                ids.add(withdrawal.withdrawal_id)
        assert len(ids) == 100

    def test_request_uses_current_time_if_none(self, manager):
        """Uses current timestamp when none provided."""
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            withdrawal = manager.request_withdrawal("0xUser", 500.0, None)
        assert withdrawal.initiation_timestamp > 0


class TestTimeLockedWithdrawalManagerCancellation:
    """Tests for withdrawal cancellation."""

    @pytest.fixture
    def manager_with_pending(self):
        """Create manager with a pending withdrawal."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=3600
            )
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            withdrawal = manager.request_withdrawal("0xUser", 2000.0, ts)
        return manager, withdrawal

    def test_cancel_valid_withdrawal(self, manager_with_pending):
        """Valid withdrawal can be cancelled by owner."""
        manager, withdrawal = manager_with_pending
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            result = manager.cancel_withdrawal(withdrawal.withdrawal_id, "0xUser")
        assert result is True
        assert withdrawal.status == "cancelled"
        assert withdrawal.withdrawal_id not in manager.pending_withdrawals

    def test_cancel_nonexistent_withdrawal(self, manager_with_pending):
        """Cancelling nonexistent withdrawal returns False."""
        manager, _ = manager_with_pending
        result = manager.cancel_withdrawal("nonexistent-id", "0xUser")
        assert result is False

    def test_cancel_by_wrong_user(self, manager_with_pending):
        """Cannot cancel withdrawal belonging to another user."""
        manager, withdrawal = manager_with_pending
        result = manager.cancel_withdrawal(withdrawal.withdrawal_id, "0xOtherUser")
        assert result is False
        assert withdrawal.status == "pending"


class TestTimeLockedWithdrawalManagerProcessing:
    """Tests for processing releasable withdrawals."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
        return manager

    def test_process_releases_ready_withdrawals(self, manager):
        """Withdrawals past release time are confirmed."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w1 = manager.request_withdrawal("0xUser1", 2000.0, ts)
            w2 = manager.request_withdrawal("0xUser2", 3000.0, ts)
        # Process after time lock expires
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            count = manager.process_releasable_withdrawals(ts + 120)
        assert count == 2
        assert w1.status == "confirmed"
        assert w2.status == "confirmed"
        assert len(manager.pending_withdrawals) == 0

    def test_process_does_not_release_early(self, manager):
        """Withdrawals before release time are not confirmed."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
        # Process before time lock expires
        count = manager.process_releasable_withdrawals(ts + 30)
        assert count == 0
        assert w.status == "pending"
        assert w.withdrawal_id in manager.pending_withdrawals

    def test_process_partial_releases(self, manager):
        """Only ready withdrawals are released."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w1 = manager.request_withdrawal("0xUser1", 2000.0, ts)
            w2 = manager.request_withdrawal("0xUser2", 3000.0, ts + 90)  # Later initiation
        # Process after first lock expires but before second
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            count = manager.process_releasable_withdrawals(ts + 70)
        assert count == 1
        assert w1.status == "confirmed"
        assert w2.status == "pending"


class TestTimeLockedWithdrawalManagerPersistence:
    """Tests for state persistence."""

    @pytest.fixture
    def storage_path(self, tmp_path):
        """Provide a temporary storage path."""
        return str(tmp_path / "withdrawals.json")

    def test_persist_state_on_request(self, storage_path):
        """State is persisted on new request."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            manager.request_withdrawal("0xUser", 2000.0, ts)
        assert os.path.exists(storage_path)
        with open(storage_path, "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["user_address"] == "0xUser"

    def test_persist_state_on_cancel(self, storage_path):
        """State is persisted on cancellation."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
            manager.cancel_withdrawal(w.withdrawal_id, "0xUser")
        with open(storage_path, "r") as f:
            data = json.load(f)
        assert len(data) == 0

    def test_load_state_on_init(self, storage_path):
        """State is loaded on initialization."""
        # Create a state file
        initial_data = [
            {
                "withdrawal_id": "w-123",
                "user_address": "0xUser",
                "amount": 2000.0,
                "initiation_timestamp": 1000,
                "release_timestamp": 2000,
            }
        ]
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        with open(storage_path, "w") as f:
            json.dump(initial_data, f)
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector"):
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        assert "w-123" in manager.pending_withdrawals
        assert manager.pending_withdrawals["w-123"].amount == 2000.0

    def test_load_state_handles_missing_file(self, tmp_path):
        """Missing state file is handled gracefully."""
        storage_path = str(tmp_path / "nonexistent.json")
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector"):
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        assert len(manager.pending_withdrawals) == 0

    def test_load_state_handles_corrupt_file(self, storage_path):
        """Corrupt state file is handled gracefully."""
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        with open(storage_path, "w") as f:
            f.write("not valid json {{{")
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector"):
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        assert len(manager.pending_withdrawals) == 0

    def test_persist_creates_directory(self, tmp_path):
        """Persist creates parent directory if needed."""
        storage_path = str(tmp_path / "subdir" / "deep" / "withdrawals.json")
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0,
                time_lock_seconds=60,
                storage_path=storage_path,
            )
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            manager.request_withdrawal("0xUser", 2000.0, ts)
        assert os.path.exists(storage_path)


class TestTimeLockedWithdrawalManagerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=3600
            )
        return manager

    def test_withdrawal_just_below_threshold(self, manager):
        """Withdrawal just below threshold is immediate."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 999.99, ts)
        assert w.status == "confirmed"

    def test_withdrawal_just_at_threshold(self, manager):
        """Withdrawal exactly at threshold is time-locked."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 1000.0, ts)
        assert w.status == "pending"

    def test_very_large_withdrawal(self, manager):
        """Very large withdrawal is handled."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 1e18, ts)
        assert w.status == "pending"
        assert w.amount == 1e18

    def test_process_at_exact_release_time(self, manager):
        """Processing at exact release time releases withdrawal."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
            count = manager.process_releasable_withdrawals(ts + 3600)
        assert count == 1
        assert w.status == "confirmed"

    def test_process_one_second_before_release(self, manager):
        """Processing one second before release does not release."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
        count = manager.process_releasable_withdrawals(ts + 3599)
        assert count == 0
        assert w.status == "pending"


class TestTimeLockedWithdrawalManagerConcurrency:
    """Tests for concurrent access scenarios."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
        return manager

    def test_concurrent_requests(self, manager):
        """Concurrent withdrawal requests are handled safely."""
        ts = int(datetime.now(timezone.utc).timestamp())
        withdrawals = []
        errors = []

        def request():
            try:
                with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                    w = manager.request_withdrawal("0xUser", 2000.0, ts)
                    withdrawals.append(w)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=request) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(withdrawals) == 20
        # All should be in pending_withdrawals
        assert len(manager.pending_withdrawals) == 20

    def test_concurrent_cancel_and_process(self, manager):
        """Concurrent cancel and process don't cause issues."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
        errors = []

        def cancel():
            try:
                with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                    manager.cancel_withdrawal(w.withdrawal_id, "0xUser")
            except Exception as e:
                errors.append(e)

        def process():
            try:
                with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                    manager.process_releasable_withdrawals(ts + 120)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=cancel),
            threading.Thread(target=process),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Withdrawal should be either cancelled or confirmed
        assert w.status in ("cancelled", "confirmed")


class TestTimeLockedWithdrawalManagerLogging:
    """Tests for logging behavior."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
        return manager

    def test_logs_time_locked_request(self, manager, caplog):
        """Time-locked request is logged."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with caplog.at_level("INFO"):
            with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                manager.request_withdrawal("0xUser", 2000.0, ts)
        assert any("time-lock applied" in r.message.lower() for r in caplog.records)

    def test_logs_immediate_request(self, manager, caplog):
        """Immediate request is logged."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with caplog.at_level("INFO"):
            with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                manager.request_withdrawal("0xUser", 500.0, ts)
        assert any("immediate" in r.message.lower() for r in caplog.records)

    def test_logs_cancel_not_found(self, manager, caplog):
        """Cancel of nonexistent withdrawal is logged."""
        with caplog.at_level("ERROR"):
            manager.cancel_withdrawal("nonexistent-id", "0xUser")
        assert any("not found" in r.message.lower() for r in caplog.records)

    def test_logs_cancel_wrong_user(self, manager, caplog):
        """Cancel by wrong user is logged."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
        with caplog.at_level("ERROR"):
            manager.cancel_withdrawal(w.withdrawal_id, "0xOtherUser")
        assert any("not authorized" in r.message.lower() for r in caplog.records)


class TestTimeLockedWithdrawalManagerSecurityEvents:
    """Tests for security event logging."""

    @pytest.fixture
    def manager(self):
        """Create a manager with mocked metrics."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
        return manager

    def test_security_event_on_time_locked_request(self, manager):
        """Security event logged for time-locked request."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch(
            "xai.wallet.time_locked_withdrawals.log_security_event"
        ) as mock_log:
            manager.request_withdrawal("0xUser", 2000.0, ts)
        mock_log.assert_called()
        call_args = mock_log.call_args_list[0]
        assert "time_locked_withdrawal_requested" in call_args[0][0]

    def test_security_event_on_immediate_request(self, manager):
        """Security event logged for immediate request."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch(
            "xai.wallet.time_locked_withdrawals.log_security_event"
        ) as mock_log:
            manager.request_withdrawal("0xUser", 500.0, ts)
        mock_log.assert_called_once()
        call_args = mock_log.call_args_list[0]
        assert "withdrawal_processed_immediately" in call_args[0][0]

    def test_security_event_on_cancel(self, manager):
        """Security event logged on cancellation."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            w = manager.request_withdrawal("0xUser", 2000.0, ts)
        with patch(
            "xai.wallet.time_locked_withdrawals.log_security_event"
        ) as mock_log:
            manager.cancel_withdrawal(w.withdrawal_id, "0xUser")
        mock_log.assert_called_once()
        call_args = mock_log.call_args_list[0]
        assert "time_locked_withdrawal_cancelled" in call_args[0][0]

    def test_security_event_on_release(self, manager):
        """Security event logged on release."""
        ts = int(datetime.now(timezone.utc).timestamp())
        with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
            manager.request_withdrawal("0xUser", 2000.0, ts)
        with patch(
            "xai.wallet.time_locked_withdrawals.log_security_event"
        ) as mock_log:
            manager.process_releasable_withdrawals(ts + 120)
        mock_log.assert_called_once()
        call_args = mock_log.call_args_list[0]
        assert "time_locked_withdrawal_released" in call_args[0][0]


class TestTimeLockedWithdrawalManagerMetrics:
    """Tests for metrics recording."""

    def test_metrics_on_time_locked_request(self):
        """Metrics recorded on time-locked request."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
            ts = int(datetime.now(timezone.utc).timestamp())
            with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                manager.request_withdrawal("0xUser", 2000.0, ts)
            mock_instance.record_time_locked_request.assert_called_once_with(1)

    def test_metrics_backlog_on_cancel(self):
        """Backlog metrics updated on cancel."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
            ts = int(datetime.now(timezone.utc).timestamp())
            with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                w = manager.request_withdrawal("0xUser", 2000.0, ts)
                manager.cancel_withdrawal(w.withdrawal_id, "0xUser")
            mock_instance.update_time_locked_backlog.assert_called_with(0)

    def test_metrics_backlog_on_process(self):
        """Backlog metrics updated on process."""
        with patch("xai.wallet.time_locked_withdrawals.MetricsCollector") as mock_mc:
            mock_instance = MagicMock()
            mock_mc.instance.return_value = mock_instance
            manager = TimeLockedWithdrawalManager(
                withdrawal_threshold=1000.0, time_lock_seconds=60
            )
            ts = int(datetime.now(timezone.utc).timestamp())
            with patch("xai.wallet.time_locked_withdrawals.log_security_event"):
                manager.request_withdrawal("0xUser", 2000.0, ts)
                manager.process_releasable_withdrawals(ts + 120)
            mock_instance.update_time_locked_backlog.assert_called_with(0)
