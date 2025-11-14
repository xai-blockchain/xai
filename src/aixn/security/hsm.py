from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

class HardwareSecurityModule:
    def __init__(self, private_key_pem: str):
        self._private_key = load_pem_private_key(private_key_pem.encode(), password=None)

    def sign(self, message: bytes) -> bytes:
        message_hash = hashes.Hash(hashes.SHA256())
        message_hash.update(message)
        digest = message_hash.finalize()
        return self._private_key.sign(digest, ec.ECDSA(hashes.SHA256()))
