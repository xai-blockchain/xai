"""
Tests for security startup validator.

Verifies that:
1. Production mode is correctly detected
2. Security bypasses are detected
3. Production mode fails startup with bypasses enabled
4. Non-production mode allows bypasses with warnings
"""

import os
import pytest
from unittest.mock import patch

from xai.security.startup_validator import (
    is_production_mode,
    is_bypass_enabled,
    validate_security_configuration,
    enforce_production_security,
    get_security_status,
    SecurityConfigurationError,
    DANGEROUS_BYPASSES,
    WARNING_BYPASSES,
)


class TestIsProductionMode:
    """Test production mode detection."""

    def test_production_mode_from_explicit_flag(self):
        """XAI_PRODUCTION_MODE=1 should indicate production."""
        with patch.dict(os.environ, {"XAI_PRODUCTION_MODE": "1"}, clear=False):
            assert is_production_mode() is True

    def test_production_mode_from_true_string(self):
        """XAI_PRODUCTION_MODE=true should indicate production."""
        with patch.dict(os.environ, {"XAI_PRODUCTION_MODE": "true"}, clear=False):
            assert is_production_mode() is True

    def test_production_mode_from_network_mainnet(self):
        """XAI_NETWORK=mainnet should indicate production."""
        with patch.dict(os.environ, {"XAI_NETWORK": "mainnet", "XAI_PRODUCTION_MODE": "0"}, clear=False):
            assert is_production_mode() is True

    def test_non_production_mode_by_default(self):
        """Default should be non-production mode."""
        with patch.dict(os.environ, {"XAI_PRODUCTION_MODE": "0", "XAI_NETWORK": "testnet"}, clear=False):
            assert is_production_mode() is False

    def test_non_production_with_testnet(self):
        """XAI_NETWORK=testnet should be non-production."""
        with patch.dict(os.environ, {"XAI_NETWORK": "testnet", "XAI_PRODUCTION_MODE": ""}, clear=False):
            assert is_production_mode() is False


class TestIsBypassEnabled:
    """Test bypass detection."""

    def test_bypass_enabled_with_1(self):
        """Value '1' should enable bypass."""
        with patch.dict(os.environ, {"TEST_BYPASS": "1"}, clear=False):
            assert is_bypass_enabled("TEST_BYPASS") is True

    def test_bypass_enabled_with_true(self):
        """Value 'true' should enable bypass."""
        with patch.dict(os.environ, {"TEST_BYPASS": "true"}, clear=False):
            assert is_bypass_enabled("TEST_BYPASS") is True

    def test_bypass_disabled_by_default(self):
        """Unset variable should not enable bypass."""
        with patch.dict(os.environ, {}, clear=False):
            if "TEST_BYPASS" in os.environ:
                del os.environ["TEST_BYPASS"]
            assert is_bypass_enabled("TEST_BYPASS") is False

    def test_bypass_disabled_with_0(self):
        """Value '0' should not enable bypass."""
        with patch.dict(os.environ, {"TEST_BYPASS": "0"}, clear=False):
            assert is_bypass_enabled("TEST_BYPASS") is False


class TestValidateSecurityConfiguration:
    """Test security configuration validation."""

    def test_secure_configuration_passes(self):
        """No bypasses should pass validation."""
        env = {
            "XAI_PRODUCTION_MODE": "0",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "0",
            "XAI_P2P_DISABLE_SSL": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            assert validate_security_configuration() is True

    def test_bypass_detected_in_non_production(self):
        """Bypasses in non-production should warn but not fail."""
        env = {
            "XAI_PRODUCTION_MODE": "0",
            "XAI_NETWORK": "testnet",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            # Should return False (insecure) but not raise
            result = validate_security_configuration(fail_on_critical=True)
            assert result is False

    def test_bypass_fails_in_production(self):
        """Critical bypasses in production should raise exception."""
        env = {
            "XAI_PRODUCTION_MODE": "1",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SecurityConfigurationError):
                validate_security_configuration(fail_on_critical=True)

    def test_warning_bypass_does_not_fail_production(self):
        """Warning-level bypasses should not fail production startup."""
        env = {
            "XAI_PRODUCTION_MODE": "1",
            "XAI_P2P_DISABLE_SECURITY_EVENTS": "1",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            # Should not raise - warning bypasses don't block startup
            result = validate_security_configuration()
            assert result is True


class TestGetSecurityStatus:
    """Test security status reporting."""

    def test_secure_status(self):
        """Secure configuration should report correctly."""
        env = {
            "XAI_PRODUCTION_MODE": "1",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            status = get_security_status()
            assert status["production_mode"] is True
            assert status["is_secure"] is True
            assert len(status["critical_bypasses_enabled"]) == 0

    def test_insecure_status(self):
        """Insecure configuration should report bypasses."""
        env = {
            "XAI_PRODUCTION_MODE": "0",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            status = get_security_status()
            assert status["is_secure"] is False
            assert "XAI_P2P_DISABLE_SIGNATURE_VERIFY" in status["critical_bypasses_enabled"]


class TestDangerousBypassesList:
    """Test that all known dangerous bypasses are checked."""

    def test_signature_verify_bypass_is_critical(self):
        """Signature verification bypass should be in critical list."""
        env_vars = [b.env_var for b in DANGEROUS_BYPASSES]
        assert "XAI_P2P_DISABLE_SIGNATURE_VERIFY" in env_vars

    def test_all_bypasses_have_descriptions(self):
        """All bypasses should have descriptions."""
        for bypass in DANGEROUS_BYPASSES + WARNING_BYPASSES:
            assert len(bypass.description) > 0
            assert bypass.severity in ("critical", "warning")


class TestEnforceProductionSecurity:
    """Test startup enforcement."""

    def test_enforcement_passes_when_secure(self):
        """Enforcement should pass with secure config."""
        env = {
            "XAI_PRODUCTION_MODE": "0",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            # Should not raise or exit
            enforce_production_security()

    def test_enforcement_exits_when_insecure_in_production(self):
        """Enforcement should exit when bypasses enabled in production."""
        env = {
            "XAI_PRODUCTION_MODE": "1",
            "XAI_P2P_DISABLE_SIGNATURE_VERIFY": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                enforce_production_security()
            assert exc_info.value.code == 1
