"""
Unit tests for JWTAuthManager token generation/validation and blacklist.
"""

import pytest

from xai.core.api_auth import JWTAuthManager


def test_generate_and_validate_token_round_trip(monkeypatch):
    """Access token validates and includes expected claims."""
    mgr = JWTAuthManager(secret_key="secret", token_expiry_hours=1, refresh_expiry_days=1)
    access, refresh = mgr.generate_token("user123", scope="admin")

    ok, claims, err = mgr.validate_token(access)
    assert ok is True
    assert claims["user_id"] == "user123"
    assert claims["scope"] == "admin"
    assert err is None

    ok_refresh, refresh_claims, err_refresh = mgr.validate_token(refresh)
    assert ok_refresh is True
    assert refresh_claims["type"] == "refresh"
    assert err_refresh is None


def test_blacklist_rejects_token():
    """Blacklisted tokens fail validation."""
    mgr = JWTAuthManager(secret_key="secret")
    access, _ = mgr.generate_token("user123")
    ok, claims, err = mgr.validate_token(access)
    assert ok is True

    mgr.blacklist.add(access)
    ok2, _, err2 = mgr.validate_token(access)
    assert ok2 is False
    assert err2 is not None


def test_invalid_signature_and_expiry(monkeypatch):
    """Invalid signature and expired tokens are rejected."""
    mgr = JWTAuthManager(secret_key="secret", token_expiry_hours=0)
    access, _ = mgr.generate_token("user123")

    # Tamper token
    tampered = access + "x"
    ok, _, err = mgr.validate_token(tampered)
    assert ok is False
    assert err is not None

    # Expired: token_expiry_hours=0 sets expiry to now; allow clock skew may validate, so force by editing exp
    import jwt as pyjwt
    decoded = pyjwt.decode(access, "secret", algorithms=["HS256"], options={"verify_exp": False})
    decoded["exp"] = 0
    expired_token = pyjwt.encode(decoded, "secret", algorithm="HS256")
    ok2, _, err2 = mgr.validate_token(expired_token)
    assert ok2 is False
    assert "expired" in (err2 or "").lower()
