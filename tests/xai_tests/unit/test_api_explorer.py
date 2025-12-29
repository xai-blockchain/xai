"""Tests for the API Explorer (Swagger UI) blueprint."""

from __future__ import annotations

import json

import pytest
from flask import Flask

from xai.api_explorer import api_explorer_bp
from xai.api_explorer.swagger_routes import _load_openapi_spec


class TestApiExplorer:
    """Test suite for API Explorer functionality."""

    @pytest.fixture
    def app(self) -> Flask:
        """Create a test Flask application."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(api_explorer_bp)
        return app

    @pytest.fixture
    def client(self, app: Flask):
        """Create a test client."""
        return app.test_client()

    def test_openapi_spec_loads(self) -> None:
        """Test that the OpenAPI spec can be loaded."""
        spec = _load_openapi_spec()
        assert spec is not None
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

    def test_openapi_spec_metadata(self) -> None:
        """Test OpenAPI spec metadata is correct."""
        spec = _load_openapi_spec()
        info = spec.get("info", {})
        assert info.get("title") == "XAI Blockchain API"
        assert "version" in info

    def test_swagger_ui_page(self, client) -> None:
        """Test Swagger UI page renders correctly."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert b"swagger-ui" in response.data.lower()
        assert b"XAI" in response.data

    def test_swagger_redirect(self, client) -> None:
        """Test /swagger redirects to /api/docs."""
        response = client.get("/swagger")
        assert response.status_code == 301
        assert response.headers.get("Location", "").endswith("/api/docs")

    def test_openapi_json_endpoint(self, client) -> None:
        """Test OpenAPI JSON endpoint returns valid JSON."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert "openapi" in data
        assert "paths" in data

    def test_openapi_yaml_endpoint(self, client) -> None:
        """Test OpenAPI YAML endpoint returns YAML content."""
        response = client.get("/api/openapi")
        assert response.status_code == 200
        assert "yaml" in response.content_type

        # Should start with openapi version
        content = response.data.decode("utf-8")
        assert content.startswith("openapi:")

    def test_endpoints_list(self, client) -> None:
        """Test endpoint listing returns valid data."""
        response = client.get("/api/docs/endpoints")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data.get("success") is True
        assert "total" in data
        assert data["total"] > 0
        assert "endpoints" in data
        assert len(data["endpoints"]) > 0

        # Check endpoint structure
        endpoint = data["endpoints"][0]
        assert "path" in endpoint
        assert "method" in endpoint
        assert "tags" in endpoint

    def test_endpoints_have_required_fields(self, client) -> None:
        """Test that listed endpoints have all required fields."""
        response = client.get("/api/docs/endpoints")
        data = json.loads(response.data)

        for endpoint in data["endpoints"]:
            assert isinstance(endpoint["path"], str)
            assert endpoint["method"] in ("GET", "POST", "PUT", "DELETE", "PATCH")
            assert isinstance(endpoint["tags"], list)
            assert isinstance(endpoint.get("deprecated", False), bool)

    def test_cache_headers(self, client) -> None:
        """Test that cache headers are set correctly."""
        response = client.get("/api/openapi.json")
        assert "Cache-Control" in response.headers

        response = client.get("/api/openapi")
        assert "Cache-Control" in response.headers
