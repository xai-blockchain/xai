from types import SimpleNamespace

from xai.core.checkpoint_sync import CheckpointSyncManager


def test_checkpoint_requires_diverse_peers():
    snapshot = {"utxo_snapshot": {}}
    import hashlib, json

    state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {"height": 5, "block_hash": "abc", "state_hash": state_hash, "data": snapshot}

    features = {
        "peerA": {"checkpoint_payload": payload},
        "peerB": {"checkpoint_payload": payload},
    }
    bc = SimpleNamespace(config=SimpleNamespace(CHECKPOINT_QUORUM=2, CHECKPOINT_MIN_PEERS=2, TRUSTED_CHECKPOINT_PUBKEYS=[]))
    mgr = CheckpointSyncManager(blockchain=bc, p2p_manager=SimpleNamespace(peer_features=features, broadcast=lambda msg: None))

    cp = mgr.request_checkpoint_from_peers()
    assert cp is not None

    # Remove diversity
    mgr.min_peer_diversity = 3
    cp2 = mgr.request_checkpoint_from_peers()
    assert cp2 is None
