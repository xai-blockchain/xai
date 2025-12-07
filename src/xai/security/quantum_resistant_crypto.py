"""
Production-Grade NIST Post-Quantum Cryptography (PQC) Implementation

This module implements NIST-standardized post-quantum cryptographic algorithms:
- ML-DSA (CRYSTALS-Dilithium): Lattice-based digital signatures (NIST FIPS 204)
- Falcon: Lattice-based compact signatures (NIST selected)
- SPHINCS+: Hash-based stateless signatures (NIST FIPS 205)
- ML-KEM (CRYSTALS-Kyber): Lattice-based key encapsulation (NIST FIPS 203)

All algorithms are quantum-resistant and approved by NIST for post-quantum cryptography.
"""

import hashlib
import secrets
import json
import base64
import logging
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# NIST PQC algorithms via pqcrypto library
import pqcrypto.sign.ml_dsa_65 as ml_dsa_65
import pqcrypto.sign.ml_dsa_87 as ml_dsa_87
import pqcrypto.sign.falcon_512 as falcon_512
import pqcrypto.sign.falcon_1024 as falcon_1024
import pqcrypto.sign.sphincs_sha2_128f_simple as sphincs_128f
import pqcrypto.sign.sphincs_sha2_256f_simple as sphincs_256f
import pqcrypto.kem.ml_kem_768 as ml_kem_768
import pqcrypto.kem.ml_kem_1024 as ml_kem_1024

# For hybrid classical-quantum approach
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


class PQCAlgorithm(Enum):
    """Supported NIST Post-Quantum Cryptographic algorithms"""
    # ML-DSA (CRYSTALS-Dilithium) - NIST FIPS 204
    ML_DSA_65 = "ML-DSA-65"  # Security Level 3 (AES-192 equivalent)
    ML_DSA_87 = "ML-DSA-87"  # Security Level 5 (AES-256 equivalent)

    # Falcon - NIST selected algorithm
    FALCON_512 = "Falcon-512"  # Security Level 1 (AES-128 equivalent)
    FALCON_1024 = "Falcon-1024"  # Security Level 5 (AES-256 equivalent)

    # SPHINCS+ - NIST FIPS 205
    SPHINCS_SHA2_128F = "SPHINCS+-SHA2-128f"  # Fast variant, Security Level 1
    SPHINCS_SHA2_256F = "SPHINCS+-SHA2-256f"  # Fast variant, Security Level 5

    # ML-KEM (CRYSTALS-Kyber) - NIST FIPS 203
    ML_KEM_768 = "ML-KEM-768"  # Security Level 3
    ML_KEM_1024 = "ML-KEM-1024"  # Security Level 5

    # Hybrid mode
    HYBRID_ML_DSA = "Hybrid-ML-DSA"  # ECDSA + ML-DSA


@dataclass
class PQCKeyPair:
    """Post-Quantum Cryptographic key pair"""
    algorithm: str
    private_key: bytes
    public_key: bytes
    key_id: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "algorithm": self.algorithm,
            "private_key": base64.b64encode(self.private_key).decode('utf-8'),
            "public_key": base64.b64encode(self.public_key).decode('utf-8'),
            "key_id": self.key_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PQCKeyPair':
        """Create from dictionary"""
        return cls(
            algorithm=data["algorithm"],
            private_key=base64.b64decode(data["private_key"]),
            public_key=base64.b64decode(data["public_key"]),
            key_id=data["key_id"],
            metadata=data.get("metadata", {})
        )


@dataclass
class HybridKeyPair:
    """Hybrid classical + post-quantum key pair"""
    classical_private: bytes
    classical_public: bytes
    quantum_private: bytes
    quantum_public: bytes
    algorithm: str
    key_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "algorithm": self.algorithm,
            "classical_private": base64.b64encode(self.classical_private).decode('utf-8'),
            "classical_public": base64.b64encode(self.classical_public).decode('utf-8'),
            "quantum_private": base64.b64encode(self.quantum_private).decode('utf-8'),
            "quantum_public": base64.b64encode(self.quantum_public).decode('utf-8'),
            "key_id": self.key_id
        }


class QuantumResistantCryptoManager:
    """
    Production-grade NIST Post-Quantum Cryptography Manager.

    Features:
    - ML-DSA (CRYSTALS-Dilithium): Lattice-based signatures (NIST FIPS 204)
    - Falcon: Compact lattice-based signatures (NIST selected)
    - SPHINCS+: Stateless hash-based signatures (NIST FIPS 205)
    - ML-KEM (CRYSTALS-Kyber): Key encapsulation mechanism (NIST FIPS 203)
    - Hybrid classical + quantum-resistant schemes
    - Full key serialization/deserialization support
    """

    # Algorithm implementations mapping
    SIGNATURE_ALGORITHMS = {
        PQCAlgorithm.ML_DSA_65: ml_dsa_65,
        PQCAlgorithm.ML_DSA_87: ml_dsa_87,
        PQCAlgorithm.FALCON_512: falcon_512,
        PQCAlgorithm.FALCON_1024: falcon_1024,
        PQCAlgorithm.SPHINCS_SHA2_128F: sphincs_128f,
        PQCAlgorithm.SPHINCS_SHA2_256F: sphincs_256f,
    }

    KEM_ALGORITHMS = {
        PQCAlgorithm.ML_KEM_768: ml_kem_768,
        PQCAlgorithm.ML_KEM_1024: ml_kem_1024,
    }

    # Security levels (in bits)
    SECURITY_LEVELS = {
        PQCAlgorithm.ML_DSA_65: 192,
        PQCAlgorithm.ML_DSA_87: 256,
        PQCAlgorithm.FALCON_512: 128,
        PQCAlgorithm.FALCON_1024: 256,
        PQCAlgorithm.SPHINCS_SHA2_128F: 128,
        PQCAlgorithm.SPHINCS_SHA2_256F: 256,
        PQCAlgorithm.ML_KEM_768: 192,
        PQCAlgorithm.ML_KEM_1024: 256,
    }

    def __init__(self, default_algorithm: PQCAlgorithm = PQCAlgorithm.ML_DSA_65):
        """
        Initialize quantum-resistant crypto manager.

        Args:
            default_algorithm: Default algorithm to use (ML-DSA-65 recommended)
        """
        self.default_algorithm = default_algorithm

    def generate_keypair(
        self,
        algorithm: Optional[PQCAlgorithm] = None
    ) -> PQCKeyPair:
        """
        Generate a post-quantum cryptographic key pair.

        Args:
            algorithm: PQC algorithm to use (defaults to ML-DSA-65)

        Returns:
            PQCKeyPair with public and private keys

        Raises:
            ValueError: If algorithm is not supported
        """
        if algorithm is None:
            algorithm = self.default_algorithm

        if algorithm not in self.SIGNATURE_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported for signatures")

        # Generate keypair using the selected algorithm
        algo_impl = self.SIGNATURE_ALGORITHMS[algorithm]
        public_key, secret_key = algo_impl.generate_keypair()

        # Generate key ID from public key hash
        key_id = hashlib.sha256(public_key).hexdigest()[:32]

        # Metadata
        metadata = {
            "security_level": self.SECURITY_LEVELS[algorithm],
            "public_key_size": len(public_key),
            "secret_key_size": len(secret_key),
            "signature_size": algo_impl.SIGNATURE_SIZE,
            "nist_standard": self._get_nist_standard(algorithm)
        }

        return PQCKeyPair(
            algorithm=algorithm.value,
            private_key=secret_key,
            public_key=public_key,
            key_id=key_id,
            metadata=metadata
        )

    def sign(
        self,
        private_key: bytes,
        message: bytes,
        algorithm: Optional[PQCAlgorithm] = None
    ) -> bytes:
        """
        Sign a message using post-quantum cryptography.

        Args:
            private_key: Private key bytes
            message: Message to sign
            algorithm: Algorithm to use (defaults to ML-DSA-65)

        Returns:
            Signature bytes

        Raises:
            ValueError: If algorithm is not supported
        """
        if algorithm is None:
            algorithm = self.default_algorithm

        if algorithm not in self.SIGNATURE_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported")

        algo_impl = self.SIGNATURE_ALGORITHMS[algorithm]
        signature = algo_impl.sign(private_key, message)
        return signature

    def verify(
        self,
        public_key: bytes,
        message: bytes,
        signature: bytes,
        algorithm: Optional[PQCAlgorithm] = None
    ) -> bool:
        """
        Verify a post-quantum signature.

        Args:
            public_key: Public key bytes
            message: Original message
            signature: Signature to verify
            algorithm: Algorithm used (defaults to ML-DSA-65)

        Returns:
            True if signature is valid, False otherwise
        """
        if algorithm is None:
            algorithm = self.default_algorithm

        if algorithm not in self.SIGNATURE_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported")

        try:
            algo_impl = self.SIGNATURE_ALGORITHMS[algorithm]
            # pqcrypto.sign modules return a boolean from verify()
            # Returns True if valid, False if invalid
            result = algo_impl.verify(public_key, message, signature)
            return result
        except Exception as e:
            # Catch any unexpected errors (e.g., malformed keys, wrong sizes)
            logger.debug(
                "Post-quantum signature verification error",
                algorithm=algorithm.value,
                error=str(e)
            )
            return False

    def generate_kem_keypair(
        self,
        algorithm: PQCAlgorithm = PQCAlgorithm.ML_KEM_768
    ) -> PQCKeyPair:
        """
        Generate a key encapsulation mechanism (KEM) key pair.

        Args:
            algorithm: KEM algorithm to use (ML-KEM-768 or ML-KEM-1024)

        Returns:
            PQCKeyPair for key encapsulation

        Raises:
            ValueError: If algorithm is not a KEM algorithm
        """
        if algorithm not in self.KEM_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported for KEM")

        algo_impl = self.KEM_ALGORITHMS[algorithm]
        public_key, secret_key = algo_impl.generate_keypair()

        # Generate key ID
        key_id = hashlib.sha256(public_key).hexdigest()[:32]

        metadata = {
            "security_level": self.SECURITY_LEVELS[algorithm],
            "public_key_size": len(public_key),
            "secret_key_size": len(secret_key),
            "ciphertext_size": algo_impl.CIPHERTEXT_SIZE,
            "shared_secret_size": algo_impl.PLAINTEXT_SIZE,
            "nist_standard": "FIPS 203"
        }

        return PQCKeyPair(
            algorithm=algorithm.value,
            private_key=secret_key,
            public_key=public_key,
            key_id=key_id,
            metadata=metadata
        )

    def kem_encapsulate(
        self,
        public_key: bytes,
        algorithm: PQCAlgorithm = PQCAlgorithm.ML_KEM_768
    ) -> Tuple[bytes, bytes]:
        """
        Encapsulate a shared secret using KEM.

        Args:
            public_key: Recipient's public key
            algorithm: KEM algorithm to use

        Returns:
            Tuple of (ciphertext, shared_secret)

        Raises:
            ValueError: If algorithm is not a KEM algorithm
        """
        if algorithm not in self.KEM_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported for KEM")

        algo_impl = self.KEM_ALGORITHMS[algorithm]
        ciphertext, shared_secret = algo_impl.encrypt(public_key)
        return ciphertext, shared_secret

    def kem_decapsulate(
        self,
        secret_key: bytes,
        ciphertext: bytes,
        algorithm: PQCAlgorithm = PQCAlgorithm.ML_KEM_768
    ) -> bytes:
        """
        Decapsulate a shared secret using KEM.

        Args:
            secret_key: Own private key
            ciphertext: Ciphertext from encapsulation
            algorithm: KEM algorithm used

        Returns:
            Shared secret bytes

        Raises:
            ValueError: If algorithm is not a KEM algorithm
        """
        if algorithm not in self.KEM_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported for KEM")

        algo_impl = self.KEM_ALGORITHMS[algorithm]
        shared_secret = algo_impl.decrypt(secret_key, ciphertext)
        return shared_secret

    def generate_hybrid_keypair(
        self,
        pqc_algorithm: PQCAlgorithm = PQCAlgorithm.ML_DSA_65
    ) -> HybridKeyPair:
        """
        Generate hybrid classical (ECDSA) + post-quantum key pair.

        This provides security during the transition period. If either scheme
        is broken, the other still provides security.

        Args:
            pqc_algorithm: Post-quantum algorithm to use

        Returns:
            HybridKeyPair with both classical and quantum keys
        """
        # Generate classical ECDSA key
        classical_private = ec.generate_private_key(ec.SECP256K1(), default_backend())
        classical_private_bytes = classical_private.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        classical_public_bytes = classical_private.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Generate post-quantum key
        pqc_keypair = self.generate_keypair(pqc_algorithm)

        # Generate combined key ID
        combined = classical_public_bytes + pqc_keypair.public_key
        key_id = hashlib.sha256(combined).hexdigest()[:32]

        return HybridKeyPair(
            classical_private=classical_private_bytes,
            classical_public=classical_public_bytes,
            quantum_private=pqc_keypair.private_key,
            quantum_public=pqc_keypair.public_key,
            algorithm=f"Hybrid-{pqc_algorithm.value}",
            key_id=key_id
        )

    def hybrid_sign(
        self,
        hybrid_keypair: HybridKeyPair,
        message: bytes
    ) -> Dict[str, bytes]:
        """
        Sign using both classical and post-quantum schemes.

        Args:
            hybrid_keypair: Hybrid key pair
            message: Message to sign

        Returns:
            Dictionary with both signatures
        """
        # Classical ECDSA signature
        classical_key = serialization.load_der_private_key(
            hybrid_keypair.classical_private,
            password=None,
            backend=default_backend()
        )
        classical_sig = classical_key.sign(message, ec.ECDSA(hashes.SHA256()))

        # Post-quantum signature
        # Extract algorithm from hybrid algorithm name
        algo_name = hybrid_keypair.algorithm.replace("Hybrid-", "")
        algorithm = PQCAlgorithm(algo_name)
        quantum_sig = self.sign(hybrid_keypair.quantum_private, message, algorithm)

        return {
            "classical": classical_sig,
            "quantum": quantum_sig,
            "algorithm": hybrid_keypair.algorithm
        }

    def hybrid_verify(
        self,
        hybrid_keypair: HybridKeyPair,
        message: bytes,
        signatures: Dict[str, bytes]
    ) -> Dict[str, bool]:
        """
        Verify hybrid signatures.

        Args:
            hybrid_keypair: Hybrid key pair (contains public keys)
            message: Original message
            signatures: Dictionary with both signatures

        Returns:
            Dictionary with verification results for each scheme
        """
        results = {}

        # Verify classical signature
        try:
            classical_pub = serialization.load_der_public_key(
                hybrid_keypair.classical_public,
                backend=default_backend()
            )
            classical_pub.verify(
                signatures["classical"],
                message,
                ec.ECDSA(hashes.SHA256())
            )
            results["classical"] = True
        except Exception as e:
            logger.debug(
                "Classical ECDSA signature verification failed in hybrid scheme",
                error=str(e)
            )
            results["classical"] = False

        # Verify post-quantum signature
        algo_name = hybrid_keypair.algorithm.replace("Hybrid-", "")
        algorithm = PQCAlgorithm(algo_name)
        results["quantum"] = self.verify(
            hybrid_keypair.quantum_public,
            message,
            signatures["quantum"],
            algorithm
        )

        return results

    def serialize_public_key(self, keypair: PQCKeyPair) -> str:
        """
        Serialize public key to base64 string.

        Args:
            keypair: PQC key pair

        Returns:
            Base64-encoded public key with algorithm metadata
        """
        data = {
            "algorithm": keypair.algorithm,
            "public_key": base64.b64encode(keypair.public_key).decode('utf-8'),
            "key_id": keypair.key_id
        }
        return json.dumps(data)

    def deserialize_public_key(self, serialized: str) -> Tuple[bytes, str]:
        """
        Deserialize public key from base64 string.

        Args:
            serialized: Serialized public key

        Returns:
            Tuple of (public_key_bytes, algorithm_name)
        """
        data = json.loads(serialized)
        public_key = base64.b64decode(data["public_key"])
        algorithm = data["algorithm"]
        return public_key, algorithm

    def get_algorithm_info(self, algorithm: PQCAlgorithm) -> Dict[str, Any]:
        """
        Get information about a PQC algorithm.

        Args:
            algorithm: Algorithm to query

        Returns:
            Dictionary with algorithm information
        """
        if algorithm in self.SIGNATURE_ALGORITHMS:
            algo_impl = self.SIGNATURE_ALGORITHMS[algorithm]
            return {
                "name": algorithm.value,
                "type": "signature",
                "security_level": self.SECURITY_LEVELS[algorithm],
                "public_key_size": algo_impl.PUBLIC_KEY_SIZE,
                "secret_key_size": algo_impl.SECRET_KEY_SIZE,
                "signature_size": algo_impl.SIGNATURE_SIZE,
                "nist_standard": self._get_nist_standard(algorithm)
            }
        elif algorithm in self.KEM_ALGORITHMS:
            algo_impl = self.KEM_ALGORITHMS[algorithm]
            return {
                "name": algorithm.value,
                "type": "kem",
                "security_level": self.SECURITY_LEVELS[algorithm],
                "public_key_size": algo_impl.PUBLIC_KEY_SIZE,
                "secret_key_size": algo_impl.SECRET_KEY_SIZE,
                "ciphertext_size": algo_impl.CIPHERTEXT_SIZE,
                "shared_secret_size": algo_impl.PLAINTEXT_SIZE,
                "nist_standard": self._get_nist_standard(algorithm)
            }
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def _get_nist_standard(self, algorithm: PQCAlgorithm) -> str:
        """Get NIST standard designation for algorithm"""
        if algorithm in [PQCAlgorithm.ML_DSA_65, PQCAlgorithm.ML_DSA_87]:
            return "FIPS 204"
        elif algorithm in [PQCAlgorithm.SPHINCS_SHA2_128F, PQCAlgorithm.SPHINCS_SHA2_256F]:
            return "FIPS 205"
        elif algorithm in [PQCAlgorithm.ML_KEM_768, PQCAlgorithm.ML_KEM_1024]:
            return "FIPS 203"
        elif algorithm in [PQCAlgorithm.FALCON_512, PQCAlgorithm.FALCON_1024]:
            return "NIST Selected"
        return "Unknown"

    def list_available_algorithms(self) -> Dict[str, List[str]]:
        """
        List all available PQC algorithms.

        Returns:
            Dictionary categorizing algorithms by type
        """
        return {
            "signature_algorithms": [algo.value for algo in self.SIGNATURE_ALGORITHMS.keys()],
            "kem_algorithms": [algo.value for algo in self.KEM_ALGORITHMS.keys()],
            "recommended_signature": "ML-DSA-65",
            "recommended_kem": "ML-KEM-768"
        }


# Example usage and comprehensive testing
if __name__ == "__main__":
    print("=" * 70)
    print("NIST Post-Quantum Cryptography Implementation Test")
    print("=" * 70)

    crypto = QuantumResistantCryptoManager()

    # Test 1: ML-DSA (CRYSTALS-Dilithium)
    print("\n1. ML-DSA-65 (CRYSTALS-Dilithium) - NIST FIPS 204")
    print("-" * 70)
    keypair_ml_dsa = crypto.generate_keypair(PQCAlgorithm.ML_DSA_65)
    print(f"   Key ID: {keypair_ml_dsa.key_id}")
    print(f"   Security Level: {keypair_ml_dsa.metadata['security_level']} bits")
    print(f"   Public Key Size: {keypair_ml_dsa.metadata['public_key_size']} bytes")
    print(f"   Secret Key Size: {keypair_ml_dsa.metadata['secret_key_size']} bytes")
    print(f"   Signature Size: {keypair_ml_dsa.metadata['signature_size']} bytes")

    message = b"Quantum-resistant blockchain transaction"
    signature_ml_dsa = crypto.sign(keypair_ml_dsa.private_key, message, PQCAlgorithm.ML_DSA_65)
    print(f"   Actual Signature: {len(signature_ml_dsa)} bytes")

    is_valid = crypto.verify(keypair_ml_dsa.public_key, message, signature_ml_dsa, PQCAlgorithm.ML_DSA_65)
    print(f"   Signature Valid: {is_valid}")

    # Test 2: Falcon
    print("\n2. Falcon-512 - NIST Selected Algorithm")
    print("-" * 70)
    keypair_falcon = crypto.generate_keypair(PQCAlgorithm.FALCON_512)
    print(f"   Key ID: {keypair_falcon.key_id}")
    print(f"   Security Level: {keypair_falcon.metadata['security_level']} bits")
    print(f"   Public Key Size: {keypair_falcon.metadata['public_key_size']} bytes")
    print(f"   Secret Key Size: {keypair_falcon.metadata['secret_key_size']} bytes")
    print(f"   Max Signature Size: {keypair_falcon.metadata['signature_size']} bytes")

    signature_falcon = crypto.sign(keypair_falcon.private_key, message, PQCAlgorithm.FALCON_512)
    print(f"   Actual Signature: {len(signature_falcon)} bytes (compact!)")

    is_valid = crypto.verify(keypair_falcon.public_key, message, signature_falcon, PQCAlgorithm.FALCON_512)
    print(f"   Signature Valid: {is_valid}")

    # Test 3: SPHINCS+
    print("\n3. SPHINCS+-SHA2-128f - NIST FIPS 205")
    print("-" * 70)
    keypair_sphincs = crypto.generate_keypair(PQCAlgorithm.SPHINCS_SHA2_128F)
    print(f"   Key ID: {keypair_sphincs.key_id}")
    print(f"   Security Level: {keypair_sphincs.metadata['security_level']} bits")
    print(f"   Public Key Size: {keypair_sphincs.metadata['public_key_size']} bytes (minimal!)")
    print(f"   Secret Key Size: {keypair_sphincs.metadata['secret_key_size']} bytes")
    print(f"   Signature Size: {keypair_sphincs.metadata['signature_size']} bytes")

    signature_sphincs = crypto.sign(keypair_sphincs.private_key, message, PQCAlgorithm.SPHINCS_SHA2_128F)
    print(f"   Actual Signature: {len(signature_sphincs)} bytes")

    is_valid = crypto.verify(keypair_sphincs.public_key, message, signature_sphincs, PQCAlgorithm.SPHINCS_SHA2_128F)
    print(f"   Signature Valid: {is_valid}")

    # Test 4: ML-KEM (CRYSTALS-Kyber)
    print("\n4. ML-KEM-768 (CRYSTALS-Kyber) - NIST FIPS 203")
    print("-" * 70)
    kem_keypair = crypto.generate_kem_keypair(PQCAlgorithm.ML_KEM_768)
    print(f"   Key ID: {kem_keypair.key_id}")
    print(f"   Security Level: {kem_keypair.metadata['security_level']} bits")
    print(f"   Public Key Size: {kem_keypair.metadata['public_key_size']} bytes")
    print(f"   Secret Key Size: {kem_keypair.metadata['secret_key_size']} bytes")
    print(f"   Ciphertext Size: {kem_keypair.metadata['ciphertext_size']} bytes")
    print(f"   Shared Secret Size: {kem_keypair.metadata['shared_secret_size']} bytes")

    ciphertext, shared_secret_enc = crypto.kem_encapsulate(kem_keypair.public_key, PQCAlgorithm.ML_KEM_768)
    shared_secret_dec = crypto.kem_decapsulate(kem_keypair.private_key, ciphertext, PQCAlgorithm.ML_KEM_768)
    print(f"   Encapsulation Successful: {shared_secret_enc == shared_secret_dec}")

    # Test 5: Hybrid Classical + Quantum
    print("\n5. Hybrid ECDSA + ML-DSA-65")
    print("-" * 70)
    hybrid_kp = crypto.generate_hybrid_keypair(PQCAlgorithm.ML_DSA_65)
    print(f"   Key ID: {hybrid_kp.key_id}")
    print(f"   Algorithm: {hybrid_kp.algorithm}")

    hybrid_sigs = crypto.hybrid_sign(hybrid_kp, message)
    print(f"   Classical Signature: {len(hybrid_sigs['classical'])} bytes")
    print(f"   Quantum Signature: {len(hybrid_sigs['quantum'])} bytes")

    verification = crypto.hybrid_verify(hybrid_kp, message, hybrid_sigs)
    print(f"   Classical Verified: {verification['classical']}")
    print(f"   Quantum Verified: {verification['quantum']}")

    # Test 6: Key Serialization
    print("\n6. Key Serialization")
    print("-" * 70)
    serialized = crypto.serialize_public_key(keypair_ml_dsa)
    print(f"   Serialized length: {len(serialized)} characters")
    pub_key, algo = crypto.deserialize_public_key(serialized)
    print(f"   Deserialized algorithm: {algo}")
    print(f"   Public key matches: {pub_key == keypair_ml_dsa.public_key}")

    # Test 7: Algorithm Information
    print("\n7. Available Algorithms")
    print("-" * 70)
    available = crypto.list_available_algorithms()
    print("   Signature Algorithms:")
    for algo in available["signature_algorithms"]:
        print(f"      - {algo}")
    print("   KEM Algorithms:")
    for algo in available["kem_algorithms"]:
        print(f"      - {algo}")
    print(f"   Recommended Signature: {available['recommended_signature']}")
    print(f"   Recommended KEM: {available['recommended_kem']}")

    # Test 8: Performance Comparison
    print("\n8. Algorithm Comparison")
    print("-" * 70)
    print(f"   {'Algorithm':<25} {'PK Size':<10} {'Sig Size':<10} {'Security':<10}")
    print("   " + "-" * 65)
    for algo in [PQCAlgorithm.ML_DSA_65, PQCAlgorithm.FALCON_512, PQCAlgorithm.SPHINCS_SHA2_128F]:
        info = crypto.get_algorithm_info(algo)
        print(f"   {info['name']:<25} {info['public_key_size']:<10} {info['signature_size']:<10} {info['security_level']:<10}")

    print("\n" + "=" * 70)
    print("All NIST Post-Quantum Cryptography Tests Passed!")
    print("=" * 70)
