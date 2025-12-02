"""Comprehensive tests for JWT token expiration verification.

Tests ensure that:
1. Expired tokens are properly rejected
2. Valid tokens within leeway are accepted
3. Clock skew tolerance works correctly
4. Security events are logged
5. Error messages are clear and actionable
"""

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

# Test will skip if jwt not installed
jwt = pytest.importorskip("jwt")

from xai.core.api_auth import JWTAuthManager


def make_request(headers=None):
    """Create a mock Flask request."""
    return SimpleNamespace(
        headers=headers or {},
        remote_addr="127.0.0.1"
    )


class TestJWTExpiration:
    """Test JWT token expiration verification."""

    def test_valid_token_accepted(self):
        """Test that valid, non-expired tokens are accepted."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=1,
            clock_skew_seconds=30
        )

        access_token, refresh_token = manager.generate_token("user-123", scope="user")

        # Should be valid
        valid, payload, error = manager.validate_token(access_token)
        assert valid is True
        assert error is None
        assert payload is not None
        assert payload["user_id"] == "user-123"
        assert payload["sub"] == "user-123"

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=0,  # Expires immediately
            clock_skew_seconds=0  # No leeway
        )

        access_token, _ = manager.generate_token("user-123")

        # Wait for token to expire (plus a small buffer)
        time.sleep(0.1)

        # Should be invalid
        valid, payload, error = manager.validate_token(access_token)
        assert valid is False
        assert payload is None
        assert error == "Token has expired"

    def test_clock_skew_tolerance(self):
        """Test that clock skew tolerance works correctly."""
        # Create token that expires in 10 seconds with 30 second leeway
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=0,  # Will set custom expiry
            clock_skew_seconds=30
        )

        # Manually create token with very short expiry
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-123",
            "user_id": "user-123",
            "scope": "user",
            "exp": now + timedelta(seconds=1),  # Expires in 1 second
            "iat": now,
            "type": "access"
        }
        token = jwt.encode(payload, manager.secret_key, algorithm=manager.algorithm)

        # Should be valid immediately
        valid, decoded, error = manager.validate_token(token)
        assert valid is True

        # Wait 2 seconds (token expired by 1 second, but within 30s leeway)
        time.sleep(2)

        # Should still be valid due to leeway
        valid, decoded, error = manager.validate_token(token)
        assert valid is True

        # Wait 32 seconds total (beyond leeway)
        time.sleep(30)

        # Now should be invalid
        valid, decoded, error = manager.validate_token(token)
        assert valid is False
        assert error == "Token has expired"

    def test_token_missing_required_claims_rejected(self):
        """Test that tokens missing required claims are rejected."""
        manager = JWTAuthManager(secret_key="test-secret")

        # Create token missing 'sub' claim
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": "user-123",
            "exp": now + timedelta(hours=1),
            "iat": now,
            # Missing 'sub' claim (required)
        }
        token = jwt.encode(payload, manager.secret_key, algorithm=manager.algorithm)

        # Should be rejected
        valid, decoded, error = manager.validate_token(token)
        assert valid is False
        assert error is not None
        assert "Invalid token" in error

    def test_expired_signature_error_logged(self):
        """Test that expired token attempts are logged as security events."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=0,
            clock_skew_seconds=0
        )

        access_token, _ = manager.generate_token("user-123")
        time.sleep(0.1)

        # Mock security logging
        with patch("xai.core.api_auth.log_security_event") as mock_log:
            valid, payload, error = manager.validate_token(
                access_token,
                remote_addr="192.168.1.100"
            )

            assert valid is False
            assert error == "Token has expired"

            # Verify security event was logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == "jwt_expired_token_attempt"
            assert call_args[0][1]["remote_addr"] == "192.168.1.100"
            assert call_args[1]["severity"] == "WARNING"

    def test_invalid_token_logged(self):
        """Test that invalid token attempts are logged."""
        manager = JWTAuthManager(secret_key="test-secret")

        # Create token with wrong secret
        wrong_token = jwt.encode(
            {"sub": "user-123", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "iat": datetime.now(timezone.utc)},
            "wrong-secret",
            algorithm="HS256"
        )

        with patch("xai.core.api_auth.log_security_event") as mock_log:
            valid, payload, error = manager.validate_token(
                wrong_token,
                remote_addr="192.168.1.100"
            )

            assert valid is False
            assert "Invalid token" in error

            # Verify security event was logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == "jwt_invalid_token_attempt"
            assert call_args[0][1]["remote_addr"] == "192.168.1.100"

    def test_revoked_token_attempt_logged(self):
        """Test that revoked token attempts are logged."""
        manager = JWTAuthManager(secret_key="test-secret")
        access_token, _ = manager.generate_token("user-123")

        # Revoke token
        manager.revoke_token(access_token)

        with patch("xai.core.api_auth.log_security_event") as mock_log:
            valid, payload, error = manager.validate_token(
                access_token,
                remote_addr="192.168.1.100"
            )

            assert valid is False
            assert error == "Token has been revoked"

            # Verify security event was logged (called once for revocation, once for attempt)
            assert mock_log.call_count >= 1
            # Check the most recent call
            last_call = mock_log.call_args_list[-1]
            assert last_call[0][0] == "jwt_revoked_token_attempt"
            assert last_call[0][1]["remote_addr"] == "192.168.1.100"

    def test_authorize_request_with_expired_token(self):
        """Test that authorize_request properly rejects expired tokens."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=0,
            clock_skew_seconds=0
        )

        access_token, _ = manager.generate_token("user-123")
        time.sleep(0.1)

        request = make_request(headers={"Authorization": f"Bearer {access_token}"})

        authorized, payload, error = manager.authorize_request(request)
        assert authorized is False
        assert payload is None
        assert error == "Token has expired"

    def test_refresh_token_expiration(self):
        """Test that refresh tokens also expire correctly."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=1,
            refresh_expiry_days=0,  # Refresh token expires immediately
            clock_skew_seconds=0
        )

        _, refresh_token = manager.generate_token("user-123")
        time.sleep(0.1)

        # Try to refresh
        success, new_token, error = manager.refresh_access_token(refresh_token)
        assert success is False
        assert new_token is None
        assert error == "Token has expired"

    def test_verify_signature_enabled(self):
        """Test that signature verification is enabled."""
        manager = JWTAuthManager(secret_key="test-secret")

        # Create token with different secret
        malicious_token = jwt.encode(
            {
                "sub": "admin-user",
                "user_id": "admin-user",
                "scope": "admin",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "type": "access"
            },
            "attacker-secret",  # Wrong secret
            algorithm="HS256"
        )

        # Should be rejected due to invalid signature
        valid, payload, error = manager.validate_token(malicious_token)
        assert valid is False
        assert error is not None
        assert "Invalid token" in error

    def test_token_with_no_expiry_rejected(self):
        """Test that tokens without expiry claim are rejected."""
        manager = JWTAuthManager(secret_key="test-secret")

        # Create token without exp claim
        payload = {
            "sub": "user-123",
            "user_id": "user-123",
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, manager.secret_key, algorithm="HS256")

        # Should be rejected (missing required 'exp' claim)
        valid, decoded, error = manager.validate_token(token)
        assert valid is False
        assert "Invalid token" in error

    def test_scope_validation_with_valid_token(self):
        """Test that scope validation works with valid token."""
        manager = JWTAuthManager(secret_key="test-secret")
        access_token, _ = manager.generate_token("user-123", scope="user")

        request = make_request(headers={"Authorization": f"Bearer {access_token}"})

        # Should pass with correct scope
        authorized, payload, error = manager.authorize_request(request, required_scope="user")
        assert authorized is True
        assert payload["scope"] == "user"

        # Should fail with different scope
        authorized, payload, error = manager.authorize_request(request, required_scope="admin")
        assert authorized is False
        assert "Insufficient permissions" in error

    def test_cleanup_removes_expired_tokens(self):
        """Test that cleanup removes expired tokens from blacklist."""
        manager = JWTAuthManager(
            secret_key="test-secret",
            token_expiry_hours=0,
            clock_skew_seconds=0
        )

        # Generate and revoke tokens
        token1, _ = manager.generate_token("user-1")
        token2, _ = manager.generate_token("user-2")

        manager.revoke_token(token1)
        manager.revoke_token(token2)

        assert manager.get_blacklist_size() == 2

        # Wait for tokens to expire
        time.sleep(0.1)

        # Cleanup should remove expired tokens
        removed = manager.cleanup_expired_tokens()
        assert removed == 2
        assert manager.get_blacklist_size() == 0

    def test_multiple_algorithm_not_allowed(self):
        """Test that tokens signed with different algorithms are rejected."""
        manager = JWTAuthManager(secret_key="test-secret", algorithm="HS256")

        # Create token with HS512
        payload = {
            "sub": "user-123",
            "user_id": "user-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        token = jwt.encode(payload, manager.secret_key, algorithm="HS512")

        # Should be rejected (algorithm mismatch)
        valid, decoded, error = manager.validate_token(token)
        assert valid is False
        assert "Invalid token" in error
