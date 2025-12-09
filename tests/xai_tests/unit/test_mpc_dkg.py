"""
Unit tests for MPC-DKG and ShamirSecretSharing.

Coverage targets:
- Share generation validation
- Secret reconstruction correctness
- DKG result verification and partial signature combination
"""

import hashlib

import pytest

from xai.security.mpc_dkg import ShamirSecretSharing, MPCDistributedKeyGeneration, SecretShare


def test_generate_and_reconstruct_secret():
    sss = ShamirSecretSharing()
    secret = 12345
    shares = sss.generate_shares(secret, threshold=2, num_shares=3)
    assert len(shares) == 3
    assert sss.verify_share(shares[0]) is True
    reconstructed = sss.reconstruct_secret(shares[:2])
    assert reconstructed == secret

    with pytest.raises(ValueError):
        sss.generate_shares(secret, threshold=4, num_shares=3)


def test_dkg_generation_and_reconstruction():
    dkg = MPCDistributedKeyGeneration()
    results, common_pub = dkg.generate_distributed_keys(num_participants=3, threshold=2)
    assert len(results) == 3
    assert all(dkg.verify_dkg_result(r) for r in results)

    reconstructed_priv = dkg.reconstruct_private_key(results[:2])
    assert b"PRIVATE KEY" in reconstructed_priv


def test_combine_partial_signatures_threshold():
    dkg = MPCDistributedKeyGeneration()
    partials = [(1, b"a"), (2, b"b")]
    combined = dkg.combine_partial_signatures(partials, threshold=2)
    assert combined == hashlib.sha256(b"ab").digest()
    with pytest.raises(ValueError):
        dkg.combine_partial_signatures(partials[:1], threshold=2)
