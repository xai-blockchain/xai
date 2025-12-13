"""
Comprehensive tests for NIST Post-Quantum Cryptography implementation.

Tests cover:
- ML-DSA (CRYSTALS-Dilithium) signatures
- Falcon signatures
- SPHINCS+ signatures
- ML-KEM (CRYSTALS-Kyber) key encapsulation
- Hybrid classical + quantum schemes
- Key serialization/deserialization
- Error handling and edge cases
"""

import pytest
import json
import base64
from src.xai.security.quantum_resistant_crypto import (
    QuantumResistantCryptoManager,
    PQCAlgorithm,
    PQCKeyPair,
    HybridKeyPair
)


@pytest.mark.security
class TestMLDSASignatures:
    """Test ML-DSA (CRYSTALS-Dilithium) signature algorithms"""

    def test_ml_dsa_65_keypair_generation(self):
        """Test ML-DSA-65 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        assert keypair.algorithm == "ML-DSA-65"
        assert len(keypair.public_key) == 1952
        assert len(keypair.private_key) == 4032
        assert keypair.key_id is not None
        assert keypair.metadata["security_level"] == 192
        assert keypair.metadata["nist_standard"] == "FIPS 204"

    def test_ml_dsa_87_keypair_generation(self):
        """Test ML-DSA-87 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_87)

        assert keypair.algorithm == "ML-DSA-87"
        assert keypair.metadata["security_level"] == 256
        assert keypair.metadata["nist_standard"] == "FIPS 204"

    def test_ml_dsa_sign_and_verify(self):
        """Test ML-DSA signing and verification"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Test message for ML-DSA signature"

        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        assert len(signature) == 3309
        assert crypto.verify(keypair.public_key, message, signature, PQCAlgorithm.ML_DSA_65)

    def test_ml_dsa_invalid_signature(self):
        """Test ML-DSA with invalid signature"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Test message"
        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        # Modify signature
        invalid_sig = bytearray(signature)
        invalid_sig[0] ^= 0xFF
        invalid_sig = bytes(invalid_sig)

        assert not crypto.verify(keypair.public_key, message, invalid_sig, PQCAlgorithm.ML_DSA_65)

    def test_ml_dsa_wrong_message(self):
        """Test ML-DSA with wrong message"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Original message"
        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        wrong_message = b"Wrong message"
        assert not crypto.verify(keypair.public_key, wrong_message, signature, PQCAlgorithm.ML_DSA_65)


@pytest.mark.security
class TestFalconSignatures:
    """Test Falcon signature algorithms"""

    def test_falcon_512_keypair_generation(self):
        """Test Falcon-512 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.FALCON_512)

        assert keypair.algorithm == "Falcon-512"
        assert len(keypair.public_key) == 897
        assert len(keypair.private_key) == 1281
        assert keypair.metadata["security_level"] == 128
        assert keypair.metadata["nist_standard"] == "NIST Selected"

    def test_falcon_1024_keypair_generation(self):
        """Test Falcon-1024 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.FALCON_1024)

        assert keypair.algorithm == "Falcon-1024"
        assert keypair.metadata["security_level"] == 256
        assert keypair.metadata["nist_standard"] == "NIST Selected"

    def test_falcon_sign_and_verify(self):
        """Test Falcon signing and verification"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.FALCON_512)
        message = b"Test message for Falcon signature"

        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.FALCON_512)

        # Falcon has variable-size signatures, max 752
        assert len(signature) <= 752
        assert crypto.verify(keypair.public_key, message, signature, PQCAlgorithm.FALCON_512)

    def test_falcon_compact_signatures(self):
        """Test that Falcon produces compact signatures"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.FALCON_512)
        message = b"Short message"

        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.FALCON_512)

        # Falcon signatures should be more compact than ML-DSA
        assert len(signature) < 1000


@pytest.mark.security
class TestSPHINCSSignatures:
    """Test SPHINCS+ signature algorithms"""

    def test_sphincs_128f_keypair_generation(self):
        """Test SPHINCS+-SHA2-128f key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)

        assert keypair.algorithm == "SPHINCS+-SHA2-128f"
        assert len(keypair.public_key) == 32  # Very small public key
        assert len(keypair.private_key) == 64  # Very small private key
        assert keypair.metadata["security_level"] == 128
        assert keypair.metadata["nist_standard"] == "FIPS 205"

    def test_sphincs_256f_keypair_generation(self):
        """Test SPHINCS+-SHA2-256f key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_256F)

        assert keypair.algorithm == "SPHINCS+-SHA2-256f"
        assert keypair.metadata["security_level"] == 256
        assert keypair.metadata["nist_standard"] == "FIPS 205"

    def test_sphincs_sign_and_verify(self):
        """Test SPHINCS+ signing and verification"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)
        message = b"Test message for SPHINCS+ signature"

        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.SPHINCS_SHA2_128F)

        assert len(signature) == 17088  # Large signature size
        assert crypto.verify(keypair.public_key, message, signature, PQCAlgorithm.SPHINCS_SHA2_128F)

    def test_sphincs_minimal_keys(self):
        """Test that SPHINCS+ has minimal key sizes"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)

        # SPHINCS+ has the smallest keys
        assert len(keypair.public_key) == 32
        assert len(keypair.private_key) == 64


@pytest.mark.security
class TestMLKEMEncapsulation:
    """Test ML-KEM (CRYSTALS-Kyber) key encapsulation"""

    def test_ml_kem_768_keypair_generation(self):
        """Test ML-KEM-768 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_kem_keypair(PQCAlgorithm.ML_KEM_768)

        assert keypair.algorithm == "ML-KEM-768"
        assert len(keypair.public_key) == 1184
        assert len(keypair.private_key) == 2400
        assert keypair.metadata["security_level"] == 192
        assert keypair.metadata["nist_standard"] == "FIPS 203"
        assert keypair.metadata["ciphertext_size"] == 1088
        assert keypair.metadata["shared_secret_size"] == 32

    def test_ml_kem_1024_keypair_generation(self):
        """Test ML-KEM-1024 key pair generation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_kem_keypair(PQCAlgorithm.ML_KEM_1024)

        assert keypair.algorithm == "ML-KEM-1024"
        assert keypair.metadata["security_level"] == 256
        assert keypair.metadata["nist_standard"] == "FIPS 203"

    def test_ml_kem_encapsulation_decapsulation(self):
        """Test ML-KEM key encapsulation and decapsulation"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_kem_keypair(PQCAlgorithm.ML_KEM_768)

        # Encapsulate
        ciphertext, shared_secret_enc = crypto.kem_encapsulate(
            keypair.public_key, PQCAlgorithm.ML_KEM_768
        )

        # Decapsulate
        shared_secret_dec = crypto.kem_decapsulate(
            keypair.private_key, ciphertext, PQCAlgorithm.ML_KEM_768
        )

        assert len(ciphertext) == 1088
        assert len(shared_secret_enc) == 32
        assert len(shared_secret_dec) == 32
        assert shared_secret_enc == shared_secret_dec

    def test_ml_kem_multiple_encapsulations(self):
        """Test that multiple encapsulations produce different ciphertexts"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_kem_keypair(PQCAlgorithm.ML_KEM_768)

        ct1, ss1 = crypto.kem_encapsulate(keypair.public_key, PQCAlgorithm.ML_KEM_768)
        ct2, ss2 = crypto.kem_encapsulate(keypair.public_key, PQCAlgorithm.ML_KEM_768)

        # Different ciphertexts and shared secrets
        assert ct1 != ct2
        assert ss1 != ss2

        # Both can be decapsulated correctly
        assert ss1 == crypto.kem_decapsulate(keypair.private_key, ct1, PQCAlgorithm.ML_KEM_768)
        assert ss2 == crypto.kem_decapsulate(keypair.private_key, ct2, PQCAlgorithm.ML_KEM_768)


@pytest.mark.security
class TestHybridSchemes:
    """Test hybrid classical + quantum schemes"""

    def test_hybrid_keypair_generation(self):
        """Test hybrid key pair generation"""
        crypto = QuantumResistantCryptoManager()
        hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)

        assert hybrid_kp.algorithm == "Hybrid-ML-DSA-65"
        assert hybrid_kp.key_id is not None
        assert len(hybrid_kp.classical_private) > 0
        assert len(hybrid_kp.classical_public) > 0
        assert len(hybrid_kp.quantum_private) > 0
        assert len(hybrid_kp.quantum_public) > 0

    def test_hybrid_sign_and_verify(self):
        """Test hybrid signing and verification"""
        crypto = QuantumResistantCryptoManager()
        hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Test message for hybrid signature"

        signatures = crypto.hybrid_sign(hybrid_kp, message)

        assert "classical" in signatures
        assert "quantum" in signatures
        assert "algorithm" in signatures
        assert len(signatures["classical"]) > 0
        assert len(signatures["quantum"]) > 0

        verification = crypto.hybrid_verify(hybrid_kp, message, signatures)

        assert verification["classical"] is True
        assert verification["quantum"] is True

    def test_hybrid_invalid_classical_signature(self):
        """Test hybrid verification with invalid classical signature"""
        crypto = QuantumResistantCryptoManager()
        hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Test message"

        signatures = crypto.hybrid_sign(hybrid_kp, message)

        # Corrupt classical signature
        corrupted_sigs = {
            "classical": b"invalid signature",
            "quantum": signatures["quantum"]
        }

        verification = crypto.hybrid_verify(hybrid_kp, message, corrupted_sigs)

        assert verification["classical"] is False
        assert verification["quantum"] is True

    def test_hybrid_invalid_quantum_signature(self):
        """Test hybrid verification with invalid quantum signature"""
        crypto = QuantumResistantCryptoManager()
        hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)
        message = b"Test message"

        signatures = crypto.hybrid_sign(hybrid_kp, message)

        # Corrupt quantum signature
        corrupted_sigs = {
            "classical": signatures["classical"],
            "quantum": b"x" * 3309
        }

        verification = crypto.hybrid_verify(hybrid_kp, message, corrupted_sigs)

        assert verification["classical"] is True
        assert verification["quantum"] is False


@pytest.mark.security
class TestKeySerialization:
    """Test key serialization and deserialization"""

    def test_serialize_public_key(self):
        """Test public key serialization"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        serialized = crypto.serialize_public_key(keypair)

        assert isinstance(serialized, str)
        assert len(serialized) > 0

        # Should be valid JSON
        data = json.loads(serialized)
        assert "algorithm" in data
        assert "public_key" in data
        assert "key_id" in data

    def test_deserialize_public_key(self):
        """Test public key deserialization"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        serialized = crypto.serialize_public_key(keypair)
        public_key, algorithm = crypto.deserialize_public_key(serialized)

        assert public_key == keypair.public_key
        assert algorithm == keypair.algorithm

    def test_keypair_to_dict(self):
        """Test converting keypair to dictionary"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        data = keypair.to_dict()

        assert "algorithm" in data
        assert "private_key" in data
        assert "public_key" in data
        assert "key_id" in data
        assert "metadata" in data

        # Keys should be base64 encoded
        assert isinstance(data["private_key"], str)
        assert isinstance(data["public_key"], str)

    def test_keypair_from_dict(self):
        """Test creating keypair from dictionary"""
        crypto = QuantumResistantCryptoManager()
        original = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        data = original.to_dict()
        restored = PQCKeyPair.from_dict(data)

        assert restored.algorithm == original.algorithm
        assert restored.private_key == original.private_key
        assert restored.public_key == original.public_key
        assert restored.key_id == original.key_id

    def test_hybrid_keypair_to_dict(self):
        """Test converting hybrid keypair to dictionary"""
        crypto = QuantumResistantCryptoManager()
        hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)

        data = hybrid_kp.to_dict()

        assert "algorithm" in data
        assert "classical_private" in data
        assert "classical_public" in data
        assert "quantum_private" in data
        assert "quantum_public" in data
        assert "key_id" in data


@pytest.mark.security
class TestAlgorithmInfo:
    """Test algorithm information queries"""

    def test_list_available_algorithms(self):
        """Test listing available algorithms"""
        crypto = QuantumResistantCryptoManager()
        available = crypto.list_available_algorithms()

        assert "signature_algorithms" in available
        assert "kem_algorithms" in available
        assert "recommended_signature" in available
        assert "recommended_kem" in available

        assert len(available["signature_algorithms"]) == 6
        assert len(available["kem_algorithms"]) == 2

    def test_get_signature_algorithm_info(self):
        """Test getting signature algorithm info"""
        crypto = QuantumResistantCryptoManager()
        info = crypto.get_algorithm_info(PQCAlgorithm.ML_DSA_65)

        assert info["name"] == "ML-DSA-65"
        assert info["type"] == "signature"
        assert info["security_level"] == 192
        assert info["public_key_size"] == 1952
        assert info["secret_key_size"] == 4032
        assert info["signature_size"] == 3309
        assert info["nist_standard"] == "FIPS 204"

    def test_get_kem_algorithm_info(self):
        """Test getting KEM algorithm info"""
        crypto = QuantumResistantCryptoManager()
        info = crypto.get_algorithm_info(PQCAlgorithm.ML_KEM_768)

        assert info["name"] == "ML-KEM-768"
        assert info["type"] == "kem"
        assert info["security_level"] == 192
        assert info["public_key_size"] == 1184
        assert info["secret_key_size"] == 2400
        assert info["ciphertext_size"] == 1088
        assert info["shared_secret_size"] == 32
        assert info["nist_standard"] == "FIPS 203"


@pytest.mark.security
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_signature_algorithm(self):
        """Test using KEM algorithm for signatures"""
        crypto = QuantumResistantCryptoManager()

        with pytest.raises(ValueError):
            crypto.generate_keypair(PQCAlgorithm.ML_KEM_768)

    def test_invalid_kem_algorithm(self):
        """Test using signature algorithm for KEM"""
        crypto = QuantumResistantCryptoManager()

        with pytest.raises(ValueError):
            crypto.generate_kem_keypair(PQCAlgorithm.ML_DSA_65)

    def test_empty_message_signing(self):
        """Test signing an empty message"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        message = b""
        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        assert crypto.verify(keypair.public_key, message, signature, PQCAlgorithm.ML_DSA_65)

    def test_large_message_signing(self):
        """Test signing a large message"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        message = b"x" * 1000000  # 1MB message
        signature = crypto.sign(keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        assert crypto.verify(keypair.public_key, message, signature, PQCAlgorithm.ML_DSA_65)

    def test_default_algorithm(self):
        """Test using default algorithm"""
        crypto = QuantumResistantCryptoManager()
        keypair = crypto.generate_keypair()

        assert keypair.algorithm == "ML-DSA-65"

        message = b"Test"
        signature = crypto.sign(keypair.private_key, message)
        assert crypto.verify(keypair.public_key, message, signature)


@pytest.mark.security
class TestCrossAlgorithmCompatibility:
    """Test that keys from one algorithm don't work with another"""

    def test_ml_dsa_keys_with_falcon_algorithm(self):
        """Test that ML-DSA keys don't verify with Falcon"""
        crypto = QuantumResistantCryptoManager()
        ml_dsa_keypair = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        falcon_keypair = crypto.generate_keypair(PQCAlgorithm.FALCON_512)

        message = b"Test message"
        ml_dsa_sig = crypto.sign(ml_dsa_keypair.private_key, message, PQCAlgorithm.ML_DSA_65)

        # Should not verify with wrong algorithm
        assert not crypto.verify(falcon_keypair.public_key, message, ml_dsa_sig, PQCAlgorithm.FALCON_512)

    def test_different_keypairs_same_algorithm(self):
        """Test that signatures from one keypair don't verify with another"""
        crypto = QuantumResistantCryptoManager()
        keypair1 = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        keypair2 = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)

        message = b"Test message"
        signature1 = crypto.sign(keypair1.private_key, message, PQCAlgorithm.ML_DSA_65)

        # Should not verify with different public key
        assert not crypto.verify(keypair2.public_key, message, signature1, PQCAlgorithm.ML_DSA_65)


@pytest.mark.security
class TestPerformanceCharacteristics:
    """Test performance characteristics of different algorithms"""

    def test_falcon_smaller_signatures_than_ml_dsa(self):
        """Test that Falcon produces smaller signatures than ML-DSA"""
        crypto = QuantumResistantCryptoManager()
        ml_dsa_kp = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        falcon_kp = crypto.generate_keypair(PQCAlgorithm.FALCON_512)

        message = b"Test message for size comparison"

        ml_dsa_sig = crypto.sign(ml_dsa_kp.private_key, message, PQCAlgorithm.ML_DSA_65)
        falcon_sig = crypto.sign(falcon_kp.private_key, message, PQCAlgorithm.FALCON_512)

        # Falcon should produce smaller signatures
        assert len(falcon_sig) < len(ml_dsa_sig)

    def test_sphincs_smallest_keys(self):
        """Test that SPHINCS+ has the smallest public keys"""
        crypto = QuantumResistantCryptoManager()
        ml_dsa_kp = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        falcon_kp = crypto.generate_keypair(PQCAlgorithm.FALCON_512)
        sphincs_kp = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)

        # SPHINCS+ should have the smallest public key
        assert len(sphincs_kp.public_key) < len(ml_dsa_kp.public_key)
        assert len(sphincs_kp.public_key) < len(falcon_kp.public_key)

    def test_sphincs_largest_signatures(self):
        """Test that SPHINCS+ produces largest signatures"""
        crypto = QuantumResistantCryptoManager()
        ml_dsa_kp = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
        falcon_kp = crypto.generate_keypair(PQCAlgorithm.FALCON_512)
        sphincs_kp = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)

        message = b"Test message"

        ml_dsa_sig = crypto.sign(ml_dsa_kp.private_key, message, PQCAlgorithm.ML_DSA_65)
        falcon_sig = crypto.sign(falcon_kp.private_key, message, PQCAlgorithm.FALCON_512)
        sphincs_sig = crypto.sign(sphincs_kp.private_key, message, PQCAlgorithm.SPHINCS_SHA2_128F)

        # SPHINCS+ should have the largest signatures
        assert len(sphincs_sig) > len(ml_dsa_sig)
        assert len(sphincs_sig) > len(falcon_sig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
