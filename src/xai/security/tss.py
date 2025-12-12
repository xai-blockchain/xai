from abc import ABC, abstractmethod
import hashlib
import json
import logging
from cryptography.exceptions import InvalidSignature
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


logger = logging.getLogger(__name__)


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
        ...

    @abstractmethod
    def distributed_sign(self, message_hash: bytes, participant_key_shares: List[Dict]) -> str:
        """
        Collects partial signatures from participants and combines them to produce
        a final threshold signature.
        """
        ...

    @abstractmethod
    def verify_threshold_signature(
        self, message_hash: bytes, signature: str, public_key: str
    ) -> bool:
        """
        Verifies a threshold signature against a message hash and the combined public key.
        """
        ...


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
            private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
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

        logger.info(
            "Generated mock participant keys",
            extra={
                "event": "tss.mock_keys_generated",
                "participants": num_participants,
                "threshold": threshold,
            },
        )
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
                except (ValueError, InvalidSignature) as exc:
                    logger.warning(
                        "MockTSS rejected invalid participant signature",
                        extra={
                            "event": "tss.invalid_signature",
                            "participant": signer_pub_hex[:16] + "...",
                        },
                    )

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
    raise SystemExit("MockTSS demo removed; use unit tests instead.")
