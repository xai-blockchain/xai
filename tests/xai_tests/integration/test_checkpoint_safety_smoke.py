import json
import hashlib
from types import SimpleNamespace

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager


def _payload(snapshot, height=5, block_hash="abc"):
    state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    return {"height": height, "block_hash": block_hash, "state_hash": state_hash, "data": snapshot}


def test_checkpoint_rejects_low_work_even_with_quorum(tmp_path):
    snapshot = {"utxo_snapshot": {"k": "v"}}
    payload = _payload(snapshot)
    payload["work"] = 1
    meta = {"height": payload["height"], "block_hash": payload["block_hash"], "url": str(tmp_path / "cp.json")}
    (tmp_path / "cp.json").write_text(json.dumps(payload), encoding="utf-8")
    bc = SimpleNamespace(
        utxo_manager=SimpleNamespace(restore=lambda snap: None),
        checkpoint_manager=SimpleNamespace(latest_checkpoint_height=None, latest_checkpoint_work=10),
        config=SimpleNamespace(CHECKPOINT_QUORUM=1, CHECKPOINT_MIN_PEERS=1, TRUSTED_CHECKPOINT_PUBKEYS=[]),
    )
    mgr = CheckpointSyncManager(blockchain=bc, p2p_manager=SimpleNamespace(_get_checkpoint_metadata=lambda: meta))
    assert mgr.fetch_validate_apply() is False


def test_checkpoint_rejects_bad_signature(tmp_path):
    snapshot = {"utxo_snapshot": {"k": "v"}}
    state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {"height": 5, "block_hash": "abc", "state_hash": state_hash, "data": snapshot, "signature": "dead", "pubkey": "beef"}
    meta = {"height": payload["height"], "block_hash": payload["block_hash"], "url": str(tmp_path / "cp.json")}
    (tmp_path / "cp.json").write_text(json.dumps(payload), encoding="utf-8")
    bc = SimpleNamespace(
        utxo_manager=SimpleNamespace(restore=lambda snap: None),
        checkpoint_manager=SimpleNamespace(latest_checkpoint_height=None, latest_checkpoint_work=None),
        config=SimpleNamespace(CHECKPOINT_QUORUM=1, CHECKPOINT_MIN_PEERS=1, TRUSTED_CHECKPOINT_PUBKEYS=["cafebabe"]),
    )
    mgr = CheckpointSyncManager(blockchain=bc, p2p_manager=SimpleNamespace(_get_checkpoint_metadata=lambda: meta))
    assert mgr.fetch_validate_apply() is False
