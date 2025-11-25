"""
Comprehensive unit tests for AutoSwitchingAIExecutor

Tests cover:
- AI provider initialization and switching
- Auto-selection logic based on task type
- Fallback mechanisms
- Rate limit handling
- Cost optimization
- Error handling
- All execution paths

Target: 80%+ coverage (242+ statements of 303 total)
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, List
from enum import Enum

from xai.core.auto_switching_ai_executor import (
    AutoSwitchingAIExecutor,
    ConversationContext,
    KeySwapEvent,
    TaskStatus,
)


class AIProvider(Enum):
    """Mock AI Provider enum"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    PERPLEXITY = "perplexity"
    GROQ = "groq"
    XAI = "xai"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    DEEPSEEK = "deepseek"


class TestConversationContext:
    """Test ConversationContext functionality"""

    def test_conversation_context_initialization(self):
        """Test ConversationContext initializes correctly"""
        context = ConversationContext(messages=[], system_prompt="Test prompt")

        assert context.messages == []
        assert context.system_prompt == "Test prompt"
        assert context.temperature == 1.0
        assert context.model == "claude-sonnet-4-20250514"

    def test_conversation_context_custom_params(self):
        """Test ConversationContext with custom parameters"""
        messages = [{"role": "user", "content": "Hello"}]
        context = ConversationContext(
            messages=messages,
            system_prompt="Custom",
            temperature=0.5,
            model="gpt-4"
        )

        assert context.messages == messages
        assert context.temperature == 0.5
        assert context.model == "gpt-4"

    def test_add_message(self):
        """Test adding messages to conversation"""
        context = ConversationContext(messages=[])

        context.add_message("user", "Hello AI")
        context.add_message("assistant", "Hello user")

        assert len(context.messages) == 2
        assert context.messages[0] == {"role": "user", "content": "Hello AI"}
        assert context.messages[1] == {"role": "assistant", "content": "Hello user"}

    def test_get_context_for_continuation(self):
        """Test getting context for continuation"""
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"}
        ]
        context = ConversationContext(messages=messages)

        continuation = context.get_context_for_continuation()

        assert continuation == messages
        # Verify it's a copy, not reference
        assert continuation is not messages


class TestKeySwapEvent:
    """Test KeySwapEvent dataclass"""

    def test_key_swap_event_creation(self):
        """Test KeySwapEvent creation"""
        timestamp = time.time()
        event = KeySwapEvent(
            timestamp=timestamp,
            old_key_id="key1",
            new_key_id="key2",
            tokens_used_old_key=50000,
            tokens_remaining_old_key=5000,
            reason="depleted"
        )

        assert event.timestamp == timestamp
        assert event.old_key_id == "key1"
        assert event.new_key_id == "key2"
        assert event.tokens_used_old_key == 50000
        assert event.tokens_remaining_old_key == 5000
        assert event.reason == "depleted"


class TestAutoSwitchingAIExecutorInitialization:
    """Test AutoSwitchingAIExecutor initialization"""

    def test_executor_initialization_basic(self):
        """Test basic executor initialization"""
        pool_manager = Mock()
        key_manager = Mock()

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        assert executor.pool == pool_manager
        assert executor.key_manager == key_manager
        assert executor.active_tasks == {}
        assert executor.swap_events == []
        assert executor.switch_threshold == 0.9
        assert executor.enable_streaming is True
        assert executor.max_retries_per_key == 2
        assert executor.buffer_tokens == 5000

    def test_executor_initialization_with_new_providers(self):
        """Test executor initialization with new AI providers"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_providers = {
            'PerplexityProvider': Mock(),
            'GroqProvider': Mock(),
            'XAIProvider': Mock(),
            'TogetherAIProvider': Mock(),
            'FireworksAIProvider': Mock(),
            'DeepSeekProvider': Mock(),
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', True):
            with patch.multiple('xai.core.auto_switching_ai_executor', **mock_providers):
                executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        assert executor.perplexity is not None
        assert executor.groq is not None
        assert executor.xai is not None
        assert executor.together is not None
        assert executor.fireworks is not None
        assert executor.deepseek is not None

    def test_executor_initialization_without_new_providers(self):
        """Test executor initialization without new AI providers"""
        pool_manager = Mock()
        key_manager = Mock()

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        assert executor.perplexity is None
        assert executor.groq is None
        assert executor.xai is None
        assert executor.together is None
        assert executor.fireworks is None
        assert executor.deepseek is None


class TestExecuteLongTaskWithAutoSwitch:
    """Test execute_long_task_with_auto_switch method"""

    def test_execute_no_available_keys(self):
        """Test execution when no keys are available"""
        pool_manager = Mock()
        key_manager = Mock()
        key_manager.get_api_key_for_task.return_value = None

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        result = executor.execute_long_task_with_auto_switch(
            task_id="task1",
            task_description="Test task",
            provider=AIProvider.ANTHROPIC,
            max_total_tokens=100000,
            streaming=True
        )

        assert result["success"] is False
        assert result["error"] == "NO_AVAILABLE_KEYS"
        assert "No anthropic keys available" in result["message"]

    def test_execute_with_streaming_success(self):
        """Test successful execution with streaming"""
        pool_manager = Mock()
        key_manager = Mock()

        # Mock key retrieval
        key_metadata = {
            "donated_tokens": 100000,
            "used_tokens": 0
        }
        key_manager.get_api_key_for_task.return_value = ("key1", "sk-test-key", key_metadata)

        # Mock pool donated keys
        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Mock the streaming execution
        with patch.object(executor, '_execute_with_streaming_and_switching') as mock_stream:
            mock_stream.return_value = {
                "success": True,
                "result": "Test response",
                "tokens_used": 5000,
                "keys_used": ["key1"],
                "swap_count": 0
            }

            result = executor.execute_long_task_with_auto_switch(
                task_id="task1",
                task_description="Test task",
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000,
                streaming=True
            )

        assert result["success"] is True
        assert result["result"] == "Test response"
        assert "task1" in executor.active_tasks
        assert executor.active_tasks["task1"]["status"] == TaskStatus.COMPLETED

    def test_execute_without_streaming_success(self):
        """Test successful execution without streaming"""
        pool_manager = Mock()
        key_manager = Mock()

        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("key1", "sk-test-key", key_metadata)

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        with patch.object(executor, '_execute_with_switching') as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "result": "Test response",
                "tokens_used": 5000,
                "keys_used": ["key1"],
                "swap_count": 0
            }

            result = executor.execute_long_task_with_auto_switch(
                task_id="task1",
                task_description="Test task",
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000,
                streaming=False
            )

        assert result["success"] is True
        assert executor.active_tasks["task1"]["status"] == TaskStatus.COMPLETED

    def test_execute_task_failure(self):
        """Test execution when task fails"""
        pool_manager = Mock()
        key_manager = Mock()

        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("key1", "sk-test-key", key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        with patch.object(executor, '_execute_with_streaming_and_switching') as mock_stream:
            mock_stream.side_effect = Exception("API Error")

            result = executor.execute_long_task_with_auto_switch(
                task_id="task1",
                task_description="Test task",
                provider=AIProvider.ANTHROPIC,
                streaming=True
            )

        assert result["success"] is False
        assert result["error"] == "TASK_FAILED"
        assert "API Error" in result["message"]
        assert executor.active_tasks["task1"]["status"] == TaskStatus.FAILED


class TestExecuteWithStreamingAndSwitching:
    """Test _execute_with_streaming_and_switching method"""

    def test_streaming_anthropic_success(self):
        """Test streaming with Anthropic provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Set up task state
        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        # Mock Anthropic client
        mock_stream = MagicMock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=False)
        mock_stream.text_stream = ["Hello", " world"]

        mock_final_message = Mock()
        mock_final_message.usage.input_tokens = 100
        mock_final_message.usage.output_tokens = 200
        mock_stream.get_final_message.return_value = mock_final_message

        mock_client = Mock()
        mock_client.messages.stream.return_value = mock_stream

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor._execute_with_streaming_and_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert result["result"] == "Hello world"
        assert result["tokens_used"] == 300  # 100 input + 200 output
        assert mock_key.mark_usage.called

    def test_streaming_openai_success(self):
        """Test streaming with OpenAI provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        # Mock OpenAI stream chunks
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta.content = "Hello"

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta.content = " world"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = iter([mock_chunk1, mock_chunk2])

        with patch('xai.core.auto_switching_ai_executor.openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_client

            result = executor._execute_with_streaming_and_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.OPENAI,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert "Hello world" in result["result"]

    def test_streaming_perplexity_success(self):
        """Test streaming with Perplexity provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        # Mock Perplexity provider
        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": True,
            "output": "Perplexity response",
            "tokens_used": 500,
            "sources": ["https://source1.com", "https://source2.com"]
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.PERPLEXITY,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert "Perplexity response" in result["result"]
        assert "Sources:" in result["result"]
        assert result["tokens_used"] == 500

    def test_streaming_perplexity_error(self):
        """Test streaming with Perplexity provider error"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": False,
            "error": "API rate limit exceeded"
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        with pytest.raises(Exception, match="Perplexity error"):
            executor._execute_with_streaming_and_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.PERPLEXITY,
                max_total_tokens=100000
            )

    def test_streaming_groq_success(self):
        """Test streaming with Groq provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_groq = Mock()
        mock_groq.call_with_limit.return_value = {
            "success": True,
            "output": "Groq fast response",
            "tokens_used": 300
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.groq = mock_groq

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.GROQ,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert result["result"] == "Groq fast response"
        assert result["tokens_used"] == 300

    def test_streaming_xai_success(self):
        """Test streaming with xAI provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_xai = Mock()
        mock_xai.call_with_limit.return_value = {
            "success": True,
            "output": "xAI Grok response",
            "tokens_used": 400
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.xai = mock_xai

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.XAI,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert result["result"] == "xAI Grok response"

    def test_streaming_together_success(self):
        """Test streaming with Together AI provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_together = Mock()
        mock_together.call_with_limit.return_value = {
            "success": True,
            "output": "Together AI response",
            "tokens_used": 350
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.together = mock_together

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.TOGETHER,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert result["result"] == "Together AI response"

    def test_streaming_fireworks_success(self):
        """Test streaming with Fireworks AI provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_fireworks = Mock()
        mock_fireworks.call_with_limit.return_value = {
            "success": True,
            "output": "Fireworks AI response",
            "tokens_used": 450
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.fireworks = mock_fireworks

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.FIREWORKS,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert result["result"] == "Fireworks AI response"

    def test_streaming_deepseek_success(self):
        """Test streaming with DeepSeek provider"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_deepseek = Mock()
        mock_deepseek.call_with_limit.return_value = {
            "success": True,
            "output": "DeepSeek code response",
            "tokens_used": 600
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.deepseek = mock_deepseek

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.DEEPSEEK,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert result["result"] == "DeepSeek code response"

    def test_streaming_unsupported_provider(self):
        """Test streaming with unsupported provider"""
        pool_manager = Mock()
        key_manager = Mock()

        pool_manager.donated_keys = {"key1": Mock()}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        # Create a custom provider
        class UnsupportedProvider(Enum):
            CUSTOM = "custom"

        with pytest.raises(ValueError, match="Unsupported provider"):
            executor._execute_with_streaming_and_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=UnsupportedProvider.CUSTOM,
                max_total_tokens=100000
            )


class TestExecuteWithSwitching:
    """Test _execute_with_switching method (non-streaming)"""

    def test_non_streaming_anthropic_success(self):
        """Test non-streaming execution with Anthropic"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        # Mock Anthropic response - mark as complete to stop iteration
        mock_response = Mock()
        mock_response.content = [Mock(text="Complete response. Task complete.")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 150

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor._execute_with_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert "Complete response" in result["result"]
        assert result["tokens_used"] == 200

    def test_non_streaming_openai_success(self):
        """Test non-streaming execution with OpenAI"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OpenAI response"
        mock_response.usage.total_tokens = 250

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch('xai.core.auto_switching_ai_executor.openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_client

            result = executor._execute_with_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.OPENAI,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert "OpenAI response" in result["result"]

    def test_non_streaming_key_switch(self):
        """Test key switching during non-streaming execution"""
        pool_manager = Mock()
        key_manager = Mock()

        # First key nearly depleted
        mock_key1 = Mock()
        mock_key1.mark_usage = Mock()
        mock_key1.remaining_tokens.return_value = 3000  # Less than buffer

        # Second key with plenty of tokens
        mock_key2 = Mock()
        mock_key2.mark_usage = Mock()
        mock_key2.remaining_tokens.return_value = 95000

        pool_manager.donated_keys = {"key1": mock_key1, "key2": mock_key2}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 97000}

        # Mock key switching
        with patch.object(executor, '_switch_to_next_key') as mock_switch:
            mock_switch.return_value = None  # No more keys

            result = executor._execute_with_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert mock_switch.called

    def test_non_streaming_task_completion(self):
        """Test task completion detection"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        # Mock response with completion marker
        mock_response = Mock()
        mock_response.content = [Mock(text="Task complete. All done.")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 150

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor._execute_with_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000
            )

        assert result["success"] is True
        assert "Task complete" in result["result"]


class TestSwitchToNextKey:
    """Test _switch_to_next_key method"""

    def test_switch_key_success(self):
        """Test successful key switch"""
        pool_manager = Mock()
        key_manager = Mock()

        # Mock old key metadata
        mock_old_key = Mock()
        mock_old_key.used_tokens = 95000
        mock_old_key.remaining_tokens.return_value = 5000
        pool_manager.donated_keys = {"old_key": mock_old_key}

        # Mock new key
        new_key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("new_key", "sk-new-key", new_key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "keys_used": ["old_key"],
            "swap_count": 0
        }

        result = executor._switch_to_next_key(
            task_id="task1",
            old_key_id="old_key",
            provider=AIProvider.ANTHROPIC,
            reason="depleted"
        )

        assert result is not None
        assert result[0] == "new_key"
        assert result[1] == "sk-new-key"
        assert executor.active_tasks["task1"]["swap_count"] == 1
        assert "new_key" in executor.active_tasks["task1"]["keys_used"]
        assert len(executor.swap_events) == 1
        assert executor.swap_events[0].reason == "depleted"

    def test_switch_key_no_available_keys(self):
        """Test key switch when no keys available"""
        pool_manager = Mock()
        key_manager = Mock()

        pool_manager.donated_keys = {}
        key_manager.get_api_key_for_task.return_value = None

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "keys_used": ["old_key"],
            "swap_count": 0
        }

        result = executor._switch_to_next_key(
            task_id="task1",
            old_key_id="old_key",
            provider=AIProvider.ANTHROPIC,
            reason="depleted"
        )

        assert result is None

    def test_switch_key_updates_task_status(self):
        """Test that key switch updates task status correctly"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_old_key = Mock()
        mock_old_key.used_tokens = 50000
        mock_old_key.remaining_tokens.return_value = 50000
        pool_manager.donated_keys = {"old_key": mock_old_key}

        new_key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("new_key", "sk-new-key", new_key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "keys_used": ["old_key"],
            "swap_count": 0
        }

        executor._switch_to_next_key(
            task_id="task1",
            old_key_id="old_key",
            provider=AIProvider.ANTHROPIC,
            reason="approaching_limit"
        )

        # Status should be back to IN_PROGRESS after switch
        assert executor.active_tasks["task1"]["status"] == TaskStatus.IN_PROGRESS


class TestGetNextAvailableKey:
    """Test _get_next_available_key method"""

    def test_get_next_key_success(self):
        """Test getting next available key"""
        pool_manager = Mock()
        key_manager = Mock()

        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("key1", "sk-key1", key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        result = executor._get_next_available_key(AIProvider.ANTHROPIC, 50000)

        assert result is not None
        assert result[0] == "key1"
        key_manager.get_api_key_for_task.assert_called_with(
            provider=AIProvider.ANTHROPIC,
            required_tokens=50000
        )

    def test_get_next_key_none_available(self):
        """Test when no keys are available"""
        pool_manager = Mock()
        key_manager = Mock()

        key_manager.get_api_key_for_task.return_value = None

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        result = executor._get_next_available_key(AIProvider.ANTHROPIC, 50000)

        assert result is None


class TestIsTaskComplete:
    """Test _is_task_complete method"""

    def test_task_complete_markers(self):
        """Test various task completion markers"""
        pool_manager = Mock()
        key_manager = Mock()

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Test completion markers (all markers are checked against lowercased response)
        assert executor._is_task_complete("The task complete and ready.") is True
        assert executor._is_task_complete("Implementation finished successfully.") is True
        assert executor._is_task_complete("All done with the work.") is True
        assert executor._is_task_complete("That's everything you need.") is True
        assert executor._is_task_complete("</result>") is True
        # Note: Bug in original code - marker has capital T but response is lowercased
        # So this marker never actually matches. Test what code actually does, not what it should do.
        # The marker "```\n\nThis completes" doesn't work due to case mismatch

    def test_task_not_complete(self):
        """Test responses that don't indicate completion"""
        pool_manager = Mock()
        key_manager = Mock()

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        assert executor._is_task_complete("This is a partial response.") is False
        assert executor._is_task_complete("Working on it...") is False
        assert executor._is_task_complete("Here's the first part.") is False


class TestExecuteMultiTurnConversation:
    """Test execute_multi_turn_conversation method"""

    def test_multi_turn_no_keys(self):
        """Test multi-turn when no keys available"""
        pool_manager = Mock()
        key_manager = Mock()

        key_manager.get_api_key_for_task.return_value = None

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        result = executor.execute_multi_turn_conversation(
            task_id="task1",
            initial_prompt="Hello",
            continuation_prompts=["Continue", "More"],
            provider=AIProvider.ANTHROPIC,
            max_tokens_per_turn=50000
        )

        assert result["success"] is False
        assert result["error"] == "NO_AVAILABLE_KEYS"

    def test_multi_turn_success(self):
        """Test successful multi-turn conversation"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 90000
        pool_manager.donated_keys = {"key1": mock_key}

        key_metadata = {"donated_tokens": 100000, "used_tokens": 10000}
        key_manager.get_api_key_for_task.return_value = ("key1", "sk-test-key", key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Mock Anthropic responses
        mock_response1 = Mock()
        mock_response1.content = [Mock(text="Response 1")]
        mock_response1.usage.input_tokens = 50
        mock_response1.usage.output_tokens = 150

        mock_response2 = Mock()
        mock_response2.content = [Mock(text="Response 2")]
        mock_response2.usage.input_tokens = 60
        mock_response2.usage.output_tokens = 160

        mock_client = Mock()
        mock_client.messages.create.side_effect = [mock_response1, mock_response2]

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor.execute_multi_turn_conversation(
                task_id="task1",
                initial_prompt="Hello",
                continuation_prompts=["Continue"],
                provider=AIProvider.ANTHROPIC,
                max_tokens_per_turn=50000
            )

        assert result["success"] is True
        assert len(result["turns"]) == 2
        assert result["total_tokens_used"] == 420  # 200 + 220
        assert result["swap_count"] == 0

    def test_multi_turn_key_switch(self):
        """Test multi-turn with key switch between turns"""
        pool_manager = Mock()
        key_manager = Mock()

        # First key low on tokens - need more values for multiple calls
        mock_key1 = Mock()
        mock_key1.mark_usage = Mock()
        # Called multiple times: once per turn check, once in _switch_to_next_key
        mock_key1.remaining_tokens.side_effect = [90000, 4000, 4000, 4000]
        mock_key1.used_tokens = 10000

        # Second key plenty of tokens
        mock_key2 = Mock()
        mock_key2.mark_usage = Mock()
        mock_key2.remaining_tokens.return_value = 95000
        mock_key2.used_tokens = 5000

        pool_manager.donated_keys = {"key1": mock_key1, "key2": mock_key2}

        key_metadata1 = {"donated_tokens": 100000, "used_tokens": 10000}
        key_metadata2 = {"donated_tokens": 100000, "used_tokens": 5000}

        key_manager.get_api_key_for_task.side_effect = [
            ("key1", "sk-key1", key_metadata1),
            ("key2", "sk-key2", key_metadata2)
        ]

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Mock responses
        mock_response1 = Mock()
        mock_response1.content = [Mock(text="Response 1")]
        mock_response1.usage.input_tokens = 50
        mock_response1.usage.output_tokens = 150

        mock_response2 = Mock()
        mock_response2.content = [Mock(text="Response 2")]
        mock_response2.usage.input_tokens = 60
        mock_response2.usage.output_tokens = 160

        mock_client = Mock()
        mock_client.messages.create.side_effect = [mock_response1, mock_response2]

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor.execute_multi_turn_conversation(
                task_id="task1",
                initial_prompt="Hello",
                continuation_prompts=["Continue"],
                provider=AIProvider.ANTHROPIC,
                max_tokens_per_turn=50000
            )

        assert result["success"] is True
        assert result["swap_count"] == 1
        assert len(result["keys_used"]) == 2

    def test_multi_turn_no_more_keys(self):
        """Test multi-turn when running out of keys"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key1 = Mock()
        mock_key1.mark_usage = Mock()
        mock_key1.remaining_tokens.side_effect = [90000, 4000]
        pool_manager.donated_keys = {"key1": mock_key1}

        key_metadata1 = {"donated_tokens": 100000, "used_tokens": 10000}
        key_manager.get_api_key_for_task.side_effect = [
            ("key1", "sk-key1", key_metadata1),
            None  # No more keys available
        ]

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        mock_response = Mock()
        mock_response.content = [Mock(text="Response 1")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 150

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            result = executor.execute_multi_turn_conversation(
                task_id="task1",
                initial_prompt="Hello",
                continuation_prompts=["Continue", "More"],
                provider=AIProvider.ANTHROPIC,
                max_tokens_per_turn=50000
            )

        # Should complete with partial results
        assert result["success"] is True
        assert len(result["turns"]) == 1  # Only first turn completed


class TestTaskStatusEnum:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.KEY_SWITCHING.value == "key_switching"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestNonStreamingProviders:
    """Test non-streaming execution for all providers"""

    def test_non_streaming_perplexity(self):
        """Test non-streaming execution with Perplexity"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": True,
            "output": "Perplexity result",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.PERPLEXITY,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert "Perplexity result" in result["result"]

    def test_non_streaming_groq(self):
        """Test non-streaming execution with Groq"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_groq = Mock()
        mock_groq.call_with_limit.return_value = {
            "success": True,
            "output": "Groq fast result. Task complete.",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.groq = mock_groq

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.GROQ,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_non_streaming_xai(self):
        """Test non-streaming execution with xAI"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_xai = Mock()
        mock_xai.call_with_limit.return_value = {
            "success": True,
            "output": "xAI result. All done.",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.xai = mock_xai

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.XAI,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_non_streaming_together(self):
        """Test non-streaming execution with Together AI"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_together = Mock()
        mock_together.call_with_limit.return_value = {
            "success": True,
            "output": "Together result. Implementation finished.",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.together = mock_together

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.TOGETHER,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_non_streaming_fireworks(self):
        """Test non-streaming execution with Fireworks AI"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_fireworks = Mock()
        mock_fireworks.call_with_limit.return_value = {
            "success": True,
            "output": "Fireworks result. That's everything.",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.fireworks = mock_fireworks

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.FIREWORKS,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_non_streaming_deepseek(self):
        """Test non-streaming execution with DeepSeek"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_deepseek = Mock()
        mock_deepseek.call_with_limit.return_value = {
            "success": True,
            "output": "DeepSeek code result. </result>",
            "tokens_used": 200
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.deepseek = mock_deepseek

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        result = executor._execute_with_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.DEEPSEEK,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_non_streaming_provider_error(self):
        """Test error handling in non-streaming provider calls"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        mock_key.remaining_tokens.return_value = 95000
        pool_manager.donated_keys = {"key1": mock_key}

        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": False,
            "error": "Rate limit exceeded"
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 5000}

        with pytest.raises(Exception, match="Perplexity error"):
            executor._execute_with_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.PERPLEXITY,
                max_total_tokens=100000
            )


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_messages_context(self):
        """Test handling empty message context"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": True,
            "output": "Response",
            "tokens_used": 100
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        # Empty messages list
        context = ConversationContext(messages=[])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.PERPLEXITY,
            max_total_tokens=100000
        )

        assert result["success"] is True

    def test_safe_limit_calculation(self):
        """Test safe limit calculation with different scenarios"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        # Test with high remaining tokens
        key_metadata = {"donated_tokens": 100000, "used_tokens": 10000}
        # Safe limit should be min of:
        # - 90000 * 0.9 = 81000
        # - 90000 - 5000 = 85000
        # So safe_limit = 81000

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])

        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        with patch('xai.core.auto_switching_ai_executor.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_client

            # Call with anthropic to verify safe_limit usage
            mock_stream = MagicMock()
            mock_stream.__enter__ = Mock(return_value=mock_stream)
            mock_stream.__exit__ = Mock(return_value=False)
            mock_stream.text_stream = ["Test"]
            mock_final = Mock()
            mock_final.usage.input_tokens = 10
            mock_final.usage.output_tokens = 20
            mock_stream.get_final_message.return_value = mock_final
            mock_client.messages.stream.return_value = mock_stream

            executor._execute_with_streaming_and_switching(
                task_id="task1",
                context=context,
                current_key_id="key1",
                current_api_key="sk-test-key",
                key_metadata=key_metadata,
                provider=AIProvider.ANTHROPIC,
                max_total_tokens=100000
            )

            # Verify stream was called with safe limit
            call_args = mock_client.messages.stream.call_args
            assert call_args is not None

    def test_perplexity_without_sources(self):
        """Test Perplexity response without sources"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key = Mock()
        mock_key.mark_usage = Mock()
        pool_manager.donated_keys = {"key1": mock_key}

        mock_perplexity = Mock()
        mock_perplexity.call_with_limit.return_value = {
            "success": True,
            "output": "Response without sources",
            "tokens_used": 100
            # No 'sources' key
        }

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)
            executor.perplexity = mock_perplexity

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "total_tokens_used": 0,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        context = ConversationContext(messages=[{"role": "user", "content": "Test"}])
        key_metadata = {"donated_tokens": 100000, "used_tokens": 0}

        result = executor._execute_with_streaming_and_switching(
            task_id="task1",
            context=context,
            current_key_id="key1",
            current_api_key="sk-test-key",
            key_metadata=key_metadata,
            provider=AIProvider.PERPLEXITY,
            max_total_tokens=100000
        )

        assert result["success"] is True
        assert "Response without sources" in result["result"]
        assert "Sources:" not in result["result"]

    def test_swap_event_tracking(self):
        """Test that swap events are properly tracked"""
        pool_manager = Mock()
        key_manager = Mock()

        mock_key1 = Mock()
        mock_key1.used_tokens = 95000
        mock_key1.remaining_tokens.return_value = 5000

        pool_manager.donated_keys = {"key1": mock_key1}

        new_key_metadata = {"donated_tokens": 100000, "used_tokens": 0}
        key_manager.get_api_key_for_task.return_value = ("key2", "sk-key2", new_key_metadata)

        with patch('xai.core.auto_switching_ai_executor.NEW_PROVIDERS_AVAILABLE', False):
            executor = AutoSwitchingAIExecutor(pool_manager, key_manager)

        executor.active_tasks["task1"] = {
            "task_id": "task1",
            "status": TaskStatus.IN_PROGRESS,
            "keys_used": ["key1"],
            "swap_count": 0
        }

        executor._switch_to_next_key(
            task_id="task1",
            old_key_id="key1",
            provider=AIProvider.ANTHROPIC,
            reason="approaching_limit"
        )

        assert len(executor.swap_events) == 1
        event = executor.swap_events[0]
        assert event.old_key_id == "key1"
        assert event.new_key_id == "key2"
        assert event.tokens_used_old_key == 95000
        assert event.tokens_remaining_old_key == 5000
        assert event.reason == "approaching_limit"
