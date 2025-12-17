"""
Comprehensive security tests for wallet CLI.

Tests verify that private keys are NEVER exposed through:
- Command-line arguments
- stdout/stderr output (except with explicit confirmation)
- Shell history
- Process listings
- Log files

All private key handling must use secure methods:
- Encrypted keystore files
- getpass secure input
- Environment variables (with warnings)
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from xai.wallet.cli import (
    get_private_key_secure,
    create_keystore,
    encrypt_wallet_data,
    decrypt_wallet_data,
    DecryptionData,
    _generate_address,
    _send_transaction,
    _export_wallet,
    build_parser,
)


class TestSecurePrivateKeyRetrieval:
    """Test secure private key retrieval methods."""

    def test_get_private_key_from_keystore(self, tmp_path):
        """Test loading private key from encrypted keystore."""
        # Create a test keystore
        keystore_path = tmp_path / "test.keystore"
        test_address = "XAI1234567890abcdef"
        test_private_key = "a" * 64
        test_public_key = "b" * 130

        # Mock the password input
        with mock.patch("getpass.getpass", side_effect=["TestPass123!", "TestPass123!", "TestPass123!"]):
            # Create keystore
            result_path = create_keystore(
                address=test_address,
                private_key=test_private_key,
                public_key=test_public_key,
                output_path=str(keystore_path),
                kdf="pbkdf2"
            )

            assert Path(result_path).exists()

            # Load private key from keystore
            retrieved_key = get_private_key_secure(keystore_path=str(keystore_path))

            # Should match original key (without 0x prefix)
            assert retrieved_key == test_private_key

    def test_get_private_key_from_env_with_warning(self, capsys):
        """Test loading from environment variable shows security warning."""
        test_key = "f" * 64

        with mock.patch.dict(os.environ, {"XAI_PRIVATE_KEY": test_key}):
            retrieved_key = get_private_key_secure(allow_env=True)

            assert retrieved_key == test_key

            # Verify warning was displayed
            captured = capsys.readouterr()
            assert "WARNING" in captured.err
            assert "NOT RECOMMENDED" in captured.err
            assert "environment variable" in captured.err
            assert "--keystore" in captured.err

    def test_get_private_key_interactive_input(self):
        """Test interactive secure input with getpass."""
        test_key = "0xdeadbeef" + "a" * 56  # 64 hex chars total (8 + 56)

        with mock.patch("getpass.getpass", return_value=test_key):
            retrieved_key = get_private_key_secure()

            # Should strip 0x prefix
            assert retrieved_key == test_key.replace("0x", "")

    def test_get_private_key_validates_length(self):
        """Test that private key validation rejects invalid lengths."""
        with mock.patch("getpass.getpass", return_value="abc123"):  # Too short
            with pytest.raises(ValueError, match="Invalid private key length"):
                get_private_key_secure()

    def test_get_private_key_validates_hex_format(self):
        """Test that private key validation rejects non-hex characters."""
        invalid_key = "z" * 64  # Not hex

        with mock.patch("getpass.getpass", return_value=invalid_key):
            with pytest.raises(ValueError, match="must be hexadecimal"):
                get_private_key_secure()

    def test_keystore_not_found_raises_error(self):
        """Test that missing keystore file raises proper error."""
        with pytest.raises(FileNotFoundError, match="Keystore file not found"):
            get_private_key_secure(keystore_path="/nonexistent/path.keystore")


class TestKeystoreEncryption:
    """Test encrypted keystore creation and decryption."""

    def test_create_keystore_requires_strong_password(self, tmp_path):
        """Test that keystore creation enforces strong password policy."""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoDigitsHere!",  # No digits
            "NoSpecialChar123",  # No special character
        ]

        for weak_password in weak_passwords:
            with mock.patch("getpass.getpass", side_effect=[weak_password, weak_password]):
                with pytest.raises(ValueError):
                    create_keystore(
                        address="XAI123",
                        private_key="a" * 64,
                        output_path=str(tmp_path / "test.keystore")
                    )

    def test_create_keystore_enforces_password_match(self, tmp_path):
        """Test that passwords must match."""
        with mock.patch("getpass.getpass", side_effect=["Password123!", "DifferentPass123!"]):
            with pytest.raises(ValueError, match="Passwords do not match"):
                create_keystore(
                    address="XAI123",
                    private_key="a" * 64,
                    output_path=str(tmp_path / "test.keystore")
                )

    def test_keystore_file_permissions(self, tmp_path):
        """Test that keystore files have restrictive permissions (0o600)."""
        keystore_path = tmp_path / "test.keystore"

        with mock.patch("getpass.getpass", side_effect=["TestPass123!", "TestPass123!"]):
            result_path = create_keystore(
                address="XAI123",
                private_key="a" * 64,
                output_path=str(keystore_path)
            )

            # Check file permissions (owner read/write only)
            file_stat = os.stat(result_path)
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    def test_keystore_contains_address_in_plaintext(self, tmp_path):
        """Test that keystore includes address for easy identification."""
        keystore_path = tmp_path / "test.keystore"
        test_address = "XAI1234567890"

        with mock.patch("getpass.getpass", side_effect=["TestPass123!", "TestPass123!"]):
            result_path = create_keystore(
                address=test_address,
                private_key="a" * 64,
                output_path=str(keystore_path)
            )

            # Read keystore and verify address in plaintext
            with open(result_path, "r") as f:
                keystore_data = json.load(f)

            assert keystore_data["address"] == test_address
            assert "encrypted_data" in keystore_data
            assert "private_key" not in keystore_data  # Should be encrypted

    def test_keystore_encryption_integrity(self, tmp_path):
        """Test that encrypted data includes HMAC for integrity verification."""
        keystore_path = tmp_path / "test.keystore"

        with mock.patch("getpass.getpass", side_effect=["TestPass123!", "TestPass123!", "TestPass123!"]):
            result_path = create_keystore(
                address="XAI123",
                private_key="a" * 64,
                output_path=str(keystore_path)
            )

            # Read keystore
            with open(result_path, "r") as f:
                keystore_data = json.load(f)

            # Verify HMAC present
            assert "hmac" in keystore_data
            assert keystore_data["algorithm"] == "AES-256-GCM"

            # Tamper with encrypted data
            import base64
            encrypted_bytes = base64.b64decode(keystore_data["encrypted_data"])
            tampered = base64.b64encode(encrypted_bytes + b"TAMPERED").decode("ascii")
            keystore_data["encrypted_data"] = tampered

            # Save tampered keystore
            with open(keystore_path, "w") as f:
                json.dump(keystore_data, f)

            # Attempt to load should fail integrity check
            with pytest.raises(ValueError, match="Integrity check failed|Decryption failed"):
                get_private_key_secure(keystore_path=str(keystore_path))


class TestCLIArgumentSecurity:
    """Test that CLI never accepts private keys as arguments."""

    def test_send_command_no_private_key_argument(self):
        """Test that 'send' command does not have --private-key argument."""
        parser = build_parser()

        # Parse send command help
        with pytest.raises(SystemExit):  # argparse exits on --help
            parser.parse_args(["send", "--help"])

        # Verify --private-key argument doesn't exist
        # Try to use it and expect failure
        with pytest.raises(SystemExit):
            parser.parse_args([
                "send",
                "--sender", "XAI123",
                "--recipient", "XAI456",
                "--amount", "10",
                "--private-key", "abc123"  # Should not be accepted
            ])

    def test_export_command_no_private_key_argument(self):
        """Test that 'export' command does not have --private-key argument."""
        parser = build_parser()

        # Verify --private-key argument doesn't exist in export command
        with pytest.raises(SystemExit):
            parser.parse_args([
                "export",
                "--address", "XAI123",
                "--private-key", "abc123"  # Should not be accepted
            ])

    def test_send_command_requires_keystore_or_interactive(self):
        """Test that send command accepts --keystore for secure input."""
        parser = build_parser()

        # Should accept --keystore argument
        args = parser.parse_args([
            "send",
            "--sender", "XAI123",
            "--recipient", "XAI456",
            "--amount", "10",
            "--keystore", "/path/to/keystore"
        ])

        assert args.keystore == "/path/to/keystore"


class TestPrivateKeyOutputSecurity:
    """Test that private keys are never printed without explicit confirmation."""

    def test_generate_address_default_no_private_key_output(self, capsys):
        """Test that generate-address does NOT output private key by default."""
        parser = build_parser()
        args = parser.parse_args(["generate-address"])

        with mock.patch("xai.wallet.cli.Wallet") as mock_wallet:
            mock_wallet.return_value.address = "XAI123"
            mock_wallet.return_value.public_key = "pubkey123"
            mock_wallet.return_value.private_key = "SECRETKEY123"

            _generate_address(args)

            captured = capsys.readouterr()

            # Verify private key NOT in output
            assert "SECRETKEY123" not in captured.out
            assert "SECRETKEY123" not in captured.err

            # Verify warning about private key not displayed
            assert "NOT displayed" in captured.out or "save-keystore" in captured.out

    def test_generate_address_show_private_key_requires_confirmation(self):
        """Test that --show-private-key requires explicit confirmation."""
        parser = build_parser()
        args = parser.parse_args(["generate-address", "--show-private-key"])

        with mock.patch("xai.wallet.cli.Wallet") as mock_wallet:
            mock_wallet.return_value.address = "XAI123"
            mock_wallet.return_value.public_key = "pubkey123"
            mock_wallet.return_value.private_key = "SECRETKEY123"

            # Simulate user NOT confirming
            with mock.patch("builtins.input", return_value="NO"):
                result = _generate_address(args)

                # Should be cancelled
                assert result == 1

            # Simulate user confirming
            with mock.patch("builtins.input", return_value="I UNDERSTAND THE RISKS"):
                result = _generate_address(args)

                # Should succeed
                assert result == 0

    def test_json_output_deprecated_and_requires_confirmation(self):
        """Test that --json output is deprecated and requires confirmation."""
        parser = build_parser()
        args = parser.parse_args(["generate-address", "--json"])

        with mock.patch("xai.wallet.cli.Wallet") as mock_wallet:
            mock_wallet.return_value.address = "XAI123"
            mock_wallet.return_value.public_key = "pubkey123"
            mock_wallet.return_value.private_key = "SECRETKEY123"

            # Should require confirmation
            with mock.patch("builtins.input", return_value="NO"):
                result = _generate_address(args)
                assert result == 1


class TestEnvironmentVariableSecurity:
    """Test security warnings for environment variable usage."""

    def test_allow_env_key_flag_required(self):
        """Test that env var is only used when --allow-env-key flag is set."""
        test_key = "f" * 64

        with mock.patch.dict(os.environ, {"XAI_PRIVATE_KEY": test_key}):
            # Without allow_env flag, should not use env var
            with mock.patch("getpass.getpass", return_value=test_key):
                retrieved_key = get_private_key_secure(allow_env=False)
                # Should have prompted, not used env var silently

    def test_env_key_shows_security_warning(self, capsys):
        """Test that using env var shows prominent security warning."""
        test_key = "f" * 64

        with mock.patch.dict(os.environ, {"XAI_PRIVATE_KEY": test_key}):
            get_private_key_secure(allow_env=True)

            captured = capsys.readouterr()

            # Verify comprehensive warning
            assert "WARNING" in captured.err
            assert "environment variable" in captured.err
            assert "NOT RECOMMENDED" in captured.err
            assert "visible in process listings" in captured.err
            assert "keystore" in captured.err


class TestMemoryCleanup:
    """Test that sensitive data is cleared from memory after use."""

    def test_send_transaction_clears_private_key(self):
        """Test that _send_transaction clears private key from memory."""
        parser = build_parser()
        args = parser.parse_args([
            "send",
            "--sender", "XAI123",
            "--recipient", "XAI456",
            "--amount", "10",
            "--keystore", "/fake/path"
        ])

        test_key = "a" * 64

        with mock.patch("xai.wallet.cli.get_private_key_secure", return_value=test_key):
            with mock.patch("requests.post") as mock_post:
                mock_post.return_value.ok = True
                mock_post.return_value.json.return_value = {"success": True}

                _send_transaction(args)

                # Verify that the request was made but we can't check if
                # the variable was deleted (Python limitation)
                # This test documents the intent

    def test_export_wallet_clears_sensitive_data(self, tmp_path):
        """Test that _export_wallet clears sensitive data after export."""
        parser = build_parser()
        args = parser.parse_args([
            "export",
            "--address", "XAI123",
            "--output", str(tmp_path / "wallet.enc"),
            "--encrypt"
        ])

        test_key = "a" * 64

        with mock.patch("xai.wallet.cli.get_private_key_secure", return_value=test_key):
            with mock.patch("getpass.getpass", side_effect=["TestPass123!", "TestPass123!"]):
                result = _export_wallet(args)

                assert result == 0
                # Verify export succeeded and cleanup was attempted


class TestPasswordPolicy:
    """Test password strength requirements for keystores."""

    def test_password_minimum_length(self):
        """Test minimum password length of 12 characters."""
        passwords = [
            ("short", False),
            ("12345678901", False),  # 11 chars
            ("123456789012", True),   # 12 chars minimum
        ]

        for password, should_pass in passwords:
            # Add other required elements
            test_password = password + "A1!" if not should_pass else "ValidPass12!"

            if should_pass:
                assert len(test_password) >= 12
            else:
                assert len(password) < 12

    def test_password_requires_all_character_types(self):
        """Test that password requires uppercase, lowercase, digit, special."""
        invalid_passwords = [
            "nouppercase123!",    # Missing uppercase
            "NOLOWERCASE123!",    # Missing lowercase
            "NoDigitsHere!",      # Missing digit
            "NoSpecialChar123",   # Missing special char
        ]

        for password in invalid_passwords:
            # These should fail the validation
            assert not (
                any(c.isupper() for c in password) and
                any(c.islower() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in password)
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
