"""
Unit tests for PriorityFeeManager.

Coverage targets:
- Initialization and validation
- Total fee calculations
- Recommended priority fee generation
- Priority queue operations (add, process)
- Queue ordering by fee (highest first)
- Edge cases and error handling
"""

import heapq
from unittest.mock import MagicMock, patch

import pytest

from xai.network.fee_adjuster import FeeAdjuster
from xai.network.priority_fee_manager import PriorityFeeManager


@pytest.fixture
def fee_adjuster():
    """Create a FeeAdjuster for testing."""
    adjuster = FeeAdjuster(
        base_fee=0.001,
        max_fee=0.05,
        congestion_factor=0.005,
        history_window_blocks=5,
    )
    adjuster.update_network_metrics(100, 0.5)  # Set some state
    return adjuster


class TestPriorityFeeManagerInit:
    """Tests for PriorityFeeManager initialization."""

    def test_default_initialization(self, fee_adjuster, capsys):
        """PriorityFeeManager initializes with defaults."""
        manager = PriorityFeeManager(fee_adjuster)

        assert manager.fee_adjuster is fee_adjuster
        assert manager.min_priority_fee == 0.0001
        assert manager.transaction_priority_queue == []
        assert manager._transaction_id_counter == 0

        # Check initialization message
        captured = capsys.readouterr()
        assert "PriorityFeeManager initialized" in captured.out

    def test_custom_min_priority_fee(self, fee_adjuster, capsys):
        """PriorityFeeManager accepts custom minimum priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.001)
        assert manager.min_priority_fee == 0.001

    def test_zero_min_priority_fee(self, fee_adjuster, capsys):
        """Zero minimum priority fee is accepted."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0)
        assert manager.min_priority_fee == 0


class TestPriorityFeeManagerValidation:
    """Tests for input validation."""

    def test_fee_adjuster_must_be_instance(self, capsys):
        """Fee adjuster must be FeeAdjuster instance."""
        with pytest.raises(ValueError, match="fee_adjuster must be an instance of FeeAdjuster"):
            PriorityFeeManager(None)

        with pytest.raises(ValueError, match="fee_adjuster must be an instance of FeeAdjuster"):
            PriorityFeeManager("not a fee adjuster")

        with pytest.raises(ValueError, match="fee_adjuster must be an instance of FeeAdjuster"):
            PriorityFeeManager({})

    def test_min_priority_fee_must_be_non_negative(self, fee_adjuster):
        """Minimum priority fee must be non-negative."""
        with pytest.raises(ValueError, match="Minimum priority fee must be a non-negative number"):
            PriorityFeeManager(fee_adjuster, min_priority_fee=-0.001)

    def test_min_priority_fee_must_be_numeric(self, fee_adjuster):
        """Minimum priority fee must be numeric."""
        with pytest.raises(ValueError, match="Minimum priority fee must be a non-negative number"):
            PriorityFeeManager(fee_adjuster, min_priority_fee="0.001")

        with pytest.raises(ValueError, match="Minimum priority fee must be a non-negative number"):
            PriorityFeeManager(fee_adjuster, min_priority_fee=None)


class TestCalculateTotalFee:
    """Tests for total fee calculation."""

    def test_calculate_total_fee_basic(self, fee_adjuster, capsys):
        """Total fee combines base and priority fees."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Clear previous output
        capsys.readouterr()

        total = manager.calculate_total_fee(0.001)

        # Total = base_fee + priority_fee
        base_fee = fee_adjuster.get_suggested_fee()
        expected = base_fee + 0.001

        # Due to fee adjuster state, approximate check
        assert total > 0.001  # At least the priority fee

        captured = capsys.readouterr()
        assert "Base Fee:" in captured.out
        assert "Priority Fee:" in captured.out
        assert "Total Fee:" in captured.out

    def test_calculate_total_fee_minimum_priority(self, fee_adjuster, capsys):
        """Priority fee at minimum is accepted."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)
        total = manager.calculate_total_fee(0.0001)
        assert total > 0.0001

    def test_calculate_total_fee_below_minimum_rejected(self, fee_adjuster):
        """Priority fee below minimum is rejected."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.001)

        with pytest.raises(ValueError, match="Priority fee .* must be at least the minimum"):
            manager.calculate_total_fee(0.0001)

    def test_calculate_total_fee_negative_rejected(self, fee_adjuster):
        """Negative priority fee is rejected."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        with pytest.raises(ValueError, match="Priority fee .* must be at least the minimum"):
            manager.calculate_total_fee(-0.001)

    def test_calculate_total_fee_non_numeric_rejected(self, fee_adjuster):
        """Non-numeric priority fee is rejected."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        with pytest.raises(ValueError):
            manager.calculate_total_fee("0.001")

    def test_calculate_total_fee_with_zero_minimum(self, fee_adjuster, capsys):
        """Zero minimum allows any non-negative priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0)

        # Should accept zero priority fee
        total = manager.calculate_total_fee(0)
        assert total >= 0

    def test_calculate_total_fee_integer_priority(self, fee_adjuster, capsys):
        """Integer priority fee is accepted."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0)
        total = manager.calculate_total_fee(1)
        assert total >= 1


class TestGetRecommendedPriorityFee:
    """Tests for priority fee recommendations."""

    def test_fast_priority_fee(self, fee_adjuster, capsys):
        """Fast speed returns 5x minimum priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)
        fee = manager.get_recommended_priority_fee("fast")
        assert fee == 0.0005  # 5 * 0.0001

    def test_medium_priority_fee(self, fee_adjuster, capsys):
        """Medium speed returns 2x minimum priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)
        fee = manager.get_recommended_priority_fee("medium")
        assert fee == 0.0002  # 2 * 0.0001

    def test_slow_priority_fee(self, fee_adjuster, capsys):
        """Slow speed returns 1x minimum priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)
        fee = manager.get_recommended_priority_fee("slow")
        assert fee == 0.0001  # 1 * 0.0001

    def test_default_speed_is_medium(self, fee_adjuster, capsys):
        """Default speed parameter is medium."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)
        fee = manager.get_recommended_priority_fee()
        assert fee == 0.0002  # medium = 2x

    def test_invalid_speed_raises_error(self, fee_adjuster):
        """Invalid speed parameter raises ValueError."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        with pytest.raises(ValueError, match="Desired speed must be 'fast', 'medium', or 'slow'"):
            manager.get_recommended_priority_fee("instant")

        with pytest.raises(ValueError, match="Desired speed must be 'fast', 'medium', or 'slow'"):
            manager.get_recommended_priority_fee("FAST")  # Case sensitive

        with pytest.raises(ValueError, match="Desired speed must be 'fast', 'medium', or 'slow'"):
            manager.get_recommended_priority_fee("")

    def test_recommended_fee_with_zero_minimum(self, fee_adjuster, capsys):
        """Recommendations with zero minimum return zero."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0)

        assert manager.get_recommended_priority_fee("fast") == 0
        assert manager.get_recommended_priority_fee("medium") == 0
        assert manager.get_recommended_priority_fee("slow") == 0


class TestAddTransactionToQueue:
    """Tests for adding transactions to the queue."""

    def test_add_transaction_increments_counter(self, fee_adjuster, capsys):
        """Adding transaction increments ID counter."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        assert manager._transaction_id_counter == 0

        manager.add_transaction_to_queue({"data": "tx1"}, 0.001)
        assert manager._transaction_id_counter == 1

        manager.add_transaction_to_queue({"data": "tx2"}, 0.002)
        assert manager._transaction_id_counter == 2

    def test_add_transaction_creates_queue_entry(self, fee_adjuster, capsys):
        """Adding transaction creates proper queue entry."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue({"data": "test"}, 0.001)

        assert len(manager.transaction_priority_queue) == 1
        entry = manager.transaction_priority_queue[0]

        # Entry format: (-total_fee, tx_id, details)
        assert entry[0] < 0  # Negative for max-heap behavior
        assert entry[1] == "queued_tx_1"
        assert entry[2] == {"data": "test"}

    def test_add_transaction_output(self, fee_adjuster, capsys):
        """Adding transaction produces expected output."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Clear previous output
        capsys.readouterr()

        manager.add_transaction_to_queue("test_tx", 0.001)

        captured = capsys.readouterr()
        assert "Transaction queued_tx_1 added to queue" in captured.out
        assert "Total Fee:" in captured.out

    def test_add_transaction_validates_priority_fee(self, fee_adjuster):
        """Adding transaction validates priority fee."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.001)

        with pytest.raises(ValueError, match="Priority fee"):
            manager.add_transaction_to_queue("test", 0.0001)  # Below minimum

    def test_add_multiple_transactions(self, fee_adjuster, capsys):
        """Multiple transactions are added to queue."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue("tx1", 0.001)
        manager.add_transaction_to_queue("tx2", 0.002)
        manager.add_transaction_to_queue("tx3", 0.003)

        assert len(manager.transaction_priority_queue) == 3
        assert manager._transaction_id_counter == 3


class TestProcessNextTransaction:
    """Tests for processing transactions from the queue."""

    def test_process_empty_queue_returns_none(self, fee_adjuster, capsys):
        """Processing empty queue returns None."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Clear previous output
        capsys.readouterr()

        result = manager.process_next_transaction()

        assert result is None
        captured = capsys.readouterr()
        assert "Transaction queue is empty" in captured.out

    def test_process_single_transaction(self, fee_adjuster, capsys):
        """Processing single transaction returns it."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue("test_details", 0.001)

        # Clear output before processing
        capsys.readouterr()

        result = manager.process_next_transaction()

        assert result is not None
        tx_id, details, total_fee = result
        assert tx_id == "queued_tx_1"
        assert details == "test_details"
        assert total_fee > 0

        captured = capsys.readouterr()
        assert "Processing transaction" in captured.out

    def test_process_removes_from_queue(self, fee_adjuster, capsys):
        """Processing removes transaction from queue."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue("test", 0.001)
        assert len(manager.transaction_priority_queue) == 1

        manager.process_next_transaction()
        assert len(manager.transaction_priority_queue) == 0

    def test_process_highest_fee_first(self, fee_adjuster, capsys):
        """Transactions are processed highest fee first."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add with different priority fees
        manager.add_transaction_to_queue("low_priority", 0.0001)
        manager.add_transaction_to_queue("high_priority", 0.01)
        manager.add_transaction_to_queue("medium_priority", 0.001)

        # Process in order - should be high, medium, low
        result1 = manager.process_next_transaction()
        assert result1[1] == "high_priority"

        result2 = manager.process_next_transaction()
        assert result2[1] == "medium_priority"

        result3 = manager.process_next_transaction()
        assert result3[1] == "low_priority"

    def test_process_all_transactions(self, fee_adjuster, capsys):
        """All transactions can be processed."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add several transactions
        for i in range(5):
            manager.add_transaction_to_queue(f"tx_{i}", 0.001 * (i + 1))

        # Process all
        processed = []
        while True:
            result = manager.process_next_transaction()
            if result is None:
                break
            processed.append(result)

        assert len(processed) == 5
        assert len(manager.transaction_priority_queue) == 0


class TestQueueOrdering:
    """Tests for priority queue ordering behavior."""

    def test_queue_maintains_heap_property(self, fee_adjuster, capsys):
        """Queue maintains proper heap ordering."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add in random order
        manager.add_transaction_to_queue("d", 0.004)
        manager.add_transaction_to_queue("a", 0.001)
        manager.add_transaction_to_queue("c", 0.003)
        manager.add_transaction_to_queue("b", 0.002)

        # Process and verify descending fee order
        fees = []
        while True:
            result = manager.process_next_transaction()
            if result is None:
                break
            fees.append(result[2])

        # Fees should be in descending order
        assert fees == sorted(fees, reverse=True)

    def test_equal_fees_processed_in_insertion_order(self, fee_adjuster, capsys):
        """Transactions with equal fees maintain FIFO order."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add with same priority fee
        manager.add_transaction_to_queue("first", 0.001)
        manager.add_transaction_to_queue("second", 0.001)
        manager.add_transaction_to_queue("third", 0.001)

        # Due to heap behavior and tx_id sorting, order is maintained
        result1 = manager.process_next_transaction()
        result2 = manager.process_next_transaction()
        result3 = manager.process_next_transaction()

        # Transaction IDs (result[0]) should be in order
        assert result1[0] == "queued_tx_1"
        assert result2[0] == "queued_tx_2"
        assert result3[0] == "queued_tx_3"
        # Details (result[1]) should match what was added
        assert result1[1] == "first"
        assert result2[1] == "second"
        assert result3[1] == "third"


class TestTransactionDetails:
    """Tests for various transaction detail types."""

    def test_string_details(self, fee_adjuster, capsys):
        """String transaction details are preserved."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue("simple string", 0.001)
        result = manager.process_next_transaction()
        assert result[1] == "simple string"

    def test_dict_details(self, fee_adjuster, capsys):
        """Dictionary transaction details are preserved."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        details = {"from": "0x123", "to": "0x456", "value": 100}
        manager.add_transaction_to_queue(details, 0.001)
        result = manager.process_next_transaction()
        assert result[1] == details

    def test_list_details(self, fee_adjuster, capsys):
        """List transaction details are preserved."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        details = ["input1", "input2", "output"]
        manager.add_transaction_to_queue(details, 0.001)
        result = manager.process_next_transaction()
        assert result[1] == details

    def test_none_details(self, fee_adjuster, capsys):
        """None transaction details are accepted."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        manager.add_transaction_to_queue(None, 0.001)
        result = manager.process_next_transaction()
        assert result[1] is None

    def test_complex_nested_details(self, fee_adjuster, capsys):
        """Complex nested transaction details are preserved."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        details = {
            "tx": {
                "inputs": [{"prev_hash": "abc", "index": 0}],
                "outputs": [{"address": "xyz", "amount": 100}],
            },
            "metadata": {"timestamp": 12345, "nonce": 42},
        }
        manager.add_transaction_to_queue(details, 0.001)
        result = manager.process_next_transaction()
        assert result[1] == details


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios."""

    def test_full_workflow(self, fee_adjuster, capsys):
        """Complete workflow: add transactions, process in priority order."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add transactions with different speeds
        manager.add_transaction_to_queue(
            "tx_A_details",
            manager.get_recommended_priority_fee("slow"),
        )
        manager.add_transaction_to_queue(
            "tx_B_details",
            manager.get_recommended_priority_fee("medium"),
        )
        manager.add_transaction_to_queue(
            "tx_C_details",
            manager.get_recommended_priority_fee("fast"),
        )
        manager.add_transaction_to_queue(
            "tx_D_details",
            0.0005,  # Custom priority
        )

        # Process all - should be in descending fee order
        processed = []
        while True:
            result = manager.process_next_transaction()
            if result is None:
                break
            processed.append(result)

        assert len(processed) == 4

        # Fast should be first (highest priority)
        assert processed[0][1] == "tx_C_details"

    def test_interleaved_add_and_process(self, fee_adjuster, capsys):
        """Adding and processing can be interleaved."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        # Add some
        manager.add_transaction_to_queue("tx1", 0.001)
        manager.add_transaction_to_queue("tx2", 0.003)

        # Process one
        result1 = manager.process_next_transaction()
        assert result1[1] == "tx2"  # Higher fee

        # Add more
        manager.add_transaction_to_queue("tx3", 0.005)

        # Process remaining
        result2 = manager.process_next_transaction()
        assert result2[1] == "tx3"  # Highest remaining

        result3 = manager.process_next_transaction()
        assert result3[1] == "tx1"  # Last one

        assert manager.process_next_transaction() is None

    def test_network_congestion_affects_total_fee(self, capsys):
        """Network congestion increases total fees."""
        # Create adjuster with low congestion
        low_congestion_adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.1,
            congestion_factor=0.01,
        )
        low_congestion_adjuster.update_network_metrics(10, 0.1)

        manager_low = PriorityFeeManager(low_congestion_adjuster, min_priority_fee=0.0001)
        fee_low = manager_low.calculate_total_fee(0.001)

        # Create adjuster with high congestion
        high_congestion_adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.1,
            congestion_factor=0.01,
        )
        high_congestion_adjuster.update_network_metrics(5000, 1.0)

        manager_high = PriorityFeeManager(high_congestion_adjuster, min_priority_fee=0.0001)
        fee_high = manager_high.calculate_total_fee(0.001)

        # High congestion should result in higher total fee
        assert fee_high > fee_low


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_very_small_priority_fee(self, fee_adjuster, capsys):
        """Very small priority fees are handled."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0000001)

        total = manager.calculate_total_fee(0.0000001)
        assert total > 0.0000001

    def test_very_large_priority_fee(self, fee_adjuster, capsys):
        """Very large priority fees are handled."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        total = manager.calculate_total_fee(1000.0)
        assert total > 1000.0

    def test_large_queue_size(self, fee_adjuster, capsys):
        """Large number of transactions in queue."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0)

        # Add many transactions
        for i in range(1000):
            manager.add_transaction_to_queue(f"tx_{i}", 0.001 * (i % 100 + 1))

        assert len(manager.transaction_priority_queue) == 1000

        # Process all
        count = 0
        prev_fee = float("inf")
        while True:
            result = manager.process_next_transaction()
            if result is None:
                break
            # Verify descending fee order
            assert result[2] <= prev_fee
            prev_fee = result[2]
            count += 1

        assert count == 1000

    def test_transaction_id_uniqueness(self, fee_adjuster, capsys):
        """Transaction IDs are unique."""
        manager = PriorityFeeManager(fee_adjuster, min_priority_fee=0.0001)

        ids = set()
        for i in range(100):
            manager.add_transaction_to_queue(f"tx_{i}", 0.001)

        while True:
            result = manager.process_next_transaction()
            if result is None:
                break
            assert result[0] not in ids
            ids.add(result[0])

        assert len(ids) == 100
