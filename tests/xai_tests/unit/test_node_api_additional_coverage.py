"""
Additional comprehensive tests for node_api.py to boost coverage to 80%+

This test file targets uncovered lines and edge cases to achieve 80%+ coverage:
- Error handling paths in all routes
- Missing field validations
- Exception scenarios
- Edge cases in recovery routes
- Exchange route error handling
- Payment processing error paths
- Crypto deposit edge cases
"""

import pytest
import json
import time
import os
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch, mock_open
from flask import Flask

from xai.core.config import Config


class TestNodeAPISendTransactionErrorPaths:
    """Test error handling in send transaction endpoint."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.blockchain = Mock()
        node.blockchain.add_transaction = Mock(return_value=True)
        node.broadcast_transaction = Mock()
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    @patch('xai.core.chain.Transaction')
    def test_send_transaction_exception(self, mock_tx_class, client):
        """Test POST /send - exception during processing."""
        mock_tx_class.side_effect = Exception("Transaction creation failed")

        tx_data = {
            "sender": "addr1",
            "recipient": "addr2",
            "amount": 10.0,
            "fee": 0.01,
            "public_key": "pubkey123",
            "nonce": 1,
            "timestamp": time.time(),
            "signature": "sig123",
        }

        response = client.post('/send',
                              data=json.dumps(tx_data),
                              content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestRequestIDMiddleware:
    """Ensure correlation IDs are generated and honored."""

    @pytest.fixture
    def client(self, tmp_path):
        node = Mock()
        node.app = Flask(__name__)
        node.blockchain = Mock()
        node.blockchain.get_stats.return_value = {
            "chain_height": 0,
            "difficulty": 1,
            "total_circulating_supply": 0,
            "latest_block_hash": "0x0",
            "pending_transactions_count": 0,
            "orphan_blocks_count": 0,
            "orphan_transactions_count": 0,
        }
        node.blockchain.storage = SimpleNamespace(data_dir=str(tmp_path))
        from xai.core.node_api import NodeAPIRoutes

        routes = NodeAPIRoutes(node)
        routes.setup_routes()
        node.app.config["TESTING"] = True
        return node.app.test_client()

    def test_response_contains_generated_request_id(self, client):
        response = client.get("/health")
        assert response.status_code in (200, 503)
        header_value = response.headers.get("X-Request-ID")
        assert header_value

    def test_request_id_header_is_preserved(self, client):
        req_id = "abc12345"
        response = client.get("/health", headers={"X-Request-ID": req_id})
        assert response.headers.get("X-Request-ID") == req_id


class TestPayloadSizeLimits:
    """Ensure oversized payloads are rejected before reaching route logic."""

    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Config, "API_MAX_JSON_BYTES", 32, raising=False)
        monkeypatch.setattr(Config, "API_KEY_STORE_PATH", str(tmp_path / "api_keys.json"), raising=False)
        node = Mock()
        node.app = Flask(__name__)
        node.blockchain = Mock()
        from xai.core.node_api import NodeAPIRoutes

        routes = NodeAPIRoutes(node)
        routes.setup_routes()
        node.app.config["TESTING"] = True
        return node.app.test_client()

    def test_large_payload_returns_413(self, client):
        payload = "x" * 128
        response = client.post("/send", data=payload, content_type="application/json")
        assert response.status_code == 413
        data = response.get_json()
        assert data["code"] == "payload_too_large"
        assert data["success"] is False
        assert response.headers.get("X-Request-ID")


class TestNodeAPIRecoveryErrorHandling:
    """Test error handling in social recovery endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.recovery_manager = Mock()
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    def test_setup_recovery_value_error(self, client, mock_node):
        """Test POST /recovery/setup - ValueError."""
        mock_node.recovery_manager.setup_guardians.side_effect = ValueError("Invalid threshold")

        data = {
            "owner_address": "owner1",
            "guardians": ["g1", "g2"],
            "threshold": 5,
            "signature": "sig-owner",
        }
        response = client.post('/recovery/setup',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        result = response.get_json()
        assert 'Invalid threshold' in result['error']

    def test_setup_recovery_exception(self, client, mock_node):
        """Test POST /recovery/setup - general exception."""
        mock_node.recovery_manager.setup_guardians.side_effect = Exception("Database error")

        data = {
            "owner_address": "owner1",
            "guardians": ["g1", "g2"],
            "threshold": 2,
            "signature": "sig-owner",
        }
        response = client.post('/recovery/setup',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500
        result = response.get_json()
        assert 'internal' in result['error'].lower()

    def test_request_recovery_value_error(self, client, mock_node):
        """Test POST /recovery/request - ValueError."""
        mock_node.recovery_manager.initiate_recovery.side_effect = ValueError("Invalid address")

        data = {
            "owner_address": "owner1",
            "new_address": "new1",
            "guardian_address": "g1",
            "signature": "sig-guardian",
        }
        response = client.post('/recovery/request',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_request_recovery_exception(self, client, mock_node):
        """Test POST /recovery/request - exception."""
        mock_node.recovery_manager.initiate_recovery.side_effect = Exception("Error")

        data = {
            "owner_address": "owner1",
            "new_address": "new1",
            "guardian_address": "g1",
            "signature": "sig-guardian",
        }
        response = client.post('/recovery/request',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_vote_recovery_value_error(self, client, mock_node):
        """Test POST /recovery/vote - ValueError."""
        mock_node.recovery_manager.vote_recovery.side_effect = ValueError("Invalid request")

        data = {
            "request_id": "req123",
            "guardian_address": "g1",
            "signature": "sig-guardian",
        }
        response = client.post('/recovery/vote',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_vote_recovery_exception(self, client, mock_node):
        """Test POST /recovery/vote - exception."""
        mock_node.recovery_manager.vote_recovery.side_effect = Exception("Error")

        data = {
            "request_id": "req123",
            "guardian_address": "g1",
            "signature": "sig-guardian",
        }
        response = client.post('/recovery/vote',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_recovery_status_exception(self, client, mock_node):
        """Test GET /recovery/status/<address> - exception."""
        mock_node.recovery_manager.get_recovery_status.side_effect = Exception("Error")

        response = client.get('/recovery/status/owner1')
        assert response.status_code == 500

    def test_cancel_recovery_value_error(self, client, mock_node):
        """Test POST /recovery/cancel - ValueError."""
        mock_node.recovery_manager.cancel_recovery.side_effect = ValueError("Invalid request")

        data = {
            "request_id": "req123",
            "owner_address": "owner1",
            "signature": "sig-owner",
        }
        response = client.post('/recovery/cancel',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_cancel_recovery_exception(self, client, mock_node):
        """Test POST /recovery/cancel - exception."""
        mock_node.recovery_manager.cancel_recovery.side_effect = Exception("Error")

        data = {
            "request_id": "req123",
            "owner_address": "owner1",
            "signature": "sig-owner",
        }
        response = client.post('/recovery/cancel',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_execute_recovery_missing_request_id(self, client):
        """Test POST /recovery/execute - missing request_id."""
        response = client.post('/recovery/execute',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Validation error' in data['error']

    def test_execute_recovery_value_error(self, client, mock_node):
        """Test POST /recovery/execute - ValueError."""
        mock_node.recovery_manager.execute_recovery.side_effect = ValueError("Not ready")

        data = {"request_id": "req123", "executor_address": "exec1"}
        response = client.post('/recovery/execute',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_execute_recovery_exception(self, client, mock_node):
        """Test POST /recovery/execute - exception."""
        mock_node.recovery_manager.execute_recovery.side_effect = Exception("Error")

        data = {"request_id": "req123", "executor_address": "exec1"}
        response = client.post('/recovery/execute',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_recovery_config_not_found(self, client, mock_node):
        """Test GET /recovery/config/<address> - not found."""
        mock_node.recovery_manager.get_recovery_config.return_value = None

        response = client.get('/recovery/config/owner1')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False

    def test_get_recovery_config_exception(self, client, mock_node):
        """Test GET /recovery/config/<address> - exception."""
        mock_node.recovery_manager.get_recovery_config.side_effect = Exception("Error")

        response = client.get('/recovery/config/owner1')
        assert response.status_code == 500

    def test_get_guardian_duties_exception(self, client, mock_node):
        """Test GET /recovery/guardian/<address> - exception."""
        mock_node.recovery_manager.get_guardian_duties.side_effect = Exception("Error")

        response = client.get('/recovery/guardian/g1')
        assert response.status_code == 500

    def test_get_recovery_requests_exception(self, client, mock_node):
        """Test GET /recovery/requests - exception."""
        mock_node.recovery_manager.get_all_requests.side_effect = Exception("Error")

        response = client.get('/recovery/requests')
        assert response.status_code == 500

    def test_get_recovery_requests_with_status_filter(self, client, mock_node):
        """Test GET /recovery/requests?status=pending."""
        mock_node.recovery_manager.get_all_requests.return_value = []

        response = client.get('/recovery/requests?status=pending')
        assert response.status_code == 200
        mock_node.recovery_manager.get_all_requests.assert_called_with(status='pending')

    def test_get_recovery_stats_exception(self, client, mock_node):
        """Test GET /recovery/stats - exception."""
        mock_node.recovery_manager.get_stats.side_effect = Exception("Error")

        response = client.get('/recovery/stats')
        assert response.status_code == 500


class TestNodeAPIGamificationErrorHandling:
    """Test error handling in gamification endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.blockchain = Mock()
        node.blockchain.treasure_manager = Mock()
        node.blockchain.treasure_manager.create_treasure_hunt.side_effect = Exception("Creation failed")
        node.blockchain.treasure_manager.claim_treasure.return_value = (False, 0)
        node.blockchain.treasure_manager.get_treasure_details.return_value = None
        node.blockchain.pending_transactions = []
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    def test_create_treasure_missing_fields(self, client):
        """Test POST /treasure/create - missing fields."""
        data = {"creator": "creator1"}
        response = client.post('/treasure/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result

    def test_create_treasure_exception(self, client):
        """Test POST /treasure/create - exception."""
        data = {
            "creator": "creator1",
            "amount": 100.0,
            "puzzle_type": "riddle",
            "puzzle_data": {"question": "What is..."},
        }
        response = client.post('/treasure/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_claim_treasure_missing_fields(self, client):
        """Test POST /treasure/claim - missing fields."""
        data = {"treasure_id": "t1"}
        response = client.post('/treasure/claim',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_claim_treasure_incorrect_solution(self, client):
        """Test POST /treasure/claim - incorrect solution."""
        data = {
            "treasure_id": "t1",
            "claimer": "claimer1",
            "solution": "wrong"
        }
        response = client.post('/treasure/claim',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] == False

    @patch('xai.core.chain.Transaction')
    def test_claim_treasure_exception(self, mock_tx_class, client, mock_node):
        """Test POST /treasure/claim - exception."""
        mock_node.blockchain.treasure_manager.claim_treasure.side_effect = Exception("Error")

        data = {
            "treasure_id": "t1",
            "claimer": "claimer1",
            "solution": "answer"
        }
        response = client.post('/treasure/claim',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_treasure_details_not_found(self, client):
        """Test GET /treasure/details/<treasure_id> - not found."""
        response = client.get('/treasure/details/nonexistent')
        assert response.status_code == 404


class TestNodeAPIMiningBonusErrorHandling:
    """Test error handling in mining bonus endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.bonus_manager = Mock()
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    def test_register_miner_missing_address(self, client):
        """Test POST /mining/register - missing address."""
        response = client.post('/mining/register',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Validation error' in data['error']

    def test_register_miner_exception(self, client, mock_node):
        """Test POST /mining/register - exception."""
        mock_node.bonus_manager.register_miner.side_effect = Exception("Error")

        response = client.post('/mining/register',
                              data=json.dumps({"address": "miner1"}),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_achievements_exception(self, client, mock_node):
        """Test GET /mining/achievements/<address> - exception."""
        mock_node.bonus_manager.check_achievements.side_effect = Exception("Error")

        response = client.get('/mining/achievements/miner1')
        assert response.status_code == 500

    def test_claim_bonus_missing_fields(self, client):
        """Test POST /mining/claim-bonus - missing fields."""
        response = client.post('/mining/claim-bonus',
                              data=json.dumps({"address": "miner1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_claim_bonus_exception(self, client, mock_node):
        """Test POST /mining/claim-bonus - exception."""
        mock_node.bonus_manager.claim_bonus.side_effect = Exception("Error")

        data = {"address": "miner1", "bonus_type": "tweet"}
        response = client.post('/mining/claim-bonus',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_create_referral_code_missing_address(self, client):
        """Test POST /mining/referral/create - missing address."""
        response = client.post('/mining/referral/create',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_create_referral_code_exception(self, client, mock_node):
        """Test POST /mining/referral/create - exception."""
        mock_node.bonus_manager.create_referral_code.side_effect = Exception("Error")

        response = client.post('/mining/referral/create',
                              data=json.dumps({"address": "miner1"}),
                              content_type='application/json')
        assert response.status_code == 500

    def test_use_referral_code_missing_fields(self, client):
        """Test POST /mining/referral/use - missing fields."""
        response = client.post('/mining/referral/use',
                              data=json.dumps({"new_address": "new1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_use_referral_code_exception(self, client, mock_node):
        """Test POST /mining/referral/use - exception."""
        mock_node.bonus_manager.use_referral_code.side_effect = Exception("Error")

        data = {"new_address": "new1", "referral_code": "REF123"}
        response = client.post('/mining/referral/use',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_user_bonuses_exception(self, client, mock_node):
        """Test GET /mining/user-bonuses/<address> - exception."""
        mock_node.bonus_manager.get_user_bonuses.side_effect = Exception("Error")

        response = client.get('/mining/user-bonuses/miner1')
        assert response.status_code == 500

    def test_get_bonus_leaderboard_exception(self, client, mock_node):
        """Test GET /mining/leaderboard - exception."""
        mock_node.bonus_manager.get_leaderboard.side_effect = Exception("Error")

        response = client.get('/mining/leaderboard')
        assert response.status_code == 500

    def test_get_mining_bonus_stats_exception(self, client, mock_node):
        """Test GET /mining/stats - exception."""
        mock_node.bonus_manager.get_stats.side_effect = Exception("Error")

        response = client.get('/mining/stats')
        assert response.status_code == 500


class TestNodeAPIExchangeErrorHandling:
    """Test error handling in exchange endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.exchange_wallet_manager = Mock()
        node._match_orders = Mock(return_value=False)
        node.blockchain = Mock()
        node.blockchain.storage = SimpleNamespace(data_dir=os.getcwd())
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    @patch('xai.core.node_api.os.path.exists')
    def test_get_order_book_no_file(self, mock_exists, client):
        """Test GET /exchange/orders - no orders file."""
        mock_exists.return_value = False

        response = client.get('/exchange/orders')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    @patch('xai.core.node_api.os.path.exists')
    def test_get_order_book_exception(self, mock_exists, client):
        """Test GET /exchange/orders - exception."""
        mock_exists.side_effect = Exception("File error")

        response = client.get('/exchange/orders')
        assert response.status_code == 500

    def test_place_order_missing_fields(self, client):
        """Test POST /exchange/place-order - missing fields."""
        response = client.post('/exchange/place-order',
                              data=json.dumps({"address": "user1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_place_order_invalid_order_type(self, client):
        """Test POST /exchange/place-order - invalid order type."""
        data = {
            "address": "user1",
            "order_type": "invalid",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD",
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        result = response.get_json()
        assert 'Invalid order type' in result['error']

    def test_place_order_negative_price(self, client):
        """Test POST /exchange/place-order - negative price."""
        data = {
            "address": "user1",
            "order_type": "buy",
            "price": -0.05,
            "amount": 100
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_place_order_insufficient_balance(self, client, mock_node):
        """Test POST /exchange/place-order - insufficient balance."""
        mock_node.exchange_wallet_manager.get_balance.return_value = {"available": 1, "locked": 0}

        data = {
            "address": "user1",
            "order_type": "buy",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD"
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        result = response.get_json()
        assert 'Insufficient' in result['error']

    def test_place_sell_order_insufficient_balance(self, client, mock_node):
        """Test POST /exchange/place-order - sell order insufficient balance."""
        mock_node.exchange_wallet_manager.get_balance.return_value = {"available": 1, "locked": 0}

        data = {
            "address": "user1",
            "order_type": "sell",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD"
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_place_order_lock_failed(self, client, mock_node):
        """Test POST /exchange/place-order - lock funds failed."""
        mock_node.exchange_wallet_manager.get_balance.return_value = {"available": 1000, "locked": 0}
        mock_node.exchange_wallet_manager.lock_for_order.return_value = False

        data = {
            "address": "user1",
            "order_type": "buy",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD"
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500
        result = response.get_json()
        assert 'Failed to lock funds' in result['error']

    @patch('xai.core.node_api.os.makedirs')
    @patch('xai.core.node_api.os.path.exists')
    def test_place_order_exception(self, mock_exists, mock_makedirs, client):
        """Test POST /exchange/place-order - exception."""
        mock_exists.side_effect = Exception("Error")

        data = {
            "address": "user1",
            "order_type": "buy",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD",
        }
        response = client.post('/exchange/place-order',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_cancel_order_missing_id(self, client):
        """Test POST /exchange/cancel-order - missing order_id."""
        response = client.post('/exchange/cancel-order',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Validation error' in data['error']

    @patch('xai.core.node_api.os.path.exists')
    def test_cancel_order_not_found_file(self, mock_exists, client):
        """Test POST /exchange/cancel-order - orders file not found."""
        mock_exists.return_value = False

        response = client.post('/exchange/cancel-order',
                              data=json.dumps({"order_id": "order123"}),
                              content_type='application/json')
        assert response.status_code == 404

    @patch('xai.core.node_api.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"buy": [], "sell": []}')
    def test_cancel_order_not_found_order(self, mock_file, mock_exists, client):
        """Test POST /exchange/cancel-order - order not found."""
        mock_exists.return_value = True

        response = client.post('/exchange/cancel-order',
                              data=json.dumps({"order_id": "nonexistent"}),
                              content_type='application/json')
        assert response.status_code == 404

    @patch('xai.core.node_api.os.path.exists')
    def test_cancel_order_exception(self, mock_exists, client):
        """Test POST /exchange/cancel-order - exception."""
        mock_exists.side_effect = Exception("Error")

        response = client.post('/exchange/cancel-order',
                              data=json.dumps({"order_id": "order123"}),
                              content_type='application/json')
        assert response.status_code == 500

    @patch('xai.core.node_api.os.path.exists')
    def test_get_my_orders_no_file(self, mock_exists, client):
        """Test GET /exchange/my-orders/<address> - no file."""
        mock_exists.return_value = False

        response = client.get('/exchange/my-orders/user1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['orders'] == []

    @patch('xai.core.node_api.os.path.exists')
    def test_get_my_orders_exception(self, mock_exists, client):
        """Test GET /exchange/my-orders/<address> - exception."""
        mock_exists.side_effect = Exception("Error")

        response = client.get('/exchange/my-orders/user1')
        assert response.status_code == 500

    @patch('xai.core.node_api.os.path.exists')
    def test_get_recent_trades_no_file(self, mock_exists, client):
        """Test GET /exchange/trades - no file."""
        mock_exists.return_value = False

        response = client.get('/exchange/trades')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    @patch('xai.core.node_api.os.path.exists')
    def test_get_recent_trades_exception(self, mock_exists, client):
        """Test GET /exchange/trades - exception."""
        mock_exists.side_effect = Exception("Error")

        response = client.get('/exchange/trades')
        assert response.status_code == 500

    def test_deposit_funds_missing_fields(self, client):
        """Test POST /exchange/deposit - missing fields."""
        response = client.post('/exchange/deposit',
                              data=json.dumps({"address": "user1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_deposit_funds_exception(self, client, mock_node):
        """Test POST /exchange/deposit - exception."""
        mock_node.exchange_wallet_manager.deposit.side_effect = Exception("Error")

        data = {
            "from_address": "wallet1",
            "to_address": "exchange1",
            "currency": "AXN",
            "amount": 100
        }
        response = client.post('/exchange/deposit',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_withdraw_funds_missing_fields(self, client):
        """Test POST /exchange/withdraw - missing fields."""
        response = client.post('/exchange/withdraw',
                              data=json.dumps({"address": "user1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_withdraw_funds_exception(self, client, mock_node):
        """Test POST /exchange/withdraw - exception."""
        mock_node.exchange_wallet_manager.withdraw.side_effect = Exception("Error")

        data = {
            "from_address": "exchange1",
            "to_address": "wallet1",
            "currency": "AXN",
            "amount": 50,
            "destination": "dest1"
        }
        response = client.post('/exchange/withdraw',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_user_balance_exception(self, client, mock_node):
        """Test GET /exchange/balance/<address> - exception."""
        mock_node.exchange_wallet_manager.get_all_balances.side_effect = Exception("Error")

        response = client.get('/exchange/balance/user1')
        assert response.status_code == 500

    def test_get_currency_balance_exception(self, client, mock_node):
        """Test GET /exchange/balance/<address>/<currency> - exception."""
        mock_node.exchange_wallet_manager.get_balance.side_effect = Exception("Error")

        response = client.get('/exchange/balance/user1/AXN')
        assert response.status_code == 500

    def test_get_transactions_exception(self, client, mock_node):
        """Test GET /exchange/transactions/<address> - exception."""
        mock_node.exchange_wallet_manager.get_transaction_history.side_effect = Exception("Error")

        response = client.get('/exchange/transactions/user1')
        assert response.status_code == 500

    @patch('xai.core.node_api.os.path.exists')
    def test_get_price_history_exception(self, mock_exists, client):
        """Test GET /exchange/price-history - exception."""
        mock_exists.side_effect = Exception("Error")

        response = client.get('/exchange/price-history')
        assert response.status_code == 500

    @patch('xai.core.node_api.os.path.exists')
    def test_get_exchange_stats_exception(self, mock_exists, client):
        """Test GET /exchange/stats - exception."""
        mock_exists.side_effect = Exception("Error")

        response = client.get('/exchange/stats')
        assert response.status_code == 500


class TestNodeAPIPaymentErrorHandling:
    """Test error handling in payment processing endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.payment_processor = Mock()
        node.exchange_wallet_manager = Mock()
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    def test_buy_with_card_missing_fields(self, client):
        """Test POST /exchange/buy-with-card - missing fields."""
        response = client.post('/exchange/buy-with-card',
                              data=json.dumps({"address": "user1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_buy_with_card_calculation_failed(self, client, mock_node):
        """Test POST /exchange/buy-with-card - calculation failed."""
        mock_node.payment_processor.calculate_purchase.return_value = {"success": False, "error": "Amount too low"}

        data = {
            "from_address": "user1",
            "to_address": "exchange1",
            "usd_amount": 1,
            "email": "user@blockchain.com",
            "card_id": "card1",
            "user_id": "cust1",
            "payment_token": "tok_123",
        }
        response = client.post('/exchange/buy-with-card',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_buy_with_card_payment_failed(self, client, mock_node):
        """Test POST /exchange/buy-with-card - payment failed."""
        mock_node.payment_processor.calculate_purchase.return_value = {"success": True, "axn_amount": 1000}
        mock_node.payment_processor.process_card_payment.return_value = {"success": False, "error": "Card declined"}

        data = {
            "from_address": "user1",
            "to_address": "exchange1",
            "usd_amount": 100,
            "email": "user@blockchain.com",
            "card_id": "card1",
            "user_id": "cust1",
            "payment_token": "tok_123",
        }
        response = client.post('/exchange/buy-with-card',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_buy_with_card_exception(self, client, mock_node):
        """Test POST /exchange/buy-with-card - exception."""
        mock_node.payment_processor.calculate_purchase.side_effect = Exception("Error")

        data = {
            "from_address": "user1",
            "to_address": "exchange1",
            "usd_amount": 100,
            "email": "user@blockchain.com",
            "card_id": "card1",
            "user_id": "cust1",
            "payment_token": "tok_123",
        }
        response = client.post('/exchange/buy-with-card',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_payment_methods_exception(self, client, mock_node):
        """Test GET /exchange/payment-methods - exception."""
        mock_node.payment_processor.get_supported_payment_methods.side_effect = Exception("Error")

        response = client.get('/exchange/payment-methods')
        assert response.status_code == 500

    def test_calculate_purchase_missing_amount(self, client):
        """Test POST /exchange/calculate-purchase - missing amount."""
        response = client.post('/exchange/calculate-purchase',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Missing usd_amount' in data['error']

    def test_calculate_purchase_exception(self, client, mock_node):
        """Test POST /exchange/calculate-purchase - exception."""
        mock_node.payment_processor.calculate_purchase.side_effect = Exception("Error")

        response = client.post('/exchange/calculate-purchase',
                              data=json.dumps({"usd_amount": 100}),
                              content_type='application/json')
        assert response.status_code == 500


class TestNodeAPICryptoDepositErrorHandling:
    """Test error handling in crypto deposit endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock node."""
        node = Mock()
        node.app = Flask(__name__)
        node.crypto_deposit_manager = Mock()
        return node

    @pytest.fixture
    def client(self, mock_node):
        """Create Flask test client."""
        from xai.core.node_api import NodeAPIRoutes
        routes = NodeAPIRoutes(mock_node)
        routes.setup_routes()
        mock_node.app.config['TESTING'] = True
        return mock_node.app.test_client()

    def test_generate_deposit_address_missing_fields(self, client):
        """Test POST /exchange/crypto/generate-address - missing fields."""
        response = client.post('/exchange/crypto/generate-address',
                              data=json.dumps({"user_address": "user1"}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_generate_deposit_address_exception(self, client, mock_node):
        """Test POST /exchange/crypto/generate-address - exception."""
        mock_node.crypto_deposit_manager.generate_deposit_address.side_effect = Exception("Error")

        data = {
            "user_address": "user1",
            "currency": "BTC"
        }
        response = client.post('/exchange/crypto/generate-address',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 500

    def test_get_deposit_addresses_exception(self, client, mock_node):
        """Test GET /exchange/crypto/addresses/<address> - exception."""
        mock_node.crypto_deposit_manager.get_user_deposit_addresses.side_effect = Exception("Error")

        response = client.get('/exchange/crypto/addresses/user1')
        assert response.status_code == 500

    def test_get_pending_deposits_exception(self, client, mock_node):
        """Test GET /exchange/crypto/pending-deposits - exception."""
        mock_node.crypto_deposit_manager.get_pending_deposits.side_effect = Exception("Error")

        response = client.get('/exchange/crypto/pending-deposits')
        assert response.status_code == 500

    def test_get_deposit_history_exception(self, client, mock_node):
        """Test GET /exchange/crypto/deposit-history/<address> - exception."""
        mock_node.crypto_deposit_manager.get_deposit_history.side_effect = Exception("Error")

        response = client.get('/exchange/crypto/deposit-history/user1')
        assert response.status_code == 500

    def test_get_crypto_stats_exception(self, client, mock_node):
        """Test GET /exchange/crypto/stats - exception."""
        mock_node.crypto_deposit_manager.get_stats.side_effect = Exception("Error")

        response = client.get('/exchange/crypto/stats')
        assert response.status_code == 500
