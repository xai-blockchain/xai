"""
Coverage for password hashing/verification fallbacks in SecurityMiddleware.
"""

import pytest
from flask import Flask

from xai.core.security.security_middleware import SecurityMiddleware


def _middleware(monkeypatch, bcrypt_available: bool) -> SecurityMiddleware:
    monkeypatch.setattr("xai.core.security_middleware.BCRYPT_AVAILABLE", bcrypt_available)
    app = Flask("pw")
    app.config["SECRET_KEY"] = "secret"
    return SecurityMiddleware(app)


def test_register_and_verify_with_bcrypt(monkeypatch):
    middleware = _middleware(monkeypatch, bcrypt_available=True)
    assert middleware.register_user("alice", "supersecret") is True
    assert middleware._verify_credentials("alice", "supersecret") is True
    assert middleware._verify_credentials("alice", "wrong") is False


def test_register_and_verify_with_pbkdf2(monkeypatch):
    middleware = _middleware(monkeypatch, bcrypt_available=False)
    assert middleware.register_user("bob", "anothersecret") is True
    assert middleware._verify_credentials("bob", "anothersecret") is True
    assert middleware._verify_credentials("bob", "wrong") is False


def test_register_rejects_short_passwords(monkeypatch):
    middleware = _middleware(monkeypatch, bcrypt_available=False)
    with pytest.raises(ValueError):
        middleware.register_user("eve", "short")
