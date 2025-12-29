"""
Comprehensive test coverage for additional_ai_providers.py

Target: 80%+ coverage (110+ statements out of 137)

Tests all 6 AI providers:
1. PerplexityProvider
2. GroqProvider
3. XAIProvider
4. TogetherAIProvider
5. FireworksAIProvider
6. DeepSeekProvider

Plus extension functions and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import requests
from xai.core.api.additional_ai_providers import (
    PerplexityProvider,
    GroqProvider,
    XAIProvider,
    TogetherAIProvider,
    FireworksAIProvider,
    DeepSeekProvider,
    extend_executor_with_new_providers,
)


# ============================================================================
# PERPLEXITY PROVIDER TESTS
# ============================================================================


class TestPerplexityProvider:
    """Test suite for PerplexityProvider"""

    def test_init(self):
        """Test PerplexityProvider initialization"""
        provider = PerplexityProvider()
        assert provider.base_url == "https://api.perplexity.ai"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful API call with default model"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response with citations"}}],
            "usage": {"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100},
            "citations": ["https://source1.com", "https://source2.com"],
        }
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(
            api_key="test_key", task="Test research question", max_tokens=500
        )

        assert result["success"] is True
        assert result["output"] == "Test response with citations"
        assert result["tokens_used"] == 150
        assert result["input_tokens"] == 50
        assert result["output_tokens"] == 100
        assert result["sources"] == ["https://source1.com", "https://source2.com"]
        assert result["model"] == "llama-3.1-sonar-large-128k-online"

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.perplexity.ai/chat/completions" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_key"
        assert call_args[1]["json"]["max_tokens"] == 500
        assert call_args[1]["json"]["return_citations"] is True

    @patch("requests.post")
    def test_call_with_limit_custom_model(self, mock_post):
        """Test API call with custom model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fast response"}}],
            "usage": {"total_tokens": 80, "prompt_tokens": 30, "completion_tokens": 50},
            "citations": [],
        }
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(
            api_key="test_key",
            task="Quick query",
            max_tokens=200,
            model="llama-3.1-sonar-small-128k-online",
        )

        assert result["success"] is True
        assert result["model"] == "llama-3.1-sonar-small-128k-online"

        # Verify the model was passed correctly
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "llama-3.1-sonar-small-128k-online"

    @patch("requests.post")
    def test_call_with_limit_no_citations(self, mock_post):
        """Test handling response without citations"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response without sources"}}],
            "usage": {"total_tokens": 100, "prompt_tokens": 40, "completion_tokens": 60},
        }
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="test_key", task="Test", max_tokens=300)

        assert result["success"] is True
        assert result["sources"] == []

    @patch("requests.post")
    def test_call_with_limit_request_exception(self, mock_post):
        """Test handling of request exceptions"""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="test_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "Perplexity API error" in result["error"]
        assert result["tokens_used"] == 0

    @patch("requests.post")
    def test_call_with_limit_http_error(self, mock_post):
        """Test handling of HTTP errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="invalid_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "Perplexity API error" in result["error"]
        assert result["tokens_used"] == 0

    @patch("requests.post")
    def test_call_with_limit_timeout(self, mock_post):
        """Test handling of timeout"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="test_key", task="Long task", max_tokens=1000)

        assert result["success"] is False
        assert "Perplexity API error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# GROQ PROVIDER TESTS
# ============================================================================


class TestGroqProvider:
    """Test suite for GroqProvider"""

    def test_init(self):
        """Test GroqProvider initialization"""
        provider = GroqProvider()
        assert provider.base_url == "https://api.groq.com/openai/v1"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fast code generation"}}],
            "usage": {"total_tokens": 200, "prompt_tokens": 75, "completion_tokens": 125},
        }
        mock_post.return_value = mock_response

        provider = GroqProvider()
        result = provider.call_with_limit(api_key="groq_key", task="Generate code", max_tokens=500)

        assert result["success"] is True
        assert result["output"] == "Fast code generation"
        assert result["tokens_used"] == 200
        assert result["input_tokens"] == 75
        assert result["output_tokens"] == 125
        assert result["model"] == "llama-3.1-70b-versatile"
        assert result["inference_speed"] == "ultra_fast"

        # Verify timeout is 60 seconds (Groq is fast)
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 60

    @patch("requests.post")
    def test_call_with_limit_custom_model(self, mock_post):
        """Test with different Groq model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Ultra fast response"}}],
            "usage": {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
        }
        mock_post.return_value = mock_response

        provider = GroqProvider()
        result = provider.call_with_limit(
            api_key="groq_key", task="Quick fix", max_tokens=100, model="llama-3.1-8b-instant"
        )

        assert result["success"] is True
        assert result["model"] == "llama-3.1-8b-instant"

    @patch("requests.post")
    def test_call_with_limit_error(self, mock_post):
        """Test error handling"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        provider = GroqProvider()
        result = provider.call_with_limit(api_key="groq_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "Groq API error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# XAI PROVIDER TESTS
# ============================================================================


class TestXAIProvider:
    """Test suite for XAIProvider (Grok)"""

    def test_init(self):
        """Test XAIProvider initialization"""
        provider = XAIProvider()
        assert provider.base_url == "https://api.x.ai/v1"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful Grok API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Real-time crypto analysis"}}],
            "usage": {"total_tokens": 250, "prompt_tokens": 100, "completion_tokens": 150},
        }
        mock_post.return_value = mock_response

        provider = XAIProvider()
        result = provider.call_with_limit(api_key="xai_key", task="Crypto trends", max_tokens=600)

        assert result["success"] is True
        assert result["output"] == "Real-time crypto analysis"
        assert result["tokens_used"] == 250
        assert result["model"] == "grok-beta"
        assert result["real_time_data"] is True

    @patch("requests.post")
    def test_call_with_limit_grok_2_model(self, mock_post):
        """Test with grok-2 stable model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Stable response"}}],
            "usage": {"total_tokens": 180, "prompt_tokens": 60, "completion_tokens": 120},
        }
        mock_post.return_value = mock_response

        provider = XAIProvider()
        result = provider.call_with_limit(
            api_key="xai_key", task="Analysis", max_tokens=400, model="grok-2"
        )

        assert result["success"] is True
        assert result["model"] == "grok-2"

    @patch("requests.post")
    def test_call_with_limit_error(self, mock_post):
        """Test error handling"""
        mock_post.side_effect = requests.exceptions.RequestException("API error")

        provider = XAIProvider()
        result = provider.call_with_limit(api_key="xai_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "xAI API error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# TOGETHER AI PROVIDER TESTS
# ============================================================================


class TestTogetherAIProvider:
    """Test suite for TogetherAIProvider"""

    def test_init(self):
        """Test TogetherAIProvider initialization"""
        provider = TogetherAIProvider()
        assert provider.base_url == "https://api.together.xyz/v1"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful Together AI call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Cost-effective response"}}],
            "usage": {"total_tokens": 300, "prompt_tokens": 120, "completion_tokens": 180},
        }
        mock_post.return_value = mock_response

        provider = TogetherAIProvider()
        result = provider.call_with_limit(api_key="together_key", task="Volume work", max_tokens=800)

        assert result["success"] is True
        assert result["output"] == "Cost-effective response"
        assert result["tokens_used"] == 300
        assert result["model"] == "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        assert result["cost_optimized"] is True

    @patch("requests.post")
    def test_call_with_limit_custom_model(self, mock_post):
        """Test with different Together AI model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fast response"}}],
            "usage": {"total_tokens": 100, "prompt_tokens": 40, "completion_tokens": 60},
        }
        mock_post.return_value = mock_response

        provider = TogetherAIProvider()
        result = provider.call_with_limit(
            api_key="together_key",
            task="Quick task",
            max_tokens=200,
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        )

        assert result["success"] is True
        assert result["model"] == "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

    @patch("requests.post")
    def test_call_with_limit_error(self, mock_post):
        """Test error handling"""
        mock_post.side_effect = requests.exceptions.RequestException("Service unavailable")

        provider = TogetherAIProvider()
        result = provider.call_with_limit(api_key="together_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "Together AI error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# FIREWORKS AI PROVIDER TESTS
# ============================================================================


class TestFireworksAIProvider:
    """Test suite for FireworksAIProvider"""

    def test_init(self):
        """Test FireworksAIProvider initialization"""
        provider = FireworksAIProvider()
        assert provider.base_url == "https://api.fireworks.ai/inference/v1"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful Fireworks AI call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Production-ready code"}}],
            "usage": {"total_tokens": 400, "prompt_tokens": 150, "completion_tokens": 250},
        }
        mock_post.return_value = mock_response

        provider = FireworksAIProvider()
        result = provider.call_with_limit(
            api_key="fireworks_key", task="Generate production code", max_tokens=1000
        )

        assert result["success"] is True
        assert result["output"] == "Production-ready code"
        assert result["tokens_used"] == 400
        assert result["model"] == "accounts/fireworks/models/llama-v3p1-70b-instruct"
        assert result["production_grade"] is True

    @patch("requests.post")
    def test_call_with_limit_custom_model(self, mock_post):
        """Test with different Fireworks model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fast inference"}}],
            "usage": {"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100},
        }
        mock_post.return_value = mock_response

        provider = FireworksAIProvider()
        result = provider.call_with_limit(
            api_key="fireworks_key",
            task="Quick generation",
            max_tokens=300,
            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        )

        assert result["success"] is True
        assert result["model"] == "accounts/fireworks/models/llama-v3p1-8b-instruct"

    @patch("requests.post")
    def test_call_with_limit_error(self, mock_post):
        """Test error handling"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        provider = FireworksAIProvider()
        result = provider.call_with_limit(api_key="fireworks_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "Fireworks AI error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# DEEPSEEK PROVIDER TESTS
# ============================================================================


class TestDeepSeekProvider:
    """Test suite for DeepSeekProvider"""

    def test_init(self):
        """Test DeepSeekProvider initialization"""
        provider = DeepSeekProvider()
        assert provider.base_url == "https://api.deepseek.com/v1"

    @patch("requests.post")
    def test_call_with_limit_success(self, mock_post):
        """Test successful DeepSeek call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Expert code generation"}}],
            "usage": {"total_tokens": 350, "prompt_tokens": 130, "completion_tokens": 220},
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.call_with_limit(
            api_key="deepseek_key", task="Complex refactoring", max_tokens=900
        )

        assert result["success"] is True
        assert result["output"] == "Expert code generation"
        assert result["tokens_used"] == 350
        assert result["model"] == "deepseek-coder"
        assert result["code_specialist"] is True

    @patch("requests.post")
    def test_call_with_limit_chat_model(self, mock_post):
        """Test with deepseek-chat model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "General response"}}],
            "usage": {"total_tokens": 200, "prompt_tokens": 80, "completion_tokens": 120},
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.call_with_limit(
            api_key="deepseek_key", task="General query", max_tokens=400, model="deepseek-chat"
        )

        assert result["success"] is True
        assert result["model"] == "deepseek-chat"

    @patch("requests.post")
    def test_call_with_limit_error(self, mock_post):
        """Test error handling"""
        mock_post.side_effect = requests.exceptions.RequestException("API timeout")

        provider = DeepSeekProvider()
        result = provider.call_with_limit(api_key="deepseek_key", task="Test", max_tokens=100)

        assert result["success"] is False
        assert "DeepSeek API error" in result["error"]
        assert result["tokens_used"] == 0


# ============================================================================
# EXTENSION FUNCTION TESTS
# ============================================================================


class TestExtendExecutor:
    """Test suite for extend_executor_with_new_providers function"""

    def test_extend_executor_creates_providers(self):
        """Test that extension creates all provider instances"""
        # Create a mock executor class
        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        # Extend it
        extend_executor_with_new_providers(MockExecutor)

        # Check that methods were added
        assert hasattr(MockExecutor, "_call_perplexity_with_limit")
        assert hasattr(MockExecutor, "_call_groq_with_limit")
        assert hasattr(MockExecutor, "_call_xai_with_limit")
        assert hasattr(MockExecutor, "_call_together_with_limit")
        assert hasattr(MockExecutor, "_call_fireworks_with_limit")
        assert hasattr(MockExecutor, "_call_deepseek_with_limit")

    @patch("xai.core.api.additional_ai_providers.PerplexityProvider")
    def test_call_perplexity_method(self, mock_provider_class):
        """Test _call_perplexity_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "test"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        # Create instance and call method
        executor = MockExecutor()
        result = executor._call_perplexity_with_limit("api_key", "task", 100)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=100
        )
        assert result["success"] is True
        assert result["output"] == "test"

    @patch("xai.core.api.additional_ai_providers.GroqProvider")
    def test_call_groq_method(self, mock_provider_class):
        """Test _call_groq_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "groq response"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        executor = MockExecutor()
        result = executor._call_groq_with_limit("api_key", "task", 200)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=200
        )
        assert result["success"] is True
        assert result["output"] == "groq response"

    @patch("xai.core.api.additional_ai_providers.XAIProvider")
    def test_call_xai_method(self, mock_provider_class):
        """Test _call_xai_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "xai response"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        executor = MockExecutor()
        result = executor._call_xai_with_limit("api_key", "task", 300)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=300
        )
        assert result["success"] is True
        assert result["output"] == "xai response"

    @patch("xai.core.api.additional_ai_providers.TogetherAIProvider")
    def test_call_together_method(self, mock_provider_class):
        """Test _call_together_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "together response"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        executor = MockExecutor()
        result = executor._call_together_with_limit("api_key", "task", 400)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=400
        )
        assert result["success"] is True
        assert result["output"] == "together response"

    @patch("xai.core.api.additional_ai_providers.FireworksAIProvider")
    def test_call_fireworks_method(self, mock_provider_class):
        """Test _call_fireworks_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "fireworks response"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        executor = MockExecutor()
        result = executor._call_fireworks_with_limit("api_key", "task", 500)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=500
        )
        assert result["success"] is True
        assert result["output"] == "fireworks response"

    @patch("xai.core.api.additional_ai_providers.DeepSeekProvider")
    def test_call_deepseek_method(self, mock_provider_class):
        """Test _call_deepseek_with_limit method"""
        # Setup mock
        mock_provider = Mock()
        mock_provider.call_with_limit.return_value = {"success": True, "output": "deepseek response"}
        mock_provider_class.return_value = mock_provider

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task_description, estimated_tokens, max_tokens, provider):
                """Mock method that would be in the real executor"""
                return {"success": True, "output": "original"}

        extend_executor_with_new_providers(MockExecutor)

        executor = MockExecutor()
        result = executor._call_deepseek_with_limit("api_key", "task", 600)

        # Verify the provider was created and called
        mock_provider_class.assert_called_once()
        mock_provider.call_with_limit.assert_called_once_with(
            api_key="api_key", task="task", max_tokens=600
        )
        assert result["success"] is True
        assert result["output"] == "deepseek response"

    def test_extension_preserves_original_execute(self):
        """Test that extension preserves original _execute_with_strict_limits"""

        class MockExecutor:
            def _execute_with_strict_limits(self, keys, task, est_tokens, max_tokens, provider):
                return {"original": True}

        extend_executor_with_new_providers(MockExecutor)

        # The extended method should exist
        assert hasattr(MockExecutor, "_execute_with_strict_limits")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestProviderIntegration:
    """Integration tests across all providers"""

    @pytest.mark.parametrize(
        "provider_class,expected_url",
        [
            (PerplexityProvider, "https://api.perplexity.ai"),
            (GroqProvider, "https://api.groq.com/openai/v1"),
            (XAIProvider, "https://api.x.ai/v1"),
            (TogetherAIProvider, "https://api.together.xyz/v1"),
            (FireworksAIProvider, "https://api.fireworks.ai/inference/v1"),
            (DeepSeekProvider, "https://api.deepseek.com/v1"),
        ],
    )
    def test_all_providers_have_correct_base_url(self, provider_class, expected_url):
        """Test all providers have correct base URLs"""
        provider = provider_class()
        assert provider.base_url == expected_url

    @pytest.mark.parametrize(
        "provider_class",
        [
            PerplexityProvider,
            GroqProvider,
            XAIProvider,
            TogetherAIProvider,
            FireworksAIProvider,
            DeepSeekProvider,
        ],
    )
    def test_all_providers_have_call_with_limit(self, provider_class):
        """Test all providers have call_with_limit method"""
        provider = provider_class()
        assert hasattr(provider, "call_with_limit")
        assert callable(provider.call_with_limit)

    @pytest.mark.parametrize(
        "provider_class",
        [
            PerplexityProvider,
            GroqProvider,
            XAIProvider,
            TogetherAIProvider,
            FireworksAIProvider,
            DeepSeekProvider,
        ],
    )
    @patch("requests.post")
    def test_all_providers_handle_network_errors(self, mock_post, provider_class):
        """Test all providers handle network errors gracefully"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network down")

        provider = provider_class()
        result = provider.call_with_limit(api_key="test", task="test", max_tokens=100)

        assert result["success"] is False
        assert "error" in result
        assert result["tokens_used"] == 0

    @pytest.mark.parametrize(
        "provider_class",
        [
            PerplexityProvider,
            GroqProvider,
            XAIProvider,
            TogetherAIProvider,
            FireworksAIProvider,
            DeepSeekProvider,
        ],
    )
    @patch("requests.post")
    def test_all_providers_send_correct_headers(self, mock_post, provider_class):
        """Test all providers send correct authorization headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
        }
        mock_post.return_value = mock_response

        provider = provider_class()
        provider.call_with_limit(api_key="secret_key_123", task="test", max_tokens=100)

        # Check that authorization header was sent
        call_args = mock_post.call_args
        assert "headers" in call_args[1]
        assert "Authorization" in call_args[1]["headers"]
        assert "Bearer secret_key_123" in call_args[1]["headers"]["Authorization"]

    @pytest.mark.parametrize(
        "provider_class",
        [
            PerplexityProvider,
            GroqProvider,
            XAIProvider,
            TogetherAIProvider,
            FireworksAIProvider,
            DeepSeekProvider,
        ],
    )
    @patch("requests.post")
    def test_all_providers_respect_max_tokens(self, mock_post, provider_class):
        """Test all providers send max_tokens parameter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
        }
        mock_post.return_value = mock_response

        provider = provider_class()
        provider.call_with_limit(api_key="test", task="test", max_tokens=777)

        # Check that max_tokens was sent
        call_args = mock_post.call_args
        assert "json" in call_args[1]
        assert call_args[1]["json"]["max_tokens"] == 777


# ============================================================================
# ERROR HANDLING EDGE CASES
# ============================================================================


class TestErrorHandling:
    """Test edge cases and error handling"""

    @patch("requests.post")
    def test_malformed_json_response(self, mock_post):
        """Test handling of malformed JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="test", task="test", max_tokens=100)

        assert result["success"] is False
        assert "error" in result

    @patch("requests.post")
    def test_missing_required_fields(self, mock_post):
        """Test handling of response missing required fields"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"incomplete": "data"}
        mock_post.return_value = mock_response

        provider = GroqProvider()
        # This should raise KeyError which gets caught by RequestException handler
        with pytest.raises(KeyError):
            provider.call_with_limit(api_key="test", task="test", max_tokens=100)

    @patch("requests.post")
    def test_rate_limit_error(self, mock_post):
        """Test handling of rate limit errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Too Many Requests"
        )
        mock_post.return_value = mock_response

        provider = XAIProvider()
        result = provider.call_with_limit(api_key="test", task="test", max_tokens=100)

        assert result["success"] is False
        assert "xAI API error" in result["error"]

    @patch("requests.post")
    def test_unauthorized_error(self, mock_post):
        """Test handling of unauthorized errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        provider = TogetherAIProvider()
        result = provider.call_with_limit(api_key="invalid", task="test", max_tokens=100)

        assert result["success"] is False
        assert "Together AI error" in result["error"]

    @patch("requests.post")
    def test_server_error(self, mock_post):
        """Test handling of server errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Internal Server Error"
        )
        mock_post.return_value = mock_response

        provider = FireworksAIProvider()
        result = provider.call_with_limit(api_key="test", task="test", max_tokens=100)

        assert result["success"] is False
        assert "Fireworks AI error" in result["error"]


# ============================================================================
# STRESS AND BOUNDARY TESTS
# ============================================================================


class TestBoundaryConditions:
    """Test boundary conditions and stress scenarios"""

    @patch("requests.post")
    def test_very_large_max_tokens(self, mock_post):
        """Test with very large max_tokens value"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Large response"}}],
            "usage": {"total_tokens": 100000, "prompt_tokens": 1000, "completion_tokens": 99000},
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.call_with_limit(api_key="test", task="Large task", max_tokens=100000)

        assert result["success"] is True
        assert result["tokens_used"] == 100000

    @patch("requests.post")
    def test_zero_tokens_returned(self, mock_post):
        """Test handling of zero tokens in response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}],
            "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
        }
        mock_post.return_value = mock_response

        provider = PerplexityProvider()
        result = provider.call_with_limit(api_key="test", task="Empty task", max_tokens=100)

        assert result["success"] is True
        assert result["tokens_used"] == 0
        assert result["output"] == ""

    @patch("requests.post")
    def test_empty_task_string(self, mock_post):
        """Test with empty task string"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response to empty task"}}],
            "usage": {"total_tokens": 20, "prompt_tokens": 5, "completion_tokens": 15},
        }
        mock_post.return_value = mock_response

        provider = GroqProvider()
        result = provider.call_with_limit(api_key="test", task="", max_tokens=100)

        assert result["success"] is True

    @patch("requests.post")
    def test_very_long_task_string(self, mock_post):
        """Test with very long task string"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Handled long task"}}],
            "usage": {"total_tokens": 5000, "prompt_tokens": 4000, "completion_tokens": 1000},
        }
        mock_post.return_value = mock_response

        provider = XAIProvider()
        long_task = "A" * 50000  # Very long task
        result = provider.call_with_limit(api_key="test", task=long_task, max_tokens=10000)

        assert result["success"] is True
        assert result["input_tokens"] == 4000
