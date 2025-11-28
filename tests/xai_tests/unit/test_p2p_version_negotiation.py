from xai.core.p2p_security import (
    HEADER_VERSION,
    HEADER_FEATURES,
    P2PSecurityConfig,
    sign_headers,
    verify_headers,
)


def test_p2p_header_version_required():
    payload = b"msg"
    # Missing version should be rejected
    ok, reason = verify_headers({}, payload)
    assert ok is False
    assert reason == "missing_protocol_version"


def test_p2p_header_version_supported():
    payload = b"msg"
    headers = {
        HEADER_VERSION: P2PSecurityConfig.PROTOCOL_VERSION,
        "X-Node-Pub": "pub",
        "X-Node-Signature": "sig",
        "X-Node-Timestamp": "1",
        "X-Node-Nonce": "n",
    }
    ok, reason = verify_headers(headers, payload)
    assert ok is False
    assert reason in {
        "missing_signature_headers",
        "timestamp_out_of_window",
    }  # missing sig data still fails gracefully


def test_sign_headers_includes_version():
    priv = "a" * 64
    pub = "b" * 66
    headers = sign_headers(priv, pub, b"hello")
    assert headers[HEADER_VERSION] == P2PSecurityConfig.PROTOCOL_VERSION
    assert set(headers[HEADER_FEATURES].split(",")) == P2PSecurityConfig.SUPPORTED_FEATURES


def test_verify_headers_rejects_bad_feature():
    payload = b"msg"
    headers = {
        HEADER_VERSION: P2PSecurityConfig.PROTOCOL_VERSION,
        "X-Node-Pub": "pub",
        "X-Node-Signature": "sig",
        "X-Node-Timestamp": "1",
        "X-Node-Nonce": "n",
        HEADER_FEATURES: "quic,unknownfeature",
    }
    ok, reason = verify_headers(headers, payload)
    assert ok is False
    assert reason == "unsupported_feature"
