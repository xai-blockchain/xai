"""
Comprehensive tests for XAI SDK TransactionClient module.

Tests cover:
- Transaction sending
- Transaction retrieval
- Transaction status checking
- Fee estimation
- Transaction confirmation checking
- Waiting for confirmation
- Error handling and validation
"""

from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from xai.sdk.python.xai_sdk.clients.transaction_client import TransactionClient
from xai.sdk.python.xai_sdk.exceptions import (
    NetworkError,
    TransactionError,
    ValidationError,
    XAIError,
)
from xai.sdk.python.xai_sdk.models import Transaction, TransactionStatus


class TestTransactionClientInit:
    """Tests for TransactionClient initialization."""

    def test_init_with_http_client(self):
        """Test TransactionClient initializes with HTTP client."""
        mock_http = Mock()
        client = TransactionClient(mock_http)
        assert client.http_client is mock_http


class TestTransactionSend:
    """Tests for transaction send method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_send_transaction_success(self, client):
        """Test successful transaction sending."""
        client.http_client.post.return_value = {
            "hash": "0xtxhash123",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "1000000000000000000",
            "timestamp": "2024-01-15T10:30:00",
            "status": "pending",
            "fee": "21000",
            "gas_used": "21000",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="1000000000000000000",
        )

        assert isinstance(tx, Transaction)
        assert tx.hash == "0xtxhash123"
        assert tx.from_address == "0xsender"
        assert tx.to_address == "0xrecipient"
        assert tx.status == TransactionStatus.PENDING

    def test_send_transaction_with_all_params(self, client):
        """Test sending with all optional parameters."""
        client.http_client.post.return_value = {
            "hash": "0xfullhash",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "pending",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
            data="0xa9059cbb...",
            gas_limit="50000",
            gas_price="20000000000",
            nonce=42,
            signature="0xsignature...",
        )

        call_args = client.http_client.post.call_args
        data = call_args[1]["data"]
        assert data["data"] == "0xa9059cbb..."
        assert data["gas_limit"] == "50000"
        assert data["gas_price"] == "20000000000"
        assert data["nonce"] == 42
        assert data["signature"] == "0xsignature..."

    def test_send_transaction_empty_from_raises_validation(self, client):
        """Test empty from_address raises ValidationError."""
        with pytest.raises(
            ValidationError, match="from_address, to_address, and amount are required"
        ):
            client.send(from_address="", to_address="0xto", amount="100")

    def test_send_transaction_empty_to_raises_validation(self, client):
        """Test empty to_address raises ValidationError."""
        with pytest.raises(
            ValidationError, match="from_address, to_address, and amount are required"
        ):
            client.send(from_address="0xfrom", to_address="", amount="100")

    def test_send_transaction_empty_amount_raises_validation(self, client):
        """Test empty amount raises ValidationError."""
        with pytest.raises(
            ValidationError, match="from_address, to_address, and amount are required"
        ):
            client.send(from_address="0xfrom", to_address="0xto", amount="")

    def test_send_transaction_parses_datetime(self, client):
        """Test transaction datetime parsing."""
        client.http_client.post.return_value = {
            "hash": "0xdatehash",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-06-15T14:30:45",
            "status": "pending",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
        )

        assert isinstance(tx.timestamp, datetime)
        assert tx.timestamp.year == 2024
        assert tx.timestamp.month == 6

    def test_send_transaction_confirmed_status(self, client):
        """Test transaction with confirmed status."""
        client.http_client.post.return_value = {
            "hash": "0xconfirmed",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "confirmed",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
        )

        assert tx.status == TransactionStatus.CONFIRMED

    def test_send_transaction_failed_status(self, client):
        """Test transaction with failed status."""
        client.http_client.post.return_value = {
            "hash": "0xfailed",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "failed",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
        )

        assert tx.status == TransactionStatus.FAILED

    def test_send_transaction_default_fee(self, client):
        """Test transaction with default fee."""
        client.http_client.post.return_value = {
            "hash": "0xdefault",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
        )

        assert tx.fee == "0"
        assert tx.gas_used == "0"


class TestTransactionGet:
    """Tests for transaction get method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_get_transaction_success(self, client):
        """Test successful transaction retrieval."""
        client.http_client.get.return_value = {
            "hash": "0xgethash",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "confirmed",
            "fee": "21000",
            "gas_used": "21000",
            "block_number": 12345,
            "block_hash": "0xblockhash",
            "confirmations": 10,
        }

        tx = client.get(tx_hash="0xgethash")

        assert isinstance(tx, Transaction)
        assert tx.hash == "0xgethash"
        assert tx.block_number == 12345
        assert tx.block_hash == "0xblockhash"
        assert tx.confirmations == 10

    def test_get_transaction_calls_correct_endpoint(self, client):
        """Test get calls correct API endpoint."""
        client.http_client.get.return_value = {
            "hash": "0xendpoint",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
        }

        client.get(tx_hash="0xendpoint")

        client.http_client.get.assert_called_once_with("/transaction/0xendpoint")

    def test_get_transaction_empty_hash_raises_validation(self, client):
        """Test empty tx_hash raises ValidationError."""
        with pytest.raises(ValidationError, match="tx_hash is required"):
            client.get(tx_hash="")

    def test_get_transaction_none_hash_raises_validation(self, client):
        """Test None tx_hash raises ValidationError."""
        with pytest.raises(ValidationError, match="tx_hash is required"):
            client.get(tx_hash=None)

    def test_get_transaction_default_confirmations(self, client):
        """Test transaction with default confirmations."""
        client.http_client.get.return_value = {
            "hash": "0xnoconf",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.get(tx_hash="0xnoconf")

        assert tx.confirmations == 0


class TestTransactionGetStatus:
    """Tests for transaction get_status method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_get_status_success(self, client):
        """Test successful status retrieval."""
        client.http_client.get.return_value = {
            "status": "confirmed",
            "confirmations": 15,
            "block_number": 12345,
        }

        result = client.get_status(tx_hash="0xstatus")

        assert result["status"] == "confirmed"
        assert result["confirmations"] == 15

    def test_get_status_calls_correct_endpoint(self, client):
        """Test get_status calls correct API endpoint."""
        client.http_client.get.return_value = {"status": "pending"}

        client.get_status(tx_hash="0xstatuscheck")

        client.http_client.get.assert_called_once_with(
            "/transaction/0xstatuscheck/status"
        )

    def test_get_status_empty_hash_raises_validation(self, client):
        """Test empty tx_hash raises ValidationError."""
        with pytest.raises(ValidationError, match="tx_hash is required"):
            client.get_status(tx_hash="")


class TestTransactionEstimateFee:
    """Tests for transaction estimate_fee method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_estimate_fee_success(self, client):
        """Test successful fee estimation."""
        client.http_client.post.return_value = {
            "gas_limit": "21000",
            "gas_price": "20000000000",
            "estimated_fee": "420000000000000",
            "priority_fee": "1000000000",
        }

        result = client.estimate_fee(
            from_address="0xfrom",
            to_address="0xto",
            amount="100",
        )

        assert result["gas_limit"] == "21000"
        assert result["estimated_fee"] == "420000000000000"

    def test_estimate_fee_with_data(self, client):
        """Test fee estimation with data."""
        client.http_client.post.return_value = {
            "gas_limit": "50000",
            "estimated_fee": "1000000000000000",
        }

        result = client.estimate_fee(
            from_address="0xfrom",
            to_address="0xto",
            amount="100",
            data="0xa9059cbb...",
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["data"] == "0xa9059cbb..."

    def test_estimate_fee_calls_correct_endpoint(self, client):
        """Test estimate_fee calls correct API endpoint."""
        client.http_client.post.return_value = {"gas_limit": "21000"}

        client.estimate_fee(
            from_address="0xfrom",
            to_address="0xto",
            amount="100",
        )

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/transaction/estimate-fee"

    def test_estimate_fee_empty_from_raises_validation(self, client):
        """Test empty from_address raises ValidationError."""
        with pytest.raises(ValidationError):
            client.estimate_fee(from_address="", to_address="0xto", amount="100")

    def test_estimate_fee_empty_to_raises_validation(self, client):
        """Test empty to_address raises ValidationError."""
        with pytest.raises(ValidationError):
            client.estimate_fee(from_address="0xfrom", to_address="", amount="100")

    def test_estimate_fee_empty_amount_raises_validation(self, client):
        """Test empty amount raises ValidationError."""
        with pytest.raises(ValidationError):
            client.estimate_fee(from_address="0xfrom", to_address="0xto", amount="")


class TestTransactionIsConfirmed:
    """Tests for transaction is_confirmed method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_is_confirmed_true(self, client):
        """Test is_confirmed returns True when confirmed."""
        client.http_client.get.return_value = {
            "status": "confirmed",
            "confirmations": 10,
        }

        result = client.is_confirmed(tx_hash="0xconfirmed")

        assert result is True

    def test_is_confirmed_false_pending(self, client):
        """Test is_confirmed returns False when pending."""
        client.http_client.get.return_value = {
            "status": "pending",
            "confirmations": 0,
        }

        result = client.is_confirmed(tx_hash="0xpending")

        assert result is False

    def test_is_confirmed_custom_confirmations(self, client):
        """Test is_confirmed with custom confirmation count."""
        client.http_client.get.return_value = {
            "status": "confirmed",
            "confirmations": 5,
        }

        # Needs 6 confirmations but only has 5
        result = client.is_confirmed(tx_hash="0xneeds6", confirmations=6)

        assert result is False

    def test_is_confirmed_exactly_required(self, client):
        """Test is_confirmed with exactly required confirmations."""
        client.http_client.get.return_value = {
            "status": "confirmed",
            "confirmations": 6,
        }

        result = client.is_confirmed(tx_hash="0xexact", confirmations=6)

        assert result is True

    def test_is_confirmed_more_than_required(self, client):
        """Test is_confirmed with more than required confirmations."""
        client.http_client.get.return_value = {
            "status": "confirmed",
            "confirmations": 100,
        }

        result = client.is_confirmed(tx_hash="0xmore", confirmations=6)

        assert result is True


class TestTransactionWaitForConfirmation:
    """Tests for transaction wait_for_confirmation method."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_for_confirmation_success(self, mock_time, mock_sleep, client):
        """Test successful wait for confirmation."""
        mock_time.side_effect = [0, 5, 10]  # Start, after 1st check, after 2nd check

        # First call returns pending, second returns confirmed
        client.http_client.get.side_effect = [
            {
                "hash": "0xwait",
                "from": "0xsender",
                "to": "0xrecipient",
                "amount": "100",
                "timestamp": "2024-01-15T10:30:00",
                "status": "pending",
                "confirmations": 0,
            },
            {
                "hash": "0xwait",
                "from": "0xsender",
                "to": "0xrecipient",
                "amount": "100",
                "timestamp": "2024-01-15T10:30:00",
                "status": "confirmed",
                "confirmations": 1,
            },
        ]

        tx = client.wait_for_confirmation(
            tx_hash="0xwait",
            confirmations=1,
            poll_interval=5,
        )

        assert tx.confirmations >= 1
        mock_sleep.assert_called_once_with(5)

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_for_confirmation_timeout(self, mock_time, mock_sleep, client):
        """Test wait for confirmation timeout."""
        mock_time.side_effect = [0, 300, 700]  # Start, after 1st check, after timeout

        client.http_client.get.return_value = {
            "hash": "0xtimeout",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "pending",
            "confirmations": 0,
        }

        with pytest.raises(TransactionError, match="timeout"):
            client.wait_for_confirmation(
                tx_hash="0xtimeout",
                confirmations=1,
                timeout=600,
                poll_interval=5,
            )

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_for_confirmation_custom_params(self, mock_time, mock_sleep, client):
        """Test wait with custom parameters."""
        mock_time.side_effect = [0, 1]

        client.http_client.get.return_value = {
            "hash": "0xcustom",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "confirmed",
            "confirmations": 10,
        }

        tx = client.wait_for_confirmation(
            tx_hash="0xcustom",
            confirmations=5,
            timeout=120,
            poll_interval=2,
        )

        assert tx.confirmations >= 5

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_for_confirmation_immediate(self, mock_time, mock_sleep, client):
        """Test wait when already confirmed."""
        # Provide enough time values for all potential time.time() calls
        mock_time.side_effect = [0, 0, 1]

        client.http_client.get.return_value = {
            "hash": "0ximmediate",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
            "status": "confirmed",
            "confirmations": 100,
        }

        tx = client.wait_for_confirmation(tx_hash="0ximmediate")

        assert tx.confirmations >= 1
        mock_sleep.assert_not_called()


class TestTransactionClientErrorHandling:
    """Tests for TransactionClient error handling."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_transaction_error_passes_through_on_send(self, client):
        """Test TransactionError passes through on send."""
        client.http_client.post.side_effect = TransactionError("Send failed")

        with pytest.raises(TransactionError, match="Send failed"):
            client.send(
                from_address="0xfrom",
                to_address="0xto",
                amount="100",
            )

    def test_transaction_error_passes_through_on_get(self, client):
        """Test TransactionError passes through on get."""
        client.http_client.get.side_effect = TransactionError("Not found")

        with pytest.raises(TransactionError, match="Not found"):
            client.get(tx_hash="0xnotfound")

    def test_transaction_error_passes_through_on_get_status(self, client):
        """Test TransactionError passes through on get_status."""
        client.http_client.get.side_effect = TransactionError("Status error")

        with pytest.raises(TransactionError, match="Status error"):
            client.get_status(tx_hash="0xstatus")

    def test_transaction_error_passes_through_on_estimate(self, client):
        """Test TransactionError passes through on estimate_fee."""
        client.http_client.post.side_effect = TransactionError("Estimate failed")

        with pytest.raises(TransactionError, match="Estimate failed"):
            client.estimate_fee(
                from_address="0xfrom",
                to_address="0xto",
                amount="100",
            )

    def test_transaction_error_passes_through_on_is_confirmed(self, client):
        """Test TransactionError passes through on is_confirmed."""
        client.http_client.get.side_effect = TransactionError("Check failed")

        with pytest.raises(TransactionError, match="Check failed"):
            client.is_confirmed(tx_hash="0xcheck")

    def test_key_error_wrapped_in_transaction_error(self, client):
        """Test KeyError is wrapped in TransactionError."""
        client.http_client.post.return_value = {}  # Missing required keys

        with pytest.raises(TransactionError, match="Failed to send transaction"):
            client.send(
                from_address="0xfrom",
                to_address="0xto",
                amount="100",
            )

    def test_value_error_wrapped_in_transaction_error(self, client):
        """Test ValueError is wrapped in TransactionError."""
        client.http_client.get.return_value = {
            "hash": "0xinvalid",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "invalid-date",
        }

        with pytest.raises(TransactionError):
            client.get(tx_hash="0xinvalid")


class TestTransactionClientEdgeCases:
    """Tests for TransactionClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create TransactionClient with mocked HTTP client."""
        mock_http = Mock()
        return TransactionClient(mock_http)

    def test_very_large_amount(self, client):
        """Test handling very large transaction amount."""
        client.http_client.post.return_value = {
            "hash": "0xlarge",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "999999999999999999999999999999",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="999999999999999999999999999999",
        )

        assert tx.amount == "999999999999999999999999999999"

    def test_zero_amount(self, client):
        """Test handling zero transaction amount."""
        client.http_client.post.return_value = {
            "hash": "0xzero",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "0",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="0",
        )

        assert tx.amount == "0"

    def test_long_transaction_hash(self, client):
        """Test handling standard transaction hash format."""
        long_hash = "0x" + "a" * 64
        client.http_client.get.return_value = {
            "hash": long_hash,
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.get(tx_hash=long_hash)

        assert tx.hash == long_hash

    def test_large_gas_values(self, client):
        """Test handling large gas values."""
        client.http_client.post.return_value = {
            "gas_limit": "10000000000",
            "gas_price": "500000000000",
            "estimated_fee": "5000000000000000000000",
        }

        result = client.estimate_fee(
            from_address="0xfrom",
            to_address="0xto",
            amount="100",
        )

        assert result["gas_limit"] == "10000000000"

    def test_nonce_zero(self, client):
        """Test handling nonce zero."""
        client.http_client.post.return_value = {
            "hash": "0xnonce0",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="100",
            nonce=0,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["nonce"] == 0

    def test_complex_data_field(self, client):
        """Test handling complex data field."""
        complex_data = "0xa9059cbb" + "0" * 128 + "ab" * 100

        client.http_client.post.return_value = {
            "hash": "0xcomplex",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": "0",
            "timestamp": "2024-01-15T10:30:00",
        }

        tx = client.send(
            from_address="0xsender",
            to_address="0xrecipient",
            amount="0",
            data=complex_data,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["data"] == complex_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
