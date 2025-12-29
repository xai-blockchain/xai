"""
XAI API Explorer - Interactive Swagger UI

Flask Blueprint providing an interactive API documentation explorer using Swagger UI.
Serves the OpenAPI 3.0 specification and provides "Try it out" functionality.

Usage:
    from xai.api_explorer import api_explorer_bp
    app.register_blueprint(api_explorer_bp)

Routes:
    /api/docs       - Swagger UI interface
    /swagger        - Alias for /api/docs
    /api/openapi    - Raw OpenAPI YAML spec
    /api/openapi.json - OpenAPI spec as JSON
"""

from xai.api_explorer.swagger_routes import api_explorer_bp

__all__ = ["api_explorer_bp"]
