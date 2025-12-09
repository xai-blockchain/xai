"""
Unit tests for TwoFactorAuthManager.

Coverage targets:
- Setup flow produces secret/URI/backup codes
- TOTP generation/verification with valid window
- Backup code verification and removal
"""

import pytest

from xai.security.two_factor_auth import TwoFactorAuthManager


def test_setup_generates_artifacts():
    manager = TwoFactorAuthManager()
    setup = manager.setup_2fa("user1", user_email="user@example.com")
    assert setup.secret
    assert "otpauth://" in setup.provisioning_uri
    assert len(setup.backup_codes) == manager.num_backup_codes
    assert setup.qr_code_url.startswith("otpauth://totp")


def test_totp_generate_and_verify():
    manager = TwoFactorAuthManager(time_window=30)
    setup = manager.setup_2fa("user1")
    code = manager.generate_totp(setup.secret)
    assert manager.verify_totp(setup.secret, code) is True
    assert manager.verify_totp(setup.secret, "000000") is False


def test_backup_code_verification():
    manager = TwoFactorAuthManager()
    backup_codes = manager._generate_backup_codes()
    hashed = manager.hash_backup_codes(backup_codes)

    is_valid, updated = manager.verify_backup_code(backup_codes[0], hashed)
    assert is_valid is True
    assert len(updated) == len(hashed) - 1

    # Invalid code
    is_valid, updated = manager.verify_backup_code("WRONG-CODE", hashed)
    assert is_valid is False
    assert updated is None
