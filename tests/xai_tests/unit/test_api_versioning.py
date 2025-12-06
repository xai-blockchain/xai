"""Tests for API version prefix handling and headers."""

from flask import Flask, jsonify

from xai.core.node_api import APIVersioningManager


def _create_app():
    app = Flask(__name__)

    @app.route("/ping")
    def ping():
        return jsonify({"message": "pong"})

    APIVersioningManager(
        app,
        supported_versions=("v1", "v2"),
        default_version="v2",
        deprecated_versions={"v1": {"sunset": "Wed, 01 Jan 2025 00:00:00 GMT"}},
        docs_url="https://example.com/docs/versioning",
    )
    return app


def test_default_version_header_applied():
    app = _create_app()
    client = app.test_client()

    response = client.get("/ping")

    assert response.status_code == 200
    assert response.headers.get("X-API-Version") == "v2"
    assert "Deprecation" not in response.headers


def test_versioned_path_sets_deprecation_headers():
    app = _create_app()
    client = app.test_client()

    response = client.get("/v1/ping")

    assert response.status_code == 200
    assert response.headers.get("X-API-Version") == "v1"
    assert response.headers.get("Deprecation") == 'version="v1"'
    assert response.headers.get("Sunset") == "Wed, 01 Jan 2025 00:00:00 GMT"
    assert response.headers.get("Link").startswith("<https://example.com/docs/versioning>")


def test_unknown_version_returns_error():
    app = _create_app()
    client = app.test_client()

    response = client.get("/v99/ping")

    assert response.status_code == 404
    assert response.headers.get("X-API-Version") == "unknown"
    payload = response.get_json()
    assert payload["code"] == "unsupported_api_version"
    assert payload["requested_version"] == "v99"
