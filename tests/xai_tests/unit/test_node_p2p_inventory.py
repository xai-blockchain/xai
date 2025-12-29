import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from xai.core.p2p.node_p2p import P2PNetworkManager


class DummyTx:
    def __init__(self, txid: str):
        self.txid = txid

    def to_dict(self):
        return {"txid": self.txid, "amount": 1}


class DummyBlock:
    def __init__(self, block_hash: str):
        self.hash = block_hash

    def to_dict(self):
        return {"hash": self.hash, "height": 1}


class DummyBlockchain:
    def __init__(self):
        self.chain = []
        self.storage = type("S", (), {"data_dir": "data"})

    def get_block_by_hash(self, block_hash):
        return DummyBlock(block_hash)


@pytest.mark.asyncio
async def test_inventory_request_triggers_getdata():
    manager = P2PNetworkManager(DummyBlockchain())
    manager._has_transaction = lambda txid: False  # type: ignore
    manager._has_block = lambda block_hash: False  # type: ignore

    websocket = AsyncMock()
    payload = {"transactions": ["tx123"], "blocks": ["blockABC"]}
    await manager._handle_inventory_announcement(websocket, "peer1", payload)

    websocket.send.assert_awaited()
    sent_raw = websocket.send.await_args.args[0]
    signed = json.loads(sent_raw)
    inner = signed["message"]["payload"]
    assert inner["type"] == "getdata"
    assert inner["payload"]["transactions"] == ["tx123"]
    assert inner["payload"]["blocks"] == ["blockABC"]


@pytest.mark.asyncio
async def test_getdata_sends_known_objects():
    blockchain = DummyBlockchain()
    manager = P2PNetworkManager(blockchain)
    manager.peer_manager.pow_manager.enabled = False
    websocket = AsyncMock()

    tx = DummyTx("tx999")
    manager._find_pending_transaction = lambda txid: tx if txid == "tx999" else None  # type: ignore
    blockchain.get_block_by_hash = lambda h: DummyBlock(h)

    payload = {"transactions": ["tx999"], "blocks": ["block999"]}
    await manager._handle_getdata_request(websocket, "peer1", payload)

    # Should send two signed messages (tx + block)
    assert websocket.send.await_count == 2
    messages = [json.loads(call.args[0]) for call in websocket.send.await_args_list]
    types = [msg["message"]["payload"]["type"] for msg in messages]
    assert "transaction" in types
    assert "block" in types
