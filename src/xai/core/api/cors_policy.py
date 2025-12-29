"""
XAI Blockchain - CORS Policy Manager

Production-grade CORS policy management with:
- Environment-based whitelist configuration
- Pattern matching for allowed origins
- Strict validation and proper headers
- Network-specific defaults (development, testnet, production)

This module implements Task 67: CORS Policy for the blockchain node.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

from flask import jsonify, make_response, request
from flask_cors import CORS

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


class CORSPolicyManager:
    """Production-grade CORS policy management.

    Implements environment-based whitelist with strict validation
    and proper header handling for cross-origin requests.

    Attributes:
        app: Flask application instance
        allowed_origins: List of allowed origin patterns
    """

    def __init__(self, app: "Flask", config: Any = None):
        """Initialize CORS policy manager.

        Args:
            app: Flask application instance
            config: Optional config object (defaults to importing Config)
        """
        self.app = app
        self._config = config
        self.allowed_origins = self._load_allowed_origins()
        self.setup_cors()

    def _get_config(self) -> Any:
        """Get configuration object lazily."""
        if self._config is not None:
            return self._config
        try:
            from xai.core.config import Config
            return Config
        except ImportError:
            return None

    def _load_allowed_origins(self) -> list[str]:
        """Load allowed origins from configuration.

        Priority:
        1. Config.API_ALLOWED_ORIGINS
        2. XAI_ALLOWED_ORIGINS environment variable
        3. Network-specific defaults

        Returns:
            List of allowed origin URLs or patterns
        """
        config = self._get_config()

        # Config-driven origins have highest precedence
        config_origins = getattr(config, "API_ALLOWED_ORIGINS", None) if config else None
        if config_origins:
            return list(config_origins)

        # Load from environment variable
        env_origins = os.getenv("XAI_ALLOWED_ORIGINS", "")
        if env_origins:
            origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
            return origins

        # Network-specific defaults
        network = os.getenv("XAI_NETWORK_TYPE", "mainnet")
        if network == "testnet":
            # More permissive for testnet
            return ["http://localhost:*", "http://127.0.0.1:*"]
        elif network == "development":
            return ["*"]  # Allow all in development

        # Production: only specific domains (empty = same origin only)
        return []

    def setup_cors(self) -> None:
        """Setup CORS with strict policies."""
        if not self.allowed_origins or len(self.allowed_origins) == 0:
            # No CORS - same origin only
            logger.info("CORS: Same-origin only (production mode)")
            return

        # Configure CORS
        CORS(
            self.app,
            origins=self.allowed_origins,
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Admin-Token"],
            expose_headers=["Content-Range", "X-Content-Range"],
            supports_credentials=True,
            max_age=3600,  # Cache preflight for 1 hour
        )

        logger.info(f"CORS configured with origins: {self.allowed_origins}")

        # Register request/response hooks
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register Flask hooks for CORS validation."""

        @self.app.before_request
        def check_cors() -> Any | None:
            """Validate origin on all requests."""
            origin = request.headers.get("Origin")

            if origin and not self.validate_origin(origin):
                logger.warning(
                    f"CORS: Blocked request from unauthorized origin: {origin}",
                    extra={"event": "security.cors_blocked", "origin": origin},
                )
                return make_response(
                    jsonify({"error": "Origin not allowed", "code": "cors_violation"}),
                    403,
                )
            return None

        @self.app.after_request
        def add_cors_headers(response: Any) -> Any:
            """Add proper CORS headers to response."""
            origin = request.headers.get("Origin")

            if origin and self.validate_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, X-API-Key"
                )

            return response

    def validate_origin(self, origin: str) -> bool:
        """Validate origin against whitelist.

        Args:
            origin: Origin URL to validate

        Returns:
            True if origin is allowed
        """
        if not origin:
            return False

        # Wildcard check
        if "*" in self.allowed_origins:
            return True

        # Exact match
        if origin in self.allowed_origins:
            return True

        # Pattern matching (e.g., http://localhost:*)
        for allowed in self.allowed_origins:
            if "*" in allowed:
                pattern = allowed.replace("*", ".*")
                if re.match(pattern, origin):
                    return True

        return False

    def add_origin(self, origin: str) -> None:
        """Dynamically add an allowed origin.

        Args:
            origin: Origin URL to allow
        """
        if origin not in self.allowed_origins:
            self.allowed_origins.append(origin)
            logger.info(
                f"CORS: Added allowed origin: {origin}",
                extra={"event": "cors.origin_added", "origin": origin},
            )

    def remove_origin(self, origin: str) -> bool:
        """Remove an allowed origin.

        Args:
            origin: Origin URL to remove

        Returns:
            True if origin was removed
        """
        if origin in self.allowed_origins:
            self.allowed_origins.remove(origin)
            logger.info(
                f"CORS: Removed allowed origin: {origin}",
                extra={"event": "cors.origin_removed", "origin": origin},
            )
            return True
        return False

    def get_origins(self) -> list[str]:
        """Get current list of allowed origins.

        Returns:
            Copy of allowed origins list
        """
        return list(self.allowed_origins)


__all__ = ["CORSPolicyManager"]
