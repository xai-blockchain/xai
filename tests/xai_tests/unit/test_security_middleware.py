"""
SecurityMiddleware unit tests covering rate limiting, CSRF enforcement,
and session fingerprint binding.
"""

from flask import Flask, jsonify

from xai.core.security_middleware import SecurityMiddleware, SecurityConfig


def _build_app(monkeypatch):
    # Tighten limits for tests
    monkeypatch.setattr(SecurityConfig, "RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(SecurityConfig, "RATE_LIMIT_WINDOW", 1)
    monkeypatch.setattr(SecurityConfig, "STRICT_SESSION_FINGERPRINTING", True)
    monkeypatch.setattr(SecurityConfig, "SESSION_BIND_USER_AGENT", True)
    monkeypatch.setattr(SecurityConfig, "SESSION_BIND_ACCEPT_LANGUAGE", False)
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret"
    middleware = SecurityMiddleware(app)

    @app.route("/ping", methods=["GET", "POST"])
    def ping():
        return jsonify({"pong": True})

    return app, middleware


def test_rate_limit_triggers(monkeypatch):
    """Rate limiter returns 429 after exceeding allowed requests."""
    app, _ = _build_app(monkeypatch)
    client = app.test_client()

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    resp = client.get("/ping")
    assert resp.status_code == 429


def test_csrf_missing_returns_403(monkeypatch):
    """POST without CSRF token is rejected when enabled."""
    app, _ = _build_app(monkeypatch)
    client = app.test_client()

    resp = client.post("/ping", json={})
    assert resp.status_code == 403
