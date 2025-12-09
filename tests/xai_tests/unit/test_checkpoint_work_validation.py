from xai.core.checkpoint_sync import CheckpointSyncManager


def test_checkpoint_work_validation_blocks_lower_work():
    cfg = type("cfg", (), {"CHECKPOINT_QUORUM": 1, "TRUSTED_CHECKPOINT_PUBKEYS": []})
    cm = type("cm", (), {"latest_checkpoint_height": 5, "latest_checkpoint_work": 500})
    mgr = CheckpointSyncManager(blockchain=type("bc", (), {"config": cfg})(), p2p_manager=None)
    mgr.checkpoint_manager = cm

    low_work_payload = {"height": 6, "block_hash": "h", "state_hash": "s", "data": {}, "work": 400}
    # Ensure integrity path passes
    assert mgr._validate_work(low_work_payload) is False
    high_work_payload = {"height": 6, "block_hash": "h", "state_hash": "s", "data": {}, "work": 600}
    assert mgr._validate_work(high_work_payload) is True
