"""Unit tests for BlockchainTradingMixin methods."""

import hashlib
import json
import pytest
from unittest.mock import MagicMock, patch

from xai.core.blockchain_components.trading_mixin import BlockchainTradingMixin, _stable_stringify


class TestStableStringify:
    """Tests for deterministic JSON serialization."""

    def test_stable_stringify_none(self):
        assert _stable_stringify(None) == "null"

    def test_stable_stringify_bool_true(self):
        assert _stable_stringify(True) == "true"

    def test_stable_stringify_bool_false(self):
        assert _stable_stringify(False) == "false"

    def test_stable_stringify_int(self):
        assert _stable_stringify(42) == "42"

    def test_stable_stringify_float(self):
        assert _stable_stringify(3.14) == "3.14"

    def test_stable_stringify_string(self):
        assert _stable_stringify("hello") == '"hello"'

    def test_stable_stringify_list(self):
        assert _stable_stringify([1, 2, 3]) == "[1,2,3]"

    def test_stable_stringify_dict_sorted_keys(self):
        result = _stable_stringify({"b": 2, "a": 1})
        assert result == '{"a":1,"b":2}'

    def test_stable_stringify_nested(self):
        result = _stable_stringify({"list": [1, {"z": 26, "a": 1}]})
        assert result == '{"list":[1,{"a":1,"z":26}]}'


class MockBlockchain(BlockchainTradingMixin):
    """Mock blockchain for testing mixin methods."""

    def __init__(self):
        self.pending_transactions = []
        self.chain = [MagicMock(hash="genesis")]
        self.orphan_blocks = {}
        self.orphan_transactions = []
        self.difficulty = 4
        self.trade_manager = MagicMock()
        self.trade_sessions = {}
        self.trade_history = []
        self.logger = MagicMock()

    def get_circulating_supply(self):
        return 1000000.0


class TestGetBlockchainDataProvider:
    """Tests for get_blockchain_data_provider method."""

    def test_returns_provider_with_correct_fields(self):
        blockchain = MockBlockchain()
        blockchain.pending_transactions = [MagicMock(get_size=lambda: 100)]

        provider = blockchain.get_blockchain_data_provider()

        assert provider.chain_height == 1
        assert provider.pending_transactions_count == 1
        assert provider.orphan_blocks_count == 0
        assert provider.orphan_transactions_count == 0
        assert provider.total_circulating_supply == 1000000.0
        assert provider.difficulty == 4
        assert provider.mempool_size_bytes == 100

    def test_handles_empty_mempool(self):
        blockchain = MockBlockchain()
        blockchain.pending_transactions = []

        provider = blockchain.get_blockchain_data_provider()

        assert provider.mempool_size_bytes == 0


class TestRegisterTradeSession:
    """Tests for register_trade_session method."""

    def test_registers_session(self):
        blockchain = MockBlockchain()
        blockchain.trade_manager.register_session.return_value = {
            "session_token": "abc123",
            "wallet_address": "XAI123",
        }

        session = blockchain.register_trade_session("XAI123")

        assert session["session_token"] == "abc123"
        assert "abc123" in blockchain.trade_sessions
        blockchain.trade_manager.register_session.assert_called_once_with("XAI123")

    def test_records_event(self):
        blockchain = MockBlockchain()
        blockchain.trade_manager.register_session.return_value = {
            "session_token": "abc123",
        }

        blockchain.register_trade_session("XAI123")

        assert len(blockchain.trade_history) == 1
        assert blockchain.trade_history[0]["type"] == "session_registered"


class TestRecordTradeEvent:
    """Tests for record_trade_event method."""

    def test_records_event(self):
        blockchain = MockBlockchain()

        blockchain.record_trade_event("order_created", {"order_id": "123"})

        assert len(blockchain.trade_history) == 1
        assert blockchain.trade_history[0]["type"] == "order_created"
        assert blockchain.trade_history[0]["payload"]["order_id"] == "123"

    def test_limits_history_size(self):
        blockchain = MockBlockchain()
        blockchain.trade_history = [{"type": f"event_{i}"} for i in range(500)]

        blockchain.record_trade_event("new_event", {})

        assert len(blockchain.trade_history) == 500
        assert blockchain.trade_history[-1]["type"] == "new_event"


class TestSubmitTradeOrder:
    """Tests for submit_trade_order method."""

    def test_rejects_missing_signature(self):
        blockchain = MockBlockchain()

        with pytest.raises(ValueError, match="signature required"):
            blockchain.submit_trade_order({"maker_address": "XAI123"})

    def test_rejects_invalid_signature_length(self):
        blockchain = MockBlockchain()

        with pytest.raises(ValueError, match="128 hex characters"):
            blockchain.submit_trade_order({
                "maker_address": "XAI123",
                "signature": "tooshort",
            })

    def test_rejects_missing_maker_address(self):
        blockchain = MockBlockchain()

        with pytest.raises(ValueError, match="maker_address required"):
            blockchain.submit_trade_order({
                "signature": "a" * 128,
            })

    def test_rejects_missing_public_key(self):
        blockchain = MockBlockchain()

        with pytest.raises(ValueError, match="maker_public_key required"):
            blockchain.submit_trade_order({
                "maker_address": "XAI123",
                "signature": "a" * 128,
            })

    @patch("xai.core.blockchain_components.trading_mixin.verify_signature_hex")
    def test_rejects_invalid_signature(self, mock_verify):
        mock_verify.return_value = False
        blockchain = MockBlockchain()

        with pytest.raises(ValueError, match="ECDSA verification failed"):
            blockchain.submit_trade_order({
                "maker_address": "XAI123",
                "maker_public_key": "04" + "a" * 128,
                "signature": "a" * 128,
                "token_offered": "XAI",
                "token_requested": "USDT",
                "amount_offered": 10,
                "amount_requested": 100,
            })

    @patch("xai.core.blockchain_components.trading_mixin.verify_signature_hex")
    def test_accepts_valid_order(self, mock_verify):
        mock_verify.return_value = True
        blockchain = MockBlockchain()

        mock_order = MagicMock()
        mock_order.order_id = "order123"
        mock_order.maker_address = "XAI123"
        mock_order.token_offered = "XAI"
        mock_order.token_requested = "USDT"
        mock_order.amount_offered = 10
        mock_order.amount_requested = 100
        mock_order.price = 10.0
        blockchain.trade_manager.place_order.return_value = (mock_order, [])

        result = blockchain.submit_trade_order({
            "wallet_address": "XAI123",  # normalize looks for wallet_address
            "maker_address": "XAI123",
            "maker_public_key": "04" + "a" * 128,
            "signature": "a" * 128,
            "token_offered": "XAI",
            "token_requested": "USDT",
            "amount_offered": 10,
            "amount_requested": 100,
        })

        assert result["success"] is True
        assert result["order_id"] == "order123"


class TestGetTradeOrders:
    """Tests for get_trade_orders method."""

    def test_returns_serialized_orders(self):
        blockchain = MockBlockchain()
        mock_order = MagicMock()
        mock_order.to_dict.return_value = {"order_id": "123"}
        blockchain.trade_manager.list_orders.return_value = [mock_order]

        orders = blockchain.get_trade_orders()

        assert len(orders) == 1
        assert orders[0]["order_id"] == "123"


class TestGetTradeMatches:
    """Tests for get_trade_matches method."""

    def test_returns_serialized_matches(self):
        blockchain = MockBlockchain()
        mock_match = MagicMock()
        mock_match.to_dict.return_value = {"match_id": "456"}
        blockchain.trade_manager.list_matches.return_value = [mock_match]

        matches = blockchain.get_trade_matches()

        assert len(matches) == 1
        assert matches[0]["match_id"] == "456"


class TestRevealTradeSecret:
    """Tests for reveal_trade_secret method."""

    def test_settles_match_on_success(self):
        blockchain = MockBlockchain()
        blockchain.trade_manager.settle_match.return_value = {"success": True}

        result = blockchain.reveal_trade_secret("match123", "secret")

        assert result["success"] is True
        assert len(blockchain.trade_history) == 1
        assert blockchain.trade_history[0]["type"] == "match_settled"

    def test_no_event_on_failure(self):
        blockchain = MockBlockchain()
        blockchain.trade_manager.settle_match.return_value = {"success": False}

        result = blockchain.reveal_trade_secret("match123", "secret")

        assert result["success"] is False
        assert len(blockchain.trade_history) == 0
