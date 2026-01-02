"""
XAI Swagger UI Routes

Flask Blueprint for serving interactive API documentation via Swagger UI.
Provides OpenAPI spec serving in both YAML and JSON formats.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from flask import Blueprint, Response, jsonify, redirect, render_template, url_for

logger = logging.getLogger(__name__)

# Locate the OpenAPI spec file relative to this module
_MODULE_DIR = Path(__file__).parent
_PROJECT_ROOT = _MODULE_DIR.parent.parent.parent  # src/xai/api_explorer -> project root
_OPENAPI_YAML_PATH = _PROJECT_ROOT / "docs" / "api" / "openapi.yaml"

# Cache for parsed OpenAPI spec
_openapi_spec_cache: dict[str, Any] | None = None


def _load_openapi_spec() -> dict[str, Any]:
    """Load and cache the OpenAPI specification.

    Returns:
        Parsed OpenAPI spec as dictionary

    Raises:
        FileNotFoundError: If openapi.yaml is missing
        yaml.YAMLError: If spec is malformed
    """
    global _openapi_spec_cache

    if _openapi_spec_cache is not None:
        return _openapi_spec_cache

    if not _OPENAPI_YAML_PATH.exists():
        # Try alternate location
        alt_path = Path(__file__).parent.parent.parent.parent / "docs" / "api" / "openapi.yaml"
        if alt_path.exists():
            spec_path = alt_path
        else:
            raise FileNotFoundError(
                f"OpenAPI spec not found at {_OPENAPI_YAML_PATH} or {alt_path}"
            )
    else:
        spec_path = _OPENAPI_YAML_PATH

    logger.info("Loading OpenAPI spec from %s", spec_path)

    with open(spec_path, "r", encoding="utf-8") as f:
        _openapi_spec_cache = yaml.safe_load(f)

    return _openapi_spec_cache


def _get_openapi_yaml() -> str:
    """Get the raw OpenAPI YAML content.

    Returns:
        OpenAPI spec as YAML string
    """
    if _OPENAPI_YAML_PATH.exists():
        with open(_OPENAPI_YAML_PATH, "r", encoding="utf-8") as f:
            return f.read()

    # Try alternate location
    alt_path = Path(__file__).parent.parent.parent.parent / "docs" / "api" / "openapi.yaml"
    if alt_path.exists():
        with open(alt_path, "r", encoding="utf-8") as f:
            return f.read()

    raise FileNotFoundError("OpenAPI spec not found")


# Create Blueprint with template folder
api_explorer_bp = Blueprint(
    "api_explorer",
    __name__,
    template_folder="templates",
    static_folder=None,
)


@api_explorer_bp.route("/api/docs")
def swagger_ui() -> str:
    """Render Swagger UI for interactive API exploration.

    Returns:
        Rendered Swagger UI HTML page
    """
    # Get spec info for page title
    try:
        spec = _load_openapi_spec()
        api_title = spec.get("info", {}).get("title", "XAI API")
        api_version = spec.get("info", {}).get("version", "1.0.0")
    except Exception as e:
        logger.warning("Could not load OpenAPI spec for title: %s", e)
        api_title = "XAI API"
        api_version = "1.0.0"

    return render_template(
        "swagger.html",
        api_title=api_title,
        api_version=api_version,
        openapi_url=url_for("api_explorer.openapi_json"),
    )


@api_explorer_bp.route("/swagger")
def swagger_redirect() -> Any:
    """Redirect /swagger to /api/docs."""
    return redirect(url_for("api_explorer.swagger_ui"), code=301)


@api_explorer_bp.route("/api/openapi")
def openapi_yaml() -> Response:
    """Serve the OpenAPI specification as YAML.

    Returns:
        OpenAPI spec in YAML format with appropriate content type
    """
    try:
        yaml_content = _get_openapi_yaml()
        return Response(
            yaml_content,
            mimetype="text/yaml",
            headers={
                "Content-Disposition": "inline; filename=openapi.yaml",
                "Cache-Control": "public, max-age=3600",
            },
        )
    except FileNotFoundError as e:
        logger.error("OpenAPI spec not found: %s", e)
        return Response(
            json.dumps({"error": "OpenAPI specification not found"}),
            status=404,
            mimetype="application/json",
        )


@api_explorer_bp.route("/api/openapi.json")
def openapi_json() -> tuple[Response, int] | Response:
    """Serve the OpenAPI specification as JSON.

    Returns:
        OpenAPI spec in JSON format
    """
    try:
        spec = _load_openapi_spec()
        response = jsonify(spec)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    except FileNotFoundError as e:
        logger.error("OpenAPI spec not found: %s", e)
        return jsonify({"error": "OpenAPI specification not found"}), 404
    except yaml.YAMLError as e:
        logger.error("OpenAPI spec parse error: %s", e)
        return jsonify({"error": "OpenAPI specification is malformed"}), 500


@api_explorer_bp.route("/api/docs/endpoints")
def list_endpoints() -> tuple[Response, int]:
    """List all API endpoints from the OpenAPI spec.

    Returns:
        JSON list of endpoints with methods and summaries
    """
    try:
        spec = _load_openapi_spec()
        endpoints = []

        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "tags": details.get("tags", []),
                        "deprecated": details.get("deprecated", False),
                    })

        # Sort by path then method
        endpoints.sort(key=lambda e: (e["path"], e["method"]))

        return jsonify({
            "success": True,
            "total": len(endpoints),
            "endpoints": endpoints,
        }), 200

    except Exception as e:
        logger.error("Error listing endpoints: %s", e)
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500
