"""
Integration Tests for AI API Endpoints (api_ai.py)

This integration test suite tests:
- Real Flask app setup with AI API handler
- End-to-end endpoint testing with realistic scenarios
- Integration between node, personal AI, and API handlers
- Request/response flow validation
- Error handling in realistic scenarios
- Multi-step workflows (e.g., create then deploy contract)
- Authentication and authorization flows
- Complex data validation scenarios
"""

import pytest
import json
import time
import hashlib
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from flask import Flask

# Import centralized validation
from xai.core.validation import validate_address, validate_string


class TestAIAPIIntegrationSetup:
    """Test AI API integration setup and initialization."""

    @pytest.fixture
    def mock_node(self):
        """Create a mock blockchain node."""
        node = Mock()
        node.validator = Mock()
        node.personal_ai = Mock()

        # Mock validator methods using centralized validation
        node.validator.validate_address = Mock(side_effect=lambda addr, _: validate_address(addr, allow_special=True))
        node.validator.validate_string = Mock(side_effect=lambda s, _: validate_string(s))

        return node

    @pytest.fixture
    def flask_app(self, mock_node):
        """Create Flask app with AI API handler."""
        from xai.core.api_ai import AIAPIHandler

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = False

        # Initialize AI API handler
        handler = AIAPIHandler(mock_node, app)

        return app, mock_node, handler

    @pytest.fixture
    def test_client(self, flask_app):
        """Create test client."""
        app, node, handler = flask_app
        return app.test_client(), node, handler

    def test_flask_app_initialization(self, flask_app):
        """Test Flask app initializes correctly with AI API handler."""
        app, node, handler = flask_app

        assert app is not None
        assert handler is not None
        assert handler.node is node
        assert handler.app is app

    def test_all_routes_registered(self, flask_app):
        """Test all expected routes are registered."""
        app, _, _ = flask_app

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

        registered_routes = [rule.rule for rule in app.url_map.iter_rules()]

        for route in expected_routes:
            assert route in registered_routes, f"Route {route} not registered"


class TestAtomicSwapIntegration:
    """Integration tests for atomic swap endpoint."""

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

        return client, node

    def test_atomic_swap_complete_flow(self, setup):
        """Test complete atomic swap flow."""
        client, node = setup

        # Setup mocks
        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': True,
            'swap_id': 'swap_abc123',
            'status': 'pending',
            'from_token': 'XAI',
            'to_token': 'BTC',
            'amount': 100,
            'estimated_time': 60,
            'transaction_hash': '0xabcdef123456'
        }

        # Execute request
        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345',
                'X-AI-Assistant': 'Trading Sage'
            },
            json={
                'swap_details': {
                    'from_token': 'XAI',
                    'to_token': 'BTC',
                    'amount': 100,
                    'slippage_tolerance': 0.5
                }
            }
        )

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['swap_id'] == 'swap_abc123'
        assert data['status'] == 'pending'
        assert 'transaction_hash' in data

        # Verify mock calls
        node.personal_ai.execute_atomic_swap_with_ai.assert_called_once()
        call_kwargs = node.personal_ai.execute_atomic_swap_with_ai.call_args[1]
        assert call_kwargs['user_address'] == 'XAI_valid_address_12345'
        assert call_kwargs['ai_provider'] == 'anthropic'
        assert call_kwargs['ai_model'] == 'claude-opus-4'
        assert call_kwargs['assistant_name'] == 'Trading Sage'

    def test_atomic_swap_invalid_address(self, setup):
        """Test atomic swap with invalid user address."""
        from xai.core.security_validation import ValidationError

        client, node = setup

        # Setup validator to reject address
        node.validator.validate_address.side_effect = ValidationError("Invalid address format")

        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'INVALID_ADDRESS',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_ADDRESS'
        assert 'Invalid address format' in data['message']

    def test_atomic_swap_ai_disabled(self, setup):
        """Test atomic swap when Personal AI is disabled."""
        client, node = setup

        # Disable Personal AI
        node.personal_ai = None
        node.validator.validate_address.return_value = None

        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'PERSONAL_AI_DISABLED'

    def test_atomic_swap_ai_provider_failure(self, setup):
        """Test atomic swap when AI provider fails."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': False,
            'error': 'AI_PROVIDER_ERROR',
            'message': 'Claude API rate limit exceeded'
        }

        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={'swap_details': {'from_token': 'XAI', 'to_token': 'BTC', 'amount': 100}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'AI_PROVIDER_ERROR'


class TestSmartContractIntegration:
    """Integration tests for smart contract endpoints."""

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

        return client, node

    def test_smart_contract_create_and_deploy_workflow(self, setup):
        """Test complete workflow: create contract then deploy it."""
        client, node = setup

        # Setup mocks
        node.validator.validate_address.return_value = None

        # Step 1: Create contract
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'pragma solidity ^0.8.0;\ncontract Token { }',
            'contract_id': 'contract_xyz789',
            'estimated_gas': 500000
        }

        create_response = client.post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'openai',
                'X-AI-Model': 'gpt-4',
                'X-User-API-Key': 'sk-openai-key-12345'
            },
            json={
                'contract_description': 'Create an ERC20 token with 1M supply',
                'contract_type': 'ERC20'
            }
        )

        assert create_response.status_code == 200
        create_data = json.loads(create_response.data)
        assert create_data['success'] is True
        contract_code = create_data['contract_code']
        assert 'pragma solidity' in contract_code

        # Step 2: Deploy the created contract
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0x1234567890abcdef1234567890abcdef12345678',
            'transaction_hash': '0xdeployment_hash_123',
            'deployment_cost': 0.05
        }

        deploy_response = client.post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'openai',
                'X-AI-Model': 'gpt-4',
                'X-User-API-Key': 'sk-openai-key-12345'
            },
            json={
                'contract_code': contract_code,
                'constructor_params': {'name': 'MyToken', 'symbol': 'MTK', 'supply': 1000000},
                'testnet': True,
                'signature': 'valid_signature_abc123'
            }
        )

        assert deploy_response.status_code == 200
        deploy_data = json.loads(deploy_response.data)
        assert deploy_data['success'] is True
        assert 'contract_address' in deploy_data
        assert deploy_data['contract_address'].startswith('0x')

    def test_contract_creation_validation(self, setup):
        """Test contract creation with various validation scenarios."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'contract TestContract { }'
        }

        # Test with minimal data
        response = client.post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={}
        )

        assert response.status_code == 200

        # Verify empty description was handled
        call_kwargs = node.personal_ai.create_smart_contract_with_ai.call_args[1]
        assert call_kwargs['contract_description'] == ''

    def test_contract_deployment_mainnet_vs_testnet(self, setup):
        """Test contract deployment on mainnet vs testnet."""
        client, node = setup

        node.validator.validate_address.return_value = None

        # Test testnet deployment
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0xtestnet_address',
            'network': 'testnet'
        }

        testnet_response = client.post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'contract_code': 'pragma solidity ^0.8.0; contract Test {}',
                'testnet': True
            }
        )

        assert testnet_response.status_code == 200
        testnet_data = json.loads(testnet_response.data)
        assert testnet_data['success'] is True

        # Test mainnet deployment
        node.personal_ai.deploy_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_address': '0xmainnet_address',
            'network': 'mainnet'
        }

        mainnet_response = client.post(
            '/personal-ai/smart-contract/deploy',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'contract_code': 'pragma solidity ^0.8.0; contract Test {}',
                'testnet': False
            }
        )

        assert mainnet_response.status_code == 200
        mainnet_data = json.loads(mainnet_response.data)
        assert mainnet_data['success'] is True


class TestTransactionOptimizationIntegration:
    """Integration tests for transaction optimization endpoint."""

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

        return client, node

    def test_transaction_optimization_flow(self, setup):
        """Test transaction optimization flow."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.optimize_transaction_with_ai.return_value = {
            'success': True,
            'original_transaction': {
                'to': 'XAI_recipient_123',
                'amount': 100,
                'fee': 0.002,
                'gas_limit': 50000
            },
            'optimized_transaction': {
                'to': 'XAI_recipient_123',
                'amount': 100,
                'fee': 0.0008,
                'gas_limit': 21000
            },
            'savings': 0.0012,
            'optimization_details': {
                'fee_reduction': '60%',
                'gas_reduction': '58%',
                'estimated_time': 'same'
            }
        }

        response = client.post(
            '/personal-ai/transaction/optimize',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'transaction': {
                    'to': 'XAI_recipient_123',
                    'amount': 100,
                    'fee': 0.002
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'optimized_transaction' in data
        assert data['savings'] > 0

    def test_transaction_optimization_missing_transaction(self, setup):
        """Test transaction optimization without transaction data."""
        client, node = setup

        node.validator.validate_address.return_value = None

        response = client.post(
            '/personal-ai/transaction/optimize',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'transaction required'


class TestBlockchainAnalysisIntegration:
    """Integration tests for blockchain analysis endpoint."""

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

        return client, node

    def test_blockchain_analysis_comprehensive(self, setup):
        """Test comprehensive blockchain analysis."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'query': 'What are the current blockchain trends?',
            'analysis': 'Based on recent blockchain activity, there are several notable trends...',
            'insights': [
                'Transaction volume increased 25% this week',
                'Average block time reduced to 2.1 seconds',
                'Smart contract deployments up 40%'
            ],
            'recommendations': [
                'Consider increasing validator rewards',
                'Monitor gas price trends'
            ],
            'data_sources': ['blockchain_metrics', 'mempool_analysis', 'historical_data']
        }

        response = client.post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345',
                'X-AI-Assistant': 'Data Analyst'
            },
            json={'query': 'What are the current blockchain trends?'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'analysis' in data
        assert 'insights' in data
        assert len(data['insights']) > 0

    def test_blockchain_analysis_missing_query(self, setup):
        """Test blockchain analysis without query."""
        client, node = setup

        node.validator.validate_address.return_value = None

        response = client.post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'query required'


class TestWalletOperationsIntegration:
    """Integration tests for wallet-related endpoints."""

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

        return client, node

    def test_wallet_analysis_complete(self, setup):
        """Test complete wallet analysis."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_analysis_with_ai.return_value = {
            'success': True,
            'analysis_type': 'portfolio_optimization',
            'portfolio_summary': {
                'total_value': 150000,
                'tokens': ['XAI', 'BTC', 'ETH'],
                'diversification_score': 8.5
            },
            'recommendations': [
                'Rebalance portfolio to increase XAI holdings',
                'Consider staking 30% of ETH',
                'Take profits on BTC position'
            ],
            'risk_assessment': {
                'overall_risk': 'moderate',
                'volatility': 'medium',
                'correlation_risk': 'low'
            }
        }

        response = client.post(
            '/personal-ai/wallet/analyze',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={'analysis_type': 'portfolio_optimization'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'portfolio_summary' in data
        assert 'recommendations' in data

    def test_wallet_recovery_with_guardians(self, setup):
        """Test wallet recovery with guardian validation."""
        from xai.core.security_validation import ValidationError

        client, node = setup

        # Setup validator to validate all guardians
        def validate_address_side_effect(address):
            if 'invalid' in address.lower():
                raise ValidationError(f"Invalid guardian address: {address}")
            return None

        node.validator.validate_address.side_effect = validate_address_side_effect
        node.personal_ai.wallet_recovery_advice.return_value = {
            'success': True,
            'recovery_steps': [
                'Contact guardian 1 for signature',
                'Contact guardian 2 for signature',
                'Submit signatures to recovery contract'
            ],
            'estimated_time': '24-48 hours',
            'guardian_count': 2,
            'threshold': 2
        }

        response = client.post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'recovery_details': {
                    'guardians': ['XAI_guardian_1', 'XAI_guardian_2'],
                    'threshold': 2,
                    'recovery_type': 'multi_sig'
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'recovery_steps' in data

    def test_wallet_recovery_invalid_guardian(self, setup):
        """Test wallet recovery with invalid guardian address."""
        from xai.core.security_validation import ValidationError

        client, node = setup

        # First call validates user address (success), second validates guardian (fails)
        node.validator.validate_address.side_effect = [
            None,
            ValidationError("Invalid guardian address format")
        ]

        response = client.post(
            '/personal-ai/wallet/recovery',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'recovery_details': {
                    'guardians': ['INVALID_GUARDIAN_ADDRESS']
                }
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_GUARDIAN_ADDRESS'


class TestNodeSetupIntegration:
    """Integration tests for node setup endpoint."""

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

        return client, node

    def test_node_setup_recommendations(self, setup):
        """Test node setup recommendations."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.validator.validate_string.return_value = None
        node.personal_ai.node_setup_recommendations.return_value = {
            'success': True,
            'setup_request': {
                'preferred_region': 'us-east-1',
                'node_type': 'full',
                'budget': 500
            },
            'recommendations': {
                'hardware': {
                    'cpu': '8 cores minimum',
                    'ram': '32GB',
                    'storage': '2TB SSD',
                    'network': '1Gbps'
                },
                'software': {
                    'os': 'Ubuntu 22.04 LTS',
                    'docker': 'required',
                    'node_version': 'latest'
                },
                'configuration': {
                    'max_peers': 50,
                    'enable_rpc': True,
                    'enable_mining': True
                },
                'estimated_cost': {
                    'monthly': 450,
                    'setup': 100
                }
            }
        }

        response = client.post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'setup_request': {
                    'preferred_region': 'us-east-1',
                    'node_type': 'full',
                    'budget': 500
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'recommendations' in data

    def test_node_setup_invalid_region(self, setup):
        """Test node setup with invalid region."""
        from xai.core.security_validation import ValidationError

        client, node = setup

        node.validator.validate_address.return_value = None
        node.validator.validate_string.side_effect = ValidationError("Region name exceeds maximum length")

        response = client.post(
            '/personal-ai/node/setup',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'setup_request': {
                    'preferred_region': 'x' * 200  # Too long
                }
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_REGION'


class TestLiquidityPoolIntegration:
    """Integration tests for liquidity pool alert endpoint."""

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

        return client, node

    def test_liquidity_alert_response(self, setup):
        """Test liquidity pool alert response."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.validator.validate_string.return_value = None
        node.personal_ai.liquidity_alert_response.return_value = {
            'success': True,
            'pool_name': 'XAI-ETH',
            'alert_type': 'low_liquidity',
            'current_liquidity': 50000,
            'threshold': 100000,
            'alert_response': 'Liquidity is below threshold. Immediate action recommended.',
            'recommended_actions': [
                'Add 50,000 in liquidity to restore balance',
                'Notify LP providers',
                'Adjust incentives to attract more liquidity'
            ],
            'estimated_impact': {
                'price_impact': '5%',
                'slippage_increase': '2x'
            }
        }

        response = client.post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={
                'pool_name': 'XAI-ETH',
                'alert_details': {
                    'type': 'low_liquidity',
                    'current_value': 50000,
                    'threshold': 100000
                }
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'alert_response' in data
        assert 'recommended_actions' in data

    def test_liquidity_alert_missing_pool_name(self, setup):
        """Test liquidity alert without pool name."""
        client, node = setup

        node.validator.validate_address.return_value = None

        response = client.post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
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

        client, node = setup

        node.validator.validate_address.return_value = None
        node.validator.validate_string.side_effect = ValidationError("Pool name exceeds maximum length")

        response = client.post(
            '/personal-ai/liquidity/alert',
            headers={
                'X-User-Address': 'XAI_valid_address_12345',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-ant-api-key-12345'
            },
            json={'pool_name': 'x' * 200}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_POOL_NAME'


class TestPersonalAIAssistantsIntegration:
    """Integration tests for Personal AI assistants endpoint."""

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

        return client, node

    def test_list_assistants_success(self, setup):
        """Test listing available AI assistants."""
        client, node = setup

        node.personal_ai.list_micro_assistants.return_value = [
            {
                'name': 'Trading Sage',
                'description': 'Expert in trading and swaps',
                'skills': ['atomic_swaps', 'liquidity_management', 'trading_advice'],
                'usage_count': 150,
                'success_rate': 0.95
            },
            {
                'name': 'Safety Overseer',
                'description': 'Security and compliance expert',
                'skills': ['security_audits', 'compliance_checks', 'risk_assessment'],
                'usage_count': 89,
                'success_rate': 0.98
            },
            {
                'name': 'Data Analyst',
                'description': 'Blockchain analytics specialist',
                'skills': ['blockchain_analysis', 'trend_detection', 'reporting'],
                'usage_count': 200,
                'success_rate': 0.92
            }
        ]

        response = client.get('/personal-ai/assistants')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['assistants']) == 3
        assert data['assistants'][0]['name'] == 'Trading Sage'
        assert data['assistants'][1]['name'] == 'Safety Overseer'

    def test_list_assistants_disabled(self, setup):
        """Test listing assistants when Personal AI is disabled."""
        client, node = setup

        node.personal_ai = None

        response = client.get('/personal-ai/assistants')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'PERSONAL_AI_DISABLED'


class TestQuestioningSystemIntegration:
    """Integration tests for AI questioning system endpoints."""

    @pytest.fixture
    def setup(self):
        """Setup test environment."""
        from xai.core.api_ai import AIAPIHandler

        node = Mock()
        node.validator = Mock()
        app = Flask(__name__)
        app.config['TESTING'] = True

        handler = AIAPIHandler(node, app)
        client = app.test_client()

        return client, node

    def test_question_submission_and_answer_workflow(self, setup):
        """Test complete workflow: submit question then submit answer."""
        client, node = setup

        # Step 1: Submit question
        question_response = client.post(
            '/questioning/submit',
            json={
                'question_text': 'Should we increase the block size from 2MB to 4MB?',
                'ai_id': 'ai_model_12345',
                'priority': 'high',
                'category': 'protocol_change'
            }
        )

        assert question_response.status_code == 200
        question_data = json.loads(question_response.data)
        assert question_data['success'] is True
        assert 'question_id' in question_data
        assert question_data['status'] == 'open_for_voting'

        question_id = question_data['question_id']

        # Step 2: Submit answer
        answer_response = client.post(
            '/questioning/answer',
            json={
                'question_id': question_id,
                'answer_text': 'Yes, we should increase to 4MB',
                'operator_address': 'XAI_operator_address_123',
                'justification': 'Current blocks are 80% full on average'
            }
        )

        assert answer_response.status_code == 200
        answer_data = json.loads(answer_response.data)
        assert answer_data['success'] is True
        assert answer_data['question_id'] == question_id

    def test_question_id_generation_uniqueness(self, setup):
        """Test that question IDs are unique."""
        client, node = setup

        question_ids = set()

        for i in range(5):
            response = client.post(
                '/questioning/submit',
                json={'question_text': f'Question number {i}'}
            )
            data = json.loads(response.data)
            question_ids.add(data['question_id'])

        # All IDs should be unique
        assert len(question_ids) == 5

    def test_get_pending_questions(self, setup):
        """Test getting pending questions."""
        client, node = setup

        response = client.get('/questioning/pending')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'count' in data
        assert 'questions' in data
        assert isinstance(data['questions'], list)


class TestAuthenticationAndHeaders:
    """Integration tests for authentication and header validation."""

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

        return client, node

    def test_missing_required_headers(self, setup):
        """Test requests with missing required headers."""
        client, node = setup

        # Missing all headers
        response = client.post(
            '/personal-ai/atomic-swap',
            json={'swap_details': {}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'MISSING_HEADERS'

    def test_partial_headers(self, setup):
        """Test requests with partial headers."""
        client, node = setup

        # Missing API key
        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4'
            },
            json={'swap_details': {}}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'X-User-API-Key' in data['message']

    def test_default_header_values(self, setup):
        """Test default values for optional headers."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.return_value = {
            'success': True
        }

        # Only provide required headers, let others default
        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-User-API-Key': 'sk-test-key'
            },
            json={'swap_details': {}}
        )

        assert response.status_code == 200

        # Verify defaults were used
        call_kwargs = node.personal_ai.execute_atomic_swap_with_ai.call_args[1]
        assert call_kwargs['ai_provider'] == 'anthropic'
        assert call_kwargs['ai_model'] == 'claude-opus-4'

    def test_different_ai_providers(self, setup):
        """Test requests with different AI providers."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'analysis': 'Test analysis'
        }

        providers = ['anthropic', 'openai', 'google', 'custom']

        for provider in providers:
            response = client.post(
                '/personal-ai/analyze',
                headers={
                    'X-User-Address': 'XAI_address_123',
                    'X-AI-Provider': provider,
                    'X-AI-Model': f'{provider}-model',
                    'X-User-API-Key': f'sk-{provider}-key'
                },
                json={'query': f'Test with {provider}'}
            )

            assert response.status_code == 200
            call_kwargs = node.personal_ai.analyze_blockchain_with_ai.call_args[1]
            assert call_kwargs['ai_provider'] == provider


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

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

        return client, node

    def test_malformed_json(self, setup):
        """Test handling of malformed JSON."""
        client, node = setup

        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key',
                'Content-Type': 'application/json'
            },
            data='{"invalid json'
        )

        # Should handle gracefully
        assert response.status_code in [400, 500]

    def test_empty_request_body(self, setup):
        """Test handling of empty request body."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.wallet_analysis_with_ai.return_value = {
            'success': True,
            'analysis': 'Default analysis'
        }

        response = client.post(
            '/personal-ai/wallet/analyze',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key',
                'Content-Type': 'application/json'
            },
            data=''
        )

        # Should handle empty body gracefully
        assert response.status_code in [200, 400]

    def test_exception_in_ai_operation(self, setup):
        """Test handling of exceptions in AI operations."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.execute_atomic_swap_with_ai.side_effect = Exception("AI service unavailable")

        response = client.post(
            '/personal-ai/atomic-swap',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key'
            },
            json={'swap_details': {}}
        )

        # Should handle exception gracefully
        assert response.status_code in [400, 500]


class TestEdgeCasesIntegration:
    """Integration tests for edge cases."""

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

        return client, node

    def test_very_long_query(self, setup):
        """Test handling of very long query strings."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'analysis': 'Analysis complete'
        }

        long_query = 'What are the trends? ' * 500  # Very long query

        response = client.post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key'
            },
            json={'query': long_query}
        )

        # Should handle long queries
        assert response.status_code in [200, 400]

    def test_null_values_in_payload(self, setup):
        """Test handling of null values in request payload."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.create_smart_contract_with_ai.return_value = {
            'success': True,
            'contract_code': 'contract code'
        }

        response = client.post(
            '/personal-ai/smart-contract/create',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key'
            },
            json={
                'contract_description': None,
                'contract_type': None
            }
        )

        # Should handle null values gracefully
        assert response.status_code == 200

    def test_unicode_in_requests(self, setup):
        """Test handling of Unicode characters in requests."""
        client, node = setup

        node.validator.validate_address.return_value = None
        node.personal_ai.analyze_blockchain_with_ai.return_value = {
            'success': True,
            'analysis': 'Analysis with unicode: 你好世界'
        }

        response = client.post(
            '/personal-ai/analyze',
            headers={
                'X-User-Address': 'XAI_address_123',
                'X-AI-Provider': 'anthropic',
                'X-AI-Model': 'claude-opus-4',
                'X-User-API-Key': 'sk-test-key'
            },
            json={'query': 'What are the trends? 区块链分析 🚀'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
