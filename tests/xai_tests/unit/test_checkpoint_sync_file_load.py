"""
Tests for loading checkpoint payloads from file.
"""

import json
import hashlib

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager


def test_load_payload_from_file(tmp_path):
    data = {"utxo": "root"}
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "height": 5,
        "block_hash": "hash5",
        "state_hash": digest,
        "data": data,
    }
    path = tmp_path / "cp.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = CheckpointSyncManager.load_payload_from_file(str(path))
    assert loaded is not None
    assert loaded.height == 5
    assert loaded.block_hash == "hash5"
    assert loaded.state_hash == digest
    assert loaded.data == {"utxo": "root"}


def test_load_payload_from_file_handles_missing(tmp_path):
    missing = tmp_path / "missing.json"
    assert CheckpointSyncManager.load_payload_from_file(str(missing)) is None


def test_fetch_payload_from_file(tmp_path):
    data = {"utxo": "root"}
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "height": 5,
        "block_hash": "hash5",
        "state_hash": digest,
        "data": data,
    }
    path = tmp_path / "cp.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    mgr = CheckpointSyncManager(blockchain=None)
    loaded = mgr.fetch_payload({"url": str(path)})
    assert loaded is not None
    assert loaded.block_hash == "hash5"


def test_fetch_validate_apply_uses_best_meta(monkeypatch, tmp_path):
    data = {"utxo": "root"}
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "height": 5,
        "block_hash": "hash5",
        "state_hash": digest,
        "data": data,
    }
    path = tmp_path / "cp.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    class DummyBC:
        def __init__(self):
            self.applied = None

        def apply_checkpoint(self, p):
            self.applied = p

    bc = DummyBC()
    mgr = CheckpointSyncManager(blockchain=bc)
    mgr._p2p_checkpoint_metadata = lambda: {"height": 5, "block_hash": "hash5", "url": str(path)}  # noqa: SLF001
    assert mgr.fetch_validate_apply() is True
    assert bc.applied is not None


def test_apply_payload_restores_utxo_snapshot(tmp_path):
    data = {"utxo_snapshot": {"addr": [{"txid": "t", "vout": 0, "amount": 1.0, "script_pubkey": "spk"}]}}
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "height": 5,
        "block_hash": "hash5",
        "state_hash": digest,
        "data": data,
    }
    path = tmp_path / "cp.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    class DummyUTXO:
        def __init__(self):
            self.restored = None

        def restore(self, snapshot):
            self.restored = snapshot

    class DummyBC:
        def __init__(self):
            self.utxo_manager = DummyUTXO()
            self.checkpoint_manager = type(
                "CM",
                (),
                {
                    "latest_checkpoint_height": None,
                    "load_latest_checkpoint": lambda self=None: None,
                    "load_checkpoint": lambda self, h=None: None,
                },
            )()

    bc = DummyBC()
    mgr = CheckpointSyncManager(blockchain=bc)
    mgr._p2p_checkpoint_metadata = lambda: {"height": 5, "block_hash": "hash5", "url": str(path)}  # noqa: SLF001
    assert mgr.fetch_validate_apply() is True
    assert bc.utxo_manager.restored == data["utxo_snapshot"]
    assert bc.checkpoint_manager.latest_checkpoint_height == 5
