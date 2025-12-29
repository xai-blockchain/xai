"""
Tests for Response Compression Middleware

Tests configuration parsing and setup functions for API response compression.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


def _check_flask_compress_available():
    """Helper to check Flask-Compress availability for skip decorator."""
    try:
        from flask_compress import Compress  # noqa: F401
        return True
    except ImportError:
        return False


class TestCompressionConfiguration:
    """Test compression configuration parsing."""

    def test_default_configuration_values(self):
        """Test default configuration values are set correctly."""
        # Clear environment and reimport
        with patch.dict(os.environ, {}, clear=True):
            # Import fresh module
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert comp.COMPRESSION_ENABLED is True  # Default enabled
            assert comp.COMPRESSION_THRESHOLD == 1024  # 1KB default
            assert comp.COMPRESSION_LEVEL == 6  # Default gzip level
            assert "application/json" in comp.COMPRESSION_MIMETYPES
            assert "text/plain" in comp.COMPRESSION_MIMETYPES

    def test_disabled_via_environment(self):
        """Test compression can be disabled via environment variable."""
        env = {
            "XAI_API_COMPRESSION_ENABLED": "0"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert comp.COMPRESSION_ENABLED is False

    def test_custom_threshold(self):
        """Test custom compression threshold."""
        env = {
            "XAI_API_COMPRESSION_THRESHOLD": "2048"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert comp.COMPRESSION_THRESHOLD == 2048

    def test_custom_compression_level(self):
        """Test custom compression level."""
        env = {
            "XAI_API_COMPRESSION_LEVEL": "9"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert comp.COMPRESSION_LEVEL == 9

    def test_invalid_compression_level_falls_back(self):
        """Test invalid compression level falls back to default."""
        env = {
            "XAI_API_COMPRESSION_LEVEL": "15"  # Invalid (>9)
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert comp.COMPRESSION_LEVEL == 6  # Falls back to default

    def test_custom_mimetypes(self):
        """Test custom mimetypes configuration."""
        env = {
            "XAI_API_COMPRESSION_MIMETYPES": "application/json,text/xml"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            assert "application/json" in comp.COMPRESSION_MIMETYPES
            assert "text/xml" in comp.COMPRESSION_MIMETYPES
            assert "text/html" not in comp.COMPRESSION_MIMETYPES


class TestGetCompressionStatus:
    """Test get_compression_status function."""

    def test_returns_configuration_dict(self):
        """Test status returns expected structure."""
        from xai.core.api.response_compression import get_compression_status

        status = get_compression_status()

        assert isinstance(status, dict)
        assert "enabled" in status
        assert "threshold_bytes" in status
        assert "level" in status
        assert "mimetypes" in status
        assert "flask_compress_available" in status
        assert "active" in status


class TestSetupCompression:
    """Test setup_compression function."""

    def test_returns_false_when_disabled(self):
        """Test setup returns False when compression is disabled."""
        env = {
            "XAI_API_COMPRESSION_ENABLED": "0"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            mock_app = MagicMock()
            result = comp.setup_compression(mock_app)
            assert result is False

    def test_handles_missing_flask_compress(self):
        """Test graceful handling when Flask-Compress not installed."""
        env = {
            "XAI_API_COMPRESSION_ENABLED": "1"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp

            # Temporarily mark Flask-Compress as unavailable
            orig = comp.FLASK_COMPRESS_AVAILABLE
            comp.FLASK_COMPRESS_AVAILABLE = False

            try:
                mock_app = MagicMock()
                result = comp.setup_compression(mock_app)
                assert result is False
            finally:
                comp.FLASK_COMPRESS_AVAILABLE = orig

    @pytest.mark.skipif(
        not _check_flask_compress_available(),
        reason="Flask-Compress not installed"
    )
    def test_enables_flask_compress_when_available(self):
        """Test Flask-Compress is enabled when available."""
        from flask import Flask

        # Ensure module is loaded with compression enabled
        env = {"XAI_API_COMPRESSION_ENABLED": "1"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import xai.core.api.response_compression as comp
            importlib.reload(comp)

            app = Flask(__name__)
            result = comp.setup_compression(app)

            assert result is True
            assert app.config.get("COMPRESS_MIMETYPES") is not None
            assert app.config.get("COMPRESS_MIN_SIZE") is not None
