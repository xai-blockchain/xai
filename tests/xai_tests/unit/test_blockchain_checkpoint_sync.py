import json

from xai.core.blockchain import Blockchain


def test_checkpoint_load_fast_recovery(tmp_path, monkeypatch):
    # Create chain and force checkpoint creation every block
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    bc = Blockchain(data_dir=tmp_path, checkpoint_interval=1, max_checkpoints=5)
    # Mine a couple blocks to create checkpoints
    bc.mine_pending_transactions(miner_address="XAI0000000000000000000000000000000000000000")
    bc.mine_pending_transactions(miner_address="XAI0000000000000000000000000000000000000000")

    # Reload blockchain to trigger checkpoint-based recovery
    bc_reloaded = Blockchain(data_dir=tmp_path, checkpoint_interval=1, max_checkpoints=5)
    assert len(bc_reloaded.chain) >= 2
    assert bc_reloaded.checkpoint_manager.latest_checkpoint_height is not None


def test_checkpoint_protection_prevents_reorg(tmp_path, monkeypatch):
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    bc = Blockchain(data_dir=tmp_path, checkpoint_interval=1, max_checkpoints=5)
    bc.mine_pending_transactions(miner_address="XAI0000000000000000000000000000000000000000")
    bc.mine_pending_transactions(miner_address="XAI0000000000000000000000000000000000000000")

    # Create alternative chain fork before checkpoint height
    alt_chain = bc.chain.copy()
    alt_chain[1].header.nonce += 1
    alt_chain[1].header.hash = alt_chain[1].header.calculate_hash()

    replaced = bc.replace_chain(alt_chain)
    assert replaced is False
