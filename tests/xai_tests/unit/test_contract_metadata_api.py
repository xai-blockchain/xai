"""Tests for contract ABI and event API endpoints."""

import pytest

from xai.core.blockchain import Blockchain
from xai.core.config import Config
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet
from xai.core.wallets.address_checksum import normalize_address


@pytest.fixture
def node_client(tmp_path):
    blockchain = Blockchain(data_dir=str(tmp_path))
    node = BlockchainNode(blockchain=blockchain, miner_address=Wallet().address)
    client = node.app.test_client()
    return node, client


def test_contract_abi_endpoint_returns_payload(node_client):
    node, client = node_client
    address = f"{Config.ADDRESS_PREFIX}{'a' * 40}"
    normalized = normalize_address(address)
    contract_key = address.upper()
    node.blockchain.contracts[contract_key] = {
        "creator": "XAITEST",
        "code": b"",
        "storage": {},
        "gas_limit": 1_000_000,
        "balance": 0,
        "created_at": 0,
    }
    node.blockchain.store_contract_abi(
        address,
        [
            {
                "type": "function",
                "name": "balanceOf",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}],
            }
        ],
        verified=True,
        source="unit-test",
    )

    response = client.get(f"/contracts/{address}/abi")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["contract_address"] == normalized
    assert payload["verified"] is True
    assert payload["abi"][0]["name"] == "balanceOf"


def test_contract_events_endpoint_filters_receipts(node_client):
    node, client = node_client
    address = f"{Config.ADDRESS_PREFIX}{'b' * 40}"
    normalized = normalize_address(address)
    contract_key = address.upper()
    from_address = f"{Config.ADDRESS_PREFIX}{'1' * 40}"
    to_address = f"{Config.ADDRESS_PREFIX}{'2' * 40}"
    node.blockchain.contract_receipts = [
        {
            "txid": "tx123",
            "contract": contract_key,
            "success": True,
            "gas_used": 21000,
            "return_data": "",
            "logs": [
                {
                    "event": "Transfer",
                    "from": from_address,
                    "to": to_address,
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
    address = f"{Config.ADDRESS_PREFIX}{'c' * 40}"
    response = client.get(f"/contracts/{address}/abi")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["code"] == "contract_abi_missing"
