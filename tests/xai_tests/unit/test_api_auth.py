"""
Unit tests for API authentication manager and key store behaviors.
"""

import json
from pathlib import Path

from flask import Flask

from xai.core.api_auth import APIAuthManager, APIKeyStore


def test_api_key_store_issue_rotate_revoke(tmp_path):
    """Key store issues, rotates, revokes keys and logs audit events."""
    store_path = tmp_path / "keys.json"
    store = APIKeyStore(str(store_path))

    plaintext, key_id = store.issue_key(label="test", scope="user")
    assert key_id in store.list_keys()

    new_plain, new_id = store.rotate_key(key_id, label="test", scope="admin")
    assert new_id in store.list_keys()
    assert key_id not in store.list_keys()

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
