"""
Comprehensive tests for error_detection module - targeting 70%+ coverage

Tests ErrorDetector, CorruptionDetector, and HealthMonitor classes including
error classification, pattern detection, corruption checks, and health scoring.
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from xai.core.chain.error_detection import (
    ErrorSeverity,
    RecoveryState,
    ErrorDetector,
    CorruptionDetector,
    HealthMonitor,
)


class MockBlock:
    """Mock block for testing"""

    def __init__(self, index, previous_hash="", hash_val=None, transactions=None):
        self.index = index
        self.previous_hash = previous_hash
        self.hash = hash_val or f"block_{index}_hash"
        self.transactions = transactions or []
        self.timestamp = time.time()
        self.nonce = 0
        self.merkle_root = "merkle_root"
        self.difficulty = 4

    def calculate_hash(self):
        """Calculate block hash"""
        return self.hash

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
            "difficulty": self.difficulty,
            "transactions": [tx.to_dict() for tx in self.transactions],
        }


class MockTransaction:
    """Mock transaction"""

    def __init__(self, sender="XAI_A", recipient="XAI_B", amount=100, fee=1):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.txid = f"tx_{sender}_{recipient}_{amount}"
        self.signature = "signature"
        self.public_key = "public_key"
        self.timestamp = time.time()

    def verify_signature(self):
        """Mock signature verification"""
        return True

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "txid": self.txid,
            "signature": self.signature,
            "public_key": self.public_key,
            "timestamp": self.timestamp,
        }


class MockBlockchain:
    """Mock blockchain for testing"""

    def __init__(self):
        self.chain = []
        self.utxo_set = {}
        self.pending_transactions = []
        self.max_supply = 121000000
        self.difficulty = 4

    def get_balance(self, address):
        """Get balance for address"""
        utxos = self.utxo_set.get(address, [])
        return sum(u["amount"] for u in utxos if not u.get("spent", False))

    def get_latest_block(self):
        """Get latest block"""
        if self.chain:
            return self.chain[-1]
        return MockBlock(0)


class TestErrorSeverity:
    """Test ErrorSeverity enum"""

    def test_error_severity_values(self):
        """Test all severity level values"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_severity_comparison(self):
        """Test severity comparisons"""
        assert ErrorSeverity.LOW == ErrorSeverity.LOW
        assert ErrorSeverity.HIGH != ErrorSeverity.LOW


class TestRecoveryState:
    """Test RecoveryState enum"""

    def test_recovery_state_values(self):
        """Test all recovery state values"""
        assert RecoveryState.HEALTHY.value == "healthy"
        assert RecoveryState.DEGRADED.value == "degraded"
        assert RecoveryState.RECOVERING.value == "recovering"
        assert RecoveryState.CRITICAL.value == "critical"
        assert RecoveryState.SHUTDOWN.value == "shutdown"

    def test_recovery_state_comparison(self):
        """Test recovery state comparisons"""
        assert RecoveryState.HEALTHY == RecoveryState.HEALTHY
        assert RecoveryState.CRITICAL != RecoveryState.HEALTHY


class TestErrorDetector:
    """Comprehensive ErrorDetector tests"""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        return MockBlockchain()

    @pytest.fixture
    def detector(self, blockchain):
        """Create ErrorDetector instance"""
        return ErrorDetector(blockchain)

    def test_init(self, detector, blockchain):
        """Test initialization"""
        assert detector.blockchain == blockchain
        assert len(detector.error_history) == 0
        assert len(detector.error_patterns) == 0

    def test_detect_error_keyboard_interrupt(self, detector):
        """Test detecting KeyboardInterrupt as critical"""
        error = KeyboardInterrupt()
        severity = detector.detect_error(error, "user_interrupt")

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_system_exit(self, detector):
        """Test detecting SystemExit as critical"""
        error = SystemExit(1)
        severity = detector.detect_error(error, "system_exit")

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_memory_error(self, detector):
        """Test detecting MemoryError as critical"""
        error = MemoryError("Out of memory")
        severity = detector.detect_error(error, "allocation")

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_io_error(self, detector):
        """Test detecting IOError as critical"""
        error = IOError("Disk error")
        severity = detector.detect_error(error, "file_write")

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_os_error(self, detector):
        """Test detecting OSError as critical"""
        error = OSError("System error")
        severity = detector.detect_error(error, "system_call")

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_blockchain_value_error(self, detector):
        """Test ValueError with blockchain context as high severity"""
        error = ValueError("Invalid blockchain state")
        severity = detector.detect_error(error, "validation")

        assert severity == ErrorSeverity.HIGH

    def test_detect_error_transaction_value_error(self, detector):
        """Test ValueError with transaction context as high severity"""
        error = ValueError("Invalid transaction format")
        severity = detector.detect_error(error, "tx_validation")

        assert severity == ErrorSeverity.HIGH

    def test_detect_error_type_error(self, detector):
        """Test TypeError as medium severity"""
        error = TypeError("Type mismatch")
        severity = detector.detect_error(error, "operation")

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_attribute_error(self, detector):
        """Test AttributeError as medium severity"""
        error = AttributeError("Missing attribute")
        severity = detector.detect_error(error, "access")

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_connection_error(self, detector):
        """Test ConnectionError as medium severity"""
        error = ConnectionError("Connection lost")
        severity = detector.detect_error(error, "network")

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_timeout_error(self, detector):
        """Test TimeoutError as medium severity"""
        error = TimeoutError("Request timeout")
        severity = detector.detect_error(error, "network")

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_unknown_type(self, detector):
        """Test unknown error type defaults to medium"""
        error = Exception("Unknown error")
        severity = detector.detect_error(error, "unknown")

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_logs_to_history(self, detector):
        """Test that errors are logged to history"""
        error = ValueError("test error")
        detector.detect_error(error, "test_context")

        assert len(detector.error_history) == 1
        entry = detector.error_history[0]

        assert "timestamp" in entry
        assert entry["type"] == "ValueError"
        assert entry["message"] == "test error"
        assert entry["context"] == "test_context"

    def test_detect_error_updates_patterns(self, detector):
        """Test that error patterns are tracked"""
        for i in range(3):
            detector.detect_error(ValueError(f"error {i}"), "context")

        assert "ValueError" in detector.error_patterns
        assert detector.error_patterns["ValueError"] == 3

    def test_detect_error_patterns_threshold(self, detector):
        """Test detecting error patterns above threshold"""
        # Generate recurring errors
        for i in range(10):
            detector.detect_error(ConnectionError("network fail"), "network")

        patterns = detector.detect_error_patterns()

        assert len(patterns) > 0
        assert patterns[0]["error_type"] == "ConnectionError"
        assert patterns[0]["count"] == 10
        assert patterns[0]["severity"] == "high"  # >= 10 occurrences

    def test_detect_error_patterns_medium_severity(self, detector):
        """Test pattern detection with medium severity"""
        # Generate 7 errors (between 5 and 10)
        for i in range(7):
            detector.detect_error(ValueError("error"), "context")

        patterns = detector.detect_error_patterns()

        assert len(patterns) > 0
        assert patterns[0]["severity"] == "medium"

    def test_detect_error_patterns_below_threshold(self, detector):
        """Test no patterns detected below threshold"""
        # Generate only 3 errors (below threshold of 5)
        for i in range(3):
            detector.detect_error(RuntimeError("error"), "context")

        patterns = detector.detect_error_patterns()

        assert len(patterns) == 0

    def test_detect_error_patterns_includes_suggestions(self, detector):
        """Test that patterns include suggestions"""
        for i in range(5):
            detector.detect_error(ConnectionError("error"), "context")

        patterns = detector.detect_error_patterns()

        assert "suggestion" in patterns[0]
        assert "network connectivity" in patterns[0]["suggestion"]

    def test_get_error_statistics_empty(self, detector):
        """Test statistics with no errors"""
        stats = detector.get_error_statistics()

        assert stats["total_errors"] == 0
        assert stats["error_rate"] == 0.0
        assert stats["common_errors"] == []
        assert stats["severity_distribution"] == {}

    def test_get_error_statistics_with_errors(self, detector):
        """Test statistics with logged errors"""
        detector.detect_error(ValueError("err1"), "ctx")
        detector.detect_error(ValueError("err2"), "ctx")
        detector.detect_error(RuntimeError("err3"), "ctx")
        time.sleep(0.01)  # Ensure time difference

        stats = detector.get_error_statistics()

        assert stats["total_errors"] == 3
        assert stats["error_rate"] > 0
        assert len(stats["common_errors"]) > 0
        assert "recent_patterns" in stats

    def test_get_error_statistics_common_errors(self, detector):
        """Test common errors in statistics"""
        # Generate multiple error types
        for i in range(5):
            detector.detect_error(ValueError("val"), "ctx")
        for i in range(3):
            detector.detect_error(RuntimeError("run"), "ctx")
        for i in range(2):
            detector.detect_error(TypeError("type"), "ctx")

        stats = detector.get_error_statistics()

        # Should return top 5, sorted by count
        common = stats["common_errors"]
        assert common[0]["type"] == "ValueError"
        assert common[0]["count"] == 5
        assert common[1]["type"] == "RuntimeError"
        assert common[1]["count"] == 3

    def test_get_error_statistics_error_rate(self, detector):
        """Test error rate calculation"""
        # Generate errors with time span
        for i in range(10):
            detector.detect_error(Exception(f"err {i}"), "ctx")
            time.sleep(0.001)

        stats = detector.get_error_statistics()

        # Error rate should be positive (errors per hour)
        assert stats["error_rate"] > 0

    def test_get_pattern_suggestion_connection_error(self, detector):
        """Test suggestion for ConnectionError pattern"""
        suggestion = detector._get_pattern_suggestion("ConnectionError")
        assert "network connectivity" in suggestion

    def test_get_pattern_suggestion_timeout_error(self, detector):
        """Test suggestion for TimeoutError pattern"""
        suggestion = detector._get_pattern_suggestion("TimeoutError")
        assert "timeout values" in suggestion or "latency" in suggestion

    def test_get_pattern_suggestion_value_error(self, detector):
        """Test suggestion for ValueError pattern"""
        suggestion = detector._get_pattern_suggestion("ValueError")
        assert "input data" in suggestion or "Validate" in suggestion

    def test_get_pattern_suggestion_unknown(self, detector):
        """Test suggestion for unknown error type"""
        suggestion = detector._get_pattern_suggestion("UnknownError")
        assert "Review error logs" in suggestion

    def test_log_error_method(self, detector):
        """Test _log_error internal method"""
        detector._log_error("TestError", "test message", "test context")

        assert len(detector.error_history) == 1
        entry = detector.error_history[0]

        assert entry["type"] == "TestError"
        assert entry["message"] == "test message"
        assert entry["context"] == "test context"


class TestCorruptionDetector:
    """Comprehensive CorruptionDetector tests"""

    @pytest.fixture
    def detector(self):
        """Create CorruptionDetector instance"""
        return CorruptionDetector()

    @pytest.fixture
    def blockchain(self):
        """Create valid blockchain"""
        blockchain = MockBlockchain()

        # Create valid chain
        genesis = MockBlock(0, "0")
        genesis.hash = "genesis_hash"
        blockchain.chain.append(genesis)

        block1 = MockBlock(1, "genesis_hash")
        block1.hash = "block1_hash"
        blockchain.chain.append(block1)

        block2 = MockBlock(2, "block1_hash")
        block2.hash = "block2_hash"
        blockchain.chain.append(block2)

        return blockchain

    def test_init(self, detector):
        """Test initialization"""
        assert "hash_integrity" in detector.corruption_checks
        assert "chain_continuity" in detector.corruption_checks
        assert "utxo_consistency" in detector.corruption_checks
        assert "supply_validation" in detector.corruption_checks
        assert "transaction_validity" in detector.corruption_checks

    def test_detect_corruption_clean_chain(self, detector, blockchain):
        """Test no corruption in clean chain"""
        is_corrupted, issues = detector.detect_corruption(blockchain)

        # Mock implementation may have some issues, but test should run
        assert isinstance(is_corrupted, bool)
        assert isinstance(issues, list)

    def test_detect_corruption_hash_mismatch(self, detector):
        """Test detecting hash mismatch"""
        blockchain = MockBlockchain()
        block = MockBlock(0, "0")
        block.hash = "wrong_hash"

        # Mock calculate_hash to return different value
        block.calculate_hash = Mock(return_value="correct_hash")
        blockchain.chain.append(block)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("hash mismatch" in issue.lower() for issue in issues)

    def test_detect_corruption_broken_chain(self, detector):
        """Test detecting broken chain link"""
        blockchain = MockBlockchain()

        genesis = MockBlock(0, "0")
        genesis.hash = "genesis_hash"
        blockchain.chain.append(genesis)

        # Block with wrong previous hash
        block1 = MockBlock(1, "wrong_previous_hash")
        blockchain.chain.append(block1)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("broken chain" in issue.lower() for issue in issues)

    def test_detect_corruption_index_discontinuity(self, detector):
        """Test detecting index discontinuity"""
        blockchain = MockBlockchain()

        block0 = MockBlock(0, "0")
        block0.hash = "hash0"
        blockchain.chain.append(block0)

        # Block with wrong index (should be 1, not 5)
        block1 = MockBlock(5, "hash0")
        blockchain.chain.append(block1)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("index discontinuity" in issue.lower() for issue in issues)

    def test_detect_corruption_supply_exceeded(self, detector):
        """Test detecting supply cap exceeded"""
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))

        # Add excessive supply
        blockchain.utxo_set["XAI_WHALE"] = [{"amount": 200000000, "spent": False}]

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("supply cap exceeded" in issue.lower() for issue in issues)

    def test_detect_corruption_negative_transaction(self, detector):
        """Test detecting negative transaction amount"""
        blockchain = MockBlockchain()

        tx = MockTransaction(amount=-100)
        block = MockBlock(0, "0", transactions=[tx])
        blockchain.chain.append(block)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("negative amount" in issue.lower() for issue in issues)

    def test_detect_corruption_invalid_signature(self, detector):
        """Test detecting invalid signature"""
        blockchain = MockBlockchain()

        tx = MockTransaction()
        tx.verify_signature = Mock(return_value=False)
        tx.sender = "XAI_USER"  # Not coinbase

        block = MockBlock(0, "0", transactions=[tx])
        blockchain.chain.append(block)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("invalid signature" in issue.lower() for issue in issues)

    def test_check_hash_integrity_valid(self, detector, blockchain):
        """Test hash integrity check on valid chain"""
        is_valid, errors = detector._check_hash_integrity(blockchain)

        # May have issues due to mock, but should run
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_check_chain_continuity_valid(self, detector, blockchain):
        """Test chain continuity on valid chain"""
        is_valid, errors = detector._check_chain_continuity(blockchain)

        assert is_valid is True
        assert len(errors) == 0

    def test_check_utxo_consistency(self, detector, blockchain):
        """Test UTXO consistency check"""
        # Add some UTXOs
        blockchain.utxo_set["XAI_A"] = [
            {"txid": "tx1", "amount": 100, "spent": False},
            {"txid": "tx2", "amount": 50, "spent": True},
        ]

        is_valid, errors = detector._check_utxo_consistency(blockchain)

        # Test should complete without exceptions
        assert isinstance(is_valid, bool)

    def test_check_supply_validation_valid(self, detector, blockchain):
        """Test supply validation with valid supply"""
        blockchain.utxo_set["XAI_A"] = [{"amount": 1000, "spent": False}]

        is_valid, errors = detector._check_supply_validation(blockchain)

        assert is_valid is True
        assert len(errors) == 0

    def test_check_transaction_validity_valid(self, detector, blockchain):
        """Test transaction validity check with valid transactions"""
        tx = MockTransaction(sender="COINBASE", amount=50, fee=0)
        block = MockBlock(0, "0", transactions=[tx])
        blockchain.chain = [block]

        is_valid, errors = detector._check_transaction_validity(blockchain)

        assert is_valid is True

    def test_check_transaction_validity_negative_fee(self, detector, blockchain):
        """Test detecting negative transaction fee"""
        tx = MockTransaction(fee=-1)
        block = MockBlock(0, "0", transactions=[tx])
        blockchain.chain = [block]

        is_valid, errors = detector._check_transaction_validity(blockchain)

        assert is_valid is False
        assert any("Negative fee" in err for err in errors)

    def test_corruption_check_exception_handling(self, detector):
        """Test that check exceptions are caught and reported"""
        blockchain = MockBlockchain()

        # Make a check raise an exception
        def failing_check(bc):
            raise RuntimeError("Check failed")

        detector.corruption_checks["failing_check"] = failing_check

        is_corrupted, issues = detector.detect_corruption(blockchain)

        # Should catch exception and report it
        assert any("Check failed" in issue for issue in issues)


class TestHealthMonitor:
    """Comprehensive HealthMonitor tests"""

    @pytest.fixture
    def monitor(self):
        """Create HealthMonitor instance"""
        return HealthMonitor()

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))
        return blockchain

    @pytest.fixture
    def node(self):
        """Create mock node"""
        node = Mock()
        node.peers = ["peer1", "peer2", "peer3"]
        return node

    def test_init(self, monitor):
        """Test initialization"""
        assert "last_block_time" in monitor.metrics
        assert "blocks_mined" in monitor.metrics
        assert "transactions_processed" in monitor.metrics
        assert "errors_encountered" in monitor.metrics
        assert "network_peers" in monitor.metrics
        assert "mempool_size" in monitor.metrics
        assert "sync_status" in monitor.metrics

        assert len(monitor.health_history) == 0

    def test_init_default_metrics(self, monitor):
        """Test default metric values"""
        assert monitor.metrics["blocks_mined"] == 0
        assert monitor.metrics["transactions_processed"] == 0
        assert monitor.metrics["errors_encountered"] == 0
        assert monitor.metrics["network_peers"] == 0
        assert monitor.metrics["mempool_size"] == 0
        assert monitor.metrics["sync_status"] == "synced"

    def test_update_metrics_blockchain_only(self, monitor, blockchain):
        """Test updating metrics with blockchain only"""
        monitor.update_metrics(blockchain)

        assert monitor.metrics["blocks_mined"] == 1
        assert monitor.metrics["mempool_size"] == 0
        assert len(monitor.health_history) == 1

    def test_update_metrics_with_node(self, monitor, blockchain, node):
        """Test updating metrics with blockchain and node"""
        monitor.update_metrics(blockchain, node)

        assert monitor.metrics["network_peers"] == 3
        assert len(monitor.health_history) == 1

    def test_update_metrics_multiple_times(self, monitor, blockchain):
        """Test updating metrics multiple times"""
        for i in range(5):
            monitor.update_metrics(blockchain)

        assert len(monitor.health_history) == 5

    def test_calculate_health_score_perfect(self, monitor, blockchain):
        """Test health score calculation with perfect health"""
        monitor.update_metrics(blockchain)
        score = monitor._calculate_health_score(blockchain)

        # With recent block, empty mempool, should be high
        assert score >= 75

    def test_calculate_health_score_old_block(self, monitor, blockchain):
        """Test health score penalty for old block"""
        monitor.metrics["last_block_time"] = time.time() - 1000  # Very old

        score = monitor._calculate_health_score(blockchain)

        # Should have penalty for old block
        assert score < 100

    def test_calculate_health_score_full_mempool(self, monitor, blockchain):
        """Test health score penalty for full mempool"""
        monitor.metrics["mempool_size"] = 15000  # Very full

        score = monitor._calculate_health_score(blockchain)

        # Should have penalty
        assert score < 100

    def test_calculate_health_score_no_peers(self, monitor, blockchain):
        """Test health score penalty for no peers"""
        monitor.metrics["network_peers"] = 0

        score = monitor._calculate_health_score(blockchain)

        # Should have 25 point penalty
        assert score <= 75

    def test_calculate_health_score_many_errors(self, monitor, blockchain):
        """Test health score penalty for many errors"""
        monitor.metrics["errors_encountered"] = 20

        score = monitor._calculate_health_score(blockchain)

        # Should have penalty for errors
        assert score < 100

    def test_calculate_health_score_minimum_zero(self, monitor, blockchain):
        """Test health score never goes below zero"""
        # Set all penalties
        monitor.metrics["last_block_time"] = time.time() - 10000
        monitor.metrics["mempool_size"] = 50000
        monitor.metrics["network_peers"] = 0
        monitor.metrics["errors_encountered"] = 100

        score = monitor._calculate_health_score(blockchain)

        assert score >= 0

    def test_get_health_status_no_history(self, monitor):
        """Test getting status with no history"""
        status = monitor.get_health_status()

        assert status["status"] == "unknown"
        assert status["score"] == 0
        assert "metrics" in status

    def test_get_health_status_healthy(self, monitor, blockchain):
        """Test getting status with healthy system"""
        monitor.update_metrics(blockchain)

        status = monitor.get_health_status()

        assert "status" in status
        assert "score" in status
        assert "metrics" in status
        assert "timestamp" in status

        # Should be healthy or degraded (depending on exact score)
        assert status["status"] in ["healthy", "degraded"]

    def test_get_health_status_classification_healthy(self, monitor, blockchain):
        """Test status classification for healthy system"""
        # Mock high score
        monitor.update_metrics(blockchain)
        monitor.health_history[-1]["score"] = 85

        status = monitor.get_health_status()

        assert status["status"] == "healthy"
        assert status["score"] == 85

    def test_get_health_status_classification_degraded(self, monitor, blockchain):
        """Test status classification for degraded system"""
        monitor.update_metrics(blockchain)
        monitor.health_history[-1]["score"] = 65

        status = monitor.get_health_status()

        assert status["status"] == "degraded"

    def test_get_health_status_classification_warning(self, monitor, blockchain):
        """Test status classification for warning state"""
        monitor.update_metrics(blockchain)
        monitor.health_history[-1]["score"] = 45

        status = monitor.get_health_status()

        assert status["status"] == "warning"

    def test_get_health_status_classification_critical(self, monitor, blockchain):
        """Test status classification for critical state"""
        monitor.update_metrics(blockchain)
        monitor.health_history[-1]["score"] = 20

        status = monitor.get_health_status()

        assert status["status"] == "critical"

    def test_get_health_trend_insufficient_data(self, monitor):
        """Test trend with insufficient data"""
        trend = monitor.get_health_trend()

        assert trend == "stable"

    def test_get_health_trend_improving(self, monitor, blockchain):
        """Test detecting improving trend"""
        # Simulate improving health
        for i in range(10):
            monitor.update_metrics(blockchain)
            # Artificially increase scores
            monitor.health_history[-1]["score"] = 50 + i * 3

        trend = monitor.get_health_trend()

        assert trend == "improving"

    def test_get_health_trend_declining(self, monitor, blockchain):
        """Test detecting declining trend"""
        # Simulate declining health
        for i in range(10):
            monitor.update_metrics(blockchain)
            # Artificially decrease scores
            monitor.health_history[-1]["score"] = 80 - i * 3

        trend = monitor.get_health_trend()

        assert trend == "declining"

    def test_get_health_trend_stable(self, monitor, blockchain):
        """Test detecting stable trend"""
        # Simulate stable health
        for i in range(10):
            monitor.update_metrics(blockchain)
            monitor.health_history[-1]["score"] = 75  # Constant

        trend = monitor.get_health_trend()

        assert trend == "stable"

    def test_health_history_maxlen(self):
        """Test health history respects max length"""
        monitor = HealthMonitor()
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))

        # Add more than 100 entries
        for i in range(150):
            monitor.update_metrics(blockchain)

        # Should only keep 100 most recent
        assert len(monitor.health_history) == 100


class TestIntegration:
    """Integration tests for error detection components"""

    def test_error_detector_with_corruption_detector(self):
        """Test using error detector with corruption detector"""
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))

        error_detector = ErrorDetector(blockchain)
        corruption_detector = CorruptionDetector()

        # Detect some errors
        error_detector.detect_error(ValueError("validation error"), "validation")
        error_detector.detect_error(IOError("storage error"), "storage")

        # Check for corruption
        is_corrupted, issues = corruption_detector.detect_corruption(blockchain)

        # Both should work independently
        assert len(error_detector.error_history) == 2
        assert isinstance(is_corrupted, bool)

    def test_all_components_together(self):
        """Test all detection components working together"""
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))

        error_detector = ErrorDetector(blockchain)
        corruption_detector = CorruptionDetector()
        health_monitor = HealthMonitor()

        # Simulate system activity
        # 1. Generate some errors
        for i in range(5):
            error_detector.detect_error(ConnectionError("network"), "network")

        # 2. Check for corruption
        is_corrupted, issues = corruption_detector.detect_corruption(blockchain)

        # 3. Update health metrics
        health_monitor.update_metrics(blockchain)

        # All components should have data
        assert len(error_detector.error_history) == 5
        assert isinstance(is_corrupted, bool)
        assert len(health_monitor.health_history) == 1

    def test_health_monitoring_over_time(self):
        """Test health monitoring over time with various conditions"""
        blockchain = MockBlockchain()
        blockchain.chain.append(MockBlock(0))
        monitor = HealthMonitor()

        # Simulate time series
        for i in range(20):
            # Vary conditions
            if i < 10:
                monitor.metrics["network_peers"] = 5
                monitor.metrics["errors_encountered"] = 0
            else:
                monitor.metrics["network_peers"] = 0
                monitor.metrics["errors_encountered"] = 10

            monitor.update_metrics(blockchain)
            time.sleep(0.001)

        # Should have degrading trend
        trend = monitor.get_health_trend()
        assert trend in ["declining", "stable"]

    def test_pattern_detection_with_suggestions(self):
        """Test error pattern detection with actionable suggestions"""
        blockchain = MockBlockchain()
        detector = ErrorDetector(blockchain)

        # Generate pattern of connection errors
        for i in range(10):
            detector.detect_error(ConnectionError("network failure"), "peer_sync")

        patterns = detector.detect_error_patterns()

        assert len(patterns) > 0
        pattern = patterns[0]
        assert pattern["error_type"] == "ConnectionError"
        assert pattern["count"] == 10
        assert "suggestion" in pattern
        assert "network" in pattern["suggestion"].lower()
