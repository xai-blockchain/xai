import os
import traceback
from src.xai.core.api_extensions import extend_node_api
from src.xai.core.node import BlockchainNode
from src.xai.ai.ai_assistant.personal_ai_assistant import PersonalAIAssistant

# Load API key from environment variable
test_api_key = os.environ.get("ANTHROPIC_API_KEY")
if not test_api_key:
    raise ValueError(
        "ANTHROPIC_API_KEY environment variable required. "
        "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
    )

node = BlockchainNode(miner_address="XAI_TEST_MINER")
node.personal_ai = PersonalAIAssistant(node.blockchain, node.safety_controls)
extend_node_api(node)
client = node.app.test_client()
headers = {
    "X-User-Address": "XAI1smoke",
    "X-AI-Provider": "anthropic",
    "X-AI-Model": "claude-opus-4",
    "X-User-API-Key": test_api_key,
}
payload = {
    "swap_details": {
        "from_coin": "XAI",
        "to_coin": "ADA",
        "amount": 0.5,
        "recipient_address": "XAI1recipient",
    }
}
res = client.post("/personal-ai/atomic-swap", json=payload, headers=headers)
print("atomic swap:", res.status_code, res.get_json()["success"])
payload = {"contract_description": "Test escrow", "contract_type": "escrow"}
res = client.post("/personal-ai/smart-contract/create", json=payload, headers=headers)
print("contract create:", res.status_code, res.get_json()["success"])
