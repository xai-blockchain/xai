import json
import time

from xai.network.peer_manager import PeerEncryption


def test_session_hmac_validation():
    enc = PeerEncryption()
    payload = {"type": "ping", "session_id": "sess1", "payload": {"msg": "hi"}}
    signed = enc.create_signed_message(payload)
    verified = enc.verify_signed_message(signed)
    assert verified is not None
    assert verified["payload"]["payload"]["msg"] == "hi"
    assert verified["sender_id"] == enc._node_identity_fingerprint()

    # Tamper with HMAC
    tampered = json.loads(signed.decode("utf-8"))
    tampered["message"]["hmac"] = "00" * 32
    tampered_bytes = json.dumps(tampered).encode("utf-8")
    assert enc.verify_signed_message(tampered_bytes) is None


def test_session_expiry():
    enc = PeerEncryption()
    enc.session_ttl_seconds = 1
    payload = {"type": "ping", "session_id": "sess2", "payload": {"msg": "hi"}}
    signed = enc.create_signed_message(payload)
    time.sleep(1.2)
    assert enc.verify_signed_message(signed) is None
