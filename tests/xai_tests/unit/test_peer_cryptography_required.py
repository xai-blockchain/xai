"""
Test that cryptography library is mandatory for PeerManager.

This test suite ensures the security requirement that the cryptography
library cannot be made optional or have fallback implementations.
"""
import sys
import os
import pytest
from unittest import mock


class TestCryptographyRequired:
    """Test that cryptography library is mandatory and fails fast."""

    def test_peer_encryption_fails_without_cryptography(self):
        """
        Test that PeerEncryption.__init__ fails fast when cryptography is unavailable.

        Security requirement: The P2P network must never run without TLS encryption.
        This test ensures that if the cryptography library is not available,
        the system fails immediately with a clear error message.
        """
        # Mock the module-level CRYPTOGRAPHY_AVAILABLE flag
        import xai.network.peer_manager as pm_module

        # Save original value
        original_available = pm_module.CRYPTOGRAPHY_AVAILABLE
        original_error = pm_module.CRYPTOGRAPHY_ERROR

        try:
            # Simulate missing cryptography library
            pm_module.CRYPTOGRAPHY_AVAILABLE = False
            pm_module.CRYPTOGRAPHY_ERROR = "No module named 'cryptography'"

            # Attempt to create PeerEncryption should fail
            with pytest.raises(ImportError) as exc_info:
                from xai.network.peer_manager import PeerEncryption
                PeerEncryption()

            # Verify error message contains helpful information
            error_message = str(exc_info.value)
            assert "cryptography" in error_message.lower()
            assert "pip install" in error_message.lower()
            assert "required" in error_message.lower()

        finally:
            # Restore original values
            pm_module.CRYPTOGRAPHY_AVAILABLE = original_available
            pm_module.CRYPTOGRAPHY_ERROR = original_error

    def test_peer_manager_fails_without_cryptography(self):
        """
        Test that PeerManager initialization fails when cryptography is unavailable.

        Security requirement: PeerManager uses PeerEncryption, which must fail
        if cryptography is not available.
        """
        import xai.network.peer_manager as pm_module

        # Save original value
        original_available = pm_module.CRYPTOGRAPHY_AVAILABLE
        original_error = pm_module.CRYPTOGRAPHY_ERROR

        try:
            # Simulate missing cryptography library
            pm_module.CRYPTOGRAPHY_AVAILABLE = False
            pm_module.CRYPTOGRAPHY_ERROR = "No module named 'cryptography'"

            # Attempt to create PeerManager should fail
            with pytest.raises(ImportError) as exc_info:
                from xai.network.peer_manager import PeerManager
                PeerManager()

            # Verify error message is helpful
            error_message = str(exc_info.value)
            assert "cryptography" in error_message.lower()
            assert "required" in error_message.lower()

        finally:
            # Restore original values
            pm_module.CRYPTOGRAPHY_AVAILABLE = original_available
            pm_module.CRYPTOGRAPHY_ERROR = original_error

    def test_no_placeholder_certificates_exist(self):
        """
        Test that the code does NOT create placeholder certificates.

        Security requirement: There must be no fallback path that creates
        placeholder/mock certificates when cryptography is unavailable.
        """
        from xai.network.peer_manager import PeerEncryption
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_dir = os.path.join(tmpdir, "certs")
            pe = PeerEncryption(cert_dir=cert_dir, key_dir=tmpdir)

            # Read the generated certificate
            with open(pe.cert_file, "rb") as f:
                cert_content = f.read()

            # Verify it's NOT a placeholder
            assert b"# Placeholder" not in cert_content
            assert b"placeholder" not in cert_content.lower()

            # Verify it's a real PEM certificate
            assert b"BEGIN CERTIFICATE" in cert_content
            assert b"END CERTIFICATE" in cert_content

            # Read the generated key
            with open(pe.key_file, "rb") as f:
                key_content = f.read()

            # Verify it's NOT a placeholder
            assert b"# Placeholder" not in key_content
            assert b"placeholder" not in key_content.lower()

            # Verify it's a real PEM key
            assert b"BEGIN" in key_content
            assert b"PRIVATE KEY" in key_content

    def test_certificate_validation_rejects_expired(self):
        """
        Test that validate_peer_certificate rejects expired certificates.

        Security requirement: The system must validate peer certificates
        and reject those that are expired.
        """
        from xai.network.peer_manager import PeerEncryption
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            pe = PeerEncryption(cert_dir=tmpdir, key_dir=tmpdir)

            # Create an expired certificate
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "test-expired"),
            ])

            # Create cert that expired yesterday
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow() - timedelta(days=365)
            ).not_valid_after(
                datetime.utcnow() - timedelta(days=1)  # Expired yesterday
            ).sign(private_key, hashes.SHA256())

            cert_bytes = cert.public_bytes(serialization.Encoding.PEM)

            # Validation should reject the expired certificate
            assert pe.validate_peer_certificate(cert_bytes) is False

    def test_certificate_validation_rejects_weak_keys(self):
        """
        Test that validate_peer_certificate rejects certificates with weak keys.

        Security requirement: Only accept RSA keys >= 2048 bits to prevent
        cryptographic attacks.
        """
        from xai.network.peer_manager import PeerEncryption
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            pe = PeerEncryption(cert_dir=tmpdir, key_dir=tmpdir)

            # Create a certificate with a weak 1024-bit key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=1024,  # Weak key size
            )

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "test-weak-key"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).sign(private_key, hashes.SHA256())

            cert_bytes = cert.public_bytes(serialization.Encoding.PEM)

            # Validation should reject the weak certificate
            assert pe.validate_peer_certificate(cert_bytes) is False

    def test_certificate_validation_accepts_valid_cert(self):
        """
        Test that validate_peer_certificate accepts valid certificates.

        Security requirement: Valid certificates with strong keys and proper
        validity periods should be accepted.
        """
        from xai.network.peer_manager import PeerEncryption
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            pe = PeerEncryption(cert_dir=tmpdir, key_dir=tmpdir)

            # Create a valid certificate with strong key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,  # Strong key size
            )

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "test-valid"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow() - timedelta(days=1)
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).sign(private_key, hashes.SHA256())

            cert_bytes = cert.public_bytes(serialization.Encoding.PEM)

            # Validation should accept the valid certificate
            assert pe.validate_peer_certificate(cert_bytes) is True

    def test_generated_certificate_has_secure_permissions(self):
        """
        Test that generated private keys have secure file permissions.

        Security requirement: Private key files must be readable only by owner
        to prevent unauthorized access.
        """
        from xai.network.peer_manager import PeerEncryption
        import tempfile
        import os
        import stat

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_dir = os.path.join(tmpdir, "certs")
            pe = PeerEncryption(cert_dir=cert_dir, key_dir=tmpdir)

            # Check private key file permissions
            key_stat = os.stat(pe.key_file)
            key_mode = stat.S_IMODE(key_stat.st_mode)

            # Should be 0o600 (read/write for owner only)
            assert key_mode == 0o600, f"Expected 0o600, got {oct(key_mode)}"

    def test_generated_certificate_uses_strong_key_size(self):
        """
        Test that self-generated certificates use strong RSA keys (2048 bits).

        Security requirement: All generated certificates must use industry-
        standard key sizes to prevent cryptographic attacks.
        """
        from xai.network.peer_manager import PeerEncryption
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_dir = os.path.join(tmpdir, "certs")
            pe = PeerEncryption(cert_dir=cert_dir, key_dir=tmpdir)

            # Read and parse the generated certificate
            with open(pe.cert_file, "rb") as f:
                cert_pem = f.read()

            cert = x509.load_pem_x509_certificate(cert_pem)
            public_key = cert.public_key()

            # Verify key size is at least 2048 bits
            assert hasattr(public_key, 'key_size')
            assert public_key.key_size >= 2048, \
                f"Key size {public_key.key_size} is below minimum 2048 bits"
