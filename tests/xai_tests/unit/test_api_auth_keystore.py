import json
import time
from pathlib import Path

import pytest

from xai.core.api_auth import APIKeyStore


def _load_jsonl(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_issue_and_list_keys_with_ttl(tmp_path, monkeypatch):
    store_path = tmp_path / "keys.json"
    store = APIKeyStore(str(store_path), default_ttl_days=1, max_ttl_days=1)

    # Fast deterministic time
    fixed_now = time.time()
    monkeypatch.setattr("time.time", lambda: fixed_now)

    plaintext, key_id = store.issue_key(label="test", scope="admin", ttl_seconds=2)
    assert plaintext
    assert key_id in store._keys

    listed = store.list_keys()
    assert key_id in listed
    meta = listed[key_id]
    assert meta["label"] == "test"
    assert meta["scope"] == "admin"
    assert meta["expired"] is False
    assert pytest.approx(meta["expires_at"], rel=1e-3) == fixed_now + 2


def test_issue_permanent_rejected_when_disabled(tmp_path):
    store = APIKeyStore(str(tmp_path / "keys.json"), allow_permanent=False)
    with pytest.raises(ValueError):
        store.issue_key(permanent=True)


def test_rotate_replaces_key_and_audits(tmp_path):
    store_path = tmp_path / "keys.json"
    store = APIKeyStore(str(store_path), default_ttl_days=1, max_ttl_days=1)

    old_plain, old_id = store.issue_key(label="rotate-me", scope="user", ttl_seconds=5)
    assert old_plain and old_id

    new_plain, new_id = store.rotate_key(old_id, label="rotate-me", scope="operator", ttl_seconds=10)
    assert new_plain != old_plain
    assert new_id != old_id
    assert new_id in store._keys
    assert old_id not in store._keys

    events = _load_jsonl(Path(store.audit_log_path))
    actions = [e["action"] for e in events]
    assert "issue" in actions
    assert "rotate" in actions


def test_hydrate_metadata_adds_missing_fields(tmp_path):
    path = tmp_path / "keys.json"
    # Pre-seed malformed data missing expires_at/permanent
    path.write_text(json.dumps({"dead": {"label": "x", "scope": "user", "created": time.time() - 5}}))
    store = APIKeyStore(str(path), default_ttl_days=1, max_ttl_days=1, allow_permanent=False)
    hydrated = store.list_keys()["dead"]
    assert hydrated["expires_at"] is not None
    assert hydrated["permanent"] is False


def test_is_expired_handles_invalid_metadata():
    assert APIKeyStore._is_expired({"expires_at": "abc"}) is True
    now = time.time()
    assert APIKeyStore._is_expired({"expires_at": now - 1}, now=now) is True
    assert APIKeyStore._is_expired({"expires_at": now + 10}, now=now) is False
