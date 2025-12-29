from types import SimpleNamespace
import hashlib
import json

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager


def test_fetch_validate_apply_requests_peers_when_no_metadata(monkeypatch):
    snapshot = {"utxo_snapshot": {"k": "v"}}
    state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {"height": 2, "block_hash": "abc", "state_hash": state_hash, "data": snapshot}

    peer_features = {"peer": {"checkpoint_payload": payload}}
    p2p = SimpleNamespace(peer_features=peer_features, broadcast=lambda msg: None)
    bc = SimpleNamespace(config=SimpleNamespace(CHECKPOINT_QUORUM=1, CHECKPOINT_MIN_PEERS=1, TRUSTED_CHECKPOINT_PUBKEYS=[]))
    mgr = CheckpointSyncManager(blockchain=bc, p2p_manager=p2p)
    # override apply_payload to observe call
    called = {}

    def _apply(cp, applier):
        called["applied"] = cp
        return True

    mgr.apply_payload = _apply  # type: ignore

    assert mgr.fetch_validate_apply() is True
    assert called["applied"].height == 2
