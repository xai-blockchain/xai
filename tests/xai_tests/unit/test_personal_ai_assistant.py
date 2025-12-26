"""
Comprehensive tests for Personal AI Assistant module.

Tests cover:
- MicroAssistantProfile data class and interaction recording
- MicroAssistantNetwork profile management and skill tracking
- PersonalAIAssistant rate limiting, caching, and AI operations
- Contract generation, atomic swaps, and blockchain analysis
"""

import time
from unittest.mock import MagicMock, patch

import pytest


class MockBlockchain:
    """Mock blockchain for testing PersonalAIAssistant."""

    def __init__(self):
        self.chain = [{"index": 0}, {"index": 1}, {"index": 2}]
        self._balances = {}

    def get_balance(self, address):
        return self._balances.get(address, 1000.0)

    def set_balance(self, address, balance):
        self._balances[address] = balance

    def get_stats(self):
        return {
            "blocks": len(self.chain),
            "pending_transactions": 5,
            "avg_fee": 0.001,
        }


class MockSafetyControls:
    """Mock safety controls for testing."""

    def __init__(self, allow_all=True):
        self.allow_all = allow_all
        self.registered_requests = {}

    def register_personal_ai_request(self, **kwargs):
        if not self.allow_all:
            return False
        request_id = kwargs.get("request_id")
        self.registered_requests[request_id] = kwargs
        return True

    def complete_personal_ai_request(self, request_id):
        self.registered_requests.pop(request_id, None)


# ============= MicroAssistantProfile Tests =============


class TestMicroAssistantProfile:
    """Tests for MicroAssistantProfile dataclass."""

    def test_profile_creation_with_defaults(self):
        """Test creating profile with default values."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantProfile

        profile = MicroAssistantProfile(
            name="TestAssistant",
            personality="friendly",
            skills=["skill1", "skill2"],
            description="A test assistant",
        )
        assert profile.name == "TestAssistant"
        assert profile.personality == "friendly"
        assert profile.skills == ["skill1", "skill2"]
        assert profile.description == "A test assistant"
        assert profile.usage_count == 0
        assert profile.tokens_consumed == 0
        assert profile.interactions == 0
        assert profile.satisfaction == 0.0

    def test_record_interaction_satisfied(self):
        """Test recording a satisfied interaction."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantProfile

        profile = MicroAssistantProfile(
            name="Test", personality="", skills=[], description=""
        )
        profile.record_interaction(100, satisfied=True)

        assert profile.usage_count == 1
        assert profile.interactions == 1
        assert profile.tokens_consumed == 100
        assert profile.satisfaction == 1.0

    def test_record_interaction_unsatisfied(self):
        """Test recording an unsatisfied interaction."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantProfile

        profile = MicroAssistantProfile(
            name="Test", personality="", skills=[], description=""
        )
        profile.record_interaction(50, satisfied=False)

        assert profile.usage_count == 1
        assert profile.satisfaction == 0.0

    def test_record_multiple_interactions_satisfaction_average(self):
        """Test that satisfaction is averaged across interactions."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantProfile

        profile = MicroAssistantProfile(
            name="Test", personality="", skills=[], description=""
        )

        profile.record_interaction(100, satisfied=True)  # 1.0
        profile.record_interaction(100, satisfied=True)  # 1.0
        profile.record_interaction(100, satisfied=False)  # 0.0
        profile.record_interaction(100, satisfied=False)  # 0.0

        assert profile.interactions == 4
        assert profile.satisfaction == 0.5  # (1+1+0+0)/4 = 0.5

    def test_record_interaction_updates_last_active(self):
        """Test that recording interaction updates last_active timestamp."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantProfile

        profile = MicroAssistantProfile(
            name="Test", personality="", skills=[], description=""
        )
        initial_time = profile.last_active
        time.sleep(0.01)
        profile.record_interaction(10, satisfied=True)

        assert profile.last_active > initial_time


# ============= MicroAssistantNetwork Tests =============


class TestMicroAssistantNetwork:
    """Tests for MicroAssistantNetwork class."""

    def test_default_profiles_seeded(self):
        """Test that default profiles are created on init."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()

        assert len(network.assistants) == 3
        assert "guiding mentor" in network.assistants
        assert "trading sage" in network.assistants
        assert "safety overseer" in network.assistants

    def test_list_profiles_returns_all_profiles(self):
        """Test listing all profiles with their details."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()
        profiles = network.list_profiles()

        assert len(profiles) == 3
        profile_names = [p["name"] for p in profiles]
        assert "Guiding Mentor" in profile_names
        assert "Trading Sage" in profile_names
        assert "Safety Overseer" in profile_names

    def test_select_profile_by_name(self):
        """Test selecting a profile by name."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()

        profile = network.select_profile("Trading Sage")
        assert profile.name == "Trading Sage"

        profile = network.select_profile("safety overseer")
        assert profile.name == "Safety Overseer"

    def test_select_profile_default_on_invalid(self):
        """Test that invalid names return default profile."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()

        profile = network.select_profile("nonexistent")
        assert profile.name == "Guiding Mentor"

        profile = network.select_profile(None)
        assert profile.name == "Guiding Mentor"

    def test_record_skill_usage(self):
        """Test that skill usage is tracked."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()
        profile = network.select_profile("Trading Sage")

        network.record_skill_usage(profile)

        assert network.skill_popularity["swaps"] == 1
        assert network.skill_popularity["liquidity"] == 1
        assert network.skill_popularity["market analysis"] == 1

    def test_record_interaction_updates_aggregates(self):
        """Test that record_interaction updates aggregate metrics."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()
        profile = network.select_profile("Guiding Mentor")

        network.record_interaction(profile, tokens=150, satisfied=True)

        assert network.aggregate_tokens == 150
        assert network.aggregate_requests == 1
        assert profile.tokens_consumed == 150

    def test_get_aggregate_metrics(self):
        """Test getting aggregate metrics including trending skills."""
        from xai.ai.ai_assistant.personal_ai_assistant import MicroAssistantNetwork

        network = MicroAssistantNetwork()

        mentor = network.select_profile("Guiding Mentor")
        trader = network.select_profile("Trading Sage")

        network.record_interaction(mentor, 100, True)
        network.record_interaction(trader, 200, True)
        network.record_interaction(trader, 150, True)

        metrics = network.get_aggregate_metrics()

        assert metrics["total_requests"] == 3
        assert metrics["total_tokens"] == 450
        assert len(metrics["trending_skills"]) <= 3


# ============= PersonalAIAssistant Tests =============


class TestPersonalAIAssistant:
    """Tests for PersonalAIAssistant class."""

    @pytest.fixture
    def assistant(self):
        """Create a PersonalAIAssistant instance for testing."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        safety = MockSafetyControls()
        return PersonalAIAssistant(blockchain, safety)

    def test_init_creates_micro_network(self, assistant):
        """Test that initialization creates micro network."""
        assert assistant.micro_network is not None
        assert len(assistant.micro_network.assistants) == 3

    def test_normalize_provider_aliases(self, assistant):
        """Test provider name normalization."""
        assert assistant._normalize_provider("grok") == "xai"
        assert assistant._normalize_provider("XAI") == "xai"
        assert assistant._normalize_provider("togetherai") == "together"
        assert assistant._normalize_provider("openai") == "openai"
        assert assistant._normalize_provider(None) == "openai"
        assert assistant._normalize_provider("  OPENAI  ") == "openai"

    def test_generate_request_id_format(self, assistant):
        """Test that request IDs have correct format."""
        request_id = assistant._generate_request_id()
        assert request_id.startswith("personal-ai-")
        parts = request_id.split("-")
        assert len(parts) >= 4

    def test_check_rate_limit_allows_first_request(self, assistant):
        """Test that first request is allowed."""
        allowed, info = assistant._check_rate_limit("0xUser1")
        assert allowed is True
        assert "current_usage" in info

    def test_check_rate_limit_respects_hourly_limit(self, assistant):
        """Test hourly rate limit enforcement."""
        user = "0xRateLimitTest"

        for i in range(100):
            allowed, _ = assistant._check_rate_limit(user)
            if allowed:
                assistant._record_usage(user, time.time())

        allowed, info = assistant._check_rate_limit(user)
        assert allowed is False
        assert info["error"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in info

    def test_record_usage_adds_to_all_windows(self, assistant):
        """Test that usage is recorded in all time windows."""
        user = "0xRecordTest"
        now = time.time()
        assistant._record_usage(user, now)

        stats = assistant.user_usage[user.upper()]
        assert len(stats["hour"]) == 1
        assert len(stats["day"]) == 1
        assert len(stats["month"]) == 1

    def test_build_cache_key_unique_per_prompt(self, assistant):
        """Test cache key generation uniqueness."""
        key1 = assistant._build_cache_key("openai", "gpt-4", "prompt one")
        key2 = assistant._build_cache_key("openai", "gpt-4", "prompt two")
        key3 = assistant._build_cache_key("openai", "gpt-4", "prompt one")

        assert key1 != key2
        assert key1 == key3

    def test_cache_ttl_zero_disables_caching(self, assistant):
        """Test that zero TTL disables caching."""
        assistant._cache_ttl = 0
        key = "test_key"
        result = {"success": True, "text": "cached"}

        assistant._store_cached_response(key, result)
        cached = assistant._get_cached_response(key)

        assert cached is None

    def test_cache_stores_and_retrieves(self, assistant):
        """Test cache storage and retrieval."""
        key = "test_cache_key"
        result = {"success": True, "text": "test response"}

        assistant._store_cached_response(key, result)
        cached = assistant._get_cached_response(key)

        assert cached is not None
        assert cached["text"] == "test response"
        assert cached.get("cached") is True

    def test_cache_expires_after_ttl(self, assistant):
        """Test that cache entries expire."""
        assistant._cache_ttl = 0.01
        key = "expiring_key"
        result = {"success": True, "text": "expiring"}

        assistant._store_cached_response(key, result)
        time.sleep(0.02)
        cached = assistant._get_cached_response(key)

        assert cached is None

    def test_cache_evicts_oldest_when_full(self, assistant):
        """Test cache eviction when max entries reached."""
        assistant._cache_max_entries = 3

        for i in range(4):
            key = f"key_{i}"
            result = {"success": True, "text": f"response_{i}"}
            assistant._store_cached_response(key, result)
            time.sleep(0.01)

        assert len(assistant._response_cache) == 3
        assert assistant._get_cached_response("key_0") is None

    def test_get_exchange_rate_default_values(self, assistant):
        """Test exchange rate calculation with default values."""
        rate = assistant._get_exchange_rate("XAI", "XAI")
        assert rate == 1.0

        rate = assistant._get_exchange_rate("BTC", "XAI")
        assert rate == 40000.0

        rate = assistant._get_exchange_rate("ETH", "BTC")
        expected = 1800.0 / 40000.0
        assert abs(rate - expected) < 0.0001

    def test_get_exchange_rate_caches_result(self, assistant):
        """Test that exchange rates are cached."""
        rate1 = assistant._get_exchange_rate("ETH", "XAI")
        rate2 = assistant._get_exchange_rate("ETH", "XAI")

        assert rate1 == rate2
        assert "ETH-XAI" in assistant.rate_cache

    def test_estimate_ai_cost_minimum_tokens(self, assistant):
        """Test AI cost estimation with minimum tokens."""
        short_prompt = "Hi"
        cost = assistant._estimate_ai_cost(short_prompt)

        assert cost["tokens_used"] >= 150
        assert cost["estimated_usd"] > 0

    def test_estimate_ai_cost_scales_with_length(self, assistant):
        """Test AI cost scales with prompt length."""
        short_cost = assistant._estimate_ai_cost("short prompt")
        long_cost = assistant._estimate_ai_cost("a" * 900)

        assert long_cost["tokens_used"] > short_cost["tokens_used"]

    def test_list_micro_assistants(self, assistant):
        """Test listing micro assistants."""
        result = assistant.list_micro_assistants()

        assert "profiles" in result
        assert "aggregated_metrics" in result
        assert len(result["profiles"]) == 3


class TestPersonalAIAssistantContractGeneration:
    """Tests for contract generation functionality."""

    @pytest.fixture
    def assistant(self):
        """Create a PersonalAIAssistant instance for testing."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        return PersonalAIAssistant(blockchain)

    def test_generate_escrow_contract_template(self, assistant):
        """Test escrow contract template generation."""
        template = assistant._generate_contract_template("escrow", "Basic escrow")
        assert "EscrowContract" in template
        assert "buyer" in template
        assert "seller" in template
        assert "buyer_confirm" in template
        assert "cancel" in template

    def test_generate_auction_contract_template(self, assistant):
        """Test auction contract template generation."""
        template = assistant._generate_contract_template("auction", "NFT auction")
        assert "AuctionContract" in template
        assert "bid" in template
        assert "highest_bid" in template
        assert "close" in template

    def test_generate_token_contract_template(self, assistant):
        """Test token contract template generation."""
        template = assistant._generate_contract_template("token", "Custom token")
        assert "TokenContract" in template
        assert "mint" in template
        assert "transfer" in template
        assert "balances" in template

    def test_generate_crowdfund_contract_template(self, assistant):
        """Test crowdfund contract template generation."""
        template = assistant._generate_contract_template("crowdfund", "Project funding")
        assert "CrowdfundContract" in template
        assert "contribute" in template
        assert "target" in template
        assert "deadline" in template

    def test_generate_lottery_contract_template(self, assistant):
        """Test lottery contract template generation."""
        template = assistant._generate_contract_template("lottery", "Weekly lottery")
        assert "LotteryContract" in template
        assert "buy_ticket" in template
        assert "draw" in template

    def test_generate_voting_contract_template(self, assistant):
        """Test voting contract template generation."""
        template = assistant._generate_contract_template("voting", "DAO vote")
        assert "VotingContract" in template
        assert "vote" in template
        assert "proposals" in template

    def test_generate_unknown_contract_type_returns_custom(self, assistant):
        """Test unknown contract type returns custom template."""
        template = assistant._generate_contract_template("unknown_type", "Custom desc")
        assert "CustomContract" in template
        assert "execute" in template


class TestPersonalAIAssistantAtomicSwap:
    """Tests for atomic swap functionality."""

    @pytest.fixture
    def assistant(self):
        """Create a PersonalAIAssistant instance for testing."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        return PersonalAIAssistant(blockchain)

    def test_build_atomic_swap_prompt(self, assistant):
        """Test atomic swap prompt building."""
        prompt = assistant._build_atomic_swap_prompt(
            user_address="0xUser",
            from_coin="XAI",
            to_coin="ETH",
            amount=100.0,
            swap_details={"recipient_address": "0xRecipient", "notes": "Test swap"},
            rate=0.0005,
        )

        assert "0xUser" in prompt
        assert "100" in prompt
        assert "XAI" in prompt
        assert "ETH" in prompt
        assert "0xRecipient" in prompt
        assert "Test swap" in prompt
        assert "HTLC" in prompt

    def test_execute_atomic_swap_missing_fields(self, assistant):
        """Test atomic swap with missing required fields."""
        result = assistant.execute_atomic_swap_with_ai(
            user_address="0xUser",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            swap_details={"from_coin": "XAI"},  # Missing to_coin and amount
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_SWAP_DETAILS"

    def test_execute_atomic_swap_invalid_amount(self, assistant):
        """Test atomic swap with invalid amount."""
        result = assistant.execute_atomic_swap_with_ai(
            user_address="0xUser",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            swap_details={
                "from_coin": "XAI",
                "to_coin": "ETH",
                "amount": "not_a_number",
            },
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_AMOUNT"


class TestPersonalAIAssistantSafetyControls:
    """Tests for safety controls integration."""

    def test_safety_controls_block_request(self):
        """Test that safety controls can block requests."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        safety = MockSafetyControls(allow_all=False)
        assistant = PersonalAIAssistant(blockchain, safety)

        result = assistant.analyze_blockchain_with_ai(
            user_address="0xUser",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            query="What is my balance?",
        )

        assert result["success"] is False
        assert result["error"] == "AI_SAFETY_STOP_ACTIVE"

    def test_safety_controls_allow_with_env_override(self):
        """Test safety controls can be overridden via environment."""
        import os
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        safety = MockSafetyControls(allow_all=False)
        assistant = PersonalAIAssistant(blockchain, safety)

        os.environ["PERSONAL_AI_ALLOW_UNSAFE"] = "1"
        try:
            allowed = assistant._should_ignore_safety_controls()
            assert allowed is True
        finally:
            del os.environ["PERSONAL_AI_ALLOW_UNSAFE"]


class TestPersonalAIAssistantWebhook:
    """Tests for webhook notifications."""

    @pytest.fixture
    def assistant_with_webhook(self):
        """Create assistant with webhook configured."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        return PersonalAIAssistant(
            blockchain, webhook_url="http://localhost:8000/webhook"
        )

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_notify_webhook_sends_post(self, mock_requests, assistant_with_webhook):
        """Test webhook notification sends POST request."""
        assistant_with_webhook._notify_webhook(
            "test_event", {"user": "0xTest", "action": "test"}
        )

        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args[1]["json"]["event"] == "test_event"
        assert call_args[1]["json"]["payload"]["user"] == "0xTest"

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests", None)
    def test_notify_webhook_handles_missing_requests(self, assistant_with_webhook):
        """Test webhook gracefully handles missing requests module."""
        assistant_with_webhook._notify_webhook("event", {})


class TestPersonalAIAssistantWalletAnalysis:
    """Tests for wallet analysis functionality."""

    @pytest.fixture
    def assistant(self):
        """Create a PersonalAIAssistant instance for testing."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        return PersonalAIAssistant(blockchain)

    def test_wallet_analysis_returns_portfolio(self, assistant):
        """Test wallet analysis returns portfolio data."""
        result = assistant.wallet_analysis_with_ai(
            user_address="0xWallet",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            analysis_type="full",
        )

        assert result["success"] is True
        assert "portfolio_analysis" in result
        assert "current_holdings" in result["portfolio_analysis"]
        assert "recommendations" in result["portfolio_analysis"]
        assert "transaction_patterns" in result

    def test_wallet_analysis_with_assistant_profile(self, assistant):
        """Test wallet analysis with specific assistant profile."""
        result = assistant.wallet_analysis_with_ai(
            user_address="0xWallet",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            analysis_type="risk",
            assistant_name="Safety Overseer",
        )

        assert result["success"] is True
        assert result["assistant_profile"]["name"] == "Safety Overseer"


class TestPersonalAIAssistantOptimization:
    """Tests for transaction optimization functionality."""

    @pytest.fixture
    def assistant(self):
        """Create a PersonalAIAssistant instance for testing."""
        from xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

        blockchain = MockBlockchain()
        return PersonalAIAssistant(blockchain)

    def test_optimize_transaction_reduces_fee(self, assistant):
        """Test that optimization reduces transaction fee."""
        original_fee = 0.1
        result = assistant.optimize_transaction_with_ai(
            user_address="0xUser",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            transaction={"amount": 100, "fee": original_fee},
        )

        assert result["success"] is True
        assert result["savings"]["optimized_fee"] < original_fee
        assert result["savings"]["saved"] > 0
        assert "recommendations" in result

    def test_optimize_transaction_respects_minimum_fee(self, assistant):
        """Test optimization respects minimum fee."""
        result = assistant.optimize_transaction_with_ai(
            user_address="0xUser",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            transaction={"amount": 100, "fee": 0.0001},
        )

        assert result["success"] is True
        min_fee = getattr(assistant.blockchain, "min_fee", 0.0001)
        assert result["optimized_transaction"]["fee"] >= min_fee


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
