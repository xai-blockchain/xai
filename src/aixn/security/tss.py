from abc import ABC, abstractmethod
import hashlib
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.backends import default_backend
from typing import List, Tuple, Dict


class TSSInterface(ABC):
    """
    Abstract Base Class for a Threshold Signature Scheme (TSS).
    Defines the interface for distributed key generation, signing, and verification.
    """

    @abstractmethod
    def generate_distributed_keys(self, num_participants: int, threshold: int) -> List[Dict]:
        """
        Generates key shares for multiple participants such that a threshold
        number of shares can reconstruct the signing key or produce a signature.
        Returns a list of dictionaries, each containing a participant's key share info.
        """
        pass

    @abstractmethod
    def distributed_sign(self, message_hash: bytes, participant_key_shares: List[Dict]) -> str:
        """
        Collects partial signatures from participants and combines them to produce
        a final threshold signature.
        """
        pass

    @abstractmethod
    def verify_threshold_signature(
        self, message_hash: bytes, signature: str, public_key: str
    ) -> bool:
        """
        Verifies a threshold signature against a message hash and the combined public key.
        """
        pass


class MockTSS(TSSInterface):
    """
    A mock implementation of a Threshold Signature Scheme using standard ECDSA.
    This simulates the threshold aspect by requiring 't' individual ECDSA signatures
    to be collected and verified. It does NOT implement true distributed key generation
    or distributed signing in a cryptographic sense. It's for conceptual demonstration.
    """

    def __init__(self):
        self._master_private_key = None
        self._master_public_key = None
        self._participants_keys = {}  # Stores {participant_id: (priv_key_hex, pub_key_hex)}

    def generate_distributed_keys(self, num_participants: int, threshold: int) -> List[Dict]:
        if threshold > num_participants:
            raise ValueError("Threshold cannot be greater than number of participants.")

        # In a real TSS, this would involve complex distributed key generation.
        # Here, we just generate individual key pairs for each participant.
        participant_key_shares = []
        for i in range(num_participants):
            private_key = ec.generate_private_key(ec.SECP256k1(), default_backend())
            public_key = private_key.public_key()

            priv_hex = private_key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            ).hex()
            pub_hex = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).hex()

            participant_id = f"participant_{i+1}"
            self._participants_keys[participant_id] = (priv_hex, pub_hex)
            participant_key_shares.append({"participant_id": participant_id, "public_key": pub_hex})

        # For verification, we'll use a "master" public key which is conceptually
        # derived from the distributed keys in a real TSS. Here, we'll just pick one.
        # In a real TSS, the master public key is derived from the key shares.
        self._master_public_key = participant_key_shares[0]["public_key"]  # Simplified

        print(f"MockTSS: Generated {num_participants} participant keys with threshold {threshold}.")
        return participant_key_shares

    def distributed_sign(
        self, message_hash: bytes, collected_signatures: List[Tuple[str, str]], threshold: int
    ) -> str:
        """
        Simulates distributed signing by verifying a threshold of individual signatures.
        Returns a concatenated string of valid signatures if threshold is met.
        """
        if len(collected_signatures) < threshold:
            raise ValueError(
                f"Insufficient signatures collected. Required: {threshold}, Got: {len(collected_signatures)}"
            )

        valid_signatures = []
        for sig_hex, signer_pub_hex in collected_signatures:
            if signer_pub_hex in [
                pk for _, pk in self._participants_keys.values()
            ]:  # Check if signer is a known participant
                try:
                    public_key = serialization.load_pem_public_key(
                        bytes.fromhex(signer_pub_hex), backend=default_backend()
                    )
                    public_key.verify(
                        bytes.fromhex(sig_hex), message_hash, ec.ECDSA(hashes.SHA256())
                    )
                    valid_signatures.append(sig_hex)
                except Exception:
                    pass  # Invalid signature

        if len(valid_signatures) >= threshold:
            # In a real TSS, partial signatures are combined cryptographically.
            # Here, we just concatenate them for a mock "threshold signature".
            return "".join(sorted(valid_signatures))
        else:
            raise ValueError(
                f"Failed to collect enough valid signatures. Valid: {len(valid_signatures)}, Required: {threshold}"
            )

    def verify_threshold_signature(
        self, message_hash: bytes, combined_signature: str, public_key: str
    ) -> bool:
        """
        In a real TSS, this would verify the combined signature against the master public key.
        Here, we just check if the combined_signature is non-empty (meaning threshold was met).
        """
        # This is a highly simplified mock verification.
        # A real TSS would verify the cryptographically combined signature.
        return bool(combined_signature) and public_key == self._master_public_key


# Example Usage (for testing purposes)
if __name__ == "__main__":
    tss_instance = MockTSS()

    # 1. Generate distributed keys for 5 participants, requiring 3 signatures
    num_participants = 5
    threshold = 3
    participant_keys = tss_instance.generate_distributed_keys(num_participants, threshold)
    master_pub_key = tss_instance._master_public_key  # Get the mock master public key

    # 2. Message to be signed (e.g., a bridge transfer transaction hash)
    message_data = {"transfer_id": "tx123", "amount": 100, "destination_chain": "Ethereum"}
    message_hash = hashlib.sha256(json.dumps(message_data, sort_keys=True).encode()).digest()

    # 3. Participants sign the message
    collected_signatures = []
    # Participant 1 signs
    p1_priv_pem = bytes.fromhex(tss_instance._participants_keys["participant_1"][0])
    p1_priv_key = serialization.load_pem_private_key(
        p1_priv_pem, password=None, backend=default_backend()
    )
    p1_pub = tss_instance._participants_keys["participant_1"][1]
    sig1 = p1_priv_key.sign(message_hash, ec.ECDSA(hashes.SHA256())).hex()
    collected_signatures.append((sig1, p1_pub))

    # Participant 2 signs
    p2_priv_pem = bytes.fromhex(tss_instance._participants_keys["participant_2"][0])
    p2_priv_key = serialization.load_pem_private_key(
        p2_priv_pem, password=None, backend=default_backend()
    )
    p2_pub = tss_instance._participants_keys["participant_2"][1]
    sig2 = p2_priv_key.sign(message_hash, ec.ECDSA(hashes.SHA256())).hex()
    collected_signatures.append((sig2, p2_pub))

    # Participant 3 signs
    p3_priv_pem = bytes.fromhex(tss_instance._participants_keys["participant_3"][0])
    p3_priv_key = serialization.load_pem_private_key(
        p3_priv_pem, password=None, backend=default_backend()
    )
    p3_pub = tss_instance._participants_keys["participant_3"][1]
    sig3 = p3_priv_key.sign(message_hash, ec.ECDSA(hashes.SHA256())).hex()
    collected_signatures.append((sig3, p3_pub))

    print(f"\nCollected {len(collected_signatures)} signatures.")

    # 4. Combine signatures (simulated)
    try:
        threshold_signature = tss_instance.distributed_sign(
            message_hash, collected_signatures, threshold
        )
        print(f"Threshold Signature (mock): {threshold_signature[:60]}...")

        # 5. Verify the threshold signature
        is_valid = tss_instance.verify_threshold_signature(
            message_hash, threshold_signature, master_pub_key
        )
        print(f"Is Threshold Signature valid? {is_valid}")
    except ValueError as e:
        print(f"Error during distributed signing: {e}")

    # Test with insufficient signatures
    print("\n--- Testing with insufficient signatures (2 of 3) ---")
    insufficient_signatures = collected_signatures[:2]
    try:
        tss_instance.distributed_sign(message_hash, insufficient_signatures, threshold)
    except ValueError as e:
        print(f"Error (expected): {e}")
