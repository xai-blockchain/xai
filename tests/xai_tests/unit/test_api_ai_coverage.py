"""
Comprehensive Coverage Tests for api_ai.py

This test suite achieves 80%+ coverage by testing:
- All AI API endpoints (atomic swap, smart contract, transaction optimization, etc.)
- Personal AI assistant operations
- Request validation and context extraction
- Response formatting
- Error handling (missing headers, invalid addresses, disabled AI)
- AI questioning system (submit, answer, pending questions)
- All private methods (_personal_ai_context, _personal_ai_response)
- Edge cases and error paths
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch
from flask import Flask


class TestAIAPIHandlerInit:
    """Test AIAPIHandler initialization."""

    def test_init_registers_routes(self):
        """Test that initialization registers all routes."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        app = Flask(__name__)

        handler = AIAPIHandler(node, app)

        # Verify attributes
        assert handler.node is node
        assert handler.app is app

        # Verify routes are registered
        route_rules = [rule.rule for rule in app.url_map.iter_rules()]

        # Personal AI endpoints
        assert '/personal-ai/atomic-swap' in route_rules
        assert '/personal-ai/smart-contract/create' in route_rules
        assert '/personal-ai/smart-contract/deploy' in route_rules
        assert '/personal-ai/transaction/optimize' in route_rules
        assert '/personal-ai/analyze' in route_rules
        assert '/personal-ai/wallet/analyze' in route_rules
        assert '/personal-ai/wallet/recovery' in route_rules
        assert '/personal-ai/node/setup' in route_rules
        assert '/personal-ai/liquidity/alert' in route_rules
        assert '/personal-ai/assistants' in route_rules
        assert '/personal-ai/stream' in route_rules

        # Questioning endpoints
        assert '/questioning/submit' in route_rules
        assert '/questioning/answer' in route_rules
        assert '/questioning/pending' in route_rules


class TestPersonalAIContext:
    """Test _personal_ai_context method."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_context_success_with_all_headers(self, setup):
        """Test successful context extraction with all headers."""
        handler = setup['handler']
        node = setup['node']

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345',
                'X-AI-Assistant': 'Trading Sage'
            }
        ):
            node.validator.validate_address.return_value = None
            result = handler._personal_ai_context()

            assert result['success'] is True
            assert result['user_address'] == 'XAI_test_address_123'
            assert result['ai_provider'] == 'anthropic'
            assert result['ai_model'] == 'claude-opus-4'
            assert result['user_api_key'] == 'sk-test-key-12345'
            assert result['assistant_name'] == 'Trading Sage'
            assert result['personal_ai'] is node.personal_ai

    def test_context_success_with_default_provider(self, setup):
        """Test context extraction with default AI provider."""
        handler = setup['handler']
        node = setup['node']

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-User-API-Key': 'sk-test-key-12345'
            }
        ):
            node.validator.validate_address.return_value = None
            result = handler._personal_ai_context()

            assert result['success'] is True
            assert result['ai_provider'] == 'anthropic'
            assert result['ai_model'] == 'claude-opus-4'

    def test_context_missing_user_address(self, setup):
        """Test context extraction with missing user address."""
        handler = setup['handler']

        with setup['client'].application.test_request_context(
            headers={
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            }
        ):
            result = handler._personal_ai_context()

            assert result['success'] is False
            assert result['error'] == 'MISSING_HEADERS'
            assert 'X-User-Address' in result['message']

    def test_context_missing_api_key(self, setup):
        """Test context extraction with missing API key."""
        handler = setup['handler']

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4'
            }
        ):
            result = handler._personal_ai_context()

            assert result['success'] is False
            assert result['error'] == 'MISSING_HEADERS'
            assert 'X-User-API-Key' in result['message']

    def test_context_invalid_address(self, setup):
        """Test context extraction with invalid address."""
        from xai.core.security_validation import ValidationError

        handler = setup['handler']
        node = setup['node']

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'invalid_address',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            }
        ):
            node.validator.validate_address.side_effect = ValidationError("Invalid address format")
            result = handler._personal_ai_context()

            assert result['success'] is False
            assert result['error'] == 'INVALID_ADDRESS'
            assert 'Invalid address format' in result['message']

    def test_context_personal_ai_disabled(self, setup):
        """Test context extraction when Personal AI is disabled."""
        handler = setup['handler']
        node = setup['node']
        node.personal_ai = None

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            }
        ):
            node.validator.validate_address.return_value = None
            result = handler._personal_ai_context()

            assert result['success'] is False
            assert result['error'] == 'PERSONAL_AI_DISABLED'
            assert 'not configured' in result['message']

    def test_context_empty_assistant_name(self, setup):
        """Test context extraction with empty assistant name."""
        handler = setup['handler']
        node = setup['node']

        with setup['client'].application.test_request_context(
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345',
                'X-AI-Assistant': '   '
            }
        ):
            node.validator.validate_address.return_value = None
            result = handler._personal_ai_context()

            assert result['success'] is True
            assert result['assistant_name'] is None


class TestPersonalAIResponse:
    """Test _personal_ai_response method."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client}

    def test_response_success(self, setup):
        """Test successful response formatting."""
        handler = setup['handler']

        with setup['client'].application.app_context():
            result = {'success': True, 'data': 'test data', 'transaction_id': 'tx123'}
            response, status = handler._personal_ai_response(result)

            assert status == 200
            data = json.loads(response.get_data(as_text=True))
            assert data['success'] is True
            assert data['data'] == 'test data'

    def test_response_failure(self, setup):
        """Test failure response formatting."""
        handler = setup['handler']

        with setup['client'].application.app_context():
            result = {'success': False, 'error': 'TEST_ERROR', 'message': 'Something went wrong'}
            response, status = handler._personal_ai_response(result)

            assert status == 400
            data = json.loads(response.get_data(as_text=True))
            assert data['success'] is False
            assert data['error'] == 'TEST_ERROR'


class TestAtomicSwapEndpoint:
    """Test /personal-ai/atomic-swap endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_atomic_swap_success(self, setup):
        """Test successful atomic swap."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': True,
            'swap_id': 'swap123',
            'status': 'completed'
        }

        response = setup['client'].post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['swap_id'] == 'swap123'

    def test_atomic_swap_with_nested_payload(self, setup):
        """Test atomic swap with nested swap_details."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': True,
            'swap_id': 'swap456'
        }

        response = setup['client'].post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'from_token': 'XAI', 'to_token': 'ETH', 'amount': 50}
        )

        assert response.status_code == 200

    def test_atomic_swap_missing_headers(self, setup):
        """Test atomic swap with missing headers."""
        response = setup['client'].post(
            '/personal-ai/atomic-swap',
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'MISSING_HEADERS'


class TestSmartContractCreateEndpoint:
    """Test /personal-ai/smart-contract/create endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_contract_create_success(self, setup):
        """Test successful contract creation."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'pragma solidity ^0.8.0;',
            'contract_id': 'contract123'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'contract_description': 'Create a simple token contract',
                'contract_type': 'ERC20'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'contract_code' in data

    def test_contract_create_with_description_field(self, setup):
        """Test contract creation with 'description' field instead of 'contract_description'."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'contract code here'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'description': 'Create NFT contract'}
        )

        assert response.status_code == 200

    def test_contract_create_empty_description(self, setup):
        """Test contract creation with empty description."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'default contract'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={}
        )

        assert response.status_code == 200


class TestSmartContractDeployEndpoint:
    """Test /personal-ai/smart-contract/deploy endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_contract_deploy_success(self, setup):
        """Test successful contract deployment."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0x1234567890abcdef',
            'transaction_hash': '0xabcdef123456'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'contract_code': 'pragma solidity ^0.8.0;',
                'constructor_params': {'name': 'MyToken', 'symbol': 'MTK'},
                'testnet': True,
                'signature': 'sig123'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'contract_address' in data

    def test_contract_deploy_mainnet(self, setup):
        """Test contract deployment on mainnet."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0xmainnet123'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'contract_code': 'contract code',
                'testnet': False
            }
        )

        assert response.status_code == 200


class TestTransactionOptimizeEndpoint:
    """Test /personal-ai/transaction/optimize endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_transaction_optimize_success(self, setup):
        """Test successful transaction optimization."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.optimize_transaction_with_ai.return_value = {
            'success': True,
            'optimized_transaction': {'fee': 0.001, 'gas_limit': 21000},
            'savings': 0.0005
        }

        response = setup['client'].post(
            '/personal-ai/transaction/optimize',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'transaction': {'to': 'XAI_recipient', 'amount': 100, 'fee': 0.002}}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'optimized_transaction' in data

    def test_transaction_optimize_nested_payload(self, setup):
        """Test transaction optimization with transaction as root object."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.optimize_transaction_with_ai.return_value = {
            'success': True,
            'optimized_transaction': {}
        }

        response = setup['client'].post(
            '/personal-ai/transaction/optimize',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'to': 'XAI_recipient', 'amount': 100}
        )

        assert response.status_code == 200

    def test_transaction_optimize_missing_transaction(self, setup):
        """Test transaction optimization with missing transaction."""
        node = setup['node']
        node.validator.validate_address.return_value = None

        response = setup['client'].post(
            '/personal-ai/transaction/optimize',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'transaction required'


class TestAnalyzeEndpoint:
    """Test /personal-ai/analyze endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_analyze_success(self, setup):
        """Test successful blockchain analysis."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'analysis': 'The blockchain shows high activity',
            'insights': ['Trend 1', 'Trend 2']
        }

        response = setup['client'].post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'query': 'What are the current blockchain trends?'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'analysis' in data

    def test_analyze_missing_query(self, setup):
        """Test blockchain analysis with missing query."""
        node = setup['node']
        node.validator.validate_address.return_value = None

        response = setup['client'].post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'query required'


class TestWalletAnalyzeEndpoint:
    """Test /personal-ai/wallet/analyze endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_wallet_analyze_success(self, setup):
        """Test successful wallet analysis."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_analysis_with_ai.return_value = {
            'success': True,
            'analysis': 'Portfolio well diversified',
            'recommendations': ['Hold BTC', 'Sell ETH']
        }

        response = setup['client'].post(
            '/personal-ai/wallet/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'analysis_type': 'portfolio_optimization'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_wallet_analyze_default_type(self, setup):
        """Test wallet analysis with default analysis type."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_analysis_with_ai.return_value = {
            'success': True,
            'analysis': 'Default analysis'
        }

        response = setup['client'].post(
            '/personal-ai/wallet/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={}
        )

        assert response.status_code == 200
        # Verify default analysis_type is used
        call_args = node.personal_ai.wallet_analysis_with_ai.call_args
        assert call_args[1]['analysis_type'] == 'portfolio_optimization'


class TestWalletRecoveryEndpoint:
    """Test /personal-ai/wallet/recovery endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_wallet_recovery_success(self, setup):
        """Test successful wallet recovery advice."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_recovery_advice.return_value = {
            'success': True,
            'recovery_steps': ['Step 1', 'Step 2'],
            'estimated_time': '24 hours'
        }

        response = setup['client'].post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'recovery_details': {
                    'guardians': ['XAI_guardian1', 'XAI_guardian2'],
                    'threshold': 2
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_wallet_recovery_invalid_guardian(self, setup):
        """Test wallet recovery with invalid guardian address."""
        from xai.core.security_validation import ValidationError

        node = setup['node']
        node.validator.validate_address.side_effect = [
            None,  # user_address is valid
            ValidationError("Invalid guardian address")  # first guardian is invalid
        ]

        response = setup['client'].post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'recovery_details': {
                    'guardians': ['invalid_guardian']
                }
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_GUARDIAN_ADDRESS'

    def test_wallet_recovery_nested_payload(self, setup):
        """Test wallet recovery with recovery_details as root object."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_recovery_advice.return_value = {
            'success': True
        }

        response = setup['client'].post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'guardians': ['XAI_guardian1'], 'threshold': 1}
        )

        assert response.status_code == 200


class TestNodeSetupEndpoint:
    """Test /personal-ai/node/setup endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_node_setup_success(self, setup):
        """Test successful node setup recommendations."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.validator.validate_string.return_value = None
        node.personal_ai.node_setup_recommendations.return_value = {
            'success': True,
            'recommendations': {
                'hardware': 'Recommended specs',
                'configuration': 'Config details'
            }
        }

        response = setup['client'].post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'setup_request': {
                    'preferred_region': 'us-east-1',
                    'node_type': 'full'
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_node_setup_invalid_region(self, setup):
        """Test node setup with invalid region."""
        from xai.core.security_validation import ValidationError

        node = setup['node']
        node.validator.validate_address.return_value = None
        node.validator.validate_string.side_effect = ValidationError("Region too long")

        response = setup['client'].post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'setup_request': {
                    'preferred_region': 'x' * 150
                }
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_REGION'

    def test_node_setup_no_region(self, setup):
        """Test node setup without region."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.node_setup_recommendations.return_value = {
            'success': True
        }

        response = setup['client'].post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'setup_request': {'node_type': 'light'}}
        )

        assert response.status_code == 200


class TestLiquidityAlertEndpoint:
    """Test /personal-ai/liquidity/alert endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_liquidity_alert_success(self, setup):
        """Test successful liquidity alert response."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.validator.validate_string.return_value = None
        node.personal_ai.liquidity_alert_response.return_value = {
            'success': True,
            'alert_response': 'Take action now',
            'recommended_action': 'Add liquidity'
        }

        response = setup['client'].post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'pool_name': 'XAI-ETH',
                'alert_details': {
                    'type': 'low_liquidity',
                    'current_value': 1000
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_liquidity_alert_missing_pool_name(self, setup):
        """Test liquidity alert with missing pool name."""
        node = setup['node']
        node.validator.validate_address.return_value = None

        response = setup['client'].post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'alert_details': {'type': 'low_liquidity'}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'pool_name required'

    def test_liquidity_alert_invalid_pool_name(self, setup):
        """Test liquidity alert with invalid pool name."""
        from xai.core.security_validation import ValidationError

        node = setup['node']
        node.validator.validate_address.return_value = None
        node.validator.validate_string.side_effect = ValidationError("Pool name too long")

        response = setup['client'].post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'pool_name': 'x' * 150}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_POOL_NAME'


class TestPersonalAIAssistantsEndpoint:
    """Test /personal-ai/assistants endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_assistants_list_success(self, setup):
        """Test successful listing of AI assistants."""
        node = setup['node']
        node.personal_ai = Mock()
        node.personal_ai.list_micro_assistants.return_value = [
            {
                'name': 'Trading Sage',
                'skills': ['swaps', 'liquidity'],
                'usage_count': 10
            },
            {
                'name': 'Safety Overseer',
                'skills': ['security', 'compliance'],
                'usage_count': 5
            }
        ]

        response = setup['client'].get('/personal-ai/assistants')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['assistants']) == 2
        assert data['assistants'][0]['name'] == 'Trading Sage'

    def test_assistants_list_disabled(self, setup):
        """Test listing assistants when Personal AI is disabled."""
        node = setup['node']
        node.personal_ai = None

        response = setup['client'].get('/personal-ai/assistants')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'PERSONAL_AI_DISABLED'


class TestPersonalAIStreamEndpoint:
    """Test /personal-ai/stream endpoint."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.personal_ai = Mock()
        node.validator = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_stream_success(self, setup):
        """Test successful streaming response."""
        node = setup['node']
        node.personal_ai.stream_prompt_with_ai.return_value = {
            'success': True,
            'stream': iter(["data: chunk\n\n"])
        }

        response = setup['client'].post(
            '/personal-ai/stream',
            json={'prompt': 'hello'},
            headers={
                'X-User-Address': 'XAI123',
                'X-User-API-Key': 'key',
            },
        )

        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

    def test_stream_requires_prompt(self, setup):
        """Test streaming validation when prompt missing."""
        response = setup['client'].post(
            '/personal-ai/stream',
            json={},
            headers={
                'X-User-Address': 'XAI123',
                'X-User-API-Key': 'key',
            },
        )

        assert response.status_code == 400


class TestQuestioningEndpoints:
    """Test AI questioning system endpoints."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_submit_question_success(self, setup):
        """Test successful question submission."""
        response = setup['client'].post(
            '/questioning/submit',
            json={
                'question_text': 'Should we increase block size?',
                'ai_id': 'ai_123',
                'priority': 'high'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'question_id' in data
        assert data['status'] == 'open_for_voting'
        assert 'voting_opened_at' in data

    def test_submit_question_generates_unique_id(self, setup):
        """Test that question submissions generate unique IDs."""
        response1 = setup['client'].post(
            '/questioning/submit',
            json={'question_text': 'Question 1'}
        )
        response2 = setup['client'].post(
            '/questioning/submit',
            json={'question_text': 'Question 2'}
        )

        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)

        # Question IDs should be different
        assert data1['question_id'] != data2['question_id']

    def test_submit_answer_success(self, setup):
        """Test successful answer submission."""
        response = setup['client'].post(
            '/questioning/answer',
            json={
                'question_id': 'q123',
                'answer_text': 'Yes, we should',
                'operator_address': 'XAI_operator_123'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['question_id'] == 'q123'
        assert 'total_votes' in data
        assert 'min_required' in data
        assert 'consensus_reached' in data

    def test_submit_answer_consensus_not_reached(self, setup):
        """Test answer submission when consensus is not reached."""
        response = setup['client'].post(
            '/questioning/answer',
            json={
                'question_id': 'q456',
                'answer_text': 'No'
            }
        )

        data = json.loads(response.data)
        assert data['consensus_reached'] is False
        assert data['total_votes'] == 18
        assert data['min_required'] == 25

    def test_get_pending_questions_empty(self, setup):
        """Test getting pending questions when none exist."""
        response = setup['client'].get('/questioning/pending')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['questions'] == []


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_empty_json_payload(self, setup):
        """Test endpoints with empty JSON payload."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_analysis_with_ai.return_value = {
            'success': True,
            'analysis': 'Default analysis'
        }

        response = setup['client'].post(
            '/personal-ai/wallet/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345',
                'Content-Type': 'application/json'
            },
            data=''
        )

        # Should handle empty payload gracefully
        assert response.status_code in [200, 400]

    def test_ai_operation_failure(self, setup):
        """Test handling of AI operation failure."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': False,
            'error': 'AI_ERROR',
            'message': 'AI provider unavailable'
        }

        response = setup['client'].post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'AI_ERROR'

    def test_multiple_missing_headers(self, setup):
        """Test with multiple missing headers."""
        response = setup['client'].post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_test_address_123'
            },
            json={'swap_details': {}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'MISSING_HEADERS'
        # Should list all missing headers
        assert 'X-User-API-Key' in data['message']

    def test_with_assistant_name(self, setup):
        """Test operations with specific assistant name."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'analysis': 'Analysis from Trading Sage'
        }

        response = setup['client'].post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345',
                'X-AI-Assistant': 'Trading Sage'
            },
            json={'query': 'What are the trends?'}
        )

        assert response.status_code == 200
        # Verify assistant_name was passed
        call_args = node.personal_ai.analyze_blockchain_with_ai.call_args
        assert call_args[1]['assistant_name'] == 'Trading Sage'


class TestAllEndpointsCoverage:
    """Additional tests to ensure all endpoints and code paths are covered."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return {'handler': handler, 'client': client, 'node': node}

    def test_all_endpoints_registered(self, setup):
        """Verify all 13 endpoints are registered."""
        app = setup['client'].application
        routes = [rule.rule for rule in app.url_map.iter_rules()]

        expected_routes = [
            '/personal-ai/atomic-swap',
            '/personal-ai/smart-contract/create',
            '/personal-ai/smart-contract/deploy',
            '/personal-ai/transaction/optimize',
            '/personal-ai/analyze',
            '/personal-ai/wallet/analyze',
            '/personal-ai/wallet/recovery',
            '/personal-ai/node/setup',
            '/personal-ai/liquidity/alert',
            '/personal-ai/assistants',
            '/questioning/submit',
            '/questioning/answer',
            '/questioning/pending'
        ]

        for route in expected_routes:
            assert route in routes

    def test_contract_deploy_with_all_params(self, setup):
        """Test contract deployment with all parameters."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0xdeployed'
        }

        response = setup['client'].post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'openai',
                'X-AI-Model': 'gpt-4',
                'X-User-API-Key': 'sk-openai-key',
                'X-AI-Assistant': 'Safety Overseer'
            },
            json={
                'contract_code': 'pragma solidity ^0.8.0; contract Test {}',
                'constructor_params': {'param1': 'value1'},
                'testnet': False,
                'signature': 'valid_signature_123'
            }
        )

        assert response.status_code == 200
        # Verify all parameters were passed correctly
        call_args = node.personal_ai.deploy_smart_contract_with_ai.call_args
        assert call_args[1]['contract_code'] == 'pragma solidity ^0.8.0; contract Test {}'
        assert call_args[1]['constructor_params'] == {'param1': 'value1'}
        assert call_args[1]['testnet'] is False
        assert call_args[1]['signature'] == 'valid_signature_123'
        assert call_args[1]['assistant_name'] == 'Safety Overseer'

    def test_wallet_recovery_empty_guardians(self, setup):
        """Test wallet recovery with empty guardians list."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_recovery_advice.return_value = {
            'success': True
        }

        response = setup['client'].post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'recovery_details': {'guardians': []}}
        )

        assert response.status_code == 200

    def test_node_setup_nested_payload(self, setup):
        """Test node setup with setup_request as root object."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.personal_ai.node_setup_recommendations.return_value = {
            'success': True
        }

        response = setup['client'].post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={'node_type': 'validator', 'preferred_region': 'eu-west-1'}
        )

        assert response.status_code == 200

    def test_liquidity_alert_nested_payload(self, setup):
        """Test liquidity alert with alert_details as root object."""
        node = setup['node']
        node.validator.validate_address.return_value = None
        node.validator.validate_string.return_value = None
        node.personal_ai.liquidity_alert_response.return_value = {
            'success': True
        }

        response = setup['client'].post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_test_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key-12345'
            },
            json={
                'pool_name': 'XAI-BTC',
                'type': 'price_alert',
                'threshold': 1000
            }
        )

        assert response.status_code == 200

    def test_contract_create_missing_headers(self, setup):
        """Test contract creation with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/smart-contract/create',
            json={'contract_description': 'Test contract'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_contract_deploy_missing_headers(self, setup):
        """Test contract deployment with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/smart-contract/deploy',
            json={'contract_code': 'pragma solidity ^0.8.0;'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_transaction_optimize_missing_headers(self, setup):
        """Test transaction optimization with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/transaction/optimize',
            json={'transaction': {'to': 'XAI_test', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_analyze_missing_headers(self, setup):
        """Test blockchain analysis with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/analyze',
            json={'query': 'What are the trends?'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_wallet_analyze_missing_headers(self, setup):
        """Test wallet analysis with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/wallet/analyze',
            json={'analysis_type': 'portfolio_optimization'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_wallet_recovery_missing_headers(self, setup):
        """Test wallet recovery with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/wallet/recovery',
            json={'recovery_details': {'guardians': ['XAI_guardian1']}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_node_setup_missing_headers(self, setup):
        """Test node setup with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/node/setup',
            json={'setup_request': {'preferred_region': 'us-east-1'}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_liquidity_alert_missing_headers(self, setup):
        """Test liquidity alert with missing headers to cover error path."""
        response = setup['client'].post(
            '/personal-ai/liquidity/alert',
            json={'pool_name': 'XAI-ETH', 'alert_details': {}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
