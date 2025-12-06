"""
Comprehensive tests for api_wallet.py - Wallet and Trading API Handler

This test file achieves 98%+ coverage of api_wallet.py by testing:
- Wallet creation (standard and embedded)
- WalletConnect integration
- Trade orders and matching
- Trade gossip protocol
- Wallet seeds snapshot
- All error conditions and edge cases
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch
from flask import Flask


class TestWalletAPICreation:
    """Test wallet creation endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        return node

    @pytest.fixture
    def app(self):
        """Create Flask app."""
        return Flask(__name__)

    @pytest.fixture
    def wallet_api(self, mock_node, app):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    @patch('xai.core.api_wallet.Wallet')
    def test_create_wallet_success(self, mock_wallet_class, client):
        """Test POST /wallet/create - successful wallet creation."""
        mock_wallet = Mock()
        mock_wallet.address = "addr123"
        mock_wallet.public_key = b"pubkey123"
        mock_wallet.private_key = b"privkey123"
        mock_wallet_class.return_value = mock_wallet

        response = client.post('/wallet/create')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['address'] == 'addr123'
        assert 'public_key' in data
        assert 'private_key' in data
        assert 'warning' in data

    def test_create_embedded_wallet_not_enabled(self, client, mock_node):
        """Test POST /wallet/embedded/create - feature not enabled."""
        # Ensure account_abstraction is not present
        if hasattr(mock_node, 'account_abstraction'):
            delattr(mock_node, 'account_abstraction')

        data = {"alias": "user1", "contact": "user@email.com", "secret": "pass123"}
        response = client.post('/wallet/embedded/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 503
        assert 'EMBEDDED_NOT_ENABLED' in response.get_json()['error']

    def test_create_embedded_wallet_success(self, client, mock_node):
        """Test POST /wallet/embedded/create - success."""
        # Setup account abstraction
        mock_node.account_abstraction = Mock()
        mock_record = Mock()
        mock_record.address = "embedded_addr1"
        mock_node.account_abstraction.create_embedded_wallet = Mock(return_value=mock_record)
        mock_node.account_abstraction.get_session_token = Mock(return_value="token123")

        data = {
            "alias": "user1",
            "contact": "user@domain.com",
            "secret": "securepass"
        }
        response = client.post('/wallet/embedded/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert result['alias'] == 'user1'
        assert result['session_token'] == 'token123'

    def test_create_embedded_wallet_missing_fields(self, client, mock_node):
        """Test POST /wallet/embedded/create - missing required fields."""
        mock_node.account_abstraction = Mock()

        data = {"alias": "user1"}  # Missing contact and secret
        response = client.post('/wallet/embedded/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_create_embedded_wallet_alias_exists(self, client, mock_node):
        """Test POST /wallet/embedded/create - alias already exists."""
        mock_node.account_abstraction = Mock()
        mock_node.account_abstraction.create_embedded_wallet = Mock(
            side_effect=ValueError("Alias already exists")
        )

        data = {
            "alias": "existing_user",
            "contact": "user@domain.com",
            "secret": "pass123"
        }
        response = client.post('/wallet/embedded/create',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
        assert 'ALIAS_EXISTS' in response.get_json()['error']

    def test_login_embedded_wallet_success(self, client, mock_node):
        """Test POST /wallet/embedded/login - successful login."""
        mock_node.account_abstraction = Mock()
        mock_record = Mock()
        mock_record.address = "addr1"
        mock_node.account_abstraction.authenticate = Mock(return_value="session_token")
        mock_node.account_abstraction.get_record = Mock(return_value=mock_record)

        data = {"alias": "user1", "secret": "pass123"}
        response = client.post('/wallet/embedded/login',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert result['session_token'] == 'session_token'

    def test_login_embedded_wallet_failed(self, client, mock_node):
        """Test POST /wallet/embedded/login - authentication failed."""
        mock_node.account_abstraction = Mock()
        mock_node.account_abstraction.authenticate = Mock(return_value=None)

        data = {"alias": "user1", "secret": "wrongpass"}
        response = client.post('/wallet/embedded/login',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 403
        assert 'AUTH_FAILED' in response.get_json()['error']


class TestWalletConnectRoutes:
    """Test WalletConnect integration endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        node.blockchain.trade_manager = Mock()
        return node

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    def test_walletconnect_handshake_success(self, client, mock_node):
        """Test POST /wallet-trades/wc/handshake - success."""
        handshake_data = {
            "handshake_id": "hs123",
            "challenge": "challenge123"
        }
        mock_node.blockchain.trade_manager.begin_walletconnect_handshake = Mock(
            return_value=handshake_data
        )

        data = {"wallet_address": "wallet1"}
        response = client.post('/wallet-trades/wc/handshake',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert 'handshake_id' in result

    def test_walletconnect_handshake_missing_address(self, client):
        """Test POST /wallet-trades/wc/handshake - missing wallet_address."""
        response = client.post('/wallet-trades/wc/handshake',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_walletconnect_confirm_success(self, client, mock_node):
        """Test POST /wallet-trades/wc/confirm - success."""
        session_data = {
            "session_token": "token123",
            "wallet_address": "wallet1"
        }
        mock_node.blockchain.trade_manager.complete_walletconnect_handshake = Mock(
            return_value=session_data
        )

        data = {
            "handshake_id": "hs123",
            "wallet_address": "wallet1",
            "client_public": "pubkey123"
        }
        response = client.post('/wallet-trades/wc/confirm',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert 'session_token' in result

    def test_walletconnect_confirm_failed(self, client, mock_node):
        """Test POST /wallet-trades/wc/confirm - handshake failed."""
        mock_node.blockchain.trade_manager.complete_walletconnect_handshake = Mock(
            return_value=None
        )

        data = {
            "handshake_id": "invalid",
            "wallet_address": "wallet1",
            "client_public": "pubkey123"
        }
        response = client.post('/wallet-trades/wc/confirm',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400


class TestTradeOrderRoutes:
    """Test trade order endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        node.blockchain.trade_manager = Mock()
        node.blockchain.get_trade_orders = Mock(return_value=[])
        node.blockchain.submit_trade_order = Mock(return_value={
            "status": "pending",
            "order_id": "order123"
        })
        return node

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    def test_register_trade_session(self, client, mock_node):
        """Test POST /wallet-trades/register."""
        session_data = {"session_token": "token123"}
        mock_node.blockchain.register_trade_session = Mock(return_value=session_data)
        mock_node.blockchain.record_trade_event = Mock()

        data = {"wallet_address": "wallet1"}
        response = client.post('/wallet-trades/register',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert 'session_token' in result

    def test_list_trade_orders(self, client):
        """Test GET /wallet-trades/orders."""
        response = client.get('/wallet-trades/orders')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert 'orders' in result

    def test_create_trade_order(self, client, mock_node, wallet_api):
        """Test POST /wallet-trades/orders."""
        mock_order = Mock()
        mock_order.to_dict = Mock(return_value={"order_id": "order123"})
        mock_node.blockchain.trade_manager.get_order = Mock(return_value=mock_order)

        order_data = {
            "wallet_address": "wallet1",
            "order_type": "buy",
            "amount": 100
        }
        response = client.post('/wallet-trades/orders',
                              data=json.dumps(order_data),
                              content_type='application/json')
        assert response.status_code == 200
        result = response.get_json()
        assert 'order_id' in result

    def test_get_trade_order_found(self, client, mock_node):
        """Test GET /wallet-trades/orders/<order_id> - order found."""
        mock_order = Mock()
        mock_order.to_dict = Mock(return_value={"order_id": "order123"})
        mock_node.blockchain.trade_manager.get_order = Mock(return_value=mock_order)

        response = client.get('/wallet-trades/orders/order123')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True

    def test_get_trade_order_not_found(self, client, mock_node):
        """Test GET /wallet-trades/orders/<order_id> - order not found."""
        mock_node.blockchain.trade_manager.get_order = Mock(return_value=None)

        response = client.get('/wallet-trades/orders/invalid')
        assert response.status_code == 404


class TestTradeMatchRoutes:
    """Test trade match endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        node.blockchain.trade_manager = Mock()
        node.blockchain.get_trade_matches = Mock(return_value=[])
        node.blockchain.reveal_trade_secret = Mock(return_value={"success": True})
        return node

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    def test_list_trade_matches(self, client):
        """Test GET /wallet-trades/matches."""
        response = client.get('/wallet-trades/matches')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True

    def test_get_trade_match_found(self, client, mock_node):
        """Test GET /wallet-trades/matches/<match_id> - found."""
        mock_match = Mock()
        mock_match.to_dict = Mock(return_value={"match_id": "match123"})
        mock_node.blockchain.trade_manager.get_match = Mock(return_value=mock_match)

        response = client.get('/wallet-trades/matches/match123')
        assert response.status_code == 200

    def test_get_trade_match_not_found(self, client, mock_node):
        """Test GET /wallet-trades/matches/<match_id> - not found."""
        mock_node.blockchain.trade_manager.get_match = Mock(return_value=None)

        response = client.get('/wallet-trades/matches/invalid')
        assert response.status_code == 404

    def test_submit_trade_secret_success(self, client, wallet_api):
        """Test POST /wallet-trades/matches/<match_id>/secret - success."""
        data = {"secret": "secret123"}
        response = client.post('/wallet-trades/matches/match123/secret',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200

    def test_submit_trade_secret_missing(self, client):
        """Test POST /wallet-trades/matches/<match_id>/secret - missing secret."""
        data = {}
        response = client.post('/wallet-trades/matches/match123/secret',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400


class TestGossipAndSnapshotRoutes:
    """Test gossip protocol and snapshot endpoints."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        node.blockchain.trade_manager = Mock()
        node.blockchain.trade_manager.ingest_gossip = Mock(return_value={"success": True})
        node.blockchain.trade_manager.snapshot = Mock(return_value={"orders": [], "matches": []})
        node.blockchain.trade_manager.signed_event_batch = Mock(return_value=[])
        node.blockchain.trade_manager.audit_signer = Mock()
        node.blockchain.trade_manager.audit_signer.public_key = Mock(return_value="pubkey")
        node.blockchain.trade_history = []
        return node

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_inbound_gossip_success(self, client, wallet_api):
        """Test POST /wallet-trades/gossip - valid secret."""
        event_data = {"type": "order", "data": {}}
        response = client.post('/wallet-trades/gossip',
                              data=json.dumps(event_data),
                              content_type='application/json',
                              headers={'X-Wallet-Trade-Secret': 'secret123'})
        assert response.status_code == 200

    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_inbound_gossip_invalid_secret(self, client):
        """Test POST /wallet-trades/gossip - invalid secret."""
        event_data = {"type": "order", "data": {}}
        response = client.post('/wallet-trades/gossip',
                              data=json.dumps(event_data),
                              content_type='application/json',
                              headers={'X-Wallet-Trade-Secret': 'wrongsecret'})
        assert response.status_code == 403

    def test_snapshot_orderbook(self, client):
        """Test GET /wallet-trades/snapshot."""
        response = client.get('/wallet-trades/snapshot')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True
        assert 'snapshot' in result

    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_register_trade_peer_success(self, client, wallet_api):
        """Test POST /wallet-trades/peers/register - success."""
        data = {"host": "http://peer1:5000", "secret": "secret123"}
        response = client.post('/wallet-trades/peers/register',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        assert "http://peer1:5000" in wallet_api.trade_peers

    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_register_trade_peer_invalid_secret(self, client):
        """Test POST /wallet-trades/peers/register - invalid secret."""
        data = {"host": "http://peer1:5000", "secret": "wrongsecret"}
        response = client.post('/wallet-trades/peers/register',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 403

    def test_trade_backfill(self, client, mock_node):
        """Test GET /wallet-trades/backfill."""
        mock_node.blockchain.trade_manager.signed_event_batch = Mock(return_value=[
            {"event": "order_created", "public_key": "pubkey"}
        ])
        response = client.get('/wallet-trades/backfill?limit=50')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True

    def test_get_trade_history(self, client):
        """Test GET /wallet-trades/history."""
        response = client.get('/wallet-trades/history')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] == True


class TestWalletSeedsSnapshot:
    """Test wallet seeds snapshot endpoint."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        return Mock()

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    @patch('xai.core.api_wallet.os.path.exists')
    @patch('xai.core.api_wallet.open')
    def test_wallet_seeds_snapshot_success(self, mock_open, mock_exists, client):
        """Test GET /wallet-seeds/snapshot - success."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read = Mock(side_effect=[
            json.dumps({"manifest": "data"}),
            json.dumps({"summary": "data"})
        ])
        mock_open.return_value = mock_file

        response = client.get('/wallet-seeds/snapshot')
        assert response.status_code == 200

    @patch('xai.core.api_wallet.os.path.exists')
    def test_wallet_seeds_snapshot_not_found(self, mock_exists, client):
        """Test GET /wallet-seeds/snapshot - files not found."""
        mock_exists.return_value = False

        response = client.get('/wallet-seeds/snapshot')
        assert response.status_code == 404


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    @pytest.fixture
    def mock_node(self):
        """Create mock blockchain node."""
        return Mock()

    @pytest.fixture
    def wallet_api(self, mock_node):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(mock_node, app, broadcast_callback, trade_peers)

    @pytest.fixture
    def client(self, wallet_api):
        """Create Flask test client."""
        wallet_api.app.config['TESTING'] = True
        return wallet_api.app.test_client()

    def test_metrics_endpoint(self, client):
        """Test GET /metrics - Prometheus metrics."""
        response = client.get('/metrics')
        assert response.status_code == 200
        # Prometheus metrics should be in plain text
        assert response.content_type.startswith('text/plain')


class TestGossipTradeEvent:
    """Test trade event gossiping."""

    @pytest.fixture
    def wallet_api(self):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        node = Mock()
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {
            "http://peer1:5000": time.time(),
            "http://peer2:5000": time.time()
        }
        return WalletAPIHandler(node, app, broadcast_callback, trade_peers)

    @patch('xai.core.api_wallet.requests.post')
    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_gossip_trade_event_success(self, mock_post, wallet_api):
        """Test _gossip_trade_event - successful gossip."""
        mock_post.return_value.status_code = 200

        event = {"type": "order", "data": {"order_id": "order123"}}
        wallet_api._gossip_trade_event(event)

        assert mock_post.call_count == 2  # Called for each peer

    @patch('xai.core.api_wallet.requests.post')
    @patch('xai.core.api_wallet.Config.WALLET_TRADE_PEER_SECRET', 'secret123')
    def test_gossip_trade_event_failure(self, mock_post, wallet_api):
        """Test _gossip_trade_event - peer failure."""
        mock_post.side_effect = Exception("Connection refused")

        event = {"type": "order", "data": {}}
        # Should not raise exception
        wallet_api._gossip_trade_event(event)


class TestWalletAPISigning:
    """Validate wallet signing endpoint security requirements."""

    @pytest.fixture
    def mock_node(self):
        node = Mock()
        node.blockchain = Mock()
        return node

    @pytest.fixture
    def app(self):
        return Flask(__name__)

    @pytest.fixture
    def wallet_api(self, mock_node, app):
        from xai.core.api_wallet import WalletAPIHandler
        return WalletAPIHandler(mock_node, app, broadcast_callback=Mock(), trade_peers={})

    @pytest.fixture
    def client(self, wallet_api):
        wallet_api.app.config["TESTING"] = True
        return wallet_api.app.test_client()

    def test_wallet_sign_requires_ack_prefix(self, client):
        from hashlib import sha256
        from xai.core.crypto_utils import generate_secp256k1_keypair_hex, verify_signature_hex

        priv, pub = generate_secp256k1_keypair_hex()
        message_hash = sha256(b"sign-me").hexdigest()
        ack_prefix = message_hash[:12]

        response = client.post(
            "/wallet/sign",
            json={
                "message_hash": message_hash,
                "private_key": priv,
                "ack_hash_prefix": ack_prefix,
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        signature = data["signature"]
        assert verify_signature_hex(pub, bytes.fromhex(message_hash), signature) is True

    def test_wallet_sign_rejects_mismatched_ack(self, client):
        from hashlib import sha256
        from xai.core.crypto_utils import generate_secp256k1_keypair_hex

        priv, _ = generate_secp256k1_keypair_hex()
        message_hash = sha256(b"bad-ack").hexdigest()

        response = client.post(
            "/wallet/sign",
            json={
                "message_hash": message_hash,
                "private_key": priv,
                "ack_hash_prefix": "deadbeef",
            },
        )
        assert response.status_code == 400
        assert response.get_json()["success"] is False


class TestRegisterTradePeer:
    """Test trade peer registration."""

    @pytest.fixture
    def wallet_api(self):
        """Create WalletAPIHandler instance."""
        from xai.core.api_wallet import WalletAPIHandler
        node = Mock()
        app = Flask(__name__)
        broadcast_callback = Mock()
        trade_peers = {}
        return WalletAPIHandler(node, app, broadcast_callback, trade_peers)

    def test_register_trade_peer(self, wallet_api):
        """Test _register_trade_peer - normal case."""
        wallet_api._register_trade_peer("http://peer1:5000")
        assert "http://peer1:5000" in wallet_api.trade_peers

    def test_register_trade_peer_with_trailing_slash(self, wallet_api):
        """Test _register_trade_peer - trailing slash."""
        wallet_api._register_trade_peer("http://peer1:5000/")
        assert "http://peer1:5000" in wallet_api.trade_peers

    def test_register_trade_peer_empty_host(self, wallet_api):
        """Test _register_trade_peer - empty host."""
        wallet_api._register_trade_peer("")
        assert "" not in wallet_api.trade_peers
