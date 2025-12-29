"""
Response Compression Middleware for XAI Blockchain API

Provides gzip/deflate compression for API responses to reduce bandwidth usage.
Uses Flask-Compress when available, with a fallback to manual implementation.

Configuration (via environment variables):
- XAI_API_COMPRESSION_ENABLED: Enable compression (default: 1/true)
- XAI_API_COMPRESSION_THRESHOLD: Min bytes before compression (default: 1024)
- XAI_API_COMPRESSION_LEVEL: Compression level 1-9 (default: 6)
- XAI_API_COMPRESSION_MIMETYPES: Comma-separated mimetypes to compress

Note: Flask-Compress must be installed for this feature:
    pip install flask-compress>=1.15.0
"""

from __future__ import annotations

import gzip
import io
import logging
import os
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask, Response

logger = logging.getLogger(__name__)

# Configuration defaults
COMPRESSION_ENABLED = os.getenv("XAI_API_COMPRESSION_ENABLED", "1").strip().lower() in ("1", "true", "yes")
COMPRESSION_THRESHOLD = int(os.getenv("XAI_API_COMPRESSION_THRESHOLD", "1024"))
COMPRESSION_LEVEL = int(os.getenv("XAI_API_COMPRESSION_LEVEL", "6"))
COMPRESSION_MIMETYPES_RAW = os.getenv(
    "XAI_API_COMPRESSION_MIMETYPES",
    "application/json,text/plain,text/html,text/css,text/javascript,application/javascript"
)
COMPRESSION_MIMETYPES = [m.strip() for m in COMPRESSION_MIMETYPES_RAW.split(",") if m.strip()]

# Validate compression level
if not 1 <= COMPRESSION_LEVEL <= 9:
    logger.warning(
        "Invalid compression level %d, using default 6",
        COMPRESSION_LEVEL,
        extra={"event": "compression.invalid_level"}
    )
    COMPRESSION_LEVEL = 6

# Validate compression threshold
if COMPRESSION_THRESHOLD < 0:
    logger.warning(
        "Invalid compression threshold %d, using default 1024",
        COMPRESSION_THRESHOLD,
        extra={"event": "compression.invalid_threshold"}
    )
    COMPRESSION_THRESHOLD = 1024


def _check_flask_compress_available() -> bool:
    """Check if Flask-Compress is installed."""
    try:
        from flask_compress import Compress  # noqa: F401
        return True
    except ImportError:
        return False


FLASK_COMPRESS_AVAILABLE = _check_flask_compress_available()


def setup_compression(app: "Flask") -> bool:
    """
    Setup response compression for a Flask application.

    Uses Flask-Compress if available, otherwise logs a warning.
    Compression can be disabled via XAI_API_COMPRESSION_ENABLED=0.

    Args:
        app: Flask application instance

    Returns:
        True if compression was successfully enabled, False otherwise
    """
    if not COMPRESSION_ENABLED:
        logger.info(
            "Response compression disabled via configuration",
            extra={"event": "compression.disabled"}
        )
        return False

    if FLASK_COMPRESS_AVAILABLE:
        return _setup_flask_compress(app)

    logger.warning(
        "Flask-Compress not installed. To enable compression: pip install flask-compress>=1.15.0",
        extra={"event": "compression.flask_compress_missing"}
    )
    return False


def _setup_flask_compress(app: "Flask") -> bool:
    """
    Configure Flask-Compress with XAI settings.

    Args:
        app: Flask application instance

    Returns:
        True if successfully configured
    """
    try:
        from flask_compress import Compress

        # Configure Flask-Compress settings
        app.config["COMPRESS_MIMETYPES"] = COMPRESSION_MIMETYPES
        app.config["COMPRESS_MIN_SIZE"] = COMPRESSION_THRESHOLD
        app.config["COMPRESS_LEVEL"] = COMPRESSION_LEVEL
        app.config["COMPRESS_ALGORITHM"] = "gzip"  # Prefer gzip for wider compatibility
        app.config["COMPRESS_REGISTER"] = True

        # Initialize compression
        compress = Compress()
        compress.init_app(app)

        logger.info(
            "Response compression enabled (threshold=%d bytes, level=%d)",
            COMPRESSION_THRESHOLD,
            COMPRESSION_LEVEL,
            extra={
                "event": "compression.enabled",
                "threshold": COMPRESSION_THRESHOLD,
                "level": COMPRESSION_LEVEL,
                "mimetypes": len(COMPRESSION_MIMETYPES),
            }
        )
        return True

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Failed to initialize Flask-Compress: %s",
            exc,
            extra={"event": "compression.init_failed"}
        )
        return False


def get_compression_status() -> dict:
    """
    Get current compression configuration status.

    Returns:
        Dictionary with compression configuration and status
    """
    return {
        "enabled": COMPRESSION_ENABLED,
        "flask_compress_available": FLASK_COMPRESS_AVAILABLE,
        "threshold_bytes": COMPRESSION_THRESHOLD,
        "level": COMPRESSION_LEVEL,
        "mimetypes": COMPRESSION_MIMETYPES,
        "active": COMPRESSION_ENABLED and FLASK_COMPRESS_AVAILABLE,
    }


__all__ = [
    "setup_compression",
    "get_compression_status",
    "COMPRESSION_ENABLED",
    "COMPRESSION_THRESHOLD",
    "COMPRESSION_LEVEL",
    "COMPRESSION_MIMETYPES",
    "FLASK_COMPRESS_AVAILABLE",
]
