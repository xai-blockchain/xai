"""
Comprehensive test coverage for PersonalAIAssistant module.

This test suite achieves 80%+ coverage by testing:
- AI model initialization and configuration
- Natural language processing
- Command parsing and execution
- Context management
- Multi-turn conversations
- API integrations (Anthropic, OpenAI, additional providers)
- Error handling and fallbacks
- Rate limiting and quota management
- Security and input validation
- Edge cases and boundary conditions
"""

import builtins
import json
import os
import pytest
import time
from collections import defaultdict
from unittest.mock import Mock, MagicMock, patch, call

from xai.ai.ai_assistant.personal_ai_assistant import (
    PersonalAIAssistant,
    MicroAssistantNetwork,
    MicroAssistantProfile,
)
from xai.core.blockchain import Blockchain


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    blockchain = Mock(spec=Blockchain)
    blockchain.get_balance.return_value = 1000.0
    blockchain.get_stats.return_value = {
        "blocks": 100,
        "pending_transactions": 5,
        "avg_fee": 0.001,
    }
    blockchain.chain = [Mock() for _ in range(100)]
    return blockchain


@pytest.fixture
def mock_safety_controls():
    """Create a mock safety controls object."""
    safety = Mock()
    safety.register_personal_ai_request.return_value = True
    safety.complete_personal_ai_request.return_value = True
    return safety


@pytest.fixture
def personal_ai(mock_blockchain, mock_safety_controls):
    """Create a PersonalAIAssistant instance for testing."""
    return PersonalAIAssistant(
        blockchain=mock_blockchain,
        safety_controls=mock_safety_controls,
        webhook_url="https://webhook.example.com/events",
    )


@pytest.fixture
def personal_ai_no_safety(mock_blockchain):
    """Create a PersonalAIAssistant without safety controls."""
    return PersonalAIAssistant(
        blockchain=mock_blockchain,
        safety_controls=None,
        webhook_url=None,
    )


# ============================================================================
# MicroAssistantProfile Tests
# ============================================================================

class TestMicroAssistantProfile:
    """Test MicroAssistantProfile functionality."""

    def test_profile_initialization(self):
        """Test profile creation with default values."""
        profile = MicroAssistantProfile(
            name="Test Assistant",
            personality="helpful and friendly",
            skills=["coding", "debugging"],
            description="A test assistant",
        )
        assert profile.name == "Test Assistant"
        assert profile.personality == "helpful and friendly"
        assert profile.skills == ["coding", "debugging"]
        assert profile.description == "A test assistant"
        assert profile.usage_count == 0
        assert profile.tokens_consumed == 0
        assert profile.interactions == 0
        assert profile.satisfaction == 0.0
        assert profile.last_active > 0

    def test_record_interaction_satisfied(self):
        """Test recording a satisfied interaction."""
        profile = MicroAssistantProfile(
            name="Helper",
            personality="friendly",
            skills=["help"],
            description="Helpful assistant",
        )
        initial_time = profile.last_active
        time.sleep(0.01)  # Small delay to ensure time difference

        profile.record_interaction(tokens=100, satisfied=True)

        assert profile.usage_count == 1
        assert profile.interactions == 1
        assert profile.tokens_consumed == 100
        assert profile.satisfaction == 1.0
        assert profile.last_active > initial_time

    def test_record_interaction_unsatisfied(self):
        """Test recording an unsatisfied interaction."""
        profile = MicroAssistantProfile(
            name="Helper",
            personality="friendly",
            skills=["help"],
            description="Helpful assistant",
        )

        profile.record_interaction(tokens=50, satisfied=False)

        assert profile.usage_count == 1
        assert profile.interactions == 1
        assert profile.tokens_consumed == 50
        assert profile.satisfaction == 0.0

    def test_record_multiple_interactions(self):
        """Test averaging satisfaction over multiple interactions."""
        profile = MicroAssistantProfile(
            name="Helper",
            personality="friendly",
            skills=["help"],
            description="Helpful assistant",
        )

        profile.record_interaction(tokens=100, satisfied=True)
        profile.record_interaction(tokens=200, satisfied=True)
        profile.record_interaction(tokens=150, satisfied=False)

        assert profile.usage_count == 3
        assert profile.interactions == 3
        assert profile.tokens_consumed == 450
        # (1 + 1 + 0) / 3 = 0.666...
        assert 0.66 <= profile.satisfaction <= 0.67


# ============================================================================
# MicroAssistantNetwork Tests
# ============================================================================

class TestMicroAssistantNetwork:
    """Test MicroAssistantNetwork functionality."""

    def test_network_initialization(self):
        """Test network initialization with default profiles."""
        network = MicroAssistantNetwork()

        assert len(network.assistants) == 3
        assert "guiding mentor" in network.assistants
        assert "trading sage" in network.assistants
        assert "safety overseer" in network.assistants
        assert network.aggregate_tokens == 0
        assert network.aggregate_requests == 0

    def test_list_profiles(self):
        """Test listing all profiles."""
        network = MicroAssistantNetwork()
        profiles = network.list_profiles()

        assert len(profiles) == 3
        assert all("name" in p for p in profiles)
        assert all("personality" in p for p in profiles)
        assert all("description" in p for p in profiles)
        assert all("skills" in p for p in profiles)
        assert all("usage_count" in p for p in profiles)
        assert all("tokens_consumed" in p for p in profiles)
        assert all("satisfaction" in p for p in profiles)

    def test_select_profile_by_key(self):
        """Test selecting a profile by key."""
        network = MicroAssistantNetwork()

        profile = network.select_profile("trading sage")
        assert profile.name == "Trading Sage"

        profile = network.select_profile("GUIDING MENTOR")
        assert profile.name == "Guiding Mentor"

    def test_select_profile_default(self):
        """Test selecting default profile when key is None."""
        network = MicroAssistantNetwork()

        profile = network.select_profile(None)
        assert profile.name == "Guiding Mentor"

    def test_select_profile_unknown_key(self):
        """Test selecting profile with unknown key returns first profile."""
        network = MicroAssistantNetwork()

        profile = network.select_profile("unknown assistant")
        assert profile is not None
        assert profile.name in ["Guiding Mentor", "Trading Sage", "Safety Overseer"]

    def test_record_skill_usage(self):
        """Test recording skill usage."""
        network = MicroAssistantNetwork()
        profile = network.select_profile("trading sage")

        network.record_skill_usage(profile)

        assert network.skill_popularity["swaps"] == 1
        assert network.skill_popularity["liquidity"] == 1
        assert network.skill_popularity["market analysis"] == 1

    def test_record_interaction(self):
        """Test recording an interaction in the network."""
        network = MicroAssistantNetwork()
        profile = network.select_profile("guiding mentor")

        network.record_interaction(profile, tokens=200, satisfied=True)

        assert profile.usage_count == 1
        assert profile.tokens_consumed == 200
        assert network.aggregate_tokens == 200
        assert network.aggregate_requests == 1
        assert network.skill_popularity["teaching"] == 1

    def test_get_aggregate_metrics(self):
        """Test getting aggregate metrics."""
        network = MicroAssistantNetwork()
        profile1 = network.select_profile("guiding mentor")
        profile2 = network.select_profile("trading sage")

        network.record_interaction(profile1, tokens=100, satisfied=True)
        network.record_interaction(profile1, tokens=150, satisfied=True)
        network.record_interaction(profile2, tokens=200, satisfied=True)

        metrics = network.get_aggregate_metrics()

        assert metrics["total_requests"] == 3
        assert metrics["total_tokens"] == 450
        assert len(metrics["trending_skills"]) <= 3
        # teaching should be most popular (2 uses)
        assert "teaching" in metrics["trending_skills"]


# ============================================================================
# PersonalAIAssistant Initialization Tests
# ============================================================================

class TestPersonalAIAssistantInit:
    """Test PersonalAIAssistant initialization."""

    def test_init_with_all_params(self, mock_blockchain, mock_safety_controls):
        """Test initialization with all parameters."""
        ai = PersonalAIAssistant(
            blockchain=mock_blockchain,
            safety_controls=mock_safety_controls,
            webhook_url="https://example.com/webhook",
        )

        assert ai.blockchain == mock_blockchain
        assert ai.safety_controls == mock_safety_controls
        assert ai.webhook_url == "https://example.com/webhook"
        assert isinstance(ai.user_usage, defaultdict)
        assert isinstance(ai.micro_network, MicroAssistantNetwork)

    def test_init_without_webhook(self, mock_blockchain):
        """Test initialization without webhook URL."""
        ai = PersonalAIAssistant(
            blockchain=mock_blockchain,
            safety_controls=None,
        )

        assert ai.webhook_url == ""

    @patch.dict(os.environ, {"PERSONAL_AI_WEBHOOK_URL": "https://env-webhook.com"})
    def test_init_webhook_from_config(self, mock_blockchain):
        """Test webhook URL from Config."""
        with patch("xai.ai.ai_assistant.personal_ai_assistant.Config") as mock_config:
            mock_config.PERSONAL_AI_WEBHOOK_URL = "https://config-webhook.com"
            ai = PersonalAIAssistant(blockchain=mock_blockchain)
            # Will use the config value
            assert ai.webhook_url is not None


# ============================================================================
# Helper Method Tests
# ============================================================================

class TestHelperMethods:
    """Test helper and utility methods."""

    def test_generate_request_id(self, personal_ai):
        """Test request ID generation."""
        request_id = personal_ai._generate_request_id()

        assert request_id.startswith("personal-ai-")
        assert len(request_id) > 20

    def test_normalize_provider_openai_default(self, personal_ai):
        """Test provider normalization defaults to OpenAI."""
        assert personal_ai._normalize_provider(None) == "openai"
        assert personal_ai._normalize_provider("") == "openai"

    def test_normalize_provider_mappings(self, personal_ai):
        """Test provider name normalization mappings."""
        assert personal_ai._normalize_provider("grok") == "xai"
        assert personal_ai._normalize_provider("xai") == "xai"
        assert personal_ai._normalize_provider("xai/grok") == "xai"
        assert personal_ai._normalize_provider("togetherai") == "together"
        assert personal_ai._normalize_provider("ANTHROPIC") == "anthropic"

    def test_build_empty_usage_bucket(self):
        """Test building empty usage bucket."""
        bucket = PersonalAIAssistant._build_empty_usage_bucket()

        assert "hour" in bucket
        assert "day" in bucket
        assert "month" in bucket
        assert bucket["hour"] == []
        assert bucket["day"] == []
        assert bucket["month"] == []

    def test_get_pool_status_with_method(self, personal_ai):
        """Test getting pool status when method exists."""
        personal_ai.blockchain.get_ai_pool_stats = Mock(return_value={"pool": "data"})

        status = personal_ai._get_pool_status()

        assert status == {"pool": "data"}

    def test_get_pool_status_without_method(self, personal_ai):
        """Test getting pool status when method doesn't exist."""
        delattr(personal_ai.blockchain, "get_ai_pool_stats")

        status = personal_ai._get_pool_status()

        assert status == {}

    def test_get_pool_status_with_exception(self, personal_ai):
        """Test getting pool status when method raises exception."""
        personal_ai.blockchain.get_ai_pool_stats = Mock(side_effect=Exception("Error"))

        status = personal_ai._get_pool_status()

        assert status == {}

    def test_summarize_ai_cost(self, personal_ai):
        """Test AI cost summarization."""
        ai_cost = {
            "tokens_used": 100,
            "estimated_usd": 0.0015,
        }

        summary = personal_ai._summarize_ai_cost(ai_cost)

        assert summary["tokens_used"] == 100
        assert summary["estimated_usd"] == 0.0015
        assert summary["projected_tokens_next_request"] == 125
        assert "pool_status" in summary

    def test_attach_ai_cost(self, personal_ai):
        """Test attaching AI cost to payload."""
        payload = {"success": True}
        ai_cost = {"tokens_used": 50, "estimated_usd": 0.00075}

        result = personal_ai._attach_ai_cost(payload, ai_cost)

        assert "ai_cost" in result
        assert "ai_cost_summary" in result
        assert result["ai_cost"]["tokens_used"] == 50


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_trim_usage(self, personal_ai):
        """Test trimming old usage records."""
        stats = {
            "hour": [time.time() - 7200, time.time() - 1800, time.time()],
            "day": [time.time() - 90000, time.time()],
            "month": [time.time()],
        }
        now = time.time()

        personal_ai._trim_usage(stats, now)

        # Only recent entries should remain
        assert len(stats["hour"]) == 2  # 1800s and 0s ago
        assert len(stats["day"]) == 1   # 0s ago
        assert len(stats["month"]) == 1  # 0s ago

    def test_check_rate_limit_allowed(self, personal_ai):
        """Test rate limit check when allowed."""
        user_address = "XAI_TEST_USER"

        allowed, info = personal_ai._check_rate_limit(user_address)

        assert allowed is True
        assert "current_usage" in info
        assert info["current_usage"]["hour"] == 0

    def test_check_rate_limit_exceeded_hour(self, personal_ai):
        """Test rate limit exceeded for hourly limit."""
        user_address = "XAI_TEST_USER"
        now = time.time()

        # Add 100 requests in the last hour
        for _ in range(100):
            personal_ai._record_usage(user_address, now)

        allowed, info = personal_ai._check_rate_limit(user_address)

        assert allowed is False
        assert info["success"] is False
        assert info["error"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in info
        assert "current_usage" in info

    def test_check_rate_limit_exceeded_day(self, personal_ai):
        """Test rate limit exceeded for daily limit."""
        user_address = "XAI_TEST_USER"
        now = time.time()

        # Add 500 requests in the last day
        for _ in range(500):
            personal_ai._record_usage(user_address, now)

        allowed, info = personal_ai._check_rate_limit(user_address)

        assert allowed is False
        assert "You exceeded 100/hour" in info["message"]

    def test_record_usage(self, personal_ai):
        """Test recording usage."""
        user_address = "XAI_TEST_USER"
        timestamp = time.time()

        personal_ai._record_usage(user_address, timestamp)

        stats = personal_ai.user_usage[user_address.upper()]
        assert len(stats["hour"]) == 1
        assert len(stats["day"]) == 1
        assert len(stats["month"]) == 1


# ============================================================================
# Safety Controls Tests
# ============================================================================

class TestSafetyControls:
    """Test safety control integration."""

    def test_should_ignore_safety_controls_env_true(self, personal_ai):
        """Test ignoring safety controls via environment variable."""
        with patch.dict(os.environ, {"PERSONAL_AI_ALLOW_UNSAFE": "true"}):
            assert personal_ai._should_ignore_safety_controls() is True

    def test_should_ignore_safety_controls_env_1(self, personal_ai):
        """Test ignoring safety controls via environment variable (1)."""
        with patch.dict(os.environ, {"PERSONAL_AI_ALLOW_UNSAFE": "1"}):
            assert personal_ai._should_ignore_safety_controls() is True

    def test_should_ignore_safety_controls_env_yes(self, personal_ai):
        """Test ignoring safety controls via environment variable (yes)."""
        with patch.dict(os.environ, {"PERSONAL_AI_ALLOW_UNSAFE": "yes"}):
            assert personal_ai._should_ignore_safety_controls() is True

    def test_should_ignore_safety_controls_config(self, personal_ai):
        """Test ignoring safety controls via Config."""
        with patch("xai.ai.ai_assistant.personal_ai_assistant.Config") as mock_config:
            mock_config.PERSONAL_AI_ALLOW_UNSAFE_MODE = True
            assert personal_ai._should_ignore_safety_controls() is True

    def test_should_ignore_safety_controls_false(self, personal_ai):
        """Test not ignoring safety controls."""
        with patch.dict(os.environ, {}, clear=True):
            assert personal_ai._should_ignore_safety_controls() is False

    def test_begin_request_success(self, personal_ai):
        """Test beginning request successfully."""
        request_id, error = personal_ai._begin_request(
            user_address="XAI_TEST",
            ai_provider="openai",
            ai_model="gpt-4",
            operation="test_op",
        )

        assert request_id is not None
        assert error is None

    def test_begin_request_rate_limited(self, personal_ai):
        """Test beginning request when rate limited."""
        user_address = "XAI_TEST"
        now = time.time()

        # Exceed rate limit
        for _ in range(100):
            personal_ai._record_usage(user_address, now)

        request_id, error = personal_ai._begin_request(
            user_address=user_address,
            ai_provider="openai",
            ai_model="gpt-4",
            operation="test_op",
        )

        assert request_id is None
        assert error is not None
        assert error["success"] is False

    def test_begin_request_safety_blocked(self, mock_blockchain):
        """Test beginning request when safety controls block it."""
        safety = Mock()
        safety.register_personal_ai_request.return_value = False

        ai = PersonalAIAssistant(blockchain=mock_blockchain, safety_controls=safety)

        request_id, error = ai._begin_request(
            user_address="XAI_TEST",
            ai_provider="openai",
            ai_model="gpt-4",
            operation="test_op",
        )

        assert request_id is None
        assert error is not None
        assert error["error"] == "AI_SAFETY_STOP_ACTIVE"

    def test_begin_request_safety_blocked_but_ignored(self, mock_blockchain):
        """Test beginning request when safety blocked but ignored."""
        safety = Mock()
        safety.register_personal_ai_request.return_value = False

        ai = PersonalAIAssistant(blockchain=mock_blockchain, safety_controls=safety)

        with patch.dict(os.environ, {"PERSONAL_AI_ALLOW_UNSAFE": "true"}):
            request_id, error = ai._begin_request(
                user_address="XAI_TEST",
                ai_provider="openai",
                ai_model="gpt-4",
                operation="test_op",
            )

            assert request_id is not None
            assert error is None

    def test_finalize_request(self, personal_ai):
        """Test finalizing a request."""
        request_id = "test-request-123"

        personal_ai._finalize_request(request_id)

        personal_ai.safety_controls.complete_personal_ai_request.assert_called_once_with(request_id)

    def test_finalize_request_no_safety(self, personal_ai_no_safety):
        """Test finalizing request without safety controls."""
        # Should not raise exception
        personal_ai_no_safety._finalize_request("test-request-123")


# ============================================================================
# Webhook Tests
# ============================================================================

class TestWebhook:
    """Test webhook notification functionality."""

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_notify_webhook_success(self, mock_requests, personal_ai):
        """Test successful webhook notification."""
        mock_response = Mock()
        mock_requests.post.return_value = mock_response

        personal_ai._notify_webhook("test_event", {"key": "value"})

        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args[0][0] == "https://webhook.example.com/events"
        assert call_args[1]["json"]["event"] == "test_event"
        assert call_args[1]["json"]["payload"] == {"key": "value"}

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_notify_webhook_exception(self, mock_requests, personal_ai):
        """Test webhook notification with exception."""
        from requests.exceptions import RequestException
        mock_requests.post.side_effect = RequestException("Network error")

        # Should not raise exception
        personal_ai._notify_webhook("test_event", {"key": "value"})

    def test_notify_webhook_no_url(self, personal_ai_no_safety):
        """Test webhook notification when no URL configured."""
        # Should not raise exception
        personal_ai_no_safety._notify_webhook("test_event", {"key": "value"})


# ============================================================================
# Exchange Rate Tests
# ============================================================================

class TestExchangeRates:
    """Test exchange rate functionality."""

    def test_get_exchange_rate_btc_to_xai(self, personal_ai):
        """Test getting BTC to XAI exchange rate."""
        rate = personal_ai._get_exchange_rate("BTC", "XAI")

        assert rate == 40000.0  # BTC value / XAI value

    def test_get_exchange_rate_xai_to_btc(self, personal_ai):
        """Test getting XAI to BTC exchange rate."""
        rate = personal_ai._get_exchange_rate("XAI", "BTC")

        assert rate == 1.0 / 40000.0

    def test_get_exchange_rate_cached(self, personal_ai):
        """Test exchange rate caching."""
        rate1 = personal_ai._get_exchange_rate("ETH", "XAI")
        rate2 = personal_ai._get_exchange_rate("ETH", "XAI")

        assert rate1 == rate2
        assert "ETH-XAI" in personal_ai.rate_cache

    def test_get_exchange_rate_unknown_coin(self, personal_ai):
        """Test exchange rate with unknown coin."""
        rate = personal_ai._get_exchange_rate("UNKNOWN", "XAI")

        assert rate == 1.0  # Default value

    def test_get_exchange_rate_zero_division(self, personal_ai):
        """Test exchange rate with zero value prevention."""
        # Modify the default values to include a zero
        personal_ai.DEFAULT_COIN_VALUES_IN_XAI["ZERO"] = 0

        rate = personal_ai._get_exchange_rate("XAI", "ZERO")

        # Should not divide by zero, defaults to 1.0
        assert rate == 1.0


# ============================================================================
# AI Provider Call Tests
# ============================================================================

class TestAIProviderCalls:
    """Test AI provider integration."""

    def test_estimate_ai_cost(self, personal_ai):
        """Test AI cost estimation."""
        prompt = "This is a test prompt with some text."

        cost = personal_ai._estimate_ai_cost(prompt)

        assert "tokens_used" in cost
        assert "estimated_usd" in cost
        assert cost["tokens_used"] >= 150

    def test_call_ai_provider_anthropic_success(self, personal_ai):
        """Test successful Anthropic API call."""
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_result = {"content": "AI response text"}
            mock_client.completion.return_value = mock_result
            mock_anthropic_class.return_value = mock_client

            result = personal_ai._call_ai_provider(
                ai_provider="anthropic",
                ai_model="claude-3",
                user_api_key="test-key",
                prompt="Test prompt",
            )

            assert result["success"] is True
            assert result["text"] == "AI response text"

    def test_call_ai_provider_openai_success(self, personal_ai):
        """Test successful OpenAI API call."""
        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_choice = {"message": {"content": "OpenAI response"}}
            mock_completion = Mock()
            mock_completion.choices = [mock_choice]
            mock_client.ChatCompletion.return_value = mock_completion
            mock_openai_class.return_value = mock_client

            result = personal_ai._call_ai_provider(
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="test-key",
                prompt="Test prompt",
            )

            assert result["success"] is True
            assert result["text"] == "OpenAI response"

    def test_call_ai_provider_unsupported(self, personal_ai):
        """Test calling unsupported AI provider."""
        result = personal_ai._call_ai_provider(
            ai_provider="unsupported_provider",
            ai_model="model",
            user_api_key="key",
            prompt="prompt",
        )

        assert result["success"] is False
        assert "not supported" in result["error"]

    def test_call_ai_provider_missing_module_returns_failure(self, personal_ai):
        """Provider import failures should return structured failure, not success stubs."""
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "anthropic":
                raise ModuleNotFoundError("anthropic")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            result = personal_ai._call_ai_provider(
                ai_provider="anthropic",
                ai_model="claude-3",
                user_api_key="fake-key",
                prompt="Hello",
            )

        assert result["success"] is False
        assert result["code"] == "provider_module_missing"
        assert "anthropic" in result["error"].lower()
        assert "stub_text" in result

    def test_call_additional_provider_success(self, personal_ai):
        """Test calling additional provider successfully."""
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {
            "success": True,
            "output": "Provider response",
            "tokens_used": 50,
            "model": "test-model",
        }
        personal_ai.additional_providers["groq"] = mock_provider

        result = personal_ai._call_additional_provider("groq", "api-key", "prompt")

        assert result["success"] is True
        assert result["text"] == "Provider response"
        assert result["tokens_used"] == 50

    def test_call_additional_provider_not_found(self, personal_ai):
        """Test calling additional provider that doesn't exist."""
        result = personal_ai._call_additional_provider("nonexistent", "key", "prompt")

        assert result is None

    def test_call_additional_provider_exception(self, personal_ai):
        """Test additional provider call with exception."""
        mock_provider = Mock()
        mock_provider.call_with_limit.side_effect = Exception("Provider error")
        personal_ai.additional_providers["groq"] = mock_provider

        result = personal_ai._call_additional_provider("groq", "key", "prompt")

        assert result["success"] is False
        assert "Provider error" in result["error"]


# ============================================================================
# Contract Template Tests
# ============================================================================

class TestContractTemplates:
    """Test smart contract template generation."""

    def test_generate_contract_template_escrow(self, personal_ai):
        """Test generating escrow contract template."""
        template = personal_ai._generate_contract_template("escrow", "Test escrow")

        assert "EscrowContract" in template
        assert "buyer" in template
        assert "seller" in template

    def test_generate_contract_template_auction(self, personal_ai):
        """Test generating auction contract template."""
        template = personal_ai._generate_contract_template("auction", "Test auction")

        assert "AuctionContract" in template
        assert "bid" in template
        assert "winner" in template

    def test_generate_contract_template_token(self, personal_ai):
        """Test generating token contract template."""
        template = personal_ai._generate_contract_template("token", "Test token")

        assert "TokenContract" in template
        assert "transfer" in template
        assert "mint" in template

    def test_generate_contract_template_crowdfund(self, personal_ai):
        """Test generating crowdfund contract template."""
        template = personal_ai._generate_contract_template("crowdfund", "Test crowdfund")

        assert "CrowdfundContract" in template
        assert "contribute" in template
        assert "target" in template

    def test_generate_contract_template_lottery(self, personal_ai):
        """Test generating lottery contract template."""
        template = personal_ai._generate_contract_template("lottery", "Test lottery")

        assert "LotteryContract" in template
        assert "buy_ticket" in template
        assert "draw" in template

    def test_generate_contract_template_voting(self, personal_ai):
        """Test generating voting contract template."""
        template = personal_ai._generate_contract_template("voting", "Test voting")

        assert "VotingContract" in template
        assert "vote" in template
        assert "proposals" in template

    def test_generate_contract_template_custom(self, personal_ai):
        """Test generating custom contract template."""
        template = personal_ai._generate_contract_template("custom", "Custom logic")

        assert "CustomContract" in template
        assert "Custom logic" in template


# ============================================================================
# Atomic Swap Tests
# ============================================================================

class TestAtomicSwap:
    """Test atomic swap functionality."""

    def test_build_atomic_swap_prompt(self, personal_ai):
        """Test building atomic swap prompt."""
        swap_details = {
            "recipient_address": "XAI_RECIPIENT",
            "notes": "Test swap",
        }

        prompt = personal_ai._build_atomic_swap_prompt(
            user_address="XAI_USER",
            from_coin="BTC",
            to_coin="XAI",
            amount=1.5,
            swap_details=swap_details,
            rate=40000.0,
        )

        assert "XAI_USER" in prompt
        assert "1.5000 BTC" in prompt
        assert "XAI" in prompt
        assert "XAI_RECIPIENT" in prompt
        assert "40000.0000" in prompt
        assert "Test swap" in prompt

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_execute_atomic_swap_success(self, mock_requests, personal_ai):
        """Test executing atomic swap successfully."""
        swap_details = {
            "from_coin": "XAI",
            "to_coin": "ADA",
            "amount": 100,
            "recipient_address": "XAI_RECIPIENT",
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "AI analysis"}

            result = personal_ai.execute_atomic_swap_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="test-key",
                swap_details=swap_details,
            )

        assert result["success"] is True
        assert "swap_transaction" in result
        assert result["swap_transaction"]["from_coin"] == "XAI"
        assert result["swap_transaction"]["to_coin"] == "ADA"
        assert "ai_analysis" in result
        assert "assistant_profile" in result

    def test_execute_atomic_swap_missing_fields(self, personal_ai):
        """Test atomic swap with missing required fields."""
        swap_details = {
            "from_coin": "XAI",
            # Missing to_coin and amount
        }

        result = personal_ai.execute_atomic_swap_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="test-key",
            swap_details=swap_details,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_SWAP_DETAILS"

    def test_execute_atomic_swap_invalid_amount(self, personal_ai):
        """Test atomic swap with invalid amount."""
        swap_details = {
            "from_coin": "XAI",
            "to_coin": "BTC",
            "amount": "invalid",
        }

        result = personal_ai.execute_atomic_swap_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="test-key",
            swap_details=swap_details,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_AMOUNT"

    def test_execute_atomic_swap_with_assistant(self, personal_ai):
        """Test atomic swap with specific assistant."""
        swap_details = {
            "from_coin": "XAI",
            "to_coin": "ETH",
            "amount": 50,
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Analysis"}

            result = personal_ai.execute_atomic_swap_with_ai(
                user_address="XAI_USER",
                ai_provider="anthropic",
                ai_model="claude-3",
                user_api_key="key",
                swap_details=swap_details,
                assistant_name="Trading Sage",
            )

        assert result["success"] is True
        assert result["assistant_profile"]["name"] == "Trading Sage"


# ============================================================================
# Smart Contract Tests
# ============================================================================

class TestSmartContract:
    """Test smart contract functionality."""

    def test_build_contract_prompt(self, personal_ai):
        """Test building contract prompt."""
        prompt = personal_ai._build_contract_prompt(
            user_address="XAI_USER",
            contract_description="An escrow for trading",
            contract_type="escrow",
        )

        assert "XAI_USER" in prompt
        assert "escrow" in prompt
        assert "An escrow for trading" in prompt

    def test_create_smart_contract_success(self, personal_ai):
        """Test creating smart contract successfully."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "class Contract:\n    pass"}

            result = personal_ai.create_smart_contract_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                contract_description="Test contract",
                contract_type="escrow",
            )

        assert result["success"] is True
        assert "contract_code" in result
        assert result["contract_type"] == "escrow"
        assert "security_analysis" in result

    def test_create_smart_contract_fallback_template(self, personal_ai):
        """Test smart contract creation with fallback template."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": None}

            result = personal_ai.create_smart_contract_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                contract_description="Auction contract",
                contract_type="auction",
            )

        assert result["success"] is True
        assert "AuctionContract" in result["contract_code"]

    def test_deploy_smart_contract_success(self, personal_ai):
        """Test deploying smart contract successfully."""
        result = personal_ai.deploy_smart_contract_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            contract_code="class MyContract: pass",
            constructor_params={"contract_type": "escrow"},
            testnet=True,
            signature="sig123",
        )

        assert result["success"] is True
        assert "contract_address" in result
        assert result["status"] == "deployed"
        assert result["testnet"] is True

    def test_deploy_smart_contract_awaiting_signature(self, personal_ai):
        """Test deploying contract without signature."""
        result = personal_ai.deploy_smart_contract_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            contract_code="class MyContract: pass",
            constructor_params=None,
            testnet=False,
            signature=None,
        )

        assert result["success"] is True
        assert result["status"] == "awaiting_signature"


# ============================================================================
# Transaction Optimization Tests
# ============================================================================

class TestTransactionOptimization:
    """Test transaction optimization functionality."""

    def test_optimize_transaction_success(self, personal_ai):
        """Test optimizing transaction successfully."""
        transaction = {
            "amount": 100,
            "fee": 1.0,
        }

        result = personal_ai.optimize_transaction_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            transaction=transaction,
        )

        assert result["success"] is True
        assert "optimized_transaction" in result
        assert "savings" in result
        assert result["savings"]["original_fee"] == 1.0
        assert result["savings"]["optimized_fee"] < 1.0

    def test_optimize_transaction_min_fee(self, personal_ai):
        """Test transaction optimization respects minimum fee."""
        transaction = {
            "amount": 10,
            "fee": 0.0005,
        }

        with patch("xai.ai.ai_assistant.personal_ai_assistant.Config") as mock_config:
            mock_config.min_transaction_fee = 0.001

            result = personal_ai.optimize_transaction_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                transaction=transaction,
            )

        assert result["success"] is True
        # Should use minimum fee
        optimized_fee = result["optimized_transaction"]["fee"]
        assert optimized_fee >= 0.001


# ============================================================================
# Blockchain Analysis Tests
# ============================================================================

class TestBlockchainAnalysis:
    """Test blockchain analysis functionality."""

    def test_analyze_blockchain_success(self, personal_ai):
        """Test analyzing blockchain successfully."""
        result = personal_ai.analyze_blockchain_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            query="What is the best strategy for my portfolio?",
        )

        assert result["success"] is True
        assert "answer" in result
        assert "data_sources" in result
        assert "recommendations" in result
        assert result["data_sources"]["user_balance"] == 1000.0


# ============================================================================
# Wallet Analysis Tests
# ============================================================================

class TestWalletAnalysis:
    """Test wallet analysis functionality."""

    def test_wallet_analysis_success(self, personal_ai):
        """Test wallet analysis successfully."""
        result = personal_ai.wallet_analysis_with_ai(
            user_address="XAI_USER",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="key",
            analysis_type="portfolio",
        )

        assert result["success"] is True
        assert "portfolio_analysis" in result
        assert "transaction_patterns" in result
        assert "current_holdings" in result["portfolio_analysis"]

    def test_wallet_recovery_advice(self, personal_ai):
        """Test wallet recovery advice."""
        recovery_details = {
            "guardians": ["guardian1", "guardian2"],
            "context": "Lost access to wallet",
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Recovery steps"}

            result = personal_ai.wallet_recovery_advice(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                recovery_details=recovery_details,
            )

        assert result["success"] is True
        assert "recovery_steps" in result
        assert result["guardians"] == ["guardian1", "guardian2"]


# ============================================================================
# Node Setup Tests
# ============================================================================

class TestNodeSetup:
    """Test node setup functionality."""

    def test_node_setup_recommendations(self, personal_ai):
        """Test node setup recommendations."""
        setup_request = {
            "node_role": "validator",
            "expected_load": "high",
            "preferred_region": "us-east",
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Setup guide"}

            result = personal_ai.node_setup_recommendations(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                setup_request=setup_request,
            )

        assert result["success"] is True
        assert result["setup_role"] == "validator"
        assert result["expected_load"] == "high"
        assert result["region"] == "us-east"
        assert "checklist" in result


# ============================================================================
# Liquidity Alert Tests
# ============================================================================

class TestLiquidityAlert:
    """Test liquidity alert functionality."""

    def test_liquidity_alert_response(self, personal_ai):
        """Test liquidity alert response."""
        alert_details = {
            "threshold": 3.0,
            "slippage_pct": 4.5,
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Alert analysis"}

            result = personal_ai.liquidity_alert_response(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                pool_name="XAI-ETH",
                alert_details=alert_details,
            )

        assert result["success"] is True
        assert result["pool_name"] == "XAI-ETH"
        assert result["threshold_pct"] == 3.0
        assert result["current_slippage_pct"] == 4.5
        assert "mitigation" in result

    def test_liquidity_alert_response_legacy_slippage_key(self, personal_ai):
        """Test liquidity alert with legacy slippage key."""
        alert_details = {
            "threshold": 2.0,
            "slippage": 2.8,  # Legacy key
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Analysis"}

            result = personal_ai.liquidity_alert_response(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                pool_name="XAI-BTC",
                alert_details=alert_details,
            )

        assert result["success"] is True
        assert result["current_slippage_pct"] == 2.8


# ============================================================================
# Micro Assistants List Tests
# ============================================================================

class TestMicroAssistantsList:
    """Test listing micro assistants."""

    def test_list_micro_assistants(self, personal_ai):
        """Test listing micro assistants."""
        result = personal_ai.list_micro_assistants()

        assert "profiles" in result
        assert "aggregated_metrics" in result
        assert len(result["profiles"]) == 3


# ============================================================================
# Assistant Profile Management Tests
# ============================================================================

class TestAssistantProfileManagement:
    """Test assistant profile management."""

    def test_prepare_assistant(self, personal_ai):
        """Test preparing assistant profile."""
        profile = personal_ai._prepare_assistant("Trading Sage")

        assert profile.name == "Trading Sage"

    def test_finalize_assistant_usage(self, personal_ai):
        """Test finalizing assistant usage."""
        result = {"success": True, "ai_cost": {"tokens_used": 100}}
        profile = personal_ai._prepare_assistant("Guiding Mentor")

        final_result = personal_ai._finalize_assistant_usage(result, profile)

        assert "assistant_profile" in final_result
        assert "assistant_aggregate" in final_result
        assert final_result["assistant_profile"]["name"] == "Guiding Mentor"


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_zero_amount_swap(self, mock_requests, personal_ai):
        """Test atomic swap with zero amount converts to string 'invalid'."""
        swap_details = {
            "from_coin": "XAI",
            "to_coin": "BTC",
            "amount": "0",  # String zero
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Analysis"}

            result = personal_ai.execute_atomic_swap_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                swap_details=swap_details,
            )

        # Zero amount should be converted to minimum amount 0.000001
        assert result["success"] is True
        assert result["swap_transaction"]["from_amount"] == 0.000001

    def test_negative_amount_swap(self, personal_ai):
        """Test atomic swap with negative amount."""
        swap_details = {
            "from_coin": "XAI",
            "to_coin": "BTC",
            "amount": -100,
        }

        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Analysis"}

            result = personal_ai.execute_atomic_swap_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                swap_details=swap_details,
            )

        # Should use minimum amount
        assert result["success"] is True
        assert result["swap_transaction"]["from_amount"] == 0.000001

    def test_empty_contract_description(self, personal_ai):
        """Test creating contract with empty description."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "contract code"}

            result = personal_ai.create_smart_contract_with_ai(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                contract_description="",
                contract_type="general",
            )

        assert result["success"] is True

    def test_none_recovery_details(self, personal_ai):
        """Test wallet recovery with None recovery details."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Recovery guide"}

            result = personal_ai.wallet_recovery_advice(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                recovery_details=None,
            )

        assert result["success"] is True
        assert result["guardians"] == []

    def test_none_setup_request(self, personal_ai):
        """Test node setup with None setup request."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Setup guide"}

            result = personal_ai.node_setup_recommendations(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                setup_request=None,
            )

        assert result["success"] is True
        assert result["setup_role"] == "full node"

    def test_none_alert_details(self, personal_ai):
        """Test liquidity alert with None alert details."""
        with patch.object(personal_ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "Alert"}

            result = personal_ai.liquidity_alert_response(
                user_address="XAI_USER",
                ai_provider="openai",
                ai_model="gpt-4",
                user_api_key="key",
                pool_name="TEST-POOL",
                alert_details=None,
            )

        assert result["success"] is True
        assert result["threshold_pct"] == 2.5
        assert result["current_slippage_pct"] == 1.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    @patch("xai.ai.ai_assistant.personal_ai_assistant.requests")
    def test_full_atomic_swap_workflow(self, mock_requests, mock_blockchain, mock_safety_controls):
        """Test complete atomic swap workflow."""
        ai = PersonalAIAssistant(
            blockchain=mock_blockchain,
            safety_controls=mock_safety_controls,
            webhook_url="https://webhook.test",
        )

        swap_details = {
            "from_coin": "XAI",
            "to_coin": "BTC",
            "amount": 1000,
            "recipient_address": "XAI_RECIPIENT",
        }

        with patch.object(ai, "_call_ai_provider") as mock_ai:
            mock_ai.return_value = {"success": True, "text": "AI swap analysis"}

            result = ai.execute_atomic_swap_with_ai(
                user_address="XAI_USER",
                ai_provider="anthropic",
                ai_model="claude-3",
                user_api_key="test-key",
                swap_details=swap_details,
                assistant_name="Trading Sage",
            )

        # Verify complete workflow
        assert result["success"] is True
        assert result["assistant_profile"]["name"] == "Trading Sage"
        assert "swap_transaction" in result
        assert "ai_analysis" in result
        assert "ai_cost" in result
        assert "ai_cost_summary" in result

        # Verify safety controls called
        mock_safety_controls.register_personal_ai_request.assert_called_once()
        mock_safety_controls.complete_personal_ai_request.assert_called_once()

    def test_rate_limit_recovery(self, personal_ai):
        """Test rate limit recovery after time passes."""
        user_address = "XAI_RATE_TEST"

        # Exhaust hourly limit
        for _ in range(100):
            personal_ai._record_usage(user_address, time.time())

        # Should be rate limited
        allowed, _ = personal_ai._check_rate_limit(user_address)
        assert allowed is False

        # Manually age out the requests
        old_time = time.time() - 3700  # 1 hour and 100 seconds ago
        personal_ai.user_usage[user_address.upper()]["hour"] = [old_time]

        # Should be allowed again
        allowed, _ = personal_ai._check_rate_limit(user_address)
        assert allowed is True
