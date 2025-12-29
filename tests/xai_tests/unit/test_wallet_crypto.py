import json

import pytest

from xai.core.wallet import Wallet
from xai.core.security.crypto_utils import generate_secp256k1_keypair_hex


def test_encrypt_payload_roundtrip():
    priv, _ = generate_secp256k1_keypair_hex()
    wallet = Wallet(private_key=priv)
    password = "supersecurepassword"
    payload = wallet._encrypt_payload("sensitive-data", password)
    decrypted = wallet._decrypt_payload(payload, password)
    assert decrypted == "sensitive-data"

    with pytest.raises(ValueError):
        wallet._decrypt_payload(payload, "wrong-password")


def test_save_load_encrypted_hmac_integrity(tmp_path):
    priv, _ = generate_secp256k1_keypair_hex()
    wallet = Wallet(private_key=priv)
    wallet_file = tmp_path / "wallet.json"
    password = "complex-passphrase-123"

    wallet.save_to_file(str(wallet_file), password=password)
    loaded = Wallet.load_from_file(str(wallet_file), password=password)
    assert loaded.private_key == wallet.private_key
    assert loaded.address == wallet.address

    # Tamper with on-disk data to trigger HMAC verification failure
    content = json.loads(wallet_file.read_text())
    content["data"]["address"] = "tampered"
    wallet_file.write_text(json.dumps(content))

    with pytest.raises(ValueError):
        Wallet.load_from_file(str(wallet_file), password=password)
