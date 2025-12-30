"""
Comprehensive tests for XAI SDK TradingClient module.

Tests cover:
- Session registration
- Order listing
- Order creation
- Order cancellation
- Order status checking
- Error handling and validation
"""

from datetime import datetime
from unittest.mock import Mock
import pytest

from xai.sdk.python.xai_sdk.clients.trading_client import TradingClient
from xai.sdk.python.xai_sdk.exceptions import (
    NetworkError,
    ValidationError,
    XAIError,
)
from xai.sdk.python.xai_sdk.models import TradeOrder


class TestTradingClientInit:
    """Tests for TradingClient initialization."""

    def test_init_with_http_client(self):
        """Test TradingClient initializes with HTTP client."""
        mock_http = Mock()
        client = TradingClient(mock_http)
        assert client.http_client is mock_http


class TestRegisterSession:
    """Tests for register_session method."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_register_session_success(self, client):
        """Test successful session registration."""
        client.http_client.post.return_value = {
            "session_id": "sess_123",
            "wallet_address": "0xwallet",
            "peer_id": "peer_abc",
            "status": "active",
            "expires_at": "2024-01-15T11:30:00",
        }

        result = client.register_session(
            wallet_address="0xwallet",
            peer_id="peer_abc",
        )

        assert result["session_id"] == "sess_123"
        assert result["status"] == "active"

    def test_register_session_calls_correct_endpoint(self, client):
        """Test register_session calls correct API endpoint."""
        client.http_client.post.return_value = {"session_id": "test"}

        client.register_session(wallet_address="0xwallet", peer_id="peer_123")

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/wallet-trades/register"
        assert call_args[1]["data"]["wallet_address"] == "0xwallet"
        assert call_args[1]["data"]["peer_id"] == "peer_123"

    def test_register_session_empty_wallet_raises_validation(self, client):
        """Test empty wallet_address raises ValidationError."""
        with pytest.raises(
            ValidationError, match="wallet_address and peer_id are required"
        ):
            client.register_session(wallet_address="", peer_id="peer_abc")

    def test_register_session_empty_peer_id_raises_validation(self, client):
        """Test empty peer_id raises ValidationError."""
        with pytest.raises(
            ValidationError, match="wallet_address and peer_id are required"
        ):
            client.register_session(wallet_address="0xwallet", peer_id="")

    def test_register_session_none_wallet_raises_validation(self, client):
        """Test None wallet_address raises ValidationError."""
        with pytest.raises(ValidationError):
            client.register_session(wallet_address=None, peer_id="peer_abc")

    def test_register_session_none_peer_id_raises_validation(self, client):
        """Test None peer_id raises ValidationError."""
        with pytest.raises(ValidationError):
            client.register_session(wallet_address="0xwallet", peer_id=None)


class TestListOrders:
    """Tests for list_orders method."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_list_orders_success(self, client):
        """Test successful order listing."""
        client.http_client.get.return_value = {
            "orders": [
                {
                    "id": "order_1",
                    "from_address": "0xfrom1",
                    "to_address": "0xto1",
                    "from_amount": "1000",
                    "to_amount": "900",
                    "created_at": "2024-01-15T10:00:00",
                    "status": "pending",
                    "expires_at": "2024-01-15T11:00:00",
                },
                {
                    "id": "order_2",
                    "from_address": "0xfrom2",
                    "to_address": "0xto2",
                    "from_amount": "2000",
                    "to_amount": "1800",
                    "created_at": "2024-01-15T10:30:00",
                    "status": "filled",
                },
            ],
        }

        orders = client.list_orders()

        assert len(orders) == 2
        assert isinstance(orders[0], TradeOrder)
        assert orders[0].id == "order_1"
        assert orders[0].status == "pending"
        assert isinstance(orders[0].expires_at, datetime)

    def test_list_orders_as_list_response(self, client):
        """Test listing when response is a direct list."""
        client.http_client.get.return_value = [
            {
                "id": "order_1",
                "from_address": "0xfrom",
                "to_address": "0xto",
                "from_amount": "100",
                "to_amount": "90",
                "created_at": "2024-01-15T10:00:00",
                "status": "pending",
            },
        ]

        orders = client.list_orders()

        assert len(orders) == 1
        assert orders[0].id == "order_1"

    def test_list_orders_empty(self, client):
        """Test empty order list."""
        client.http_client.get.return_value = {"orders": []}

        orders = client.list_orders()

        assert orders == []

    def test_list_orders_calls_correct_endpoint(self, client):
        """Test list_orders calls correct API endpoint."""
        client.http_client.get.return_value = {"orders": []}

        client.list_orders()

        client.http_client.get.assert_called_once_with("/wallet-trades/orders")

    def test_list_orders_parses_datetime(self, client):
        """Test datetime parsing in orders."""
        client.http_client.get.return_value = {
            "orders": [
                {
                    "id": "order_1",
                    "from_address": "0xfrom",
                    "to_address": "0xto",
                    "from_amount": "100",
                    "to_amount": "90",
                    "created_at": "2024-06-15T14:30:45",
                    "status": "pending",
                    "expires_at": "2024-06-15T15:30:45",
                },
            ],
        }

        orders = client.list_orders()

        assert isinstance(orders[0].created_at, datetime)
        assert orders[0].created_at.year == 2024
        assert orders[0].created_at.month == 6
        assert isinstance(orders[0].expires_at, datetime)

    def test_list_orders_without_expires_at(self, client):
        """Test orders without expiration date."""
        client.http_client.get.return_value = {
            "orders": [
                {
                    "id": "order_1",
                    "from_address": "0xfrom",
                    "to_address": "0xto",
                    "from_amount": "100",
                    "to_amount": "90",
                    "created_at": "2024-01-15T10:00:00",
                    "status": "pending",
                },
            ],
        }

        orders = client.list_orders()

        assert orders[0].expires_at is None


class TestCreateOrder:
    """Tests for create_order method."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_create_order_success(self, client):
        """Test successful order creation."""
        client.http_client.post.return_value = {
            "id": "order_new",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "1000",
            "to_amount": "950",
            "created_at": "2024-01-15T10:00:00",
            "status": "pending",
        }

        order = client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="1000",
            to_amount="950",
        )

        assert isinstance(order, TradeOrder)
        assert order.id == "order_new"
        assert order.from_amount == "1000"
        assert order.to_amount == "950"

    def test_create_order_with_timeout(self, client):
        """Test order creation with timeout."""
        client.http_client.post.return_value = {
            "id": "order_timeout",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "500",
            "to_amount": "450",
            "created_at": "2024-01-15T10:00:00",
            "status": "pending",
        }

        order = client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="500",
            to_amount="450",
            timeout=3600,  # 1 hour
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["timeout"] == 3600

    def test_create_order_without_timeout(self, client):
        """Test order creation without timeout."""
        client.http_client.post.return_value = {
            "id": "order_notimeout",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "500",
            "to_amount": "450",
            "created_at": "2024-01-15T10:00:00",
            "status": "pending",
        }

        client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="500",
            to_amount="450",
        )

        call_args = client.http_client.post.call_args
        assert "timeout" not in call_args[1]["data"]

    def test_create_order_calls_correct_endpoint(self, client):
        """Test create_order calls correct API endpoint."""
        client.http_client.post.return_value = {
            "id": "test",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "100",
            "to_amount": "90",
            "created_at": "2024-01-15T10:00:00",
        }

        client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="100",
            to_amount="90",
        )

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/wallet-trades/orders"

    def test_create_order_empty_from_address_raises_validation(self, client):
        """Test empty from_address raises ValidationError."""
        with pytest.raises(
            ValidationError,
            match="from_address, to_address, from_amount, and to_amount are required",
        ):
            client.create_order(
                from_address="",
                to_address="0xto",
                from_amount="100",
                to_amount="90",
            )

    def test_create_order_empty_to_address_raises_validation(self, client):
        """Test empty to_address raises ValidationError."""
        with pytest.raises(ValidationError):
            client.create_order(
                from_address="0xfrom",
                to_address="",
                from_amount="100",
                to_amount="90",
            )

    def test_create_order_empty_from_amount_raises_validation(self, client):
        """Test empty from_amount raises ValidationError."""
        with pytest.raises(ValidationError):
            client.create_order(
                from_address="0xfrom",
                to_address="0xto",
                from_amount="",
                to_amount="90",
            )

    def test_create_order_empty_to_amount_raises_validation(self, client):
        """Test empty to_amount raises ValidationError."""
        with pytest.raises(ValidationError):
            client.create_order(
                from_address="0xfrom",
                to_address="0xto",
                from_amount="100",
                to_amount="",
            )


class TestCancelOrder:
    """Tests for cancel_order method."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_cancel_order_success(self, client):
        """Test successful order cancellation."""
        client.http_client.post.return_value = {
            "order_id": "order_123",
            "status": "cancelled",
            "cancelled_at": "2024-01-15T10:30:00",
        }

        result = client.cancel_order(order_id="order_123")

        assert result["status"] == "cancelled"

    def test_cancel_order_calls_correct_endpoint(self, client):
        """Test cancel_order calls correct API endpoint."""
        client.http_client.post.return_value = {"status": "cancelled"}

        client.cancel_order(order_id="order_abc")

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/wallet-trades/orders/order_abc/cancel"
        assert call_args[1]["data"] == {}

    def test_cancel_order_empty_id_raises_validation(self, client):
        """Test empty order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="order_id is required"):
            client.cancel_order(order_id="")

    def test_cancel_order_none_id_raises_validation(self, client):
        """Test None order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="order_id is required"):
            client.cancel_order(order_id=None)

    def test_cancel_order_already_cancelled(self, client):
        """Test cancelling an already cancelled order."""
        client.http_client.post.return_value = {
            "order_id": "order_123",
            "status": "already_cancelled",
            "message": "Order was already cancelled",
        }

        result = client.cancel_order(order_id="order_123")

        assert result["status"] == "already_cancelled"


class TestGetOrderStatus:
    """Tests for get_order_status method."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_get_order_status_success(self, client):
        """Test successful order status retrieval."""
        client.http_client.get.return_value = {
            "order_id": "order_123",
            "status": "pending",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:15:00",
        }

        result = client.get_order_status(order_id="order_123")

        assert result["status"] == "pending"
        assert result["order_id"] == "order_123"

    def test_get_order_status_calls_correct_endpoint(self, client):
        """Test get_order_status calls correct API endpoint."""
        client.http_client.get.return_value = {"status": "pending"}

        client.get_order_status(order_id="order_xyz")

        client.http_client.get.assert_called_once_with(
            "/wallet-trades/orders/order_xyz/status"
        )

    def test_get_order_status_empty_id_raises_validation(self, client):
        """Test empty order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="order_id is required"):
            client.get_order_status(order_id="")

    def test_get_order_status_none_id_raises_validation(self, client):
        """Test None order_id raises ValidationError."""
        with pytest.raises(ValidationError, match="order_id is required"):
            client.get_order_status(order_id=None)

    def test_get_order_status_filled(self, client):
        """Test order status for filled order."""
        client.http_client.get.return_value = {
            "order_id": "order_filled",
            "status": "filled",
            "filled_at": "2024-01-15T10:30:00",
            "tx_hash": "0xtxhash",
        }

        result = client.get_order_status(order_id="order_filled")

        assert result["status"] == "filled"
        assert result["tx_hash"] == "0xtxhash"

    def test_get_order_status_expired(self, client):
        """Test order status for expired order."""
        client.http_client.get.return_value = {
            "order_id": "order_expired",
            "status": "expired",
            "expired_at": "2024-01-15T12:00:00",
        }

        result = client.get_order_status(order_id="order_expired")

        assert result["status"] == "expired"


class TestTradingClientErrorHandling:
    """Tests for TradingClient error handling."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_xai_error_passes_through_on_register(self, client):
        """Test XAIError passes through on register_session."""
        client.http_client.post.side_effect = XAIError("Registration failed")

        with pytest.raises(XAIError, match="Registration failed"):
            client.register_session(wallet_address="0xwallet", peer_id="peer")

    def test_xai_error_passes_through_on_list(self, client):
        """Test XAIError passes through on list_orders."""
        client.http_client.get.side_effect = XAIError("List failed")

        with pytest.raises(XAIError, match="List failed"):
            client.list_orders()

    def test_xai_error_passes_through_on_create(self, client):
        """Test XAIError passes through on create_order."""
        client.http_client.post.side_effect = XAIError("Create failed")

        with pytest.raises(XAIError, match="Create failed"):
            client.create_order(
                from_address="0xfrom",
                to_address="0xto",
                from_amount="100",
                to_amount="90",
            )

    def test_xai_error_passes_through_on_cancel(self, client):
        """Test XAIError passes through on cancel_order."""
        client.http_client.post.side_effect = XAIError("Cancel failed")

        with pytest.raises(XAIError, match="Cancel failed"):
            client.cancel_order(order_id="order_123")

    def test_xai_error_passes_through_on_status(self, client):
        """Test XAIError passes through on get_order_status."""
        client.http_client.get.side_effect = XAIError("Status failed")

        with pytest.raises(XAIError, match="Status failed"):
            client.get_order_status(order_id="order_123")

    def test_network_error_on_list(self, client):
        """Test network error on list_orders."""
        client.http_client.get.side_effect = NetworkError("Connection refused")

        with pytest.raises(NetworkError):
            client.list_orders()

    def test_key_error_wrapped_in_xai_error(self, client):
        """Test KeyError is wrapped in XAIError."""
        client.http_client.post.return_value = {}  # Missing required keys

        with pytest.raises(XAIError, match="Failed to create trade order"):
            client.create_order(
                from_address="0xfrom",
                to_address="0xto",
                from_amount="100",
                to_amount="90",
            )


class TestTradingClientEdgeCases:
    """Tests for TradingClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create TradingClient with mocked HTTP client."""
        mock_http = Mock()
        return TradingClient(mock_http)

    def test_very_large_amounts(self, client):
        """Test handling very large trade amounts."""
        client.http_client.post.return_value = {
            "id": "order_large",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "9" * 60,
            "to_amount": "8" * 60,
            "created_at": "2024-01-15T10:00:00",
            "status": "pending",
        }

        order = client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="9" * 60,
            to_amount="8" * 60,
        )

        assert len(order.from_amount) == 60

    def test_zero_amounts(self, client):
        """Test handling zero trade amounts."""
        client.http_client.post.return_value = {
            "id": "order_zero",
            "from_address": "0xfrom",
            "to_address": "0xto",
            "from_amount": "0",
            "to_amount": "0",
            "created_at": "2024-01-15T10:00:00",
            "status": "pending",
        }

        order = client.create_order(
            from_address="0xfrom",
            to_address="0xto",
            from_amount="0",
            to_amount="0",
        )

        assert order.from_amount == "0"

    def test_long_order_id(self, client):
        """Test handling long order IDs."""
        long_id = "order_" + "a" * 100
        client.http_client.get.return_value = {
            "order_id": long_id,
            "status": "pending",
        }

        result = client.get_order_status(order_id=long_id)

        assert result["order_id"] == long_id

    def test_special_characters_in_peer_id(self, client):
        """Test handling special characters in peer_id."""
        client.http_client.post.return_value = {
            "session_id": "sess_123",
            "status": "active",
        }

        result = client.register_session(
            wallet_address="0xwallet",
            peer_id="peer/with:special@chars#123",
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["peer_id"] == "peer/with:special@chars#123"

    def test_order_with_all_statuses(self, client):
        """Test orders with various status values."""
        statuses = ["pending", "filled", "cancelled", "expired", "partial"]

        for status in statuses:
            client.http_client.get.return_value = {
                "order_id": "order_test",
                "status": status,
            }

            result = client.get_order_status(order_id="order_test")

            assert result["status"] == status

    def test_list_many_orders(self, client):
        """Test listing many orders."""
        orders_data = [
            {
                "id": f"order_{i}",
                "from_address": "0xfrom",
                "to_address": "0xto",
                "from_amount": str(i * 100),
                "to_amount": str(i * 90),
                "created_at": "2024-01-15T10:00:00",
                "status": "pending",
            }
            for i in range(100)
        ]

        client.http_client.get.return_value = {"orders": orders_data}

        orders = client.list_orders()

        assert len(orders) == 100
        assert orders[50].id == "order_50"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
