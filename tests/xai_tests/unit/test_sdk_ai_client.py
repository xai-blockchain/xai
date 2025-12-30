"""
Comprehensive tests for XAI SDK AIClient module.

Tests cover:
- Atomic swap operations
- Smart contract creation and deployment
- Transaction optimization
- Blockchain and wallet analysis
- Node setup recommendations
- Liquidity alerts
- AI assistant listing and streaming
"""

from unittest.mock import Mock, MagicMock, patch
import pytest

from xai.sdk.python.xai_sdk.clients.ai_client import AIClient
from xai.sdk.python.xai_sdk.exceptions import (
    NetworkError,
    ValidationError,
    XAIError,
)


class TestAIClientInit:
    """Tests for AIClient initialization."""

    def test_init_with_http_client(self):
        """Test AIClient initializes with HTTP client."""
        mock_http = Mock()
        client = AIClient(mock_http)
        assert client.http_client is mock_http

    def test_init_stores_http_client_reference(self):
        """Test HTTP client reference is stored."""
        mock_http = Mock()
        client = AIClient(mock_http)
        mock_http.some_attr = "value"
        assert client.http_client.some_attr == "value"


class TestAtomicSwap:
    """Tests for atomic_swap method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_atomic_swap_success(self, client):
        """Test successful atomic swap execution."""
        client.http_client.post.return_value = {
            "swap_id": "swap_123",
            "status": "initiated",
            "from_currency": "XAI",
            "to_currency": "BTC",
            "amount": 100.0,
            "recipient_address": "bc1qtest123",
            "hash_lock": "abc123",
        }

        result = client.atomic_swap(
            from_currency="XAI",
            to_currency="BTC",
            amount=100.0,
            recipient_address="bc1qtest123",
        )

        assert result["swap_id"] == "swap_123"
        assert result["status"] == "initiated"
        client.http_client.post.assert_called_once_with(
            "/personal-ai/atomic-swap",
            data={
                "from_currency": "XAI",
                "to_currency": "BTC",
                "amount": 100.0,
                "recipient_address": "bc1qtest123",
            },
        )

    def test_atomic_swap_with_different_currencies(self, client):
        """Test atomic swap with various currency pairs."""
        client.http_client.post.return_value = {"swap_id": "swap_456"}

        result = client.atomic_swap(
            from_currency="ETH",
            to_currency="LTC",
            amount=5.5,
            recipient_address="ltc1qtest456",
        )

        assert result["swap_id"] == "swap_456"
        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["from_currency"] == "ETH"
        assert call_args[1]["data"]["to_currency"] == "LTC"

    def test_atomic_swap_network_error(self, client):
        """Test atomic swap with network error."""
        client.http_client.post.side_effect = NetworkError("Connection refused")

        with pytest.raises(NetworkError, match="Connection refused"):
            client.atomic_swap(
                from_currency="XAI",
                to_currency="BTC",
                amount=100.0,
                recipient_address="bc1qtest123",
            )

    def test_atomic_swap_with_zero_amount(self, client):
        """Test atomic swap with zero amount."""
        client.http_client.post.return_value = {"swap_id": "swap_789"}

        result = client.atomic_swap(
            from_currency="XAI",
            to_currency="BTC",
            amount=0.0,
            recipient_address="bc1qtest",
        )

        assert "swap_id" in result

    def test_atomic_swap_with_small_amount(self, client):
        """Test atomic swap with very small amount."""
        client.http_client.post.return_value = {"swap_id": "swap_small"}

        result = client.atomic_swap(
            from_currency="XAI",
            to_currency="BTC",
            amount=0.00000001,
            recipient_address="bc1qtest",
        )

        assert result["swap_id"] == "swap_small"


class TestCreateContract:
    """Tests for create_contract method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_create_contract_token(self, client):
        """Test creating a token contract."""
        client.http_client.post.return_value = {
            "contract_id": "contract_123",
            "type": "token",
            "source_code": "contract Token { ... }",
            "bytecode": "0x608060...",
        }

        result = client.create_contract(
            contract_type="token",
            parameters={"name": "MyToken", "symbol": "MTK", "decimals": 18},
        )

        assert result["contract_id"] == "contract_123"
        assert result["type"] == "token"
        client.http_client.post.assert_called_once()

    def test_create_contract_nft(self, client):
        """Test creating an NFT contract."""
        client.http_client.post.return_value = {
            "contract_id": "nft_123",
            "type": "nft",
        }

        result = client.create_contract(
            contract_type="nft",
            parameters={"name": "MyNFT", "base_uri": "ipfs://..."},
        )

        assert result["type"] == "nft"

    def test_create_contract_escrow(self, client):
        """Test creating an escrow contract."""
        client.http_client.post.return_value = {
            "contract_id": "escrow_123",
            "type": "escrow",
        }

        result = client.create_contract(
            contract_type="escrow",
            parameters={"parties": ["addr1", "addr2"], "amount": "1000"},
        )

        assert result["type"] == "escrow"

    def test_create_contract_with_description(self, client):
        """Test creating contract with description."""
        client.http_client.post.return_value = {"contract_id": "desc_123"}

        result = client.create_contract(
            contract_type="token",
            parameters={"name": "DescToken"},
            description="A token for testing descriptions",
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["description"] == "A token for testing descriptions"

    def test_create_contract_without_description(self, client):
        """Test creating contract without description."""
        client.http_client.post.return_value = {"contract_id": "nodesc_123"}

        client.create_contract(
            contract_type="token",
            parameters={"name": "NoDescToken"},
        )

        call_args = client.http_client.post.call_args
        assert "description" not in call_args[1]["data"]

    def test_create_contract_empty_parameters(self, client):
        """Test creating contract with empty parameters."""
        client.http_client.post.return_value = {"contract_id": "empty_123"}

        result = client.create_contract(
            contract_type="custom",
            parameters={},
        )

        assert result["contract_id"] == "empty_123"

    def test_create_contract_complex_parameters(self, client):
        """Test creating contract with complex nested parameters."""
        client.http_client.post.return_value = {"contract_id": "complex_123"}

        complex_params = {
            "features": {
                "burnable": True,
                "mintable": True,
                "pausable": False,
            },
            "roles": ["admin", "minter"],
            "limits": {"max_supply": 1000000},
        }

        result = client.create_contract(
            contract_type="token",
            parameters=complex_params,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["parameters"] == complex_params


class TestDeployContract:
    """Tests for deploy_contract method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_deploy_contract_success(self, client):
        """Test successful contract deployment."""
        client.http_client.post.return_value = {
            "contract_address": "0x1234567890abcdef",
            "tx_hash": "0xdeadbeef",
            "gas_used": "21000",
            "status": "deployed",
        }

        result = client.deploy_contract(
            contract_code="0x608060405234801561001057...",
        )

        assert result["contract_address"] == "0x1234567890abcdef"
        assert result["status"] == "deployed"

    def test_deploy_contract_with_constructor_args(self, client):
        """Test deployment with constructor arguments."""
        client.http_client.post.return_value = {
            "contract_address": "0xabcdef123456",
            "status": "deployed",
        }

        result = client.deploy_contract(
            contract_code="0x608060...",
            constructor_args=["arg1", 123, True],
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["constructor_args"] == ["arg1", 123, True]

    def test_deploy_contract_with_gas_limit(self, client):
        """Test deployment with custom gas limit."""
        client.http_client.post.return_value = {
            "contract_address": "0x999888777",
            "status": "deployed",
        }

        result = client.deploy_contract(
            contract_code="0x608060...",
            gas_limit=500000,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["gas_limit"] == 500000

    def test_deploy_contract_with_all_options(self, client):
        """Test deployment with all optional parameters."""
        client.http_client.post.return_value = {
            "contract_address": "0xfullopt",
            "status": "deployed",
        }

        result = client.deploy_contract(
            contract_code="0x608060...",
            constructor_args=["name", 18],
            gas_limit=1000000,
        )

        call_args = client.http_client.post.call_args
        data = call_args[1]["data"]
        assert data["constructor_args"] == ["name", 18]
        assert data["gas_limit"] == 1000000

    def test_deploy_contract_empty_constructor_args(self, client):
        """Test deployment with empty constructor args list."""
        client.http_client.post.return_value = {"contract_address": "0xempty"}

        client.deploy_contract(
            contract_code="0x608060...",
            constructor_args=[],
        )

        call_args = client.http_client.post.call_args
        # Empty list should not be included (falsy check in implementation)
        assert "constructor_args" not in call_args[1]["data"]

    def test_deploy_contract_network_error(self, client):
        """Test deployment with network error."""
        client.http_client.post.side_effect = NetworkError("Timeout")

        with pytest.raises(NetworkError, match="Timeout"):
            client.deploy_contract(contract_code="0x608060...")


class TestOptimizeTransaction:
    """Tests for optimize_transaction method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_optimize_transaction_basic(self, client):
        """Test basic transaction optimization."""
        client.http_client.post.return_value = {
            "original_gas": "21000",
            "optimized_gas": "18000",
            "savings_percent": 14.3,
            "optimized_transaction": {"gas_limit": "18000"},
        }

        tx = {"to": "0x123", "value": "1000000", "data": "0x"}
        result = client.optimize_transaction(transaction=tx)

        assert result["optimized_gas"] == "18000"
        assert result["savings_percent"] == 14.3

    def test_optimize_transaction_with_goals(self, client):
        """Test optimization with specific goals."""
        client.http_client.post.return_value = {
            "optimized_transaction": {"gas_price": "1"},
            "goals_met": ["low_fee"],
        }

        result = client.optimize_transaction(
            transaction={"to": "0x123", "value": "1000"},
            optimization_goals=["low_fee", "fast_confirmation"],
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["optimization_goals"] == ["low_fee", "fast_confirmation"]

    def test_optimize_transaction_without_goals(self, client):
        """Test optimization without specific goals."""
        client.http_client.post.return_value = {"optimized_transaction": {}}

        client.optimize_transaction(transaction={"to": "0x123"})

        call_args = client.http_client.post.call_args
        assert "optimization_goals" not in call_args[1]["data"]

    def test_optimize_transaction_complex_tx(self, client):
        """Test optimization with complex transaction."""
        client.http_client.post.return_value = {"optimized_transaction": {}}

        complex_tx = {
            "to": "0x123",
            "value": "0",
            "data": "0xa9059cbb000000000000...",
            "gas_limit": "100000",
            "gas_price": "20000000000",
            "nonce": 42,
        }

        result = client.optimize_transaction(
            transaction=complex_tx,
            optimization_goals=["batch_transactions"],
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["transaction"] == complex_tx


class TestAnalyzeBlockchain:
    """Tests for analyze_blockchain method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_analyze_blockchain_basic_query(self, client):
        """Test basic blockchain analysis query."""
        client.http_client.post.return_value = {
            "analysis": "The blockchain shows healthy activity...",
            "metrics": {"tps": 100, "avg_block_time": 15},
        }

        result = client.analyze_blockchain(query="What is the current network health?")

        assert "analysis" in result
        assert result["metrics"]["tps"] == 100

    def test_analyze_blockchain_with_context(self, client):
        """Test analysis with additional context."""
        client.http_client.post.return_value = {
            "analysis": "Based on the context provided...",
        }

        context = {"timeframe": "last_24h", "focus_area": "defi"}
        result = client.analyze_blockchain(
            query="Analyze DeFi activity",
            context=context,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["context"] == context

    def test_analyze_blockchain_without_context(self, client):
        """Test analysis without context."""
        client.http_client.post.return_value = {"analysis": "General analysis..."}

        client.analyze_blockchain(query="General network status")

        call_args = client.http_client.post.call_args
        assert "context" not in call_args[1]["data"]

    def test_analyze_blockchain_complex_query(self, client):
        """Test analysis with complex query."""
        client.http_client.post.return_value = {
            "analysis": "Complex analysis result",
            "data_points": 1000,
        }

        result = client.analyze_blockchain(
            query="Compare transaction patterns between addresses 0x123 and 0x456 over the last month, identifying any anomalies",
            context={
                "addresses": ["0x123", "0x456"],
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )

        assert result["data_points"] == 1000


class TestAnalyzeWallet:
    """Tests for analyze_wallet method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_analyze_wallet_success(self, client):
        """Test successful wallet analysis."""
        client.http_client.post.return_value = {
            "address": "0x1234567890abcdef",
            "risk_score": 15,
            "transaction_patterns": ["regular_trader", "defi_user"],
            "recommendations": ["diversify portfolio"],
        }

        result = client.analyze_wallet(address="0x1234567890abcdef")

        assert result["address"] == "0x1234567890abcdef"
        assert result["risk_score"] == 15
        assert "regular_trader" in result["transaction_patterns"]

    def test_analyze_wallet_request_format(self, client):
        """Test analyze_wallet request format."""
        client.http_client.post.return_value = {"address": "0xtest"}

        client.analyze_wallet(address="0xtest")

        client.http_client.post.assert_called_once_with(
            "/personal-ai/wallet/analyze",
            data={"address": "0xtest"},
        )

    def test_analyze_wallet_network_error(self, client):
        """Test wallet analysis with network error."""
        client.http_client.post.side_effect = NetworkError("Timeout")

        with pytest.raises(NetworkError):
            client.analyze_wallet(address="0x123")


class TestWalletRecoveryAdvice:
    """Tests for wallet_recovery_advice method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_wallet_recovery_basic(self, client):
        """Test basic wallet recovery advice."""
        client.http_client.post.return_value = {
            "recovery_possible": True,
            "confidence": 0.85,
            "steps": ["Step 1...", "Step 2..."],
        }

        result = client.wallet_recovery_advice(
            partial_info={"known_words": ["apple", "banana", "cherry"]},
        )

        assert result["recovery_possible"] is True
        assert result["confidence"] == 0.85

    def test_wallet_recovery_with_dates(self, client):
        """Test recovery with date information."""
        client.http_client.post.return_value = {
            "recovery_possible": True,
            "narrowed_timeframe": "2023-06 to 2023-08",
        }

        result = client.wallet_recovery_advice(
            partial_info={
                "creation_date_range": {"start": "2023-06", "end": "2023-08"},
                "last_transaction": "2023-07-15",
            },
        )

        assert result["narrowed_timeframe"] == "2023-06 to 2023-08"

    def test_wallet_recovery_minimal_info(self, client):
        """Test recovery with minimal information."""
        client.http_client.post.return_value = {
            "recovery_possible": False,
            "reason": "Insufficient information",
        }

        result = client.wallet_recovery_advice(
            partial_info={"wallet_type": "hardware"},
        )

        assert result["recovery_possible"] is False


class TestNodeSetupRecommendations:
    """Tests for node_setup_recommendations method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_node_setup_basic(self, client):
        """Test basic node setup recommendations."""
        client.http_client.post.return_value = {
            "recommended_config": {"memory": "16GB", "storage": "1TB SSD"},
            "estimated_sync_time": "24 hours",
        }

        result = client.node_setup_recommendations()

        assert result["recommended_config"]["memory"] == "16GB"

    def test_node_setup_with_hardware_specs(self, client):
        """Test recommendations based on hardware specs."""
        client.http_client.post.return_value = {
            "compatibility": "excellent",
            "optimizations": ["enable pruning", "adjust cache size"],
        }

        specs = {"cpu_cores": 8, "ram_gb": 32, "storage_gb": 2000}
        result = client.node_setup_recommendations(hardware_specs=specs)

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["hardware_specs"] == specs

    def test_node_setup_with_use_case(self, client):
        """Test recommendations for specific use case."""
        client.http_client.post.return_value = {
            "recommended_node_type": "full_archive",
            "storage_requirement": "5TB",
        }

        result = client.node_setup_recommendations(use_case="archive")

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["use_case"] == "archive"

    def test_node_setup_with_all_params(self, client):
        """Test recommendations with all parameters."""
        client.http_client.post.return_value = {"status": "optimized"}

        result = client.node_setup_recommendations(
            hardware_specs={"cpu_cores": 16, "ram_gb": 64},
            use_case="validator",
        )

        call_args = client.http_client.post.call_args
        assert "hardware_specs" in call_args[1]["data"]
        assert call_args[1]["data"]["use_case"] == "validator"

    def test_node_setup_empty_payload(self, client):
        """Test recommendations with no parameters."""
        client.http_client.post.return_value = {"default_config": True}

        client.node_setup_recommendations()

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"] == {}


class TestLiquidityAlert:
    """Tests for liquidity_alert method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_liquidity_alert_basic(self, client):
        """Test basic liquidity alert setup."""
        client.http_client.post.return_value = {
            "alert_id": "alert_123",
            "pool_id": "pool_xyz",
            "status": "active",
        }

        result = client.liquidity_alert(
            pool_id="pool_xyz",
            alert_type="price_change",
        )

        assert result["alert_id"] == "alert_123"
        assert result["status"] == "active"

    def test_liquidity_alert_with_threshold(self, client):
        """Test alert with threshold value."""
        client.http_client.post.return_value = {"alert_id": "alert_456"}

        result = client.liquidity_alert(
            pool_id="pool_abc",
            alert_type="volume",
            threshold=1000000.0,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["threshold"] == 1000000.0

    def test_liquidity_alert_impermanent_loss(self, client):
        """Test impermanent loss alert."""
        client.http_client.post.return_value = {
            "alert_id": "il_alert",
            "alert_type": "impermanent_loss",
        }

        result = client.liquidity_alert(
            pool_id="uniswap_pool_1",
            alert_type="impermanent_loss",
            threshold=5.0,  # 5% IL threshold
        )

        assert result["alert_type"] == "impermanent_loss"

    def test_liquidity_alert_zero_threshold(self, client):
        """Test alert with zero threshold."""
        client.http_client.post.return_value = {"alert_id": "zero_thresh"}

        client.liquidity_alert(
            pool_id="pool_test",
            alert_type="price_change",
            threshold=0.0,
        )

        call_args = client.http_client.post.call_args
        # Zero is a valid threshold value
        assert call_args[1]["data"]["threshold"] == 0.0

    def test_liquidity_alert_without_threshold(self, client):
        """Test alert without threshold."""
        client.http_client.post.return_value = {"alert_id": "no_thresh"}

        client.liquidity_alert(
            pool_id="pool_test",
            alert_type="price_change",
        )

        call_args = client.http_client.post.call_args
        assert "threshold" not in call_args[1]["data"]


class TestListAssistants:
    """Tests for list_assistants method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_list_assistants_success(self, client):
        """Test successful assistant listing."""
        client.http_client.get.return_value = {
            "assistants": [
                {"id": "asst_1", "name": "General", "capabilities": ["chat"]},
                {"id": "asst_2", "name": "Trading", "capabilities": ["trading", "analysis"]},
            ],
        }

        result = client.list_assistants()

        assert len(result) == 2
        assert result[0]["id"] == "asst_1"
        assert result[1]["name"] == "Trading"

    def test_list_assistants_empty(self, client):
        """Test listing with no assistants."""
        client.http_client.get.return_value = {"assistants": []}

        result = client.list_assistants()

        assert result == []

    def test_list_assistants_missing_key(self, client):
        """Test listing with missing 'assistants' key."""
        client.http_client.get.return_value = {}

        result = client.list_assistants()

        assert result == []

    def test_list_assistants_calls_correct_endpoint(self, client):
        """Test correct endpoint is called."""
        client.http_client.get.return_value = {"assistants": []}

        client.list_assistants()

        client.http_client.get.assert_called_once_with("/personal-ai/assistants")


class TestStream:
    """Tests for stream method."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_stream_basic(self, client):
        """Test basic streaming response."""
        client.http_client.post_stream = Mock(return_value=iter(["Hello", " ", "World"]))

        chunks = list(client.stream(prompt="Say hello"))

        assert chunks == ["Hello", " ", "World"]

    def test_stream_with_assistant_id(self, client):
        """Test streaming with specific assistant."""
        client.http_client.post_stream = Mock(return_value=iter(["Response"]))

        list(client.stream(prompt="Test", assistant_id="asst_123"))

        call_args = client.http_client.post_stream.call_args
        assert call_args[1]["data"]["assistant_id"] == "asst_123"

    def test_stream_with_context(self, client):
        """Test streaming with context."""
        client.http_client.post_stream = Mock(return_value=iter(["Response"]))

        context = {"previous_messages": ["msg1", "msg2"]}
        list(client.stream(prompt="Continue", context=context))

        call_args = client.http_client.post_stream.call_args
        assert call_args[1]["data"]["context"] == context

    def test_stream_with_all_params(self, client):
        """Test streaming with all parameters."""
        client.http_client.post_stream = Mock(return_value=iter(["Full response"]))

        list(
            client.stream(
                prompt="Full test",
                assistant_id="asst_full",
                context={"key": "value"},
            )
        )

        call_args = client.http_client.post_stream.call_args
        data = call_args[1]["data"]
        assert data["prompt"] == "Full test"
        assert data["assistant_id"] == "asst_full"
        assert data["context"] == {"key": "value"}

    def test_stream_yields_chunks(self, client):
        """Test that stream yields chunks one at a time."""
        client.http_client.post_stream = Mock(
            return_value=iter(["chunk1", "chunk2", "chunk3"])
        )

        gen = client.stream(prompt="Test")

        assert next(gen) == "chunk1"
        assert next(gen) == "chunk2"
        assert next(gen) == "chunk3"

    def test_stream_empty_response(self, client):
        """Test streaming with empty response."""
        client.http_client.post_stream = Mock(return_value=iter([]))

        chunks = list(client.stream(prompt="Empty"))

        assert chunks == []

    def test_stream_without_optional_params(self, client):
        """Test streaming without optional parameters."""
        client.http_client.post_stream = Mock(return_value=iter(["Response"]))

        list(client.stream(prompt="Simple prompt"))

        call_args = client.http_client.post_stream.call_args
        data = call_args[1]["data"]
        assert "assistant_id" not in data
        assert "context" not in data


class TestAIClientErrorHandling:
    """Tests for AIClient error handling across methods."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_api_error_propagation(self, client):
        """Test that API errors propagate correctly."""
        try:
            # Import APIError if available
            from xai.sdk.python.xai_sdk.exceptions import APIError

            client.http_client.post.side_effect = APIError("API Error")

            with pytest.raises(APIError):
                client.create_contract(
                    contract_type="token",
                    parameters={"name": "Test"},
                )
        except ImportError:
            # APIError not in exceptions, use XAIError instead
            client.http_client.post.side_effect = XAIError("API Error")

            with pytest.raises(XAIError):
                client.create_contract(
                    contract_type="token",
                    parameters={"name": "Test"},
                )

    def test_xai_error_propagation(self, client):
        """Test that XAI errors propagate correctly."""
        client.http_client.post.side_effect = XAIError("Generic error", code=500)

        with pytest.raises(XAIError) as exc_info:
            client.deploy_contract(contract_code="0x123")

        assert exc_info.value.code == 500

    def test_network_error_on_post(self, client):
        """Test network error on POST request."""
        client.http_client.post.side_effect = NetworkError("Connection reset")

        with pytest.raises(NetworkError, match="Connection reset"):
            client.optimize_transaction(transaction={"to": "0x123"})

    def test_network_error_on_get(self, client):
        """Test network error on GET request."""
        client.http_client.get.side_effect = NetworkError("DNS resolution failed")

        with pytest.raises(NetworkError, match="DNS"):
            client.list_assistants()


class TestAIClientEdgeCases:
    """Tests for AIClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create AIClient with mocked HTTP client."""
        mock_http = Mock()
        return AIClient(mock_http)

    def test_unicode_in_prompt(self, client):
        """Test handling unicode characters in prompt."""
        client.http_client.post_stream = Mock(
            return_value=iter(["Response with emojis"])
        )

        list(client.stream(prompt="What is blockchain?"))

        call_args = client.http_client.post_stream.call_args
        assert "prompt" in call_args[1]["data"]

    def test_very_long_contract_code(self, client):
        """Test handling very long contract code."""
        client.http_client.post.return_value = {"contract_address": "0xlong"}

        long_code = "0x" + "ab" * 50000  # 100KB of bytecode

        result = client.deploy_contract(contract_code=long_code)

        assert result["contract_address"] == "0xlong"

    def test_special_characters_in_query(self, client):
        """Test handling special characters in analysis query."""
        client.http_client.post.return_value = {"analysis": "Result"}

        query = "Analyze <script>alert('xss')</script> & more"
        result = client.analyze_blockchain(query=query)

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["query"] == query

    def test_null_values_in_context(self, client):
        """Test handling null values in context."""
        client.http_client.post.return_value = {"analysis": "OK"}

        context = {"key1": None, "key2": "value"}
        result = client.analyze_blockchain(query="Test", context=context)

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["context"]["key1"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
