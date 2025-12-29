import json

from ecdsa import SigningKey, SECP256k1

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager


def _sign_payload(sk: SigningKey, payload_data):
    material = {
        "height": int(payload_data["height"]),
        "block_hash": str(payload_data["block_hash"]),
        "state_hash": str(payload_data["state_hash"]),
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib
    digest = hashlib.sha256(blob).digest()
    return sk.sign_digest(digest).hex()


def test_checkpoint_signature_honors_trusted_signer():
    sk = SigningKey.generate(curve=SECP256k1)
    pub_hex = sk.get_verifying_key().to_string().hex()
    payload = {
        "height": 10,
        "block_hash": "dead",
        "state_hash": "beef",
        "data": {},
        "pubkey": pub_hex,
        "work": 100,
    }
    payload["signature"] = _sign_payload(sk, payload)

    cfg = type("cfg", (), {"CHECKPOINT_QUORUM": 1, "TRUSTED_CHECKPOINT_PUBKEYS": [pub_hex]})
    mgr = CheckpointSyncManager(blockchain=type("bc", (), {"config": cfg})(), p2p_manager=None)
    assert mgr._validate_payload_signature(payload) is True

    # Tamper with signer
    other = SigningKey.generate(curve=SECP256k1)
    payload["signature"] = _sign_payload(other, payload)
    assert mgr._validate_payload_signature(payload) is False
