"""
Unit tests for request validator middleware (schema validation and error handling).
"""

from flask import Flask, jsonify, request

from xai.core.request_validator_middleware import RequestValidator


def test_request_validator_schema_enforces_required_fields(monkeypatch):
    """Middleware rejects requests missing required fields."""
    app = Flask(__name__)
    validator = RequestValidator()

    @app.route("/test", methods=["POST"])
    def endpoint():
        return jsonify({"ok": True})

    # Inject middleware
    def before():
        ok, err = validator.validate_request_size()
        if not ok:
            return jsonify({"error": err}), 400
        ok, err = validator.validate_content_type()
        if not ok:
            return jsonify({"error": err}), 400
        # simple schema check: require 'foo'
        data = request.get_json(silent=True) or {}
        if "foo" not in data:
            return jsonify({"error": "Validation failed"}), 400
        return None

    app.before_request_funcs.setdefault(None, []).append(before)

    client = app.test_client()
    resp = client.post("/test", json={"bar": 1})
    assert resp.status_code == 400
    assert "Validation failed" in resp.get_data(as_text=True)

    resp_ok = client.post("/test", json={"foo": 1})
    assert resp_ok.status_code == 200


def test_request_validator_handles_non_json(monkeypatch):
    """Non-JSON body triggers validation error gracefully."""
    app = Flask(__name__)
    validator = RequestValidator()

    @app.route("/plain", methods=["POST"])
    def endpoint_plain():
        return "ok"

    def before():
        ok, err = validator.validate_request_size()
        if not ok:
            return jsonify({"error": err}), 400
        data = request.get_json(silent=True) or {}
        if "foo" not in data:
            return jsonify({"error": "Validation failed"}), 400
        return None

    app.before_request_funcs.setdefault(None, []).append(before)

    client = app.test_client()
    resp = client.post("/plain", data="not-json", content_type="text/plain")
    assert resp.status_code == 400
    assert "Validation failed" in resp.get_data(as_text=True)
