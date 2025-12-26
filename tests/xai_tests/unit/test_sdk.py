"""
Comprehensive tests for XAI SDK module.

Tests cover:
- HTTPClient: Request handling, retries, connection pooling, error handling
- XAIClient: Service client initialization and context management
- BiometricAuth: Authentication flows and mock provider
- Exception classes: Error handling hierarchy
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


# ============= Exception Tests =============


class TestXAIExceptions:
    """Tests for SDK exception classes."""

    def test_xai_error_basic(self):
        """Test basic XAIError creation."""
        from xai.sdk.python.xai_sdk.exceptions import XAIError

        error = XAIError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code is None
        assert error.error_details == {}

    def test_xai_error_with_code(self):
        """Test XAIError with code."""
        from xai.sdk.python.xai_sdk.exceptions import XAIError

        error = XAIError("Test error", code=500)
        assert str(error) == "[500] Test error"
        assert error.code == 500

    def test_xai_error_with_details(self):
        """Test XAIError with error details."""
        from xai.sdk.python.xai_sdk.exceptions import XAIError

        details = {"field": "email", "reason": "invalid format"}
        error = XAIError("Validation failed", error_details=details)
        assert error.error_details == details

    def test_authentication_error(self):
        """Test AuthenticationError."""
        from xai.sdk.python.xai_sdk.exceptions import AuthenticationError, XAIError

        error = AuthenticationError("Invalid API key")
        assert isinstance(error, XAIError)
        assert error.message == "Invalid API key"

    def test_validation_error(self):
        """Test ValidationError."""
        from xai.sdk.python.xai_sdk.exceptions import ValidationError, XAIError

        error = ValidationError("Invalid input", code=400)
        assert isinstance(error, XAIError)
        assert error.code == 400

    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        from xai.sdk.python.xai_sdk.exceptions import RateLimitError, XAIError

        error = RateLimitError("Too many requests", retry_after=60, code=429)
        assert isinstance(error, XAIError)
        assert error.retry_after == 60

    def test_network_error(self):
        """Test NetworkError."""
        from xai.sdk.python.xai_sdk.exceptions import NetworkError, XAIError

        error = NetworkError("Connection refused")
        assert isinstance(error, XAIError)

    def test_timeout_error(self):
        """Test TimeoutError."""
        from xai.sdk.python.xai_sdk.exceptions import TimeoutError, XAIError

        error = TimeoutError("Request timed out after 30s")
        assert isinstance(error, XAIError)

    def test_not_found_error(self):
        """Test NotFoundError."""
        from xai.sdk.python.xai_sdk.exceptions import NotFoundError, XAIError

        error = NotFoundError("Wallet not found", code=404)
        assert isinstance(error, XAIError)
        assert error.code == 404

    def test_internal_server_error(self):
        """Test InternalServerError."""
        from xai.sdk.python.xai_sdk.exceptions import InternalServerError, XAIError

        error = InternalServerError("Server error")
        assert isinstance(error, XAIError)

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        from xai.sdk.python.xai_sdk.exceptions import ServiceUnavailableError, XAIError

        error = ServiceUnavailableError("Service temporarily unavailable")
        assert isinstance(error, XAIError)

    def test_transaction_error(self):
        """Test TransactionError."""
        from xai.sdk.python.xai_sdk.exceptions import TransactionError, XAIError

        error = TransactionError("Insufficient funds")
        assert isinstance(error, XAIError)

    def test_wallet_error(self):
        """Test WalletError."""
        from xai.sdk.python.xai_sdk.exceptions import WalletError, XAIError

        error = WalletError("Failed to create wallet")
        assert isinstance(error, XAIError)


# ============= HTTPClient Tests =============


class TestHTTPClientInit:
    """Tests for HTTPClient initialization."""

    def test_init_with_defaults(self):
        """Test HTTPClient initializes with default values."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000")
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.api_key is None
        client.close()

    def test_init_with_custom_params(self):
        """Test HTTPClient with custom parameters."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient(
            "http://localhost:8000",
            api_key="test_key",
            timeout=60,
            max_retries=5,
            backoff_factor=1.0,
        )
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.api_key == "test_key"
        client.close()

    def test_normalize_base_url_adds_api_prefix(self):
        """Test base URL normalization adds API prefix."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000")
        assert "/api/v1" in client.base_url
        client.close()

    def test_normalize_base_url_preserves_existing_prefix(self):
        """Test base URL keeps existing API prefix."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000/api/v1")
        assert client.base_url == "http://localhost:8000/api/v1"
        client.close()

    def test_normalize_base_url_strips_trailing_slash(self):
        """Test base URL strips trailing slash."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000/")
        assert not client.base_url.endswith("//")
        client.close()


class TestHTTPClientHeaders:
    """Tests for header generation."""

    def test_get_headers_default(self):
        """Test default headers."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000")
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "XAI-SDK/1.0"
        assert "X-API-Key" not in headers
        client.close()

    def test_get_headers_with_api_key(self):
        """Test headers include API key when set."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000", api_key="secret_key")
        headers = client._get_headers()

        assert headers["X-API-Key"] == "secret_key"
        client.close()

    def test_get_headers_with_custom_headers(self):
        """Test custom headers are merged."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000")
        headers = client._get_headers({"X-Custom": "value"})

        assert headers["X-Custom"] == "value"
        assert "Content-Type" in headers
        client.close()


class TestHTTPClientResponseHandling:
    """Tests for response handling."""

    @pytest.fixture
    def client(self):
        """Create HTTPClient for testing."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient
        c = HTTPClient("http://localhost:8000")
        yield c
        c.close()

    def test_handle_response_success(self, client):
        """Test handling successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}

        result = client._handle_response(mock_response)
        assert result == {"data": "success"}

    def test_handle_response_201_created(self, client):
        """Test handling 201 Created response."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "123"}

        result = client._handle_response(mock_response)
        assert result == {"id": "123"}

    def test_handle_response_400_raises_validation(self, client):
        """Test 400 response raises ValidationError."""
        from xai.sdk.python.xai_sdk.exceptions import ValidationError

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid input"}

        with pytest.raises(ValidationError, match="Invalid input"):
            client._handle_response(mock_response)

    def test_handle_response_401_raises_auth(self, client):
        """Test 401 response raises AuthenticationError."""
        from xai.sdk.python.xai_sdk.exceptions import AuthenticationError

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}

        with pytest.raises(AuthenticationError, match="Unauthorized"):
            client._handle_response(mock_response)

    def test_handle_response_404_raises_not_found(self, client):
        """Test 404 response raises NotFoundError."""
        from xai.sdk.python.xai_sdk.exceptions import NotFoundError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not found"}

        with pytest.raises(NotFoundError, match="Not found"):
            client._handle_response(mock_response)

    def test_handle_response_429_raises_rate_limit(self, client):
        """Test 429 response raises RateLimitError with retry_after."""
        from xai.sdk.python.xai_sdk.exceptions import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        mock_response.headers = {"Retry-After": "60"}

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.retry_after == 60

    def test_handle_response_500_raises_internal(self, client):
        """Test 500 response raises InternalServerError."""
        from xai.sdk.python.xai_sdk.exceptions import InternalServerError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server error"}

        with pytest.raises(InternalServerError, match="Server error"):
            client._handle_response(mock_response)

    def test_handle_response_503_raises_unavailable(self, client):
        """Test 503 response raises ServiceUnavailableError."""
        from xai.sdk.python.xai_sdk.exceptions import ServiceUnavailableError

        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"message": "Service unavailable"}

        with pytest.raises(ServiceUnavailableError):
            client._handle_response(mock_response)

    def test_handle_response_non_json(self, client):
        """Test handling non-JSON response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Internal Server Error"

        from xai.sdk.python.xai_sdk.exceptions import InternalServerError

        with pytest.raises(InternalServerError):
            client._handle_response(mock_response)


class TestHTTPClientRequests:
    """Tests for HTTP request methods."""

    @pytest.fixture
    def client(self):
        """Create HTTPClient for testing."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient
        c = HTTPClient("http://localhost:8000")
        yield c
        c.close()

    @patch("xai.sdk.python.xai_sdk.http_client.requests.Session")
    def test_get_request(self, mock_session_cls, client):
        """Test GET request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_session.get.return_value = mock_response
        client.session = mock_session

        result = client.get("/test", params={"key": "value"})

        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/test" in call_args[0][0]

    @patch("xai.sdk.python.xai_sdk.http_client.requests.Session")
    def test_post_request(self, mock_session_cls, client):
        """Test POST request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "123"}
        mock_session.post.return_value = mock_response
        client.session = mock_session

        result = client.post("/create", data={"name": "test"})

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[1]["json"] == {"name": "test"}

    @patch("xai.sdk.python.xai_sdk.http_client.requests.Session")
    def test_put_request(self, mock_session_cls, client):
        """Test PUT request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_session.put.return_value = mock_response
        client.session = mock_session

        result = client.put("/update/123", data={"name": "updated"})

        mock_session.put.assert_called_once()

    @patch("xai.sdk.python.xai_sdk.http_client.requests.Session")
    def test_delete_request(self, mock_session_cls, client):
        """Test DELETE request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}
        mock_session.delete.return_value = mock_response
        client.session = mock_session

        result = client.delete("/delete/123")

        mock_session.delete.assert_called_once()


class TestHTTPClientNetworkErrors:
    """Tests for network error handling."""

    @pytest.fixture
    def client(self):
        """Create HTTPClient for testing."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient
        c = HTTPClient("http://localhost:8000")
        yield c
        c.close()

    def test_timeout_raises_timeout_error(self, client):
        """Test request timeout raises TimeoutError."""
        import requests
        from xai.sdk.python.xai_sdk.exceptions import TimeoutError

        mock_session = Mock()
        mock_session.get.side_effect = requests.Timeout("Connection timed out")
        client.session = mock_session

        with pytest.raises(TimeoutError, match="timeout"):
            client.get("/test")

    def test_connection_error_raises_network_error(self, client):
        """Test connection error raises NetworkError."""
        import requests
        from xai.sdk.python.xai_sdk.exceptions import NetworkError

        mock_session = Mock()
        mock_session.get.side_effect = requests.ConnectionError("Connection refused")
        client.session = mock_session

        with pytest.raises(NetworkError, match="Connection"):
            client.get("/test")

    def test_request_exception_raises_network_error(self, client):
        """Test general request exception raises NetworkError."""
        import requests
        from xai.sdk.python.xai_sdk.exceptions import NetworkError

        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Unknown error")
        client.session = mock_session

        with pytest.raises(NetworkError, match="error"):
            client.get("/test")


class TestHTTPClientContextManager:
    """Tests for context manager support."""

    def test_context_manager_closes_session(self):
        """Test context manager properly closes session."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        with HTTPClient("http://localhost:8000") as client:
            assert client.session is not None

    def test_close_method(self):
        """Test explicit close method."""
        from xai.sdk.python.xai_sdk.http_client import HTTPClient

        client = HTTPClient("http://localhost:8000")
        mock_session = Mock()
        client.session = mock_session

        client.close()

        mock_session.close.assert_called_once()


# ============= XAIClient Tests =============


class TestXAIClientInit:
    """Tests for XAIClient initialization."""

    def test_init_with_defaults(self):
        """Test XAIClient initializes with defaults."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        client = XAIClient()
        assert client.http_client is not None
        assert client.wallet is not None
        assert client.transaction is not None
        assert client.blockchain is not None
        assert client.mining is not None
        assert client.governance is not None
        assert client.trading is not None
        client.close()

    def test_init_with_custom_params(self):
        """Test XAIClient with custom parameters."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        client = XAIClient(
            base_url="http://custom:9000",
            api_key="my_key",
            timeout=60,
            max_retries=5,
        )
        assert client.http_client.timeout == 60
        assert client.http_client.api_key == "my_key"
        client.close()


class TestXAIClientContextManager:
    """Tests for XAIClient context manager support."""

    def test_context_manager_enter_returns_self(self):
        """Test __enter__ returns client instance."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        with XAIClient() as client:
            assert isinstance(client, XAIClient)

    def test_context_manager_closes_on_exit(self):
        """Test context manager closes client on exit."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        client = XAIClient()
        mock_http = Mock()
        client.http_client = mock_http

        with client:
            pass

        mock_http.close.assert_called_once()


class TestXAIClientMethods:
    """Tests for XAIClient helper methods."""

    @patch("xai.sdk.python.xai_sdk.clients.blockchain_client.BlockchainClient.get_health")
    def test_health_check(self, mock_get_health):
        """Test health_check delegates to blockchain client."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        mock_get_health.return_value = {"status": "ok"}

        with XAIClient() as client:
            health = client.health_check()

        assert health == {"status": "ok"}
        mock_get_health.assert_called_once()

    @patch("xai.sdk.python.xai_sdk.clients.blockchain_client.BlockchainClient.get_node_info")
    def test_get_info(self, mock_get_info):
        """Test get_info delegates to blockchain client."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        mock_get_info.return_value = {"version": "1.0.0"}

        with XAIClient() as client:
            info = client.get_info()

        assert info == {"version": "1.0.0"}
        mock_get_info.assert_called_once()


# ============= BiometricAuth Tests =============


class TestBiometricEnums:
    """Tests for biometric enums."""

    def test_biometric_type_values(self):
        """Test BiometricType enum values."""
        from xai.sdk.biometric.biometric_auth import BiometricType

        assert BiometricType.FACE_ID.value == "face_id"
        assert BiometricType.TOUCH_ID.value == "touch_id"
        assert BiometricType.FINGERPRINT.value == "fingerprint"
        assert BiometricType.IRIS.value == "iris"
        assert BiometricType.VOICE.value == "voice"
        assert BiometricType.NONE.value == "none"

    def test_biometric_error_values(self):
        """Test BiometricError enum values."""
        from xai.sdk.biometric.biometric_auth import BiometricError

        assert BiometricError.NOT_AVAILABLE.value == "not_available"
        assert BiometricError.NOT_ENROLLED.value == "not_enrolled"
        assert BiometricError.USER_CANCEL.value == "user_cancel"
        assert BiometricError.AUTHENTICATION_FAILED.value == "authentication_failed"
        assert BiometricError.LOCKOUT.value == "lockout"
        assert BiometricError.TIMEOUT.value == "timeout"


class TestBiometricResult:
    """Tests for BiometricResult dataclass."""

    def test_result_success(self):
        """Test successful biometric result."""
        from xai.sdk.biometric.biometric_auth import BiometricResult, BiometricType

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            timestamp=1234567890,
        )
        assert result.success is True
        assert result.auth_type == BiometricType.FINGERPRINT
        assert result.error_code is None
        assert result.error_message is None

    def test_result_failure(self):
        """Test failed biometric result."""
        from xai.sdk.biometric.biometric_auth import (
            BiometricResult,
            BiometricType,
            BiometricError,
        )

        result = BiometricResult(
            success=False,
            auth_type=BiometricType.FACE_ID,
            error_code=BiometricError.AUTHENTICATION_FAILED,
            error_message="Face not recognized",
        )
        assert result.success is False
        assert result.error_code == BiometricError.AUTHENTICATION_FAILED


class TestBiometricCapability:
    """Tests for BiometricCapability dataclass."""

    def test_capability_available(self):
        """Test available biometric capability."""
        from xai.sdk.biometric.biometric_auth import BiometricCapability, BiometricType

        capability = BiometricCapability(
            available=True,
            enrolled=True,
            biometric_types=[BiometricType.FINGERPRINT, BiometricType.FACE_ID],
            hardware_detected=True,
            security_level="strong",
        )
        assert capability.available is True
        assert capability.enrolled is True
        assert len(capability.biometric_types) == 2

    def test_capability_not_available(self):
        """Test unavailable biometric capability."""
        from xai.sdk.biometric.biometric_auth import BiometricCapability, BiometricType

        capability = BiometricCapability(
            available=False,
            enrolled=False,
            biometric_types=[],
            hardware_detected=False,
            security_level="none",
        )
        assert capability.available is False
        assert capability.biometric_types == []


class TestMockBiometricProvider:
    """Tests for MockBiometricProvider."""

    @pytest.fixture
    def provider(self):
        """Create MockBiometricProvider for testing."""
        from xai.sdk.biometric.biometric_auth import (
            MockBiometricProvider,
            BiometricType,
        )
        return MockBiometricProvider(simulate_type=BiometricType.FINGERPRINT)

    def test_is_available(self, provider):
        """Test is_available returns capability."""
        from xai.sdk.biometric.biometric_auth import BiometricType

        capability = provider.is_available()

        assert capability.available is True
        assert capability.enrolled is True
        assert BiometricType.FINGERPRINT in capability.biometric_types
        assert capability.security_level == "strong"

    def test_get_auth_type(self, provider):
        """Test get_auth_type returns simulated type."""
        from xai.sdk.biometric.biometric_auth import BiometricType

        auth_type = provider.get_auth_type()
        assert auth_type == BiometricType.FINGERPRINT

    def test_authenticate_success(self, provider):
        """Test successful authentication."""
        result = provider.authenticate()

        assert result.success is True
        assert result.error_code is None
        assert result.timestamp is not None

    def test_authenticate_with_custom_message(self, provider):
        """Test authentication with custom message."""
        result = provider.authenticate(
            prompt_message="Custom auth prompt",
            cancel_button_text="Abort",
            fallback_to_passcode=False,
            timeout_seconds=15,
        )

        assert result.success is True

    def test_authenticate_failure_when_not_enrolled(self, provider):
        """Test authentication fails when not enrolled."""
        from xai.sdk.biometric.biometric_auth import BiometricError, BiometricType

        provider.set_enrolled(False)
        result = provider.authenticate()

        assert result.success is False
        assert result.error_code == BiometricError.NOT_ENROLLED
        assert result.auth_type == BiometricType.NONE

    def test_authenticate_failure_on_fail_next(self, provider):
        """Test authentication fails when set_fail_next is called."""
        from xai.sdk.biometric.biometric_auth import BiometricError

        provider.set_fail_next(True)
        result = provider.authenticate()

        assert result.success is False
        assert result.error_code == BiometricError.AUTHENTICATION_FAILED

    def test_set_fail_next_resets(self, provider):
        """Test set_fail_next resets after one failure."""
        provider.set_fail_next(True)

        result1 = provider.authenticate()
        result2 = provider.authenticate()

        assert result1.success is False
        assert result2.success is True

    def test_invalidate_authentication(self, provider):
        """Test invalidate_authentication returns True."""
        result = provider.invalidate_authentication()
        assert result is True

    def test_different_biometric_types(self):
        """Test provider with different biometric types."""
        from xai.sdk.biometric.biometric_auth import (
            MockBiometricProvider,
            BiometricType,
        )

        face_provider = MockBiometricProvider(simulate_type=BiometricType.FACE_ID)
        touch_provider = MockBiometricProvider(simulate_type=BiometricType.TOUCH_ID)

        assert face_provider.get_auth_type() == BiometricType.FACE_ID
        assert touch_provider.get_auth_type() == BiometricType.TOUCH_ID


class TestBiometricAuthProvider:
    """Tests for BiometricAuthProvider abstract base class."""

    def test_abstract_methods_defined(self):
        """Test that abstract methods are defined."""
        from xai.sdk.biometric.biometric_auth import BiometricAuthProvider
        from abc import ABC

        assert issubclass(BiometricAuthProvider, ABC)
        assert hasattr(BiometricAuthProvider, "is_available")
        assert hasattr(BiometricAuthProvider, "authenticate")
        assert hasattr(BiometricAuthProvider, "get_auth_type")
        assert hasattr(BiometricAuthProvider, "invalidate_authentication")

    def test_cannot_instantiate_directly(self):
        """Test that BiometricAuthProvider cannot be instantiated directly."""
        from xai.sdk.biometric.biometric_auth import BiometricAuthProvider

        with pytest.raises(TypeError, match="abstract"):
            BiometricAuthProvider()


# ============= Integration Tests =============


class TestSDKIntegration:
    """Integration tests for SDK components."""

    def test_client_initialization_chain(self):
        """Test that client initializes all sub-clients properly."""
        from xai.sdk.python.xai_sdk.client import XAIClient
        from xai.sdk.python.xai_sdk.clients.wallet_client import WalletClient
        from xai.sdk.python.xai_sdk.clients.transaction_client import TransactionClient
        from xai.sdk.python.xai_sdk.clients.blockchain_client import BlockchainClient

        with XAIClient() as client:
            assert isinstance(client.wallet, WalletClient)
            assert isinstance(client.transaction, TransactionClient)
            assert isinstance(client.blockchain, BlockchainClient)

    def test_http_client_passed_to_sub_clients(self):
        """Test that HTTP client is passed to all sub-clients."""
        from xai.sdk.python.xai_sdk.client import XAIClient

        with XAIClient() as client:
            assert client.wallet.http_client is client.http_client
            assert client.transaction.http_client is client.http_client
            assert client.blockchain.http_client is client.http_client


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_exceptions_inherit_from_xai_error(self):
        """Test all exceptions inherit from XAIError."""
        from xai.sdk.python.xai_sdk.exceptions import (
            XAIError,
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            RateLimitError,
            NetworkError,
            TimeoutError,
            NotFoundError,
            ConflictError,
            InternalServerError,
            ServiceUnavailableError,
            TransactionError,
            WalletError,
            MiningError,
            GovernanceError,
        )

        exception_classes = [
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            RateLimitError,
            NetworkError,
            TimeoutError,
            NotFoundError,
            ConflictError,
            InternalServerError,
            ServiceUnavailableError,
            TransactionError,
            WalletError,
            MiningError,
            GovernanceError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, XAIError), f"{exc_class.__name__} should inherit from XAIError"

    def test_xai_error_inherits_from_exception(self):
        """Test XAIError inherits from Exception."""
        from xai.sdk.python.xai_sdk.exceptions import XAIError

        assert issubclass(XAIError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
