import json

import pytest

from core import api_extensions
from core.api_extensions import extend_node_api
from core.node import BlockchainNode
from ai_assistant.personal_ai_assistant import PersonalAIAssistant

VALID_TEST_ADDRESS = 'XAI1integration' + '0' * 25
VALID_RECIPIENT_ADDRESS = 'XAI1recipient' + '0' * 27


@pytest.fixture
def app_client(monkeypatch):
    node = BlockchainNode(miner_address='XAI_TEST_MINER')
    node.personal_ai = PersonalAIAssistant(node.blockchain, node.safety_controls)
    monkeypatch.setattr(api_extensions.APIExtensions, 'setup_wallet_trades_routes', lambda self: None)
    extend_node_api(node)
    return node.app.test_client()


def _headers():
    return {
        'X-User-Address': VALID_TEST_ADDRESS,
        'X-AI-Provider': 'anthropic',
        'X-AI-Model': 'claude-sonnet-4',
        'X-User-API-Key': 'test-personal-key',
        'X-AI-Assistant': 'Guiding Mentor',
    }


def test_personal_ai_atomic_swap(app_client):
    payload = {
        'swap_details': {
            'from_coin': 'XAI',
            'to_coin': 'ADA',
            'amount': 1.25,
            'recipient_address': VALID_RECIPIENT_ADDRESS
        }
    }
    response = app_client.post('/personal-ai/atomic-swap', json=payload, headers=_headers())
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']
    assert 'swap_transaction' in data


def test_personal_ai_missing_headers(app_client):
    response = app_client.post('/personal-ai/atomic-swap', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'MISSING_HEADERS'


def test_personal_ai_contract_create(app_client):
    payload = {
        'contract_description': 'Escrow for 10 XAI between Alice and Bob',
        'contract_type': 'escrow'
    }
    response = app_client.post('/personal-ai/smart-contract/create', json=payload, headers=_headers())
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']
    assert 'contract_code' in data
