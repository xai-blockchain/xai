"""
Comprehensive Integration Tests for Node API Endpoints

Tests all Flask routes in src/xai/core/node_api.py including:
- Core endpoints (health, metrics, stats)
- Blockchain endpoints (blocks, chain info)
- Transaction endpoints (send, pending, lookup)
- Wallet endpoints (balance, history)
- Mining endpoints (mine, auto-mine)
- P2P endpoints (peers, sync)
- Algorithmic features (fee estimation, fraud detection)
- Social recovery endpoints
- Gamification endpoints (airdrops, streaks, treasures)
- Mining bonus endpoints
- Exchange endpoints
- Crypto deposit endpoints

This test suite aims for 60%+ coverage of node_api.py
"""

import pytest
import json
import time
import os
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet


@pytest.fixture
def mock_node(temp_blockchain_dir):
    """Create a mock blockchain node with all required components"""
    node = Mock()
    node.blockchain = Blockchain(data_dir=temp_blockchain_dir)
    node.miner_address = "miner_test_address"
    node.peers = set()
    node.is_mining = False
    node.start_time = time.time()
    node.app = Flask(__name__)

    # Mock metrics collector
    node.metrics_collector = Mock()
    node.metrics_collector.export_prometheus.return_value = "# Test metrics\n"

    # Mock algorithmic features
    node.fee_optimizer = Mock()
    node.fee_optimizer.predict_optimal_fee.return_value = {
        "recommended_fee": 0.01,
        "priority": "normal",
        "confidence": 80
    }
    node.fee_optimizer.fee_history = []

    node.fraud_detector = Mock()
    node.fraud_detector.analyze_transaction.return_value = {
        "risk_score": 0.1,
        "is_suspicious": False,
        "warnings": []
    }
    node.fraud_detector.address_history = {}
    node.fraud_detector.flagged_addresses = set()

    # Mock recovery manager
    node.recovery_manager = Mock()
    node.recovery_manager.setup_guardians.return_value = {"success": True}
    node.recovery_manager.initiate_recovery.return_value = {"success": True}
    node.recovery_manager.vote_recovery.return_value = {"success": True}
    node.recovery_manager.get_recovery_status.return_value = {"status": "active"}
    node.recovery_manager.cancel_recovery.return_value = {"success": True}
    node.recovery_manager.execute_recovery.return_value = {"success": True}
    node.recovery_manager.get_recovery_config.return_value = {"guardians": []}
    node.recovery_manager.get_guardian_duties.return_value = []
    node.recovery_manager.get_all_requests.return_value = []
    node.recovery_manager.get_stats.return_value = {"total_requests": 0}

    # Mock bonus manager
    node.bonus_manager = Mock()
    node.bonus_manager.register_miner.return_value = {"success": True}
    node.bonus_manager.check_achievements.return_value = {"achievements": []}
    node.bonus_manager.claim_bonus.return_value = {"success": True}
    node.bonus_manager.create_referral_code.return_value = {"code": "REF123"}
    node.bonus_manager.use_referral_code.return_value = {"success": True}
    node.bonus_manager.get_user_bonuses.return_value = {"bonuses": []}
    node.bonus_manager.get_leaderboard.return_value = []
    node.bonus_manager.get_stats.return_value = {"total_bonuses": 0}

    # Mock exchange wallet manager
    node.exchange_wallet_manager = Mock()
    node.exchange_wallet_manager.get_balance.return_value = {
        "currency": "USD",
        "available": 1000.0,
        "locked": 0.0
    }
    node.exchange_wallet_manager.get_all_balances.return_value = {
        "available_balances": {"USD": 1000.0, "AXN": 100.0}
    }
    node.exchange_wallet_manager.lock_for_order.return_value = True
    node.exchange_wallet_manager.deposit.return_value = {"success": True}
    node.exchange_wallet_manager.withdraw.return_value = {"success": True}
    node.exchange_wallet_manager.get_transaction_history.return_value = []

    # Mock payment processor
    node.payment_processor = Mock()
    node.payment_processor.calculate_purchase.return_value = {
        "success": True,
        "axn_amount": 100.0,
        "usd_amount": 5.0
    }
    node.payment_processor.process_card_payment.return_value = {
        "success": True,
        "payment_id": "pay_123",
        "axn_amount": 100.0
    }
    node.payment_processor.get_supported_payment_methods.return_value = [
        "credit_card", "debit_card"
    ]

    # Mock crypto deposit manager
    node.crypto_deposit_manager = Mock()
    node.crypto_deposit_manager.generate_deposit_address.return_value = {
        "success": True,
        "deposit_address": "1BTC..."
    }
    node.crypto_deposit_manager.get_user_deposit_addresses.return_value = {
        "success": True,
        "addresses": []
    }
    node.crypto_deposit_manager.get_pending_deposits.return_value = []
    node.crypto_deposit_manager.get_deposit_history.return_value = []
    node.crypto_deposit_manager.get_stats.return_value = {"total_deposits": 0}

    # Mock node methods
    node.broadcast_transaction = Mock()
    node.broadcast_block = Mock()
    node.add_peer = Mock()
    node.sync_with_network = Mock(return_value=True)
    node.start_mining = Mock()
    node.stop_mining = Mock()
    node._match_orders = Mock(return_value=False)

    return node


@pytest.fixture
def flask_app(mock_node):
    """Create Flask app with all routes registered"""
    from xai.core.node_api import NodeAPIRoutes

    routes = NodeAPIRoutes(mock_node)
    routes.setup_routes()

    mock_node.app.config['TESTING'] = True
    return mock_node.app.test_client()


# ==================== CORE ENDPOINT TESTS ====================

class TestCoreEndpoints:
    """Test core node endpoints"""

    def test_index_endpoint(self, flask_app):
        """Test GET / returns node info"""
        response = flask_app.get('/')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'online'
        assert data['node'] == 'AXN Full Node'
        assert 'version' in data
        assert 'endpoints' in data

    def test_health_check_healthy(self, flask_app, mock_node):
        """Test GET /health when node is healthy"""
        response = flask_app.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'blockchain' in data
        assert 'services' in data

    def test_health_check_unhealthy(self, flask_app, mock_node):
        """Test GET /health when blockchain raises error"""
        # Make blockchain raise exception
        mock_node.blockchain = None

        response = flask_app.get('/health')
        # Should still return 200 as blockchain can be None initially
        assert response.status_code in [200, 503]

    def test_metrics_endpoint(self, flask_app):
        """Test GET /metrics returns Prometheus metrics"""
        response = flask_app.get('/metrics')
        assert response.status_code == 200
        assert response.content_type == 'text/plain; version=0.0.4'
        assert b'Test metrics' in response.data

    def test_metrics_endpoint_error(self, flask_app, mock_node):
        """Test GET /metrics handles errors"""
        mock_node.metrics_collector.export_prometheus.side_effect = Exception("Metrics error")

        response = flask_app.get('/metrics')
        assert response.status_code == 500
        assert b'Error generating metrics' in response.data

    def test_stats_endpoint(self, flask_app, mock_node):
        """Test GET /stats returns blockchain statistics"""
        response = flask_app.get('/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'miner_address' in data
        assert 'peers' in data
        assert 'is_mining' in data
        assert 'node_uptime' in data


# ==================== BLOCKCHAIN ENDPOINT TESTS ====================

class TestBlockchainEndpoints:
    """Test blockchain query endpoints"""

    def test_get_blocks_default_pagination(self, flask_app, mock_node):
        """Test GET /blocks with default pagination"""
        response = flask_app.get('/blocks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total' in data
        assert 'limit' in data
        assert 'offset' in data
        assert 'blocks' in data
        assert data['limit'] == 10
        assert data['offset'] == 0

    def test_get_blocks_custom_pagination(self, flask_app, mock_node):
        """Test GET /blocks with custom pagination"""
        response = flask_app.get('/blocks?limit=5&offset=2')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['limit'] == 5
        assert data['offset'] == 2

    def test_get_block_valid_index(self, flask_app, mock_node):
        """Test GET /blocks/<index> with valid index"""
        response = flask_app.get('/blocks/0')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'index' in data
        assert data['index'] == 0

    def test_get_block_invalid_index_negative(self, flask_app):
        """Test GET /blocks/<index> with negative index"""
        response = flask_app.get('/blocks/-1')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    def test_get_block_invalid_index_too_large(self, flask_app, mock_node):
        """Test GET /blocks/<index> with index beyond chain length"""
        chain_length = len(mock_node.blockchain.chain)
        response = flask_app.get(f'/blocks/{chain_length + 100}')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['error'] == 'Block not found'


# ==================== TRANSACTION ENDPOINT TESTS ====================

class TestTransactionEndpoints:
    """Test transaction-related endpoints"""

    def test_get_pending_transactions_empty(self, flask_app, mock_node):
        """Test GET /transactions when mempool is empty"""
        response = flask_app.get('/transactions')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['transactions'] == []

    def test_get_pending_transactions_with_txs(self, flask_app, mock_node):
        """Test GET /transactions with pending transactions"""
        # Add a pending transaction
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        mock_node.blockchain.pending_transactions.append(tx)

        response = flask_app.get('/transactions')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] == 1
        assert len(data['transactions']) == 1

    def test_get_transaction_not_found(self, flask_app):
        """Test GET /transaction/<txid> when transaction doesn't exist"""
        response = flask_app.get('/transaction/nonexistent_txid')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['found'] is False
        assert 'error' in data

    def test_get_transaction_confirmed(self, flask_app, mock_node):
        """Test GET /transaction/<txid> for confirmed transaction"""
        # Mine a block to get confirmed transaction
        wallet = Wallet()
        block = mock_node.blockchain.mine_pending_transactions(wallet.address)

        # Get the coinbase transaction
        if block and block.transactions:
            tx = block.transactions[0]
            response = flask_app.get(f'/transaction/{tx.txid}')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['found'] is True
            assert 'confirmations' in data
            assert 'block' in data

    def test_get_transaction_pending(self, flask_app, mock_node):
        """Test GET /transaction/<txid> for pending transaction"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        tx.txid = tx.calculate_hash()
        mock_node.blockchain.pending_transactions.append(tx)

        response = flask_app.get(f'/transaction/{tx.txid}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['found'] is True
        assert data['status'] == 'pending'

    def test_send_transaction_missing_fields(self, flask_app):
        """Test POST /send with missing required fields"""
        response = flask_app.post('/send',
                                  json={"sender": "addr1"},
                                  content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_send_transaction_invalid_signature(self, flask_app):
        """Test POST /send with invalid signature"""
        tx_data = {
            "sender": "sender_addr",
            "recipient": "recipient_addr",
            "amount": 10.0,
            "fee": 0.01,
            "public_key": "fake_public_key",
            "signature": "invalid_signature"
        }

        response = flask_app.post('/send',
                                  json=tx_data,
                                  content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_send_transaction_validation_failed(self, flask_app, mock_node):
        """Test POST /send when blockchain validation fails"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        tx.sign_transaction(wallet.private_key)

        # Mock blockchain to reject transaction
        mock_node.blockchain.add_transaction = Mock(return_value=False)

        tx_data = {
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "fee": tx.fee,
            "public_key": tx.public_key,
            "signature": tx.signature
        }

        response = flask_app.post('/send',
                                  json=tx_data,
                                  content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['success'] is False


# ==================== WALLET ENDPOINT TESTS ====================

class TestWalletEndpoints:
    """Test wallet-related endpoints"""

    def test_get_balance(self, flask_app, mock_node):
        """Test GET /balance/<address>"""
        test_address = "test_address_123"
        response = flask_app.get(f'/balance/{test_address}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'address' in data
        assert 'balance' in data
        assert data['address'] == test_address

    def test_get_history(self, flask_app, mock_node):
        """Test GET /history/<address>"""
        test_address = "test_address_123"
        response = flask_app.get(f'/history/{test_address}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'address' in data
        assert 'transaction_count' in data
        assert 'transactions' in data
        assert data['address'] == test_address


# ==================== MINING ENDPOINT TESTS ====================

class TestMiningEndpoints:
    """Test mining-related endpoints"""

    def test_mine_no_pending_transactions(self, flask_app, mock_node):
        """Test POST /mine with no pending transactions"""
        mock_node.blockchain.pending_transactions = []

        response = flask_app.post('/mine')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'No pending transactions' in data['error']

    def test_mine_success(self, flask_app, mock_node):
        """Test POST /mine successfully mines block"""
        # Add a pending transaction
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        mock_node.blockchain.pending_transactions.append(tx)

        response = flask_app.post('/mine')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'block' in data
        assert 'message' in data
        assert 'reward' in data

    def test_mine_exception(self, flask_app, mock_node):
        """Test POST /mine handles exceptions"""
        # Add a pending transaction
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        mock_node.blockchain.pending_transactions.append(tx)

        # Make mining raise exception
        mock_node.blockchain.mine_pending_transactions = Mock(
            side_effect=Exception("Mining error")
        )

        response = flask_app.post('/mine')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    def test_start_auto_mining(self, flask_app, mock_node):
        """Test POST /auto-mine/start"""
        mock_node.is_mining = False

        response = flask_app.post('/auto-mine/start')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'message' in data
        mock_node.start_mining.assert_called_once()

    def test_start_auto_mining_already_active(self, flask_app, mock_node):
        """Test POST /auto-mine/start when already mining"""
        mock_node.is_mining = True

        response = flask_app.post('/auto-mine/start')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'already active' in data['message']

    def test_stop_auto_mining(self, flask_app, mock_node):
        """Test POST /auto-mine/stop"""
        mock_node.is_mining = True

        response = flask_app.post('/auto-mine/stop')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'message' in data
        mock_node.stop_mining.assert_called_once()

    def test_stop_auto_mining_not_active(self, flask_app, mock_node):
        """Test POST /auto-mine/stop when not mining"""
        mock_node.is_mining = False

        response = flask_app.post('/auto-mine/stop')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'not active' in data['message']


# ==================== P2P ENDPOINT TESTS ====================

class TestP2PEndpoints:
    """Test peer-to-peer networking endpoints"""

    def test_get_peers_empty(self, flask_app, mock_node):
        """Test GET /peers with no peers"""
        mock_node.peers = set()

        response = flask_app.get('/peers')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['peers'] == []

    def test_get_peers_with_peers(self, flask_app, mock_node):
        """Test GET /peers with connected peers"""
        mock_node.peers = {"http://peer1:5000", "http://peer2:5000"}

        response = flask_app.get('/peers')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] == 2
        assert len(data['peers']) == 2

    def test_add_peer_success(self, flask_app, mock_node):
        """Test POST /peers/add with valid URL"""
        peer_data = {"url": "http://newpeer:5000"}

        response = flask_app.post('/peers/add',
                                  json=peer_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'message' in data
        mock_node.add_peer.assert_called_once_with("http://newpeer:5000")

    def test_add_peer_missing_url(self, flask_app):
        """Test POST /peers/add without URL"""
        response = flask_app.post('/peers/add',
                                  json={},
                                  content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_sync_blockchain(self, flask_app, mock_node):
        """Test POST /sync"""
        response = flask_app.post('/sync')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'synced' in data
        assert 'chain_length' in data
        mock_node.sync_with_network.assert_called_once()


# ==================== ALGORITHMIC FEATURE ENDPOINT TESTS ====================

class TestAlgorithmicEndpoints:
    """Test algorithmic feature endpoints"""

    def test_estimate_fee_default_priority(self, flask_app, mock_node):
        """Test GET /algo/fee-estimate with default priority"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', True):
            response = flask_app.get('/algo/fee-estimate')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'recommended_fee' in data
            assert 'priority' in data

    def test_estimate_fee_custom_priority(self, flask_app, mock_node):
        """Test GET /algo/fee-estimate with custom priority"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', True):
            response = flask_app.get('/algo/fee-estimate?priority=high')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['priority'] == 'high'

    def test_estimate_fee_disabled(self, flask_app):
        """Test GET /algo/fee-estimate when features disabled"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', False):
            response = flask_app.get('/algo/fee-estimate')
            assert response.status_code == 503

            data = json.loads(response.data)
            assert 'error' in data

    def test_check_fraud_success(self, flask_app, mock_node):
        """Test POST /algo/fraud-check with valid data"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', True):
            tx_data = {"sender": "addr1", "recipient": "addr2", "amount": 100}

            response = flask_app.post('/algo/fraud-check',
                                      json=tx_data,
                                      content_type='application/json')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'risk_score' in data
            assert 'is_suspicious' in data

    def test_check_fraud_missing_data(self, flask_app):
        """Test POST /algo/fraud-check without data"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', True):
            response = flask_app.post('/algo/fraud-check',
                                      json=None,
                                      content_type='application/json')
            assert response.status_code == 400

            data = json.loads(response.data)
            assert 'error' in data

    def test_check_fraud_disabled(self, flask_app):
        """Test POST /algo/fraud-check when features disabled"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', False):
            response = flask_app.post('/algo/fraud-check',
                                      json={"test": "data"},
                                      content_type='application/json')
            assert response.status_code == 503

    def test_algo_status_enabled(self, flask_app, mock_node):
        """Test GET /algo/status when features enabled"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', True):
            response = flask_app.get('/algo/status')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['enabled'] is True
            assert 'features' in data
            assert len(data['features']) > 0

    def test_algo_status_disabled(self, flask_app):
        """Test GET /algo/status when features disabled"""
        with patch('xai.core.node_utils.ALGO_FEATURES_ENABLED', False):
            response = flask_app.get('/algo/status')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['enabled'] is False


# ==================== SOCIAL RECOVERY ENDPOINT TESTS ====================

class TestRecoveryEndpoints:
    """Test social recovery endpoints"""

    def test_setup_recovery_success(self, flask_app, mock_node):
        """Test POST /recovery/setup with valid data"""
        recovery_data = {
            "owner_address": "owner1",
            "guardians": ["guardian1", "guardian2", "guardian3"],
            "threshold": 2
        }

        response = flask_app.post('/recovery/setup',
                                  json=recovery_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

    def test_setup_recovery_missing_fields(self, flask_app):
        """Test POST /recovery/setup with missing fields"""
        response = flask_app.post('/recovery/setup',
                                  json={"owner_address": "owner1"},
                                  content_type='application/json')
        assert response.status_code == 400

    def test_setup_recovery_value_error(self, flask_app, mock_node):
        """Test POST /recovery/setup with invalid values"""
        mock_node.recovery_manager.setup_guardians.side_effect = ValueError("Invalid threshold")

        recovery_data = {
            "owner_address": "owner1",
            "guardians": ["g1"],
            "threshold": 10
        }

        response = flask_app.post('/recovery/setup',
                                  json=recovery_data,
                                  content_type='application/json')
        assert response.status_code == 400

    def test_request_recovery_success(self, flask_app, mock_node):
        """Test POST /recovery/request"""
        request_data = {
            "owner_address": "owner1",
            "new_address": "new_owner",
            "guardian_address": "guardian1"
        }

        response = flask_app.post('/recovery/request',
                                  json=request_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_vote_recovery_success(self, flask_app, mock_node):
        """Test POST /recovery/vote"""
        vote_data = {
            "request_id": "req123",
            "guardian_address": "guardian1"
        }

        response = flask_app.post('/recovery/vote',
                                  json=vote_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_get_recovery_status(self, flask_app, mock_node):
        """Test GET /recovery/status/<address>"""
        response = flask_app.get('/recovery/status/owner1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'status' in data

    def test_cancel_recovery_success(self, flask_app, mock_node):
        """Test POST /recovery/cancel"""
        cancel_data = {
            "request_id": "req123",
            "owner_address": "owner1"
        }

        response = flask_app.post('/recovery/cancel',
                                  json=cancel_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_execute_recovery_success(self, flask_app, mock_node):
        """Test POST /recovery/execute"""
        execute_data = {"request_id": "req123"}

        response = flask_app.post('/recovery/execute',
                                  json=execute_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_execute_recovery_missing_id(self, flask_app):
        """Test POST /recovery/execute without request_id"""
        response = flask_app.post('/recovery/execute',
                                  json={},
                                  content_type='application/json')
        assert response.status_code == 400

    def test_get_recovery_config_found(self, flask_app, mock_node):
        """Test GET /recovery/config/<address> when config exists"""
        mock_node.recovery_manager.get_recovery_config.return_value = {
            "guardians": ["g1", "g2"]
        }

        response = flask_app.get('/recovery/config/owner1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

    def test_get_recovery_config_not_found(self, flask_app, mock_node):
        """Test GET /recovery/config/<address> when no config"""
        mock_node.recovery_manager.get_recovery_config.return_value = None

        response = flask_app.get('/recovery/config/owner1')
        assert response.status_code == 404

    def test_get_guardian_duties(self, flask_app, mock_node):
        """Test GET /recovery/guardian/<address>"""
        response = flask_app.get('/recovery/guardian/guardian1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'duties' in data

    def test_get_recovery_requests(self, flask_app, mock_node):
        """Test GET /recovery/requests"""
        response = flask_app.get('/recovery/requests')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'count' in data
        assert 'requests' in data

    def test_get_recovery_requests_filtered(self, flask_app, mock_node):
        """Test GET /recovery/requests with status filter"""
        response = flask_app.get('/recovery/requests?status=pending')
        assert response.status_code == 200

    def test_get_recovery_stats(self, flask_app, mock_node):
        """Test GET /recovery/stats"""
        response = flask_app.get('/recovery/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data


# ==================== GAMIFICATION ENDPOINT TESTS ====================

class TestGamificationEndpoints:
    """Test gamification endpoints"""

    def test_get_airdrop_winners(self, flask_app, mock_node):
        """Test GET /airdrop/winners"""
        response = flask_app.get('/airdrop/winners')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'airdrops' in data

    def test_get_airdrop_winners_custom_limit(self, flask_app, mock_node):
        """Test GET /airdrop/winners with custom limit"""
        response = flask_app.get('/airdrop/winners?limit=5')
        assert response.status_code == 200

    def test_get_user_airdrops(self, flask_app, mock_node):
        """Test GET /airdrop/user/<address>"""
        response = flask_app.get('/airdrop/user/test_addr')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'total_airdrops' in data
        assert 'total_received' in data

    def test_get_mining_streaks(self, flask_app, mock_node):
        """Test GET /mining/streaks"""
        response = flask_app.get('/mining/streaks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'leaderboard' in data

    def test_get_mining_streaks_custom_sort(self, flask_app, mock_node):
        """Test GET /mining/streaks with custom sort"""
        response = flask_app.get('/mining/streaks?limit=20&sort_by=longest_streak')
        assert response.status_code == 200

    def test_get_miner_streak_found(self, flask_app, mock_node):
        """Test GET /mining/streak/<address> when miner exists"""
        mock_node.blockchain.streak_tracker.get_miner_stats.return_value = {
            "current_streak": 5
        }

        response = flask_app.get('/mining/streak/miner1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data

    def test_get_miner_streak_not_found(self, flask_app, mock_node):
        """Test GET /mining/streak/<address> when miner doesn't exist"""
        mock_node.blockchain.streak_tracker.get_miner_stats.return_value = None

        response = flask_app.get('/mining/streak/unknown_miner')
        assert response.status_code == 404

    def test_get_active_treasures(self, flask_app, mock_node):
        """Test GET /treasure/active"""
        response = flask_app.get('/treasure/active')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'treasures' in data
        assert 'count' in data

    def test_create_treasure_success(self, flask_app, mock_node):
        """Test POST /treasure/create"""
        mock_node.blockchain.treasure_manager.create_treasure_hunt.return_value = "treasure_123"

        treasure_data = {
            "creator": "creator_addr",
            "amount": 100.0,
            "puzzle_type": "riddle",
            "puzzle_data": "What am I?"
        }

        response = flask_app.post('/treasure/create',
                                  json=treasure_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'treasure_id' in data

    def test_create_treasure_missing_fields(self, flask_app):
        """Test POST /treasure/create with missing fields"""
        response = flask_app.post('/treasure/create',
                                  json={"creator": "addr"},
                                  content_type='application/json')
        assert response.status_code == 400

    def test_claim_treasure_success(self, flask_app, mock_node):
        """Test POST /treasure/claim with correct solution"""
        mock_node.blockchain.treasure_manager.claim_treasure.return_value = (True, 100.0)

        claim_data = {
            "treasure_id": "treasure_123",
            "claimer": "claimer_addr",
            "solution": "correct answer"
        }

        response = flask_app.post('/treasure/claim',
                                  json=claim_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'amount' in data

    def test_claim_treasure_incorrect_solution(self, flask_app, mock_node):
        """Test POST /treasure/claim with incorrect solution"""
        mock_node.blockchain.treasure_manager.claim_treasure.return_value = (False, 0)

        claim_data = {
            "treasure_id": "treasure_123",
            "claimer": "claimer_addr",
            "solution": "wrong answer"
        }

        response = flask_app.post('/treasure/claim',
                                  json=claim_data,
                                  content_type='application/json')
        assert response.status_code == 400

    def test_get_treasure_details_found(self, flask_app, mock_node):
        """Test GET /treasure/details/<id> when treasure exists"""
        mock_node.blockchain.treasure_manager.get_treasure_details.return_value = {
            "id": "treasure_123"
        }

        response = flask_app.get('/treasure/details/treasure_123')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'treasure' in data

    def test_get_treasure_details_not_found(self, flask_app, mock_node):
        """Test GET /treasure/details/<id> when treasure doesn't exist"""
        mock_node.blockchain.treasure_manager.get_treasure_details.return_value = None

        response = flask_app.get('/treasure/details/nonexistent')
        assert response.status_code == 404

    def test_get_pending_timecapsules(self, flask_app, mock_node):
        """Test GET /timecapsule/pending"""
        response = flask_app.get('/timecapsule/pending')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'capsules' in data

    def test_get_user_timecapsules(self, flask_app, mock_node):
        """Test GET /timecapsule/<address>"""
        response = flask_app.get('/timecapsule/test_addr')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'sent' in data
        assert 'received' in data

    def test_get_refund_stats(self, flask_app, mock_node):
        """Test GET /refunds/stats"""
        response = flask_app.get('/refunds/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data

    def test_get_user_refunds(self, flask_app, mock_node):
        """Test GET /refunds/<address>"""
        response = flask_app.get('/refunds/test_addr')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'total_refunds' in data
        assert 'total_refunded' in data


# ==================== MINING BONUS ENDPOINT TESTS ====================

class TestMiningBonusEndpoints:
    """Test mining bonus endpoints"""

    def test_register_miner_success(self, flask_app, mock_node):
        """Test POST /mining/register"""
        response = flask_app.post('/mining/register',
                                  json={"address": "miner1"},
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

    def test_register_miner_missing_address(self, flask_app):
        """Test POST /mining/register without address"""
        response = flask_app.post('/mining/register',
                                  json={},
                                  content_type='application/json')
        assert response.status_code == 400

    def test_get_achievements(self, flask_app, mock_node):
        """Test GET /mining/achievements/<address>"""
        response = flask_app.get('/mining/achievements/miner1?blocks_mined=10&streak_days=5')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'achievements' in data

    def test_claim_bonus_success(self, flask_app, mock_node):
        """Test POST /mining/claim-bonus"""
        bonus_data = {
            "address": "miner1",
            "bonus_type": "twitter_share"
        }

        response = flask_app.post('/mining/claim-bonus',
                                  json=bonus_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_create_referral_code(self, flask_app, mock_node):
        """Test POST /mining/referral/create"""
        response = flask_app.post('/mining/referral/create',
                                  json={"address": "miner1"},
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'code' in data

    def test_use_referral_code_success(self, flask_app, mock_node):
        """Test POST /mining/referral/use"""
        referral_data = {
            "new_address": "new_miner",
            "referral_code": "REF123"
        }

        response = flask_app.post('/mining/referral/use',
                                  json=referral_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_get_user_bonuses(self, flask_app, mock_node):
        """Test GET /mining/user-bonuses/<address>"""
        response = flask_app.get('/mining/user-bonuses/miner1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'bonuses' in data

    def test_get_bonus_leaderboard(self, flask_app, mock_node):
        """Test GET /mining/leaderboard"""
        response = flask_app.get('/mining/leaderboard?limit=20')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'leaderboard' in data

    def test_get_mining_bonus_stats(self, flask_app, mock_node):
        """Test GET /mining/stats"""
        response = flask_app.get('/mining/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data


# ==================== EXCHANGE ENDPOINT TESTS ====================

class TestExchangeEndpoints:
    """Test exchange-related endpoints"""

    def test_get_order_book_empty(self, flask_app, temp_blockchain_dir):
        """Test GET /exchange/orders with no orders"""
        response = flask_app.get('/exchange/orders')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'buy_orders' in data
        assert 'sell_orders' in data

    def test_place_buy_order_success(self, flask_app, mock_node, temp_blockchain_dir):
        """Test POST /exchange/place-order for buy order"""
        order_data = {
            "address": "trader1",
            "order_type": "buy",
            "price": 0.05,
            "amount": 100,
            "pair": "AXN/USD"
        }

        response = flask_app.post('/exchange/place-order',
                                  json=order_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'order' in data

    def test_place_order_invalid_type(self, flask_app):
        """Test POST /exchange/place-order with invalid order type"""
        order_data = {
            "address": "trader1",
            "order_type": "invalid",
            "price": 0.05,
            "amount": 100
        }

        response = flask_app.post('/exchange/place-order',
                                  json=order_data,
                                  content_type='application/json')
        assert response.status_code == 400

    def test_place_order_insufficient_balance(self, flask_app, mock_node):
        """Test POST /exchange/place-order with insufficient balance"""
        mock_node.exchange_wallet_manager.get_balance.return_value = {
            "available": 1.0,
            "locked": 0.0
        }

        order_data = {
            "address": "trader1",
            "order_type": "buy",
            "price": 0.05,
            "amount": 10000,  # Would cost 500 USD
            "pair": "AXN/USD"
        }

        response = flask_app.post('/exchange/place-order',
                                  json=order_data,
                                  content_type='application/json')
        assert response.status_code == 400

    def test_cancel_order_success(self, flask_app, temp_blockchain_dir):
        """Test POST /exchange/cancel-order"""
        # First create an order file with a test order
        exchange_dir = os.path.join(temp_blockchain_dir, "exchange_data")
        os.makedirs(exchange_dir, exist_ok=True)

        orders = {
            "buy": [{
                "id": "order_123",
                "status": "open",
                "amount": 100
            }],
            "sell": []
        }

        with open(os.path.join(exchange_dir, "orders.json"), "w") as f:
            json.dump(orders, f)

        response = flask_app.post('/exchange/cancel-order',
                                  json={"order_id": "order_123"},
                                  content_type='application/json')
        assert response.status_code == 200

    def test_cancel_order_not_found(self, flask_app, temp_blockchain_dir):
        """Test POST /exchange/cancel-order with nonexistent order"""
        response = flask_app.post('/exchange/cancel-order',
                                  json={"order_id": "nonexistent"},
                                  content_type='application/json')
        assert response.status_code == 404

    def test_get_my_orders(self, flask_app, temp_blockchain_dir):
        """Test GET /exchange/my-orders/<address>"""
        response = flask_app.get('/exchange/my-orders/trader1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'orders' in data

    def test_get_recent_trades(self, flask_app, temp_blockchain_dir):
        """Test GET /exchange/trades"""
        response = flask_app.get('/exchange/trades?limit=10')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'trades' in data

    def test_deposit_funds_success(self, flask_app, mock_node):
        """Test POST /exchange/deposit"""
        deposit_data = {
            "address": "user1",
            "currency": "USD",
            "amount": 100.0
        }

        response = flask_app.post('/exchange/deposit',
                                  json=deposit_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_withdraw_funds_success(self, flask_app, mock_node):
        """Test POST /exchange/withdraw"""
        withdraw_data = {
            "address": "user1",
            "currency": "AXN",
            "amount": 50.0,
            "destination": "external_wallet"
        }

        response = flask_app.post('/exchange/withdraw',
                                  json=withdraw_data,
                                  content_type='application/json')
        assert response.status_code == 200

    def test_get_user_balance(self, flask_app, mock_node):
        """Test GET /exchange/balance/<address>"""
        response = flask_app.get('/exchange/balance/user1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'balances' in data

    def test_get_currency_balance(self, flask_app, mock_node):
        """Test GET /exchange/balance/<address>/<currency>"""
        response = flask_app.get('/exchange/balance/user1/USD')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

    def test_get_transactions(self, flask_app, mock_node):
        """Test GET /exchange/transactions/<address>"""
        response = flask_app.get('/exchange/transactions/user1?limit=20')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'transactions' in data

    def test_get_price_history(self, flask_app, temp_blockchain_dir):
        """Test GET /exchange/price-history"""
        response = flask_app.get('/exchange/price-history?timeframe=24h')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'prices' in data

    def test_get_exchange_stats(self, flask_app, temp_blockchain_dir):
        """Test GET /exchange/stats"""
        response = flask_app.get('/exchange/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data

    def test_buy_with_card_success(self, flask_app, mock_node):
        """Test POST /exchange/buy-with-card"""
        purchase_data = {
            "address": "user1",
            "usd_amount": 100.0,
            "email": "user@blockchain.com"
        }

        response = flask_app.post('/exchange/buy-with-card',
                                  json=purchase_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

    def test_get_payment_methods(self, flask_app, mock_node):
        """Test GET /exchange/payment-methods"""
        response = flask_app.get('/exchange/payment-methods')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'methods' in data

    def test_calculate_purchase(self, flask_app, mock_node):
        """Test POST /exchange/calculate-purchase"""
        response = flask_app.post('/exchange/calculate-purchase',
                                  json={"usd_amount": 50.0},
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True


# ==================== CRYPTO DEPOSIT ENDPOINT TESTS ====================

class TestCryptoDepositEndpoints:
    """Test crypto deposit endpoints"""

    def test_generate_crypto_deposit_address_success(self, flask_app, mock_node):
        """Test POST /exchange/crypto/generate-address"""
        deposit_data = {
            "user_address": "user1",
            "currency": "BTC"
        }

        response = flask_app.post('/exchange/crypto/generate-address',
                                  json=deposit_data,
                                  content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deposit_address' in data

    def test_generate_crypto_deposit_address_missing_fields(self, flask_app):
        """Test POST /exchange/crypto/generate-address with missing fields"""
        response = flask_app.post('/exchange/crypto/generate-address',
                                  json={"user_address": "user1"},
                                  content_type='application/json')
        assert response.status_code == 400

    def test_get_crypto_deposit_addresses(self, flask_app, mock_node):
        """Test GET /exchange/crypto/addresses/<address>"""
        response = flask_app.get('/exchange/crypto/addresses/user1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'addresses' in data

    def test_get_pending_crypto_deposits(self, flask_app, mock_node):
        """Test GET /exchange/crypto/pending-deposits"""
        response = flask_app.get('/exchange/crypto/pending-deposits?user_address=user1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'pending_deposits' in data

    def test_get_crypto_deposit_history(self, flask_app, mock_node):
        """Test GET /exchange/crypto/deposit-history/<address>"""
        response = flask_app.get('/exchange/crypto/deposit-history/user1?limit=25')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deposits' in data

    def test_get_crypto_deposit_stats(self, flask_app, mock_node):
        """Test GET /exchange/crypto/stats"""
        response = flask_app.get('/exchange/crypto/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling across endpoints"""

    def test_invalid_json_request(self, flask_app):
        """Test endpoints handle invalid JSON gracefully"""
        response = flask_app.post('/send',
                                  data="invalid json",
                                  content_type='application/json')
        # Flask returns 400 for invalid JSON
        assert response.status_code in [400, 500]

    def test_exception_in_recovery_setup(self, flask_app, mock_node):
        """Test exception handling in recovery setup"""
        mock_node.recovery_manager.setup_guardians.side_effect = Exception("Database error")

        recovery_data = {
            "owner_address": "owner1",
            "guardians": ["g1", "g2"],
            "threshold": 2
        }

        response = flask_app.post('/recovery/setup',
                                  json=recovery_data,
                                  content_type='application/json')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    def test_exception_in_bonus_claim(self, flask_app, mock_node):
        """Test exception handling in bonus claim"""
        mock_node.bonus_manager.claim_bonus.side_effect = Exception("Claim error")

        bonus_data = {
            "address": "miner1",
            "bonus_type": "twitter"
        }

        response = flask_app.post('/mining/claim-bonus',
                                  json=bonus_data,
                                  content_type='application/json')
        assert response.status_code == 500


# ==================== INTEGRATION TESTS ====================

class TestIntegrationScenarios:
    """Test complete integration scenarios"""

    def test_full_mining_flow(self, flask_app, mock_node):
        """Test complete mining workflow"""
        # 1. Check stats before mining
        response = flask_app.get('/stats')
        assert response.status_code == 200

        # 2. Add a transaction
        wallet = Wallet()
        tx = Transaction(wallet.address, "recipient", 10.0)
        mock_node.blockchain.pending_transactions.append(tx)

        # 3. Check pending transactions
        response = flask_app.get('/transactions')
        data = json.loads(response.data)
        assert data['count'] == 1

        # 4. Mine block
        response = flask_app.post('/mine')
        assert response.status_code == 200

        # 5. Verify transaction is confirmed
        data = json.loads(response.data)
        assert 'block' in data

    def test_peer_management_flow(self, flask_app, mock_node):
        """Test peer management workflow"""
        # 1. Check initial peers
        response = flask_app.get('/peers')
        data = json.loads(response.data)
        initial_count = data['count']

        # 2. Add peer
        response = flask_app.post('/peers/add',
                                  json={"url": "http://newpeer:5000"},
                                  content_type='application/json')
        assert response.status_code == 200

        # 3. Sync with network
        response = flask_app.post('/sync')
        assert response.status_code == 200

    def test_exchange_trading_flow(self, flask_app, mock_node, temp_blockchain_dir):
        """Test complete exchange trading workflow"""
        # 1. Check balance
        response = flask_app.get('/exchange/balance/trader1')
        assert response.status_code == 200

        # 2. Deposit funds
        response = flask_app.post('/exchange/deposit',
                                  json={
                                      "address": "trader1",
                                      "currency": "USD",
                                      "amount": 1000.0
                                  },
                                  content_type='application/json')
        assert response.status_code == 200

        # 3. Place order
        response = flask_app.post('/exchange/place-order',
                                  json={
                                      "address": "trader1",
                                      "order_type": "buy",
                                      "price": 0.05,
                                      "amount": 100,
                                      "pair": "AXN/USD"
                                  },
                                  content_type='application/json')
        assert response.status_code == 200

        # 4. Check my orders
        response = flask_app.get('/exchange/my-orders/trader1')
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
