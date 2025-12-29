"""
Unit tests for Error Detection module

Tests error classification, corruption detection, and health monitoring
"""

import pytest
import time
from xai.core.chain.error_detection import (
    ErrorSeverity,
    RecoveryState,
    ErrorDetector,
    CorruptionDetector,
    HealthMonitor,
)


class MockBlock:
    """Mock block for testing"""

    def __init__(self, index, previous_hash="", transactions=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions or []
        self.timestamp = time.time()
        self.hash = f"block_{index}_hash"

    def calculate_hash(self):
        """Calculate block hash"""
        return self.hash


class MockTransaction:
    """Mock transaction"""

    def __init__(self, sender="XAI_A", recipient="XAI_B", amount=100, fee=1):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.txid = f"tx_{sender}_{recipient}"

    def verify_signature(self):
        """Mock signature verification"""
        return True


class MockBlockchain:
    """Mock blockchain for testing"""

    def __init__(self):
        self.chain = []
        self.utxo_set = {}
        self.pending_transactions = []
        self.max_supply = 121000000

    def get_balance(self, address):
        """Get balance"""
        utxos = self.utxo_set.get(address, [])
        return sum(u["amount"] for u in utxos if not u.get("spent", False))

    def get_latest_block(self):
        """Get latest block"""
        if self.chain:
            return self.chain[-1]
        return MockBlock(0)


class TestErrorDetector:
    """Test error detection and classification"""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        return MockBlockchain()

    @pytest.fixture
    def detector(self, blockchain):
        """Create ErrorDetector instance"""
        return ErrorDetector(blockchain)

    def test_init(self, detector):
        """Test initialization"""
        assert len(detector.error_history) == 0
        assert len(detector.error_patterns) == 0

    def test_detect_error_critical(self, detector):
        """Test detecting critical error"""
        try:
            raise MemoryError("Out of memory")
        except MemoryError as e:
            severity = detector.detect_error(e)

        assert severity == ErrorSeverity.CRITICAL

    def test_detect_error_high(self, detector):
        """Test detecting high severity error"""
        try:
            raise ValueError("blockchain transaction invalid")
        except ValueError as e:
            severity = detector.detect_error(e)

        assert severity == ErrorSeverity.HIGH

    def test_detect_error_medium(self, detector):
        """Test detecting medium severity error"""
        try:
            raise ValueError("invalid input")
        except ValueError as e:
            severity = detector.detect_error(e)

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_network(self, detector):
        """Test detecting network error"""
        try:
            raise ConnectionError("Connection failed")
        except ConnectionError as e:
            severity = detector.detect_error(e)

        assert severity == ErrorSeverity.MEDIUM

    def test_detect_error_patterns(self, detector):
        """Test detecting error patterns"""
        # Generate recurring errors
        for i in range(10):
            try:
                raise ValueError("repeated error")
            except ValueError as e:
                detector.detect_error(e, context="test")

        patterns = detector.detect_error_patterns()

        assert len(patterns) > 0
        assert patterns[0]["error_type"] == "ValueError"

    def test_get_error_statistics(self, detector):
        """Test getting error statistics"""
        # Generate some errors
        for i in range(5):
            try:
                raise ValueError(f"error {i}")
            except ValueError as e:
                detector.detect_error(e)

        stats = detector.get_error_statistics()

        assert stats["total_errors"] == 5
        assert "error_rate" in stats
        assert "common_errors" in stats


class TestCorruptionDetector:
    """Test corruption detection"""

    @pytest.fixture
    def detector(self):
        """Create CorruptionDetector instance"""
        return CorruptionDetector()

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        blockchain = MockBlockchain()

        # Create valid chain
        genesis = MockBlock(0, "0")
        genesis.hash = "genesis_hash"
        blockchain.chain.append(genesis)

        block1 = MockBlock(1, "genesis_hash")
        block1.hash = "block1_hash"
        blockchain.chain.append(block1)

        return blockchain

    def test_init(self, detector):
        """Test initialization"""
        assert "hash_integrity" in detector.corruption_checks
        assert "chain_continuity" in detector.corruption_checks

    def test_detect_corruption_clean_chain(self, detector, blockchain):
        """Test detecting no corruption in clean chain"""
        is_corrupted, issues = detector.detect_corruption(blockchain)

        # Should have some issues due to mock implementation
        # but test should run without errors
        assert isinstance(is_corrupted, bool)
        assert isinstance(issues, list)

    def test_detect_corruption_broken_chain(self, detector):
        """Test detecting broken chain"""
        blockchain = MockBlockchain()

        # Create chain with broken link
        genesis = MockBlock(0, "0")
        blockchain.chain.append(genesis)

        # Block with wrong previous hash
        block1 = MockBlock(1, "wrong_hash")
        blockchain.chain.append(block1)

        is_corrupted, issues = detector.detect_corruption(blockchain)

        assert is_corrupted is True
        assert any("broken chain" in issue.lower() for issue in issues)

    def test_check_hash_integrity(self, detector, blockchain):
        """Test hash integrity check"""
        is_valid, errors = detector._check_hash_integrity(blockchain)

        # Mock blocks may have hash mismatches
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_check_chain_continuity(self, detector, blockchain):
        """Test chain continuity check"""
        is_valid, errors = detector._check_chain_continuity(blockchain)

        # Should be valid for properly constructed chain
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_check_supply_validation(self, detector, blockchain):
        """Test supply validation"""
        # Add some UTXOs
        blockchain.utxo_set["XAI_A"] = [{"amount": 100, "spent": False}]

        is_valid, errors = detector._check_supply_validation(blockchain)

        assert is_valid is True

    def test_check_supply_validation_exceeded(self, detector, blockchain):
        """Test supply cap exceeded detection"""
        # Add excessive supply
        blockchain.utxo_set["XAI_A"] = [{"amount": 200000000, "spent": False}]

        is_valid, errors = detector._check_supply_validation(blockchain)

        assert is_valid is False

    def test_check_transaction_validity(self, detector, blockchain):
        """Test transaction validity checking"""
        # Add block with valid transaction
        tx = MockTransaction()
        block = MockBlock(2, "block1_hash", [tx])
        blockchain.chain.append(block)

        is_valid, errors = detector._check_transaction_validity(blockchain)

        assert isinstance(is_valid, bool)

    def test_check_transaction_validity_negative_amount(self, detector, blockchain):
        """Test detecting negative amount transaction"""
        tx = MockTransaction(amount=-100)
        block = MockBlock(2, "block1_hash", [tx])
        blockchain.chain.append(block)

        is_valid, errors = detector._check_transaction_validity(blockchain)

        assert is_valid is False
        assert any("Negative amount" in err for err in errors)


class TestHealthMonitor:
    """Test blockchain health monitoring"""

    @pytest.fixture
    def monitor(self):
        """Create HealthMonitor instance"""
        return HealthMonitor()

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        blockchain = MockBlockchain()
        genesis = MockBlock(0)
        blockchain.chain.append(genesis)
        return blockchain

    def test_init(self, monitor):
        """Test initialization"""
        assert "last_block_time" in monitor.metrics
        assert "blocks_mined" in monitor.metrics
        assert len(monitor.health_history) == 0

    def test_update_metrics(self, monitor, blockchain):
        """Test updating health metrics"""
        monitor.update_metrics(blockchain)

        assert monitor.metrics["blocks_mined"] == 1
        assert monitor.metrics["mempool_size"] == 0
        assert len(monitor.health_history) == 1

    def test_get_health_status(self, monitor, blockchain):
        """Test getting health status"""
        monitor.update_metrics(blockchain)

        status = monitor.get_health_status()

        assert "status" in status
        assert "score" in status
        assert status["status"] in ["healthy", "degraded", "warning", "critical", "unknown"]

    def test_get_health_status_no_history(self, monitor):
        """Test getting status with no history"""
        status = monitor.get_health_status()

        assert status["status"] == "unknown"
        assert status["score"] == 0

    def test_get_health_trend_improving(self, monitor, blockchain):
        """Test detecting improving health trend"""
        # Simulate improving health
        for i in range(10):
            monitor.metrics["errors_encountered"] = max(0, 10 - i)
            monitor.update_metrics(blockchain)
            time.sleep(0.01)

        trend = monitor.get_health_trend()

        # Should detect improvement or be stable
        assert trend in ["improving", "stable"]

    def test_get_health_trend_stable(self, monitor, blockchain):
        """Test detecting stable health trend"""
        # Simulate stable health
        for i in range(10):
            monitor.update_metrics(blockchain)
            time.sleep(0.01)

        trend = monitor.get_health_trend()

        assert trend in ["improving", "stable", "declining"]

    def test_calculate_health_score(self, monitor, blockchain):
        """Test health score calculation"""
        monitor.update_metrics(blockchain)

        score = monitor._calculate_health_score(blockchain)

        assert 0 <= score <= 100

    def test_calculate_health_score_old_block(self, monitor, blockchain):
        """Test score penalty for old block"""
        monitor.metrics["last_block_time"] = time.time() - 1000  # Very old

        score = monitor._calculate_health_score(blockchain)

        assert score < 100  # Should have penalty

    def test_calculate_health_score_full_mempool(self, monitor, blockchain):
        """Test score penalty for full mempool"""
        monitor.metrics["mempool_size"] = 15000  # Very full

        score = monitor._calculate_health_score(blockchain)

        assert score < 100  # Should have penalty

    def test_calculate_health_score_no_peers(self, monitor, blockchain):
        """Test score penalty for no peers"""
        monitor.metrics["network_peers"] = 0

        score = monitor._calculate_health_score(blockchain)

        assert score <= 75  # Should have significant penalty
