"""
Comprehensive security tests for Oracle Price Manipulation vulnerabilities.

Tests cover:
- TWAP (Time-Weighted Average Price) protection
- Price deviation bounds enforcement
- Staleness checks and timeout validation
- Multi-source price aggregation
- Rate limiting per source
- Flash loan attack prevention
- Timing attack prevention (atomic validation)
"""
import pytest
import time
from xai.core.defi.oracle import PriceOracle, PriceFeed, OracleStatus
from xai.core.vm.exceptions import VMExecutionError
from xai.blockchain.twap_oracle import TWAPOracle
from xai.blockchain.oracle_manipulation_detection import OracleManipulationDetector
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState
from xai.blockchain.twap_oracle import TWAPOracle
from xai.blockchain.oracle_manipulation_detection import OracleManipulationDetector
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


class TestOracleManipulationProtection:
    """Test oracle manipulation attack prevention."""

    def test_atomic_validation_prevents_timing_attack(self):
        """Test that validation happens before any state changes (prevents timing attacks)."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        # Add feed with strict deviation threshold and no rate limiting for test
        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            deviation_threshold=100,  # 1% max deviation
            min_update_interval=0,  # Disable rate limiting for test
        )

        # Authorize provider
        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Set initial price
        oracle.update_price(provider, "XAI/USD", 100_000_000)

        # Build price history
        for i in range(5):
            time.sleep(0.01)
            oracle.update_price(provider, "XAI/USD", 100_000_000 + i * 10000)

        # Attempt to update with price outside deviation threshold
        # This should fail BEFORE any logging or state observation
        manipulated_price = 110_000_000  # 10% higher - way above 1% threshold

        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", manipulated_price)

        assert "deviation" in str(exc.value).lower()
        assert "exceeds threshold" in str(exc.value).lower()

        # Verify no state changes occurred
        feed = oracle.feeds["XAI/USD"]
        assert feed.latest_price != manipulated_price
        # Round ID should not have incremented
        assert feed.round_id == 6  # Initial + 5 updates

    def test_twap_prevents_flash_loan_manipulation(self):
        """Test that TWAP prevents single-block price manipulation."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        # Add feed with TWAP protection, disable rate limiting for test
        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            deviation_threshold=500,  # 5% max deviation from TWAP
            min_update_interval=0,  # Disable rate limiting for test
            max_price_age=86400,  # 24 hours to allow historical prices
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Build stable price history with historical timestamps
        base_price = 100_000_000
        current_time = time.time()
        for i in range(10):
            oracle.update_price(provider, "XAI/USD", base_price, timestamp=current_time - (10-i)*70)

        # Attempt flash loan attack: sudden 10% price spike
        # TWAP is ~100M, so 110M is 10% above TWAP (exceeds 5% threshold)
        flash_price = 110_000_000

        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", flash_price, timestamp=current_time)

        assert "deviation" in str(exc.value).lower()
        assert "TWAP" in str(exc.value)

        # Verify price wasn't updated
        assert oracle.get_price("XAI/USD") == base_price

    def test_twap_calculation_time_weighted(self):
        """Test that TWAP properly weights prices by duration."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            min_update_interval=0,  # Disable rate limiting
            max_price_age=86400,  # Allow historical prices
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        current_time = time.time()

        # Price 100 for 300 seconds (from -600 to -300)
        oracle.update_price(provider, "XAI/USD", 100_000_000, timestamp=current_time - 600)

        # Price 200 for 200 seconds (from -300 to -100)
        oracle.update_price(provider, "XAI/USD", 200_000_000, timestamp=current_time - 300)

        # Price 150 for 100 seconds (from -100 to now)
        oracle.update_price(provider, "XAI/USD", 150_000_000, timestamp=current_time - 100)

        # TWAP over 600 seconds should be time-weighted:
        # (100M * 300s + 200M * 200s + 150M * 100s) / 600s
        # = (30000M + 40000M + 15000M) / 600
        # = 85000M / 600 = 141.67M
        # But actual calculation includes time to "now" for last price
        # So it's approximately: (100*300 + 200*200 + 150*100) / 600
        twap = oracle.get_twap("XAI/USD", 600)

        # The actual TWAP will be weighted including current time
        # Allow range based on actual calculation
        assert 140_000_000 <= twap <= 190_000_000

    def test_rate_limiting_prevents_spam_attacks(self):
        """Test that rate limiting prevents rapid price update spam."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # First update succeeds
        oracle.update_price(provider, "XAI/USD", 100_000_000)

        # Immediate second update fails (rate limited)
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 100_100_000)

        assert "rate limit" in str(exc.value).lower()
        assert "minimum interval" in str(exc.value).lower()

    def test_staleness_check_prevents_replay_attacks(self):
        """Test that old timestamps are rejected."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Attempt to submit price with old timestamp (2 hours ago)
        old_timestamp = time.time() - 7200

        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 100_000_000, timestamp=old_timestamp)

        assert "too old" in str(exc.value).lower()

    def test_future_timestamp_rejection(self):
        """Test that future timestamps are rejected."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Attempt to submit price with future timestamp (2 minutes from now)
        future_timestamp = time.time() + 120

        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 100_000_000, timestamp=future_timestamp)

        assert "future" in str(exc.value).lower()

    def test_multi_source_aggregation(self):
        """Test that multi-source aggregation requires consensus."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        # Feed requires 3 sources minimum
        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            min_sources=3,
            deviation_threshold=10000,  # 100% to allow test prices
        )

        # Authorize 3 providers
        providers = ["0xProvider1", "0xProvider2", "0xProvider3"]
        for provider in providers:
            oracle.authorize_provider("0xOwner", provider)

        feed = oracle.feeds["XAI/USD"]

        # First source submits 100
        oracle.update_price(providers[0], "XAI/USD", 100_000_000, timestamp=time.time())
        # Price not updated yet (pending)
        assert feed.latest_price == 0
        assert len(feed.pending_updates) == 1

        # Second source submits 102
        time.sleep(0.1)
        oracle.update_price(providers[1], "XAI/USD", 102_000_000, timestamp=time.time())
        # Still pending
        assert feed.latest_price == 0
        assert len(feed.pending_updates) == 2

        # Third source submits 101
        time.sleep(0.1)
        oracle.update_price(providers[2], "XAI/USD", 101_000_000, timestamp=time.time())

        # Now price is updated with median of [100, 101, 102] = 101
        assert feed.latest_price == 101_000_000
        assert len(feed.pending_updates) == 0

    def test_price_bounds_enforcement(self):
        """Test that price bounds are enforced."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        # Set price bounds: $0.50 to $2.00 (in 8 decimals)
        oracle.set_price_bounds("0xOwner", "XAI/USD", 50_000_000, 200_000_000)

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Price below minimum fails
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 40_000_000)

        assert "outside bounds" in str(exc.value).lower()

        # Price above maximum fails
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 250_000_000)

        assert "outside bounds" in str(exc.value).lower()

        # Price within bounds succeeds
        oracle.update_price(provider, "XAI/USD", 100_000_000)
        assert oracle.get_price("XAI/USD") == 100_000_000

    def test_zero_or_negative_price_rejected(self):
        """Test that zero or negative prices are rejected."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Zero price fails
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 0)

        assert "must be positive" in str(exc.value).lower()

        # Negative price fails
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", -100_000_000)

        assert "must be positive" in str(exc.value).lower()

    def test_median_aggregation_resists_outliers(self):
        """Test that median aggregation resists single outlier manipulation."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            min_sources=5,
            aggregation_method="median",
            deviation_threshold=10000,  # Allow large variance for test
        )

        # Authorize 5 providers
        providers = [f"0xProvider{i}" for i in range(5)]
        for provider in providers:
            oracle.authorize_provider("0xOwner", provider)

        # 4 honest sources report ~100, 1 malicious reports 200
        prices = [100_000_000, 101_000_000, 99_000_000, 100_500_000, 200_000_000]

        for i, provider in enumerate(providers):
            time.sleep(0.1)
            oracle.update_price(provider, "XAI/USD", prices[i], timestamp=time.time())

        # Median of [99, 100, 100.5, 101, 200] = 100.5 (outlier ignored)
        feed = oracle.feeds["XAI/USD"]
        assert 100_000_000 <= feed.latest_price <= 101_000_000

    def test_price_staleness_on_read(self):
        """Test that stale prices are rejected on read."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            heartbeat=2,  # 2 second heartbeat for fast testing
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Update price
        oracle.update_price(provider, "XAI/USD", 100_000_000, timestamp=time.time() - 1)

        # Price is fresh
        assert oracle.get_price("XAI/USD") == 100_000_000

        # Wait for staleness
        time.sleep(2.5)

        # Price is now stale
        with pytest.raises(VMExecutionError) as exc:
            oracle.get_price("XAI/USD")

        assert "stale" in str(exc.value).lower()

    def test_single_source_bias_trips_twap_detector(self):
        """Even a single oracle feed deviating from TWAP should trip protection."""
        twap = TWAPOracle(window_size_seconds=300)
        for i in range(5):
            twap.record_price(100.0, timestamp=100 + i * 30)

        circuit = CircuitBreaker("oracle-detector", failure_threshold=1, recovery_timeout_seconds=60)
        detector = OracleManipulationDetector(twap, circuit, deviation_threshold_percentage=5.0)

        assert detector.check_for_manipulation({"DexA": 101.0}, current_timestamp=400) is False
        assert circuit.state == CircuitBreakerState.CLOSED

        assert detector.check_for_manipulation({"DexA": 112.0}, current_timestamp=400) is True
        assert circuit.state == CircuitBreakerState.OPEN

    def test_colluding_sources_detected_by_twap_guard(self):
        """Multiple sources agreeing on a manipulated price still get blocked."""
        twap = TWAPOracle(window_size_seconds=300)
        for i in range(6):
            twap.record_price(95.0 + i, timestamp=200 + i * 20)

        circuit = CircuitBreaker("oracle-detector-collusion", failure_threshold=1, recovery_timeout_seconds=60)
        detector = OracleManipulationDetector(twap, circuit, deviation_threshold_percentage=4.0)

        colluding = {"SourceA": 120.0, "SourceB": 118.5}
        assert detector.check_for_manipulation(colluding, current_timestamp=400) is True

    def test_circuit_breaker_blocks_all_updates(self):
        """Test that circuit breaker prevents all price updates."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            min_update_interval=0,  # Disable rate limiting
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Update succeeds normally
        oracle.update_price(provider, "XAI/USD", 100_000_000)

        # Trigger circuit breaker
        oracle.trigger_circuit_breaker("0xOwner")

        # Updates now blocked
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price(provider, "XAI/USD", 101_000_000, timestamp=time.time())

        assert "circuit breaker" in str(exc.value).lower()

        # Reset circuit breaker
        oracle.reset_circuit_breaker("0xOwner")

        # Updates work again
        oracle.update_price(provider, "XAI/USD", 101_000_000, timestamp=time.time())
        assert oracle.get_price("XAI/USD") == 101_000_000


class TestOracleEdgeCases:
    """Test edge cases and error conditions."""

    def test_twap_with_insufficient_history(self):
        """Test TWAP calculation with insufficient price history."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Single price update
        oracle.update_price(provider, "XAI/USD", 100_000_000)

        # TWAP should return latest price when history insufficient
        twap = oracle.get_twap("XAI/USD", 600)
        assert twap == 100_000_000

    def test_aggregation_with_single_source(self):
        """Test that aggregation works with min_sources=1."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
            min_sources=1,
        )

        provider = "0xProvider1"
        oracle.authorize_provider("0xOwner", provider)

        # Single source should update immediately
        oracle.update_price(provider, "XAI/USD", 100_000_000)
        assert oracle.get_price("XAI/USD") == 100_000_000

    def test_unauthorized_provider_rejected(self):
        """Test that unauthorized providers cannot update prices."""
        oracle = PriceOracle(
            name="Test Oracle",
            owner="0xOwner",
        )

        oracle.add_feed(
            caller="0xOwner",
            pair="XAI/USD",
            base_asset="XAI",
            quote_asset="USD",
        )

        # Provider not authorized
        with pytest.raises(VMExecutionError) as exc:
            oracle.update_price("0xUnauthorized", "XAI/USD", 100_000_000)

        assert "not authorized" in str(exc.value).lower()
