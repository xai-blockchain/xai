import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from xai.wallet.multisig_wallet import MultiSigWallet


def _generate_keypair():
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_bytes.hex()


def _create_wallet(owner_count: int = 3, threshold: int = 2):
    owners = [_generate_keypair() for _ in range(owner_count)]
    privates = [p for p, _ in owners]
    publics = [pub for _, pub in owners]
    wallet = MultiSigWallet(public_keys=publics, threshold=threshold)
    return wallet, privates, publics


def _sign_payload(private_key, payload: bytes) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(payload)
    hashed = digest.finalize()
    signature = private_key.sign(hashed, ec.ECDSA(hashes.SHA256()))
    return signature.hex()


def test_create_transaction_assigns_nonce_and_sequence():
    wallet, _, _ = _create_wallet()
    tx1 = wallet.create_transaction("tx1", {"amount": 10})
    tx2 = wallet.create_transaction("tx2", {"amount": 20})

    assert tx1["nonce"] == 0
    assert tx1["sequence"] == 1
    assert tx2["nonce"] == 1
    assert tx2["sequence"] == 2


def test_finalized_nonce_cannot_be_reused():
    wallet, privs, publics = _create_wallet()
    tx = wallet.create_transaction("tx1", {"amount": 5})
    payload = wallet._serialize_for_signing(tx)  # pylint: disable=protected-access
    sigs = [
        _sign_payload(privs[0], payload),
        _sign_payload(privs[1], payload),
    ]

    wallet.add_partial_signature("tx1", publics[0], sigs[0])
    wallet.add_partial_signature("tx1", publics[1], sigs[1])
    wallet.finalize_transaction("tx1")

    with pytest.raises(ValueError, match="Nonce .* already used"):
        wallet.create_transaction("tx-replay", {"amount": 5}, nonce=0)


def test_pending_nonce_conflict_is_rejected():
    wallet, _, _ = _create_wallet()
    wallet.create_transaction("tx1", {"amount": 3})
    with pytest.raises(ValueError, match="Nonce .* already used"):
        wallet.create_transaction("tx2", {"amount": 4}, nonce=0)


def test_signatures_bound_to_nonce_and_sequence():
    wallet, privs, publics = _create_wallet()
    tx = wallet.create_transaction("tx1", {"amount": 5})

    # Forge signature against legacy payload lacking nonce metadata.
    legacy_payload = json.dumps({"tx_data": tx["tx_data"]}, sort_keys=True).encode()
    digest = hashes.Hash(hashes.SHA256())
    digest.update(legacy_payload)
    legacy_hash = digest.finalize()
    forged_sig = privs[0].sign(legacy_hash, ec.ECDSA(hashes.SHA256())).hex()

    with pytest.raises(ValueError, match="Invalid signature"):
        wallet.add_partial_signature("tx1", publics[0], forged_sig)

    # Valid signature using canonical payload succeeds.
    payload = wallet._serialize_for_signing(tx)  # pylint: disable=protected-access
    valid_sig = _sign_payload(privs[0], payload)
    status = wallet.add_partial_signature("tx1", publics[0], valid_sig)
    assert status["signatures_collected"] == 1
