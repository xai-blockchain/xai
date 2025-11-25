"""
Custom pytest fixtures for the xai/core test sources.
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest


from xai.core.blockchain_persistence import BlockchainStorage


@pytest.fixture(scope="module")
def storage():
    """Provide temporary blockchain storage for persistence tests."""
    temp_dir = tempfile.mkdtemp(prefix="blockchain_persistence_")
    storage = BlockchainStorage(data_dir=temp_dir)

    blockchain_data = _create_mock_blockchain(5)
    storage.save_to_disk(blockchain_data)

    yield storage

    try:
        storage.close()
    except AttributeError:
        pass

    shutil.rmtree(temp_dir, ignore_errors=True)


def _create_mock_blockchain(num_blocks: int = 5) -> dict:
    """Create mock blockchain data used by the persistence fixture."""
    chain = []

    for i in range(num_blocks):
        block = {
            "index": i,
            "timestamp": time.time(),
            "transactions": [
                {
                    "txid": f"tx_{i}_0",
                    "sender": "COINBASE" if i == 0 else f"sender_{i}",
                    "recipient": f"recipient_{i}",
                    "amount": 12.0,
                    "fee": 0.0 if i == 0 else 0.24,
                    "timestamp": time.time(),
                    "signature": f"sig_{i}",
                    "public_key": f"pubkey_{i}",
                    "tx_type": "normal",
                    "nonce": i,
                }
            ],
            "previous_hash": "0" if i == 0 else f"hash_{i-1}",
            "merkle_root": f"merkle_{i}",
            "nonce": i * 1000,
            "hash": f"hash_{i}",
            "difficulty": 4,
        }
        chain.append(block)

    return {
        "chain": chain,
        "pending_transactions": [],
        "difficulty": 4,
        "stats": {
            "blocks": num_blocks,
            "total_transactions": num_blocks,
            "pending_transactions": 0,
        },
    }
