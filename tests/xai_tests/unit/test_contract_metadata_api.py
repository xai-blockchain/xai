"""Tests for contract ABI and event API endpoints."""

import pytest

from xai.core.node import BlockchainNode


@pytest.fixture
def node_client():
    node = BlockchainNode(miner_address="XAI_TEST_MINER")
    client = node.app.test_client()
    return node, client


def test_contract_abi_endpoint_returns_payload(node_client):
    node, client = node_client
    address = "XAI" + "A" * 40
    normalized = address.upper()
    node.blockchain.contracts[normalized] = {
        "creator": "XAITEST",
        "code": b"",
        "storage": {},
        "gas_limit": 1_000_000,
        "balance": 0,
        "created_at": 0,
        "abi": [
            {
                "type": "function",
                "name": "balanceOf",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}],
            }
        ],
        "abi_verified": True,
        "abi_source": "unit-test",
        "abi_updated_at": 123.0,
    }

    response = client.get(f"/contracts/{address}/abi")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["contract_address"] == normalized
    assert payload["verified"] is True
    assert payload["abi"][0]["name"] == "balanceOf"


def test_contract_events_endpoint_filters_receipts(node_client):
    node, client = node_client
    address = "XAI" + "B" * 40
    normalized = address.upper()
    node.blockchain.contract_receipts = [
        {
            "txid": "tx123",
            "contract": normalized,
            "success": True,
            "gas_used": 21000,
            "return_data": "",
            "logs": [
                {
                    "event": "Transfer",
                    "from": "XAI" + "1" * 40,
                    "to": "XAI" + "2" * 40,
                    "value": 15,
                }
            ],
            "block_index": 12,
            "block_hash": "0xabc",
            "timestamp": 1700000000,
        }
    ]

    response = client.get(f"/contracts/{address}/events?limit=5&offset=0")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["total"] == 1
    event = payload["events"][0]
    assert event["event"] == "Transfer"
    assert event["data"]["value"] == 15
    assert event["block_index"] == 12


def test_contract_abi_missing_returns_404(node_client):
    node, client = node_client
    address = "XAI" + "C" * 40
    response = client.get(f"/contracts/{address}/abi")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["code"] == "contract_abi_missing"
