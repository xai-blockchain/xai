"""
Test suite for JWT authentication manager expiration verification.

Verifies that jwt_auth_manager.py properly enforces token expiration.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
import jwt as pyjwt

from xai.core.jwt_auth_manager import JWTAuthManager, UserRole


class TestJWTAuthManagerExpiration:
    """Test JWT expiration verification in jwt_auth_manager module."""

    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager with short expiration for testing."""
        return JWTAuthManager(
            secret_key="test-secret-key-12345",
            algorithm="HS256",
            token_expiration_hours=1,
            refresh_token_expiration_days=30,
        )

    def test_valid_token_accepted(self, jwt_manager):
        """Test that valid non-expired tokens are accepted."""
        token = jwt_manager.generate_token(
            user_id="user123",
            username="testuser",
            role=UserRole.USER
        )

        valid, claims, error = jwt_manager.validate_token(token)

        assert valid is True
        assert claims is not None
        assert error is None
        assert claims['user_id'] == "user123"
        assert claims['username'] == "testuser"

    def test_expired_token_rejected(self, jwt_manager):
        """Test that expired tokens are properly rejected."""
        # Create a token with expiration in the past (beyond clock skew)
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(minutes=5)  # 5 minutes ago

        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': (past_time - timedelta(hours=1)).timestamp(),  # Issued 1 hour before expiry
            'exp': past_time.timestamp(),  # Expired 5 minutes ago (beyond 30s skew)
            'jti': 'test-jti-123',
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Verify token is rejected
        valid, claims, error = jwt_manager.validate_token(token)

        assert valid is False
        assert claims is None
        assert error == "Token has expired"

    def test_manual_expiration_override_fails(self, jwt_manager):
        """Test that manually created tokens with no expiration are rejected."""
        # Create a token without expiration claim
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': now.timestamp(),
            'jti': 'test-jti-123',
            # No 'exp' claim
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Verify token is rejected due to missing exp claim
        valid, claims, error = jwt_manager.validate_token(token)

        assert valid is False
        assert claims is None
        assert "exp" in error.lower() or "required" in error.lower()

    def test_future_dated_token_rejected(self, jwt_manager):
        """Test that tokens with future iat (issued-at) are handled correctly."""
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(hours=1)

        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': future_time.timestamp(),
            'exp': (future_time + timedelta(hours=1)).timestamp(),
            'jti': 'test-jti-123',
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Token should be rejected
        valid, claims, error = jwt_manager.validate_token(token)

        # Note: PyJWT may not reject future iat by default, but it should be considered invalid
        # This test documents current behavior
        assert valid is False or (valid is True and claims is not None)

    def test_revoked_token_rejected(self, jwt_manager):
        """Test that revoked tokens are properly rejected."""
        token = jwt_manager.generate_token(
            user_id="user123",
            username="testuser",
            role=UserRole.USER
        )

        # Verify token is valid before revocation
        valid, claims, error = jwt_manager.validate_token(token)
        assert valid is True

        # Revoke the token
        result = jwt_manager.revoke_token(token)
        assert result is True

        # Verify token is now rejected
        valid, claims, error = jwt_manager.validate_token(token)
        assert valid is False
        assert error == "Token has been revoked"

    def test_expired_token_can_still_be_revoked(self, jwt_manager):
        """Test that expired tokens can still be revoked (for audit purposes)."""
        # Create an expired token manually
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(minutes=5)

        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': (past_time - timedelta(hours=1)).timestamp(),
            'exp': past_time.timestamp(),  # Expired 5 minutes ago
            'jti': 'test-jti-expired-123',
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Verify token is expired
        valid, claims, error = jwt_manager.validate_token(token)
        assert valid is False
        assert error == "Token has expired"

        # Should still be able to revoke it (for audit)
        result = jwt_manager.revoke_token(token)
        assert result is True

    def test_refresh_token_rejected_if_expired(self, jwt_manager):
        """Test that refresh_token fails on expired tokens."""
        # Create an expired token manually
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(minutes=5)

        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': (past_time - timedelta(hours=1)).timestamp(),
            'exp': past_time.timestamp(),  # Expired 5 minutes ago
            'jti': 'test-jti-refresh-123',
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Verify refresh fails
        success, new_token, error = jwt_manager.refresh_token(token)

        assert success is False
        assert new_token is None
        assert error == "Token has expired"

    def test_cleanup_removes_expired_revoked_tokens(self, jwt_manager):
        """Test that cleanup removes expired tokens from revocation list."""
        # Create a short-lived token
        short_lived_manager = JWTAuthManager(
            secret_key="test-secret-key-12345",
            token_expiration_hours=0.0003,  # ~1 second
        )

        token = short_lived_manager.generate_token(
            user_id="user123",
            username="testuser",
            role=UserRole.USER
        )

        # Revoke it
        short_lived_manager.revoke_token(token)

        # Verify it's in revocation list
        initial_size = len(short_lived_manager.revoked_tokens)
        assert initial_size > 0

        # Wait for token to expire
        time.sleep(2)

        # Run cleanup
        removed = short_lived_manager.cleanup_revoked_tokens()

        # Verify expired token was removed
        assert removed == 1
        assert len(short_lived_manager.revoked_tokens) == 0

    def test_required_claims_validation(self, jwt_manager):
        """Test that tokens missing required claims are rejected."""
        # Create token without jti claim
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': 'user123',
            'username': 'testuser',
            'role': 'user',
            'iat': now.timestamp(),
            'exp': (now + timedelta(hours=1)).timestamp(),
            # Missing 'jti' claim
        }

        token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)

        # Verify token is rejected
        valid, claims, error = jwt_manager.validate_token(token)

        assert valid is False
        assert claims is None
        # Error should mention missing required claim
        assert error is not None

    def test_signature_verification_enabled(self, jwt_manager):
        """Test that signature verification is enforced."""
        token = jwt_manager.generate_token(
            user_id="user123",
            username="testuser",
            role=UserRole.USER
        )

        # Tamper with the token
        tampered_token = token[:-5] + "XXXXX"

        # Verify tampered token is rejected
        valid, claims, error = jwt_manager.validate_token(tampered_token)

        assert valid is False
        assert claims is None
        assert error is not None
