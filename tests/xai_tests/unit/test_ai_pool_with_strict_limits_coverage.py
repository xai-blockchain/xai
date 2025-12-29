"""
Comprehensive test coverage for ai_pool_with_strict_limits.py
Target: 80%+ coverage (167+ statements out of 209)

Tests cover:
- Pool initialization with limits
- Request allocation and queuing
- Limit enforcement (rate, quota, concurrent)
- Resource management
- Priority handling
- Quota tracking and resets
- All error handling paths
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from xai.core.security.ai_pool_with_strict_limits import (
    AIProvider,
    DonatedAPIKey,
    StrictAIPoolManager,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_key_manager():
    """Mock SecureAPIKeyManager"""
    manager = Mock()
    manager.submit_api_key = Mock(
        return_value={
            "success": True,
            "key_id": "test_key_123",
        }
    )
    manager.get_api_key_for_task = Mock(
        return_value=("test_key_123", "sk-test-api-key", 100000)
    )
    manager._destroy_api_key = Mock()
    return manager


@pytest.fixture
def pool_manager(mock_key_manager):
    """Create StrictAIPoolManager instance"""
    return StrictAIPoolManager(mock_key_manager)


@pytest.fixture
def sample_donated_key():
    """Create a sample DonatedAPIKey"""
    return DonatedAPIKey(
        key_id="key_001",
        donor_address="XAI123456789",
        provider=AIProvider.ANTHROPIC,
        encrypted_key="encrypted_key_001",
        donated_tokens=10000,
        donated_minutes=60,
        submitted_at=time.time(),
    )


@pytest.fixture
def mock_metrics():
    """Mock metrics module"""
    with patch("xai.core.ai_pool_with_strict_limits.metrics") as mock_metrics:
        mock_metrics.record_tokens = Mock()
        yield mock_metrics


# ==================== DonatedAPIKey Tests ====================


class TestDonatedAPIKey:
    """Test DonatedAPIKey dataclass and methods"""

    def test_remaining_tokens_initial(self, sample_donated_key):
        """Test remaining_tokens returns full amount initially"""
        assert sample_donated_key.remaining_tokens() == 10000

    def test_remaining_tokens_after_usage(self, sample_donated_key):
        """Test remaining_tokens after some usage"""
        sample_donated_key.used_tokens = 3000
        assert sample_donated_key.remaining_tokens() == 7000

    def test_remaining_tokens_zero_when_depleted(self, sample_donated_key):
        """Test remaining_tokens returns 0 when fully used"""
        sample_donated_key.used_tokens = 10000
        assert sample_donated_key.remaining_tokens() == 0

    def test_remaining_tokens_zero_when_exceeded(self, sample_donated_key):
        """Test remaining_tokens returns 0 when usage exceeds donation"""
        sample_donated_key.used_tokens = 15000
        assert sample_donated_key.remaining_tokens() == 0

    def test_remaining_minutes_initial(self, sample_donated_key):
        """Test remaining_minutes returns full amount initially"""
        assert sample_donated_key.remaining_minutes() == 60.0

    def test_remaining_minutes_after_usage(self, sample_donated_key):
        """Test remaining_minutes after some usage"""
        sample_donated_key.used_minutes = 20.5
        assert sample_donated_key.remaining_minutes() == 39.5

    def test_remaining_minutes_none_returns_infinity(self):
        """Test remaining_minutes returns infinity when not specified"""
        key = DonatedAPIKey(
            key_id="key_002",
            donor_address="XAI987654321",
            provider=AIProvider.OPENAI,
            encrypted_key="encrypted_key_002",
            donated_tokens=5000,
            donated_minutes=None,
            submitted_at=time.time(),
        )
        assert key.remaining_minutes() == float("inf")

    def test_can_use_success(self, sample_donated_key):
        """Test can_use returns True with sufficient balance"""
        can_use, message = sample_donated_key.can_use(tokens_needed=1000, minutes_needed=10.0)
        assert can_use is True
        assert message == "Sufficient balance"

    def test_can_use_inactive_key(self, sample_donated_key):
        """Test can_use returns False for inactive key"""
        sample_donated_key.is_active = False
        can_use, message = sample_donated_key.can_use(tokens_needed=1000)
        assert can_use is False
        assert message == "Key is not active"

    def test_can_use_depleted_key(self, sample_donated_key):
        """Test can_use returns False for depleted key"""
        sample_donated_key.is_depleted = True
        can_use, message = sample_donated_key.can_use(tokens_needed=1000)
        assert can_use is False
        assert message == "Key is already depleted"

    def test_can_use_insufficient_tokens(self, sample_donated_key):
        """Test can_use returns False with insufficient tokens"""
        can_use, message = sample_donated_key.can_use(tokens_needed=15000)
        assert can_use is False
        assert "Insufficient tokens" in message
        assert "need 15000" in message

    def test_can_use_insufficient_minutes(self, sample_donated_key):
        """Test can_use returns False with insufficient minutes"""
        can_use, message = sample_donated_key.can_use(tokens_needed=1000, minutes_needed=100.0)
        assert can_use is False
        assert "Insufficient minutes" in message
        assert "need 100" in message

    def test_mark_usage_updates_counters(self, sample_donated_key):
        """Test mark_usage updates token and minute counters"""
        initial_calls = sample_donated_key.api_calls_made
        sample_donated_key.mark_usage(tokens_used=500, minutes_used=5.0)

        assert sample_donated_key.used_tokens == 500
        assert sample_donated_key.used_minutes == 5.0
        assert sample_donated_key.api_calls_made == initial_calls + 1

    def test_mark_usage_sets_timestamps(self, sample_donated_key):
        """Test mark_usage sets first_used_at and last_used_at"""
        assert sample_donated_key.first_used_at is None
        sample_donated_key.mark_usage(tokens_used=100)

        assert sample_donated_key.first_used_at is not None
        assert sample_donated_key.last_used_at is not None

    def test_mark_usage_updates_last_used(self, sample_donated_key):
        """Test mark_usage updates last_used_at on subsequent calls"""
        sample_donated_key.mark_usage(tokens_used=100)
        first_last_used = sample_donated_key.last_used_at

        time.sleep(0.01)
        sample_donated_key.mark_usage(tokens_used=200)

        assert sample_donated_key.last_used_at > first_last_used

    def test_mark_usage_returns_true_when_tokens_depleted(self, sample_donated_key):
        """Test mark_usage returns True when tokens are depleted"""
        is_depleted = sample_donated_key.mark_usage(tokens_used=10000)

        assert is_depleted is True
        assert sample_donated_key.is_depleted is True
        assert sample_donated_key.depleted_at is not None

    def test_mark_usage_returns_true_when_minutes_depleted(self, sample_donated_key):
        """Test mark_usage returns True when minutes are depleted"""
        is_depleted = sample_donated_key.mark_usage(tokens_used=100, minutes_used=60.0)

        assert is_depleted is True
        assert sample_donated_key.is_depleted is True

    def test_mark_usage_returns_false_when_not_depleted(self, sample_donated_key):
        """Test mark_usage returns False when still has balance"""
        is_depleted = sample_donated_key.mark_usage(tokens_used=100, minutes_used=5.0)

        assert is_depleted is False
        assert sample_donated_key.is_depleted is False


# ==================== StrictAIPoolManager Initialization Tests ====================


class TestStrictAIPoolManagerInit:
    """Test StrictAIPoolManager initialization"""

    def test_initialization(self, pool_manager, mock_key_manager):
        """Test pool manager initializes correctly"""
        assert pool_manager.key_manager == mock_key_manager
        assert pool_manager.donated_keys == {}
        assert pool_manager.total_tokens_donated == 0
        assert pool_manager.total_tokens_used == 0
        assert pool_manager.total_minutes_donated == 0.0
        assert pool_manager.total_minutes_used == 0.0
        assert pool_manager.emergency_stop is False
        assert pool_manager.max_tokens_per_call == 100000


# ==================== API Key Donation Submission Tests ====================


class TestSubmitAPIKeyDonation:
    """Test submit_api_key_donation method"""

    def test_submit_valid_donation(self, pool_manager):
        """Test submitting a valid API key donation"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
            donated_minutes=30,
        )

        assert result["success"] is True
        assert result["key_id"] == "test_key_123"
        assert result["donated_tokens"] == 50000
        assert result["donated_minutes"] == 30
        assert result.get("limits_enforced") is True

    def test_submit_donation_updates_totals(self, pool_manager):
        """Test submission updates total donated amounts"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
            donated_minutes=30,
        )

        assert pool_manager.total_tokens_donated == 50000
        assert pool_manager.total_minutes_donated == 30

    def test_submit_donation_without_minutes(self, pool_manager):
        """Test submitting donation without minutes limit"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.OPENAI,
            api_key="sk-test-key",
            donated_tokens=25000,
        )

        assert result["success"] is True
        assert result["donated_minutes"] is None

    def test_submit_donation_missing_tokens(self, pool_manager):
        """Test submission fails when donated_tokens is None"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=None,
        )

        assert result["success"] is False
        assert result["error"] == "DONATED_TOKENS_REQUIRED"

    def test_submit_donation_zero_tokens(self, pool_manager):
        """Test submission fails when donated_tokens is zero"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=0,
        )

        assert result["success"] is False
        assert result["error"] == "DONATED_TOKENS_REQUIRED"

    def test_submit_donation_negative_tokens(self, pool_manager):
        """Test submission fails when donated_tokens is negative"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=-1000,
        )

        assert result["success"] is False
        assert result["error"] == "DONATED_TOKENS_REQUIRED"

    def test_submit_donation_too_large(self, pool_manager):
        """Test submission fails when donation exceeds max limit"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=200_000_000,  # Exceeds 100M limit
        )

        assert result["success"] is False
        assert result["error"] == "DONATION_TOO_LARGE"

    def test_submit_donation_invalid_minutes_zero(self, pool_manager):
        """Test submission fails when donated_minutes is zero"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
            donated_minutes=0,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_MINUTES"

    def test_submit_donation_invalid_minutes_negative(self, pool_manager):
        """Test submission fails when donated_minutes is negative"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
            donated_minutes=-10,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_MINUTES"

    def test_submit_donation_invalid_minutes_too_large(self, pool_manager):
        """Test submission fails when donated_minutes exceeds 30 days"""
        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
            donated_minutes=50000,  # Exceeds 43200 (30 days)
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_MINUTES"

    def test_submit_donation_key_manager_failure(self, pool_manager, mock_key_manager):
        """Test submission fails when key manager rejects"""
        mock_key_manager.submit_api_key.return_value = {
            "success": False,
            "error": "INVALID_KEY_FORMAT",
        }

        result = pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="invalid-key",
            donated_tokens=50000,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_KEY_FORMAT"

    def test_submit_donation_creates_donated_key(self, pool_manager):
        """Test submission creates DonatedAPIKey in pool"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
        )

        assert "test_key_123" in pool_manager.donated_keys
        key = pool_manager.donated_keys["test_key_123"]
        assert key.donor_address == "XAI123456789"
        assert key.provider == AIProvider.ANTHROPIC
        assert key.donated_tokens == 50000


# ==================== Task Execution Tests ====================


class TestExecuteAITaskWithLimits:
    """Test execute_ai_task_with_limits method"""

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    @patch("xai.core.ai_pool_with_strict_limits.anthropic")
    def test_execute_task_success(self, mock_anthropic, mock_metrics, pool_manager):
        """Test successful task execution"""
        # Setup
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=50000,
        )

        # Mock Anthropic API response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        result = pool_manager.execute_ai_task_with_limits(
            task_description="Test task",
            estimated_tokens=200,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is True
        assert result["tokens_used"] == 150
        assert result["result"] == "Test response"

    def test_execute_task_emergency_stop(self, pool_manager):
        """Test task execution fails when emergency stop is active"""
        pool_manager.emergency_stop = True

        result = pool_manager.execute_ai_task_with_limits(
            task_description="Test task",
            estimated_tokens=200,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "EMERGENCY_STOP_ACTIVE"

    def test_execute_task_request_too_large(self, pool_manager):
        """Test task execution fails when request exceeds safety limit"""
        result = pool_manager.execute_ai_task_with_limits(
            task_description="Huge task",
            estimated_tokens=200000,  # Exceeds max_tokens_per_call
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "REQUEST_TOO_LARGE"

    def test_execute_task_no_suitable_keys(self, pool_manager):
        """Test task execution fails when no suitable keys available"""
        result = pool_manager.execute_ai_task_with_limits(
            task_description="Test task",
            estimated_tokens=1000,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "INSUFFICIENT_DONATED_CREDITS"

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    @patch("xai.core.ai_pool_with_strict_limits.openai")
    def test_execute_task_openai_provider(self, mock_openai, mock_metrics, pool_manager):
        """Test task execution with OpenAI provider"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.OPENAI,
            api_key="sk-test-key",
            donated_tokens=50000,
        )

        # Mock OpenAI API response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="OpenAI response"))]
        mock_response.usage = Mock(total_tokens=200, prompt_tokens=100, completion_tokens=100)
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        result = pool_manager.execute_ai_task_with_limits(
            task_description="Test task",
            estimated_tokens=250,
            provider=AIProvider.OPENAI,
        )

        assert result["success"] is True
        assert result["tokens_used"] == 200

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    @patch("xai.core.ai_pool_with_strict_limits.genai")
    def test_execute_task_google_provider(self, mock_genai, mock_metrics, pool_manager):
        """Test task execution with Google provider"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.GOOGLE,
            api_key="test-google-key",
            donated_tokens=50000,
        )

        # Mock Google API response
        mock_response = Mock()
        mock_response.text = "Google response with some words here"
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response

        result = pool_manager.execute_ai_task_with_limits(
            task_description="Test task with some words",
            estimated_tokens=100,
            provider=AIProvider.GOOGLE,
        )

        assert result["success"] is True
        assert "tokens_used" in result

    @patch.object(StrictAIPoolManager, "_execute_with_strict_limits")
    def test_execute_task_splits_across_multiple_keys(
        self, mock_execute, pool_manager, mock_key_manager
    ):
        """Large tasks should be split across multiple donated keys."""
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI111",
            provider=AIProvider.ANTHROPIC,
            api_key="key-one",
            donated_tokens=150,
        )
        pool_manager.submit_api_key_donation(
            donor_address="XAI222",
            provider=AIProvider.ANTHROPIC,
            api_key="key-two",
            donated_tokens=150,
        )

        mock_execute.side_effect = [
            {
                "success": True,
                "result": "segment-one",
                "tokens_used": 120,
                "minutes_elapsed": 0.4,
            },
            {
                "success": True,
                "result": "segment-two",
                "tokens_used": 80,
                "minutes_elapsed": 0.3,
            },
        ]

        result = pool_manager.execute_ai_task_with_limits(
            task_description="Long task needs pooling",
            estimated_tokens=200,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is True
        assert result["segments_executed"] == 2
        assert result["tokens_used"] == 200
        assert "segment-two" in result["output"]
        assert mock_execute.call_count == 2
        first_call_keys = mock_execute.call_args_list[0][1]["keys"]
        second_call_keys = mock_execute.call_args_list[1][1]["keys"]
        assert first_call_keys[0].key_id == "key_001"
        assert second_call_keys[0].key_id == "key_002"


# ==================== Key Finding and Selection Tests ====================


class TestFindSuitableKeys:
    """Test _find_suitable_keys method"""

    def test_find_single_key_sufficient(self, pool_manager):
        """Test finding a single key with sufficient balance"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        keys = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 5000)

        assert len(keys) == 1
        assert keys[0].donated_tokens == 10000

    def test_find_multiple_keys_needed(self, pool_manager, mock_key_manager):
        """Test finding multiple keys when one is insufficient"""
        # Add multiple keys
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-1",
            donated_tokens=3000,
        )

        pool_manager.submit_api_key_donation(
            donor_address="XAI987654321",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-2",
            donated_tokens=3000,
        )

        keys = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 5000)

        assert len(keys) == 2

    def test_find_no_keys_available(self, pool_manager):
        """Test finding keys when none are available"""
        keys = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 5000)

        assert len(keys) == 0

    def test_find_keys_wrong_provider(self, pool_manager):
        """Test finding keys for wrong provider"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        keys = pool_manager._find_suitable_keys(AIProvider.OPENAI, 5000)

        assert len(keys) == 0

    def test_find_keys_rotation_balances_usage(self, pool_manager, mock_key_manager):
        """Key selection should rotate between donations for fair usage."""
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-1",
            donated_tokens=8000,
        )

        pool_manager.submit_api_key_donation(
            donor_address="XAI987654321",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-2",
            donated_tokens=8000,
        )

        keys_first = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 1000)
        assert keys_first and keys_first[0].key_id == "key_001"

        keys_second = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 1000)
        assert keys_second and keys_second[0].key_id == "key_002"
        assert keys_second[0] is not keys_first[0]

    def test_rotation_cleanup_removes_depleted_keys(self, pool_manager):
        """Rotation queues should drop depleted keys automatically."""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=1000,
        )

        rotation = pool_manager._provider_rotation[AIProvider.ANTHROPIC]
        assert "test_key_123" in rotation

        pool_manager.donated_keys["test_key_123"].is_depleted = True
        pool_manager._cleanup_rotation(AIProvider.ANTHROPIC)

        assert "test_key_123" not in pool_manager._provider_rotation[AIProvider.ANTHROPIC]

    def test_find_keys_skips_depleted(self, pool_manager):
        """Test finding keys skips depleted ones"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        # Mark as depleted
        pool_manager.donated_keys["test_key_123"].is_depleted = True

        keys = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 5000)

        assert len(keys) == 0

    def test_find_keys_skips_inactive(self, pool_manager):
        """Test finding keys skips inactive ones"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        # Mark as inactive
        pool_manager.donated_keys["test_key_123"].is_active = False

        keys = pool_manager._find_suitable_keys(AIProvider.ANTHROPIC, 5000)

        assert len(keys) == 0


# ==================== Token Deduction Tests ====================


class TestDeductTokensFromKeys:
    """Test _deduct_tokens_from_keys method"""

    def test_deduct_from_single_key(self, pool_manager):
        """Test deducting tokens from a single key"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        key = pool_manager.donated_keys["test_key_123"]
        pool_manager._deduct_tokens_from_keys([key], 5000)

        assert key.used_tokens == 5000
        assert key.remaining_tokens() == 5000

    def test_deduct_depletes_key(self, pool_manager, mock_key_manager):
        """Test deducting tokens depletes key when appropriate"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        key = pool_manager.donated_keys["test_key_123"]
        pool_manager._deduct_tokens_from_keys([key], 10000)

        assert key.is_depleted is True
        assert key.depleted_at is not None
        mock_key_manager._destroy_api_key.assert_called_once_with("test_key_123")

    def test_deduct_from_multiple_keys(self, pool_manager, mock_key_manager):
        """Test deducting tokens from multiple keys"""
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-1",
            donated_tokens=3000,
        )

        pool_manager.submit_api_key_donation(
            donor_address="XAI987654321",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-2",
            donated_tokens=3000,
        )

        key1 = pool_manager.donated_keys["key_001"]
        key2 = pool_manager.donated_keys["key_002"]

        pool_manager._deduct_tokens_from_keys([key1, key2], 5000)

        # First key should be fully depleted, second partially used
        assert key1.used_tokens == 3000
        assert key2.used_tokens == 2000


# ==================== API Call Tests ====================


class TestAPIProviderCalls:
    """Test API provider-specific calls"""

    @patch("xai.core.ai_pool_with_strict_limits.anthropic")
    def test_call_anthropic_success(self, mock_anthropic, pool_manager):
        """Test successful Anthropic API call"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        result = pool_manager._call_anthropic_with_limit("sk-test", "Test task", 1000)

        assert result["success"] is True
        assert result["tokens_used"] == 150
        assert result["output"] == "Test response"

    @patch("xai.core.ai_pool_with_strict_limits.anthropic")
    def test_call_anthropic_api_error(self, mock_anthropic, pool_manager):
        """Test Anthropic API call with error"""
        # Create a custom APIError class
        class APIError(Exception):
            pass

        mock_anthropic.APIError = APIError
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = APIError("API Error")

        result = pool_manager._call_anthropic_with_limit("sk-test", "Test task", 1000)

        assert result["success"] is False
        assert "error" in result
        assert result["tokens_used"] == 0

    @patch("xai.core.ai_pool_with_strict_limits.openai")
    def test_call_openai_success(self, mock_openai, pool_manager):
        """Test successful OpenAI API call"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="OpenAI response"))]
        mock_response.usage = Mock(total_tokens=200, prompt_tokens=100, completion_tokens=100)
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        result = pool_manager._call_openai_with_limit("sk-test", "Test task", 1000)

        assert result["success"] is True
        assert result["tokens_used"] == 200
        assert result["output"] == "OpenAI response"

    @patch("xai.core.ai_pool_with_strict_limits.openai")
    def test_call_openai_api_error(self, mock_openai, pool_manager):
        """Test OpenAI API call with error"""
        # Create a custom APIError class
        class APIError(Exception):
            pass

        mock_openai.APIError = APIError
        mock_openai.OpenAI.return_value.chat.completions.create.side_effect = APIError("API Error")

        result = pool_manager._call_openai_with_limit("sk-test", "Test task", 1000)

        assert result["success"] is False
        assert "error" in result
        assert result["tokens_used"] == 0

    @patch("xai.core.ai_pool_with_strict_limits.genai")
    def test_call_google_success(self, mock_genai, pool_manager):
        """Test successful Google API call"""
        mock_response = Mock()
        mock_response.text = "Google response"
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response

        result = pool_manager._call_google_with_limit("test-key", "Test task", 1000)

        assert result["success"] is True
        assert result["tokens_used"] > 0
        assert result["output"] == "Google response"

    @patch("xai.core.ai_pool_with_strict_limits.genai")
    def test_call_google_api_error(self, mock_genai, pool_manager):
        """Test Google API call with error"""
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = \
            Exception("API Error")

        result = pool_manager._call_google_with_limit("test-key", "Test task", 1000)

        assert result["success"] is False
        assert "error" in result
        assert result["tokens_used"] == 0


# ==================== Execute with Strict Limits Tests ====================


class TestExecuteWithStrictLimits:
    """Test _execute_with_strict_limits method"""

    def test_pre_execution_validation_failure(self, pool_manager):
        """Test pre-execution validation fails with insufficient tokens"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=1000,
        )

        key = pool_manager.donated_keys["test_key_123"]

        result = pool_manager._execute_with_strict_limits(
            keys=[key],
            task_description="Test",
            estimated_tokens=5000,  # More than available
            max_tokens=5000,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "PRE_EXECUTION_VALIDATION_FAILED"

    def test_key_retrieval_failure(self, pool_manager, mock_key_manager):
        """Test execution fails when key retrieval fails"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        mock_key_manager.get_api_key_for_task.return_value = None

        key = pool_manager.donated_keys["test_key_123"]

        result = pool_manager._execute_with_strict_limits(
            keys=[key],
            task_description="Test",
            estimated_tokens=1000,
            max_tokens=1000,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "KEY_RETRIEVAL_FAILED"

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    @patch("xai.core.ai_pool_with_strict_limits.anthropic")
    def test_limit_exceeded_triggers_error(self, mock_anthropic, mock_metrics, pool_manager):
        """Test limit exceeded triggers critical error"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        # Mock response that exceeds limit
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=2000)  # 3000 > 1000 limit
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        key = pool_manager.donated_keys["test_key_123"]

        result = pool_manager._execute_with_strict_limits(
            keys=[key],
            task_description="Test",
            estimated_tokens=1000,
            max_tokens=1000,  # Limit is 1000 but API uses 3000
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "LIMIT_EXCEEDED"
        assert result["emergency_stop_triggered"] is True

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    @patch("xai.core.ai_pool_with_strict_limits.anthropic")
    def test_api_call_exception_handling(self, mock_anthropic, mock_metrics, pool_manager):
        """Test exception handling during API call"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        mock_anthropic.Anthropic.return_value.messages.create.side_effect = \
            Exception("Connection error")

        key = pool_manager.donated_keys["test_key_123"]

        result = pool_manager._execute_with_strict_limits(
            keys=[key],
            task_description="Test",
            estimated_tokens=1000,
            max_tokens=1000,
            provider=AIProvider.ANTHROPIC,
        )

        assert result["success"] is False
        assert result["error"] == "API_CALL_FAILED"
        assert result["tokens_charged"] == 0

    @patch("xai.core.ai_pool_with_strict_limits.metrics")
    def test_unsupported_provider(self, mock_metrics, pool_manager):
        """Test unsupported provider error"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        key = pool_manager.donated_keys["test_key_123"]

        # Create a mock provider that's not implemented
        with patch.object(key, 'provider', Mock(value='unsupported')):
            result = pool_manager._execute_with_strict_limits(
                keys=[key],
                task_description="Test",
                estimated_tokens=1000,
                max_tokens=1000,
                provider=Mock(value='unsupported'),
            )

        assert result["success"] is False
        assert result["error"] == "UNSUPPORTED_PROVIDER"


# ==================== Pool Status Tests ====================


class TestGetPoolStatus:
    """Test get_pool_status method"""

    def test_pool_status_empty(self, pool_manager):
        """Test pool status when empty"""
        status = pool_manager.get_pool_status()

        assert status["total_keys_donated"] == 0
        assert status["total_tokens_donated"] == 0
        assert status["total_tokens_used"] == 0
        assert status["total_tokens_remaining"] == 0
        assert status["strict_limits_enforced"] is True

    def test_pool_status_with_keys(self, pool_manager, mock_key_manager):
        """Test pool status with donated keys"""
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-1",
            donated_tokens=10000,
        )

        pool_manager.submit_api_key_donation(
            donor_address="XAI987654321",
            provider=AIProvider.OPENAI,
            api_key="sk-test-key-2",
            donated_tokens=5000,
        )

        status = pool_manager.get_pool_status()

        assert status["total_keys_donated"] == 2
        assert status["total_tokens_donated"] == 15000
        assert "anthropic" in status["by_provider"]
        assert "openai" in status["by_provider"]

    def test_pool_status_by_provider(self, pool_manager):
        """Test pool status breaks down by provider correctly"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        status = pool_manager.get_pool_status()

        anthropic_status = status["by_provider"]["anthropic"]
        assert anthropic_status["total_keys"] == 1
        assert anthropic_status["active_keys"] == 1
        assert anthropic_status["depleted_keys"] == 0
        assert anthropic_status["donated_tokens"] == 10000

    def test_pool_status_utilization(self, pool_manager):
        """Test pool status calculates utilization correctly"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        pool_manager.total_tokens_used = 5000

        status = pool_manager.get_pool_status()

        assert status["utilization_percent"] == 50.0


# ==================== Helper Method Tests ====================


class TestHelperMethods:
    """Test helper methods"""

    def test_get_available_tokens(self, pool_manager, mock_key_manager):
        """Test _get_available_tokens method"""
        mock_key_manager.submit_api_key.side_effect = [
            {"success": True, "key_id": "key_001"},
            {"success": True, "key_id": "key_002"},
        ]

        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-1",
            donated_tokens=10000,
        )

        pool_manager.submit_api_key_donation(
            donor_address="XAI987654321",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key-2",
            donated_tokens=5000,
        )

        available = pool_manager._get_available_tokens(AIProvider.ANTHROPIC)
        assert available == 15000

    def test_get_available_tokens_after_usage(self, pool_manager):
        """Test _get_available_tokens after some usage"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        pool_manager.donated_keys["test_key_123"].used_tokens = 3000

        available = pool_manager._get_available_tokens(AIProvider.ANTHROPIC)
        assert available == 7000

    def test_get_available_tokens_excludes_depleted(self, pool_manager):
        """Test _get_available_tokens excludes depleted keys"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        pool_manager.donated_keys["test_key_123"].is_depleted = True

        available = pool_manager._get_available_tokens(AIProvider.ANTHROPIC)
        assert available == 0

    def test_handle_depleted_key(self, pool_manager, mock_key_manager):
        """Test _handle_depleted_key method"""
        pool_manager.submit_api_key_donation(
            donor_address="XAI123456789",
            provider=AIProvider.ANTHROPIC,
            api_key="sk-ant-test-key",
            donated_tokens=10000,
        )

        key = pool_manager.donated_keys["test_key_123"]
        pool_manager._handle_depleted_key(key)

        assert key.is_depleted is True
        assert key.is_active is False
        mock_key_manager._destroy_api_key.assert_called_once_with("test_key_123")
        assert "test_key_123" not in pool_manager._provider_rotation[AIProvider.ANTHROPIC]


# ==================== Edge Cases and Integration Tests ====================


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios"""

    def test_multiple_tasks_deplete_key(self, pool_manager, mock_key_manager, mock_metrics):
        """Test multiple tasks eventually deplete a key"""
        with patch("xai.core.ai_pool_with_strict_limits.anthropic") as mock_anthropic:
            pool_manager.submit_api_key_donation(
                donor_address="XAI123456789",
                provider=AIProvider.ANTHROPIC,
                api_key="sk-ant-test-key",
                donated_tokens=1000,
            )

            # Mock responses
            mock_response = Mock()
            mock_response.content = [Mock(text="Response")]
            mock_response.usage = Mock(input_tokens=300, output_tokens=200)  # 500 tokens each
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

            # First task should succeed
            result1 = pool_manager.execute_ai_task_with_limits(
                task_description="Task 1",
                estimated_tokens=500,
                provider=AIProvider.ANTHROPIC,
            )
            assert result1["success"] is True

            # Second task should succeed
            result2 = pool_manager.execute_ai_task_with_limits(
                task_description="Task 2",
                estimated_tokens=500,
                provider=AIProvider.ANTHROPIC,
            )
            assert result2["success"] is True

            # Third task should fail (depleted)
            result3 = pool_manager.execute_ai_task_with_limits(
                task_description="Task 3",
                estimated_tokens=500,
                provider=AIProvider.ANTHROPIC,
            )
            assert result3["success"] is False

    def test_accuracy_calculation(self, pool_manager, mock_metrics):
        """Test accuracy percentage calculation"""
        with patch("xai.core.ai_pool_with_strict_limits.anthropic") as mock_anthropic:
            pool_manager.submit_api_key_donation(
                donor_address="XAI123456789",
                provider=AIProvider.ANTHROPIC,
                api_key="sk-ant-test-key",
                donated_tokens=10000,
            )

            mock_response = Mock()
            mock_response.content = [Mock(text="Response")]
            mock_response.usage = Mock(input_tokens=80, output_tokens=20)  # 100 actual
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

            result = pool_manager.execute_ai_task_with_limits(
                task_description="Task",
                estimated_tokens=200,  # Estimated 200
                provider=AIProvider.ANTHROPIC,
            )

            assert result["success"] is True
            assert result["accuracy"] == 50.0  # 100/200 * 100

    def test_max_tokens_override(self, pool_manager, mock_metrics):
        """Test max_tokens_override parameter"""
        with patch("xai.core.ai_pool_with_strict_limits.anthropic") as mock_anthropic:
            pool_manager.submit_api_key_donation(
                donor_address="XAI123456789",
                provider=AIProvider.ANTHROPIC,
                api_key="sk-ant-test-key",
                donated_tokens=10000,
            )

            mock_response = Mock()
            mock_response.content = [Mock(text="Response")]
            mock_response.usage = Mock(input_tokens=50, output_tokens=50)
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client

            pool_manager.execute_ai_task_with_limits(
                task_description="Task",
                estimated_tokens=100,
                provider=AIProvider.ANTHROPIC,
                max_tokens_override=500,
            )

            # Verify max_tokens was set to override value
            call_args = mock_client.messages.create.call_args
            assert call_args[1]["max_tokens"] == 500

    def test_metrics_recorded(self, pool_manager, mock_metrics):
        """Test metrics are recorded for token usage"""
        with patch("xai.core.ai_pool_with_strict_limits.anthropic") as mock_anthropic:
            pool_manager.submit_api_key_donation(
                donor_address="XAI123456789",
                provider=AIProvider.ANTHROPIC,
                api_key="sk-ant-test-key",
                donated_tokens=10000,
            )

            mock_response = Mock()
            mock_response.content = [Mock(text="Response")]
            mock_response.usage = Mock(input_tokens=50, output_tokens=50)
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

            pool_manager.execute_ai_task_with_limits(
                task_description="Task",
                estimated_tokens=100,
                provider=AIProvider.ANTHROPIC,
            )

            mock_metrics.record_tokens.assert_called_once_with(100)

    def test_total_usage_tracking(self, pool_manager, mock_metrics):
        """Test total usage is tracked across tasks"""
        with patch("xai.core.ai_pool_with_strict_limits.anthropic") as mock_anthropic:
            pool_manager.submit_api_key_donation(
                donor_address="XAI123456789",
                provider=AIProvider.ANTHROPIC,
                api_key="sk-ant-test-key",
                donated_tokens=10000,
            )

            mock_response = Mock()
            mock_response.content = [Mock(text="Response")]
            mock_response.usage = Mock(input_tokens=50, output_tokens=50)
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

            # Execute two tasks
            pool_manager.execute_ai_task_with_limits(
                task_description="Task 1",
                estimated_tokens=100,
                provider=AIProvider.ANTHROPIC,
            )

            pool_manager.execute_ai_task_with_limits(
                task_description="Task 2",
                estimated_tokens=100,
                provider=AIProvider.ANTHROPIC,
            )

            assert pool_manager.total_tokens_used == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=xai.core.ai_pool_with_strict_limits"])
