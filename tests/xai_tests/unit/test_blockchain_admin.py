import time
from pathlib import Path

from xai.core.blockchain import Blockchain
from xai.core.blockchain_components.block import Block
from xai.core.chain.blockchain_storage import BlockchainStorage


def _mine_coinbase_block(blockchain: Blockchain, recipient: str) -> Block:
    """Helper to append a mined block using the real mining pipeline."""
    block = blockchain.mine_pending_transactions(miner_address=recipient)
    assert block is not None
    return block


def test_blockchain_storage_reset_erases_state(tmp_path):
    storage = BlockchainStorage(data_dir=str(tmp_path))
    blocks_file = Path(storage.blocks_dir) / "blocks_0.json"
    blocks_file.write_text("{}", encoding="utf-8")
    utxo_file = Path(storage.utxo_file)
    utxo_file.write_text("{}", encoding="utf-8")
    checkpoints_dir = Path(storage.data_dir) / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)

    storage.reset_storage()

    assert storage.block_index is not None
    assert not blocks_file.exists()
    assert not utxo_file.exists()
    assert (Path(storage.blocks_dir)).is_dir()
    assert checkpoints_dir.is_dir()


def test_reset_chain_state_rebuilds_genesis(tmp_path):
    blockchain = Blockchain(data_dir=str(tmp_path), checkpoint_interval=1)
    _mine_coinbase_block(blockchain, "XAI000000000000000000000000000000000001")
    assert blockchain.chain[-1].index == 1

    summary = blockchain.reset_chain_state()

    assert summary["new_height"] == 0
    assert len(blockchain.chain) == 1
    assert blockchain.pending_transactions == []
    assert Path(blockchain.data_dir, "blocks").exists()


def test_restore_checkpoint_rewinds_chain(tmp_path):
    blockchain = Blockchain(data_dir=str(tmp_path), checkpoint_interval=1)
    _mine_coinbase_block(blockchain, "XAI000000000000000000000000000000000010")
    _mine_coinbase_block(blockchain, "XAI000000000000000000000000000000000020")
    assert blockchain.chain[-1].index == 2
    assert blockchain.checkpoint_manager.list_checkpoints()

    summary = blockchain.restore_checkpoint(1)

    assert summary["new_height"] == 1
    assert blockchain.chain[-1].index == 1
    assert blockchain.pending_transactions == []
