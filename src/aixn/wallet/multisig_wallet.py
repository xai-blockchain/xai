from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from typing import List, Dict

class MultiSigWallet:
    def __init__(self, public_keys: List[str], threshold: int):
        if threshold > len(public_keys):
            raise ValueError("Threshold cannot be greater than the number of public keys.")
        self.public_keys = [load_pem_public_key(bytes.fromhex(pk)) for pk in public_keys]
        self.threshold = threshold

    def verify_signatures(self, message: bytes, signatures: Dict[str, str]) -> bool:
        message_hash = hashes.Hash(hashes.SHA256())
        message_hash.update(message)
        digest = message_hash.finalize()

        valid_signatures = 0
        for pub_key_hex, signature_hex in signatures.items():
            try:
                public_key = load_pem_public_key(bytes.fromhex(pub_key_hex))
                signature = bytes.fromhex(signature_hex)
                public_key.verify(signature, digest, ec.ECDSA(hashes.SHA256()))
                valid_signatures += 1
            except Exception:
                continue

        return valid_signatures >= self.threshold
