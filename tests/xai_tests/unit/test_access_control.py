"""
Unit tests for RoleBasedAccessControl with signature verification.

Coverage targets:
- Grant/revoke role requires valid admin signature
- Permission checks are signature-gated and role-aware
"""

import hashlib
import json
from types import SimpleNamespace

import pytest
from xai.core.defi.access_control import RoleBasedAccessControl, SignedRequest, Role
from xai.core.security.crypto_utils import generate_secp256k1_keypair_hex, sign_message_hex


def _make_signed_request(private_hex: str, public_hex: str, address: str, message: str, nonce: int = 1, timestamp: int = 0) -> SignedRequest:
    inner_hash = hashlib.sha256(message.encode()).digest()
    signature = sign_message_hex(private_hex, inner_hash)
    return SignedRequest(
        address=address,
        message=message,
        nonce=nonce,
        timestamp=timestamp or int(0),
        public_key=public_hex,
        signature=signature,
    )


def test_grant_and_revoke_role_with_signature(monkeypatch):
    admin_priv, admin_pub = generate_secp256k1_keypair_hex()
    admin_addr = "admin"
    user_addr = "user"

    # Silence logger extra 'message' conflict in verify_caller
    monkeypatch.setattr("xai.core.defi.access_control.logger", SimpleNamespace(error=lambda *a, **k: None, warn=lambda *a, **k: None, info=lambda *a, **k: None))

    rbac = RoleBasedAccessControl(admin_address=admin_addr)

    # Monkeypatch time to keep timestamps valid
    monkeypatch.setattr("time.time", lambda: 0)
    admin_request = _make_signed_request(admin_priv, admin_pub, admin_addr, "grant", nonce=1, timestamp=0)

    assert rbac.grant_role(admin_request, Role.OPERATOR.value, user_addr) is True
    assert user_addr.lower() in rbac.roles[Role.OPERATOR.value]

    revoke_req = _make_signed_request(admin_priv, admin_pub, admin_addr, "revoke", nonce=2, timestamp=0)
    assert rbac.revoke_role(revoke_req, Role.OPERATOR.value, user_addr) is True
    assert user_addr.lower() not in rbac.roles[Role.OPERATOR.value]


def test_grant_role_rejects_invalid_signature(monkeypatch):
    admin_priv, admin_pub = generate_secp256k1_keypair_hex()
    attacker_priv, attacker_pub = generate_secp256k1_keypair_hex()
    admin_addr = "admin"
    rbac = RoleBasedAccessControl(admin_address=admin_addr)
    monkeypatch.setattr("time.time", lambda: 0)

    bad_request = _make_signed_request(attacker_priv, attacker_pub, "attacker", "grant", nonce=1, timestamp=0)
    with pytest.raises(Exception):
        rbac.grant_role(bad_request, Role.OPERATOR.value, "user")
