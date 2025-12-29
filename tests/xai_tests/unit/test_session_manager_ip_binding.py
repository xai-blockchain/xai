from flask import Flask
import pytest

from xai.core.security.security_middleware import SecurityConfig, SessionManager


@pytest.fixture(name="app")
def fixture_app():
    return Flask(__name__)


def test_resolve_client_ip_does_not_trust_headers_by_default(app: Flask, monkeypatch: pytest.MonkeyPatch):
    manager = SessionManager()
    monkeypatch.setattr(SecurityConfig, "TRUST_PROXY_HEADERS", False)
    with app.test_request_context("/", headers={"X-Forwarded-For": "203.0.113.10"}, environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        assert manager._resolve_client_ip() == "10.0.0.1"  # pylint: disable=protected-access


def test_resolve_client_ip_respects_trusted_proxies(app: Flask, monkeypatch: pytest.MonkeyPatch):
    manager = SessionManager()
    monkeypatch.setattr(SecurityConfig, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(SecurityConfig, "TRUSTED_PROXY_IPS", ["10.1.1.1"])
    with app.test_request_context(
        "/",
        headers={"X-Forwarded-For": "198.51.100.5"},
        environ_base={"REMOTE_ADDR": "10.1.1.1"},
    ):
        assert manager._resolve_client_ip() == "198.51.100.5"  # pylint: disable=protected-access


def test_session_fingerprint_rejects_ip_spoof(app: Flask, monkeypatch: pytest.MonkeyPatch):
    manager = SessionManager()
    monkeypatch.setattr(SecurityConfig, "TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr(SecurityConfig, "STRICT_SESSION_FINGERPRINTING", True)
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.0.2.1"}):
        token = manager.create_session("user-1")

    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "203.0.113.9"}):
        is_valid, _ = manager.validate_session(token)
        assert is_valid is False
