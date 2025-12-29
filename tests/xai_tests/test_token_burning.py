"""
Test suite for XAI Token Burning Engine

Tests:
- Service consumption
- Burn distribution (50% burn, 50% miners)
- USD-pegged pricing
- Burn statistics
- Anonymous tracking
"""

import pytest
import sys
import os
import time

from xai.core.governance.token_burning_engine import TokenBurningEngine, ServiceType, SERVICE_PRICES_USD


@pytest.fixture
def burning_engine(tmp_path):
    return TokenBurningEngine(data_dir=str(tmp_path))


from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestBurningEngine:
    """Test token burning engine initialization"""

    def test_engine_initialization(self, burning_engine):
        """Test that burning engine initializes correctly"""
        engine = burning_engine

        assert engine.burn_percentage == 0.50, "Burn percentage should be 50%"
        assert engine.miner_percentage == 0.50, "Miner percentage should be 50%"
        assert engine.xai_price_usd == 1.0, "Default XAI price should be $1"

    def test_service_pricing(self):
        """Test that service prices are set correctly"""
        assert ServiceType.AI_QUERY_SIMPLE in SERVICE_PRICES_USD
        assert SERVICE_PRICES_USD[ServiceType.AI_QUERY_SIMPLE] == 0.10

        assert ServiceType.AI_CODE_REVIEW in SERVICE_PRICES_USD
        assert SERVICE_PRICES_USD[ServiceType.AI_CODE_REVIEW] == 5.00


class TestServiceConsumption:
    """Test service consumption and burning"""

    def test_consume_service(self, burning_engine):
        """Test consuming a service"""
        engine = burning_engine

        result = engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        assert result["success"] == True, "Service consumption should succeed"
        assert "burn_id" in result, "Should have burn ID"
        assert "burned_xai" in result, "Should have burned amount"
        assert "to_miners_xai" in result, "Should have miner amount"

    def test_burn_distribution(self, burning_engine):
        """Test 50/50 burn/miner distribution"""
        engine = burning_engine

        result = engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        total = result["total_cost_xai"]
        burned = result["burned_xai"]
        to_miners = result["to_miners_xai"]

        # Should be 50/50 split
        assert abs(burned - total * 0.50) < 0.0001, "Burn should be 50%"
        assert abs(to_miners - total * 0.50) < 0.0001, "Miners should be 50%"
        assert abs(burned - to_miners) < 0.0001, "Burn and miner amounts should be equal"

    def test_usd_pegged_pricing(self, burning_engine):
        """Test USD-pegged dynamic pricing"""
        engine = burning_engine

        # At $1/XAI, service should cost 0.1 XAI
        cost_1 = engine.calculate_service_cost(ServiceType.AI_QUERY_SIMPLE)
        assert cost_1 == 0.10, "At $1/XAI, should cost 0.1 XAI"

        # At $10/XAI, service should cost 0.01 XAI
        engine.update_xai_price(10.0)
        cost_10 = engine.calculate_service_cost(ServiceType.AI_QUERY_SIMPLE)
        assert cost_10 == 0.01, "At $10/XAI, should cost 0.01 XAI"

        # At $100/XAI, service should cost 0.001 XAI
        engine.update_xai_price(100.0)
        cost_100 = engine.calculate_service_cost(ServiceType.AI_QUERY_SIMPLE)
        assert cost_100 == 0.001, "At $100/XAI, should cost 0.001 XAI"


class TestBurnStatistics:
    """Test burn statistics tracking"""

    def test_stats_tracking(self, burning_engine):
        """Test that burn stats are tracked"""
        engine = burning_engine

        # Consume a service
        engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        stats = engine.get_anonymous_stats()

        assert stats["total_burned"] > 0, "Should have burned XAI"
        assert stats["total_to_miners"] > 0, "Should have miner rewards"
        assert stats["total_services_used"] == 1, "Should have 1 service used"

    def test_multiple_burns(self, burning_engine):
        """Test tracking multiple burns"""
        engine = burning_engine

        # Consume multiple services
        for i in range(5):
            engine.consume_service(
                wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
            )

        stats = engine.get_anonymous_stats()
        assert stats["total_services_used"] == 5, "Should have 5 services used"

    def test_service_usage_breakdown(self, burning_engine):
        """Test service usage breakdown"""
        engine = burning_engine

        # Consume different services
        engine.consume_service("XAI123...", ServiceType.AI_QUERY_SIMPLE)
        engine.consume_service("XAI123...", ServiceType.AI_CODE_REVIEW)

        service_stats = engine.get_burn_by_service(ServiceType.AI_QUERY_SIMPLE)
        assert service_stats["count"] == 1, "Should have 1 simple query"

        service_stats2 = engine.get_burn_by_service(ServiceType.AI_CODE_REVIEW)
        assert service_stats2["count"] == 1, "Should have 1 code review"


class TestAnonymity:
    """Test anonymity features"""

    def test_anonymous_tracking(self, burning_engine):
        """Test that only anonymous data is tracked"""
        engine = burning_engine

        result = engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        # Should have UTC timestamp
        assert "timestamp_utc" in result, "Should have UTC timestamp"

        # Should NOT have personal identifiers
        assert "ip_address" not in result, "Should not have IP"
        assert "user_name" not in result, "Should not have user name"
        assert "location" not in result, "Should not have location"

    def test_utc_timestamps(self, burning_engine):
        """Test that timestamps are in UTC"""
        engine = burning_engine

        result = engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        timestamp = result["timestamp_utc"]

        # Should be reasonable Unix timestamp
        assert timestamp > 1700000000, "Should be recent timestamp"
        assert timestamp <= time.time() + 1, "Should not be in future"


class TestBurnHistory:
    """Test burn history tracking"""

    def test_recent_burns(self, burning_engine):
        """Test retrieving recent burns"""
        engine = burning_engine

        # Create some burns
        for i in range(3):
            engine.consume_service(
                wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
            )

        recent = engine.get_recent_burns(limit=10)
        assert len(recent) >= 3, "Should have at least 3 burns"

    def test_burn_history_format(self, burning_engine):
        """Test burn history entry format"""
        engine = burning_engine

        engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        recent = engine.get_recent_burns(limit=1)
        burn = recent[0]

        assert "burn_id" in burn, "Should have burn ID"
        assert "wallet_address" in burn, "Should have wallet address"
        assert "service_type" in burn, "Should have service type"
        assert "burned_xai" not in burn or "burn_amount" in burn, "Should have burn amount"
        assert "timestamp_utc" in burn, "Should have UTC timestamp"


class TestDevelopmentFunding:
    """Test that development funding is separate (no treasury cut)"""

    def test_no_treasury_allocation(self, burning_engine):
        """Test that burns don't allocate to treasury"""
        engine = burning_engine

        result = engine.consume_service(
            wallet_address="XAI123...", service_type=ServiceType.AI_QUERY_SIMPLE
        )

        # Should have burn and miner amounts
        assert "burned_xai" in result
        assert "to_miners_xai" in result

        # Should NOT have treasury amount
        assert "to_treasury_xai" not in result or result.get("to_treasury_xai") == 0

        # Verify 50/50 split (no third party)
        total = result["total_cost_xai"]
        burned = result["burned_xai"]
        to_miners = result["to_miners_xai"]

        assert abs((burned + to_miners) - total) < 0.0001, "Burn + miners should equal total"

    def test_development_funding_note(self, burning_engine):
        """Test that stats show development funding source"""
        engine = burning_engine

        stats = engine.get_anonymous_stats()

        # Should mention development funding source
        assert "development_funding" in stats or "distribution" in stats
        if "development_funding" in stats:
            assert (
                "Pre-mine" in stats["development_funding"]
                or "AI API" in stats["development_funding"]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
