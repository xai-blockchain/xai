"""
Security tests for Wallet API - Private Key Exposure Prevention

This test suite verifies that the /wallet/create endpoint NEVER exposes
private keys in plain text HTTP responses.

Critical Security Requirements:
1. NO private keys in HTTP response bodies
2. Encrypted keystores only, with strong passwords required
3. Client-side decryption enforced
4. Comprehensive logging of security events
"""

import pytest
import json
from flask import Flask
from unittest.mock import Mock, patch

from xai.core.api_wallet import WalletAPIHandler
from xai.core.wallet import Wallet


@pytest.fixture
def flask_app():
    """Create Flask test application"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def mock_node():
    """Create mock blockchain node"""
    node = Mock()
    node.blockchain = Mock()
    node.blockchain.trade_manager = Mock()
    node.blockchain.trade_manager.snapshot = Mock(return_value={"orders": [], "matches": []})
    node.blockchain.trade_manager.audit_signer = Mock()
    node.blockchain.trade_manager.audit_signer.public_key = Mock(return_value="mock_key")
    node.blockchain.trade_manager.signed_event_batch = Mock(return_value=[])
    node.blockchain.get_trade_orders = Mock(return_value=[])
    node.blockchain.get_trade_matches = Mock(return_value=[])
    return node


@pytest.fixture
def wallet_api_handler(flask_app, mock_node):
    """Create WalletAPIHandler instance"""
    handler = WalletAPIHandler(
        node=mock_node,
        app=flask_app,
        broadcast_callback=Mock(),
        trade_peers={}
    )
    return handler


@pytest.fixture
def test_client(flask_app, wallet_api_handler):
    """Create Flask test client"""
    return flask_app.test_client()


class TestPrivateKeySecurityWalletCreate:
    """
    Test suite ensuring /wallet/create NEVER returns private keys in plain text.

    This is a CRITICAL security requirement. Any test failure here indicates
    a severe vulnerability that would expose user funds.
    """

    def test_wallet_create_requires_password(self, test_client):
        """CRITICAL: Wallet creation must require encryption password"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({}),
            content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data["success"] is False
        assert "encryption_password required" in data["error"]
        assert "documentation" in data

    def test_wallet_create_rejects_weak_password(self, test_client):
        """CRITICAL: Must reject passwords shorter than 12 characters"""
        weak_passwords = ["", "short", "abc123", "password1"]

        for weak_password in weak_passwords:
            response = test_client.post(
                "/wallet/create",
                data=json.dumps({"encryption_password": weak_password}),
                content_type="application/json"
            )

            assert response.status_code == 400, f"Failed to reject weak password: {weak_password}"
            data = json.loads(response.data)

            assert data["success"] is False
            assert "weak_password" in data["error"] or "encryption_password required" in data["error"]

    def test_wallet_create_never_returns_private_key(self, test_client):
        """
        CRITICAL SECURITY TEST: Verify private key is NEVER in response.

        This is the main security vulnerability being fixed. The response must
        NEVER contain a "private_key" field in plain text.
        """
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "StrongPassword123!@#"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        # CRITICAL: Verify NO private key in response
        assert "private_key" not in data, "SECURITY VIOLATION: private_key found in response!"

        # Verify encrypted keystore is present instead
        assert "encrypted_keystore" in data
        assert "success" in data
        assert data["success"] is True

    def test_wallet_create_returns_encrypted_keystore(self, test_client):
        """Verify encrypted keystore structure is correct"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "VeryStrongPassword123!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        # Verify encrypted keystore has correct structure
        encrypted_keystore = data["encrypted_keystore"]
        assert "ciphertext" in encrypted_keystore
        assert "nonce" in encrypted_keystore
        assert "salt" in encrypted_keystore

        # Verify all components are base64-encoded strings
        assert isinstance(encrypted_keystore["ciphertext"], str)
        assert isinstance(encrypted_keystore["nonce"], str)
        assert isinstance(encrypted_keystore["salt"], str)
        assert len(encrypted_keystore["ciphertext"]) > 0
        assert len(encrypted_keystore["nonce"]) > 0
        assert len(encrypted_keystore["salt"]) > 0

    def test_wallet_create_returns_public_data(self, test_client):
        """Verify public data (address, public_key) is still returned"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "SecurePassword456!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        # Public data should be present
        assert "address" in data
        assert "public_key" in data

        # Verify format
        assert data["address"].startswith("XAI")
        assert len(data["public_key"]) > 0

    def test_wallet_create_includes_security_warnings(self, test_client):
        """Verify security warnings and instructions are included"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "AnotherStrongPass1!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        # Verify security guidance is included
        assert "instructions" in data
        assert "warning" in data
        assert "client_decryption_guide" in data

        # Verify warnings contain critical security messages
        warning = data["warning"].lower()
        assert "never share" in warning or "never" in warning
        assert "password" in warning or "private key" in warning

    def test_encrypted_keystore_can_be_decrypted(self, test_client):
        """Verify the encrypted keystore can be decrypted with the password"""
        password = "TestDecryptionPassword123!"

        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": password}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        encrypted_keystore = data["encrypted_keystore"]

        # Attempt to decrypt using Wallet's _decrypt_payload_static method
        try:
            decrypted_json = Wallet._decrypt_payload_static(encrypted_keystore, password)
            wallet_data = json.loads(decrypted_json)

            # Verify decrypted data contains expected fields
            assert "private_key" in wallet_data
            assert "public_key" in wallet_data
            assert "address" in wallet_data

            # Verify address matches
            assert wallet_data["address"] == data["address"]

        except Exception as e:
            pytest.fail(f"Failed to decrypt keystore: {e}")

    def test_encrypted_keystore_cannot_be_decrypted_with_wrong_password(self, test_client):
        """Verify wrong password fails to decrypt"""
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword456!"

        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": correct_password}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        encrypted_keystore = data["encrypted_keystore"]

        # Attempt to decrypt with wrong password should fail
        with pytest.raises((ValueError, Exception)):
            Wallet._decrypt_payload_static(encrypted_keystore, wrong_password)

    def test_multiple_wallet_creations_unique_keystores(self, test_client):
        """Verify each wallet creation produces unique encrypted keystores"""
        password = "SamePasswordForAll123!"

        responses = []
        for _ in range(3):
            response = test_client.post(
                "/wallet/create",
                data=json.dumps({"encryption_password": password}),
                content_type="application/json"
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 201

        # Extract encrypted keystores
        keystores = [json.loads(r.data)["encrypted_keystore"]["ciphertext"] for r in responses]

        # All should be different (different wallets, different ciphertexts)
        assert len(set(keystores)) == 3, "Encrypted keystores should be unique"

    def test_wallet_create_http_status_code(self, test_client):
        """Verify correct HTTP status code (201 Created)"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "StatusCodeTest123!"}),
            content_type="application/json"
        )

        # Should return 201 Created, not 200 OK
        assert response.status_code == 201

    def test_password_not_logged_or_exposed(self, test_client):
        """Verify password is never logged or exposed in response"""
        password = "SecretPassword123!"

        with patch("xai.core.api_wallet.logger") as mock_logger:
            response = test_client.post(
                "/wallet/create",
                data=json.dumps({"encryption_password": password}),
                content_type="application/json"
            )

            assert response.status_code == 201
            data = json.loads(response.data)

            # Verify password is not in response
            response_json = json.dumps(data)
            assert password not in response_json, "Password exposed in response!"

            # Verify password is not in logged messages
            for call in mock_logger.info.call_args_list + mock_logger.warning.call_args_list:
                log_message = str(call)
                assert password not in log_message, "Password exposed in logs!"


class TestOtherAPIEndpointsNoPrivateKeyExposure:
    """
    Verify other API endpoints do not expose private keys either.

    This ensures the vulnerability fix is comprehensive across all endpoints.
    """

    def test_sign_transaction_accepts_but_not_returns_private_key(self, test_client):
        """
        /wallet/sign endpoint must accept private key in request (for signing)
        but must NEVER echo it back in the response.
        """
        # Note: This endpoint is designed for client-side signing and should
        # accept private keys over HTTPS, but must not return them.

        from xai.core.crypto_utils import generate_secp256k1_keypair_hex
        import hashlib

        priv, pub = generate_secp256k1_keypair_hex()
        message = "test message"
        message_hash = hashlib.sha256(message.encode()).hexdigest()

        response = test_client.post(
            "/wallet/sign",
            data=json.dumps({
                "message_hash": message_hash,
                "private_key": priv,
                "ack_hash_prefix": message_hash[:8]
            }),
            content_type="application/json"
        )

        data = json.loads(response.data)

        # CRITICAL: Verify private key is NOT in response
        assert "private_key" not in data, "SECURITY VIOLATION: private_key in sign response!"

        # Should only contain signature
        if response.status_code == 200:
            assert "signature" in data

    def test_derive_public_key_not_return_private_key(self, test_client):
        """
        /wallet/derive-public-key must accept private key but not return it.
        """
        from xai.core.crypto_utils import generate_secp256k1_keypair_hex

        priv, _ = generate_secp256k1_keypair_hex()

        response = test_client.post(
            "/wallet/derive-public-key",
            data=json.dumps({"private_key": priv}),
            content_type="application/json"
        )

        data = json.loads(response.data)

        # CRITICAL: Verify private key is NOT in response
        assert "private_key" not in data, "SECURITY VIOLATION: private_key in derive response!"

        # Should only contain public key
        if response.status_code == 200:
            assert "public_key" in data


class TestSecurityDocumentation:
    """Verify security documentation and error messages are helpful"""

    def test_error_messages_include_documentation_links(self, test_client):
        """Error responses should guide users to security documentation"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({}),
            content_type="application/json"
        )

        data = json.loads(response.data)

        assert "documentation" in data or "client_decryption_guide" in data

    def test_success_response_includes_decryption_guide(self, test_client):
        """Success responses should include decryption guidance"""
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "GuideTestPassword123!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        assert "client_decryption_guide" in data
        assert isinstance(data["client_decryption_guide"], str)
        assert len(data["client_decryption_guide"]) > 0


class TestRegressionPrivateKeyExposure:
    """
    Regression tests to ensure the vulnerability stays fixed.

    These tests explicitly check for the original vulnerability pattern.
    """

    def test_no_plain_text_private_key_in_any_response_field(self, test_client):
        """
        Comprehensive check: Ensure NO field in the response contains a plain private key.

        This test would have FAILED before the fix.
        """
        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "RegressionTest123!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        # Recursively check all fields
        def check_no_private_key(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # The field name "private_key" should not exist
                    assert key != "private_key", f"Found 'private_key' field at {path}.{key}"
                    check_no_private_key(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_private_key(item, f"{path}[{i}]")

        check_no_private_key(data)

    def test_encrypted_keystore_not_obviously_decodable(self, test_client):
        """
        Verify the encrypted keystore is not just base64-encoded plaintext.

        A common mistake is to "encrypt" by just base64 encoding. This test
        ensures actual encryption is used.
        """
        import base64

        response = test_client.post(
            "/wallet/create",
            data=json.dumps({"encryption_password": "EncryptionTest123!"}),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)

        encrypted_keystore = data["encrypted_keystore"]
        ciphertext = encrypted_keystore["ciphertext"]

        # Try to decode as base64 and check if it's JSON (would indicate weak encoding)
        try:
            decoded = base64.b64decode(ciphertext)
            # If it decodes to valid JSON, it's probably just encoded, not encrypted
            try:
                json.loads(decoded)
                pytest.fail("Ciphertext appears to be just base64-encoded JSON, not encrypted!")
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Good - it's not readable JSON after base64 decode
                pass
        except Exception:
            # Good - can't even decode as base64 (though it should be base64)
            pass
