from types import SimpleNamespace

import pytest

from xai.core.api_auth import APIAuthManager, APIKeyStore, JWTAuthManager


def make_request(headers=None, args=None):
    return SimpleNamespace(headers=headers or {}, args=args or {})


def test_api_auth_enforces_required_keys_and_admin_scope(tmp_path):
    store_path = tmp_path / "keys.json"
    store = APIKeyStore(str(store_path))
    manager = APIAuthManager(required=True, allowed_keys=["manual-user"], admin_keys=["manual-admin"], store=store)

    user_plain, user_id = store.issue_key(label="user", scope="user")
    admin_plain, admin_id = store.issue_key(label="admin", scope="admin")
    manager.refresh_from_store()

    ok, _ = manager.authorize(make_request(headers={"X-API-Key": "manual-user"}))
    assert ok is True

    ok, _ = manager.authorize(make_request(headers={"X-API-Key": user_plain}))
    assert ok is True

    ok, _ = manager.authorize(make_request(headers={}))
    assert ok is False

    ok, _ = manager.authorize_admin(make_request(headers={"X-Admin-Token": "manual-admin"}))
    assert ok is True

    ok, reason = manager.authorize_admin(make_request(headers={"X-Admin-Token": admin_plain}))
    assert ok is True and reason is None

    ok, _ = manager.authorize_admin(make_request(headers={"X-Admin-Token": user_plain}))
    assert ok is False


def test_jwt_auth_scope_and_revocation():
    pytest.importorskip("jwt")
    manager = JWTAuthManager(secret_key="super-secret", token_expiry_hours=1, refresh_expiry_days=1, algorithm="HS256")
    access, refresh = manager.generate_token("user-123", scope="admin")

    ok, payload, err = manager.authorize_request(make_request(headers={"Authorization": f"Bearer {access}"}), required_scope="admin")
    assert ok is True and payload["user_id"] == "user-123"

    ok, _, err = manager.authorize_request(make_request(headers={"Authorization": f"Bearer {access}"}), required_scope="user")
    assert ok is False and "Insufficient permissions" in (err or "")

    refreshed_ok, new_access, err = manager.refresh_access_token(refresh)
    assert refreshed_ok is True
    assert new_access is not None

    manager.revoke_token(access)
    ok, _, err = manager.authorize_request(make_request(headers={"Authorization": f"Bearer {access}"}))
    assert ok is False
    assert "revoked" in (err or "").lower()
