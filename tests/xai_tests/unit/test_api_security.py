"""
Unit tests for API security manager rate limiting and payload validation wiring.
"""

import types

import pytest
from flask import Flask

from xai.core import api_security
from xai.core.api_security import APISecurityManager, RateLimitExceeded


class DummyConfig:
    API_RATE_LIMIT = 2
    API_RATE_WINDOW_SECONDS = 60
    API_MAX_JSON_BYTES = 128


def _make_app(monkeypatch):
    """Create a Flask app wired with APISecurityManager enforcing before_request."""
    monkeypatch.setattr(api_security, "Config", DummyConfig)
    mgr = APISecurityManager()
    app = Flask(__name__)
    app.before_request(mgr.enforce_request)
    return app, mgr


def test_rate_limit_blocks_after_threshold(monkeypatch):
    """Requests beyond configured limit raise RateLimitExceeded."""
    app, _ = _make_app(monkeypatch)
    client = app.test_client()

    with app.test_request_context("/", json={}):
        # First two allowed
        for _ in range(2):
            client.get("/")
        with pytest.raises(RateLimitExceeded):
            # Third should trip rate limit
            app.preprocess_request()


def test_payload_size_validation(monkeypatch):
    """Large payloads trigger ValidationError."""
    app, _ = _make_app(monkeypatch)
    # Add a dummy route to allow request processing
    @app.route("/", methods=["POST"])
    def _noop():
        return "", 204
    client = app.test_client()

    big_body = "x" * (DummyConfig.API_MAX_JSON_BYTES + 1)
    resp = client.post(
        "/",
        data=big_body,
        headers={"Content-Type": "application/json"},
        # Let Flask's built-in max content length handling respond instead of raising
        buffered=True,
    )
    assert resp.status_code in (400, 413, 500)


def test_validation_invoked_for_json(monkeypatch):
    """validate_api_request is invoked with provided payload."""
    app, _ = _make_app(monkeypatch)
    @app.route("/", methods=["POST"])
    def _noop():
        return "", 204
    client = app.test_client()
    called = {}

    def fake_validate(data, max_size):
        called["data"] = data
        called["max_size"] = max_size

    monkeypatch.setattr(api_security, "validate_api_request", fake_validate)

    resp = client.post("/", json={"hello": "world"})
    assert resp.status_code in (200, 204, 400)
    assert called["data"] == {"hello": "world"}
    assert called["max_size"] == DummyConfig.API_MAX_JSON_BYTES
