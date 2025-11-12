import traceback
from core.api_extensions import extend_node_api
from core.node import BlockchainNode
from ai_assistant.personal_ai_assistant import PersonalAIAssistant
try:
    node = BlockchainNode(miner_address='XAI_TEST_MINER')
    node.personal_ai = PersonalAIAssistant(node.blockchain, node.safety_controls)
    extend_node_api(node)
    client = node.app.test_client()
    headers = {
        'X-User-Address': 'XAI1smoke',
        'X-AI-Provider': 'anthropic',
        'X-AI-Model': 'claude-opus-4',
        'X-User-API-Key': 'test-key'
    }
    payload = {'swap_details': {'from_coin': 'XAI', 'to_coin': 'ADA', 'amount': 0.5, 'recipient_address': 'XAI1recipient'}}
    res = client.post('/personal-ai/atomic-swap', json=payload, headers=headers)
    print('atomic swap:', res.status_code, res.get_json()['success'])
    payload = {'contract_description': 'Test escrow', 'contract_type': 'escrow'}
    res = client.post('/personal-ai/smart-contract/create', json=payload, headers=headers)
    print('contract create:', res.status_code, res.get_json()['success'])
except Exception:
    traceback.print_exc()
    raise

