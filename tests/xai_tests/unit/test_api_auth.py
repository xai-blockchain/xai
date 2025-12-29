"""
Unit tests for API authentication manager and key store behaviors.
"""

import json
import time
from pathlib import Path

from flask import Flask

from xai.core.api.api_auth import APIAuthManager, APIKeyStore


def test_api_key_store_issue_rotate_revoke(tmp_path):
    """Key store issues, rotates, revokes keys and logs audit events."""
    store_path = tmp_path / "keys.json"
    store = APIKeyStore(str(store_path))

    plaintext, key_id = store.issue_key(label="test", scope="user")
    assert key_id in store.list_keys()
    metadata = store.list_keys()[key_id]
    assert metadata.get("expires_at") is not None
    assert metadata.get("permanent") is False

    new_plain, new_id = store.rotate_key(key_id, label="test", scope="admin")
    assert new_id in store.list_keys()
    assert key_id not in store.list_keys()
    rotated_meta = store.list_keys()[new_id]
    assert rotated_meta.get("scope") == "admin"
    assert rotated_meta.get("expires_at") is not None

    assert store.revoke_key(new_id) is True
    assert new_id not in store.list_keys()

    events = store.get_events()
    assert any(e["action"] == "issue" for e in events)
    assert any(e["action"] == "rotate" for e in events)
    assert any(e["action"] == "revoke" for e in events)


def test_api_auth_manager_extraction_and_validation(tmp_path):
    """APIAuthManager extracts keys from headers and validates admin vs user hashes."""
    app = Flask(__name__)
    store = APIKeyStore(str(tmp_path / "keys.json"))
    plaintext, key_id = store.issue_key(scope="admin")

    mgr = APIAuthManager(required=True, allowed_keys=["manual"], admin_keys=["admin"], store=store)

    with app.test_request_context("/", headers={"Authorization": f"Bearer {plaintext}", "X-Admin-Token": plaintext}):
        from flask import request as flask_request
        req = flask_request
        assert mgr._extract_key(req) == plaintext
        ok, err = mgr.authorize(req)
        assert ok is True and err is None
        ok_admin, _ = mgr.authorize_admin(req)
        assert ok_admin is True

    with app.test_request_context("/", headers={"X-API-Key": "manual"}):
        from flask import request as flask_request
        req2 = flask_request
        assert mgr._extract_key(req2) == "manual"
        ok_user, err_user = mgr.authorize(req2)
        assert ok_user is True and err_user is None


def test_api_auth_rejects_expired_store_keys(tmp_path):
    """Expired API keys are rejected with a clear error message."""
    app = Flask(__name__)
    store = APIKeyStore(str(tmp_path / "keys.json"))
    plaintext, key_id = store.issue_key(scope="user", ttl_seconds=60)

    # Force expiration
    store._keys[key_id]["expires_at"] = time.time() - 1  # type: ignore[attr-defined]
    store._persist()

    mgr = APIAuthManager(required=True, store=store)
    mgr.refresh_from_store()

    with app.test_request_context("/", headers={"X-API-Key": plaintext}):
        from flask import request as flask_request
        ok, reason = mgr.authorize(flask_request)
        assert ok is False
        assert reason == "API key expired"
