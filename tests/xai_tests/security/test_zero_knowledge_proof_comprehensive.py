"""
Comprehensive tests for production Zero-Knowledge Proof implementation.

Tests all ZKP protocols:
1. Schnorr protocol (discrete log knowledge)
2. Pedersen commitments (hiding and binding)
3. Range proofs (value in range)
4. Set membership proofs (membership without revealing element)
"""

import pytest
import secrets
from xai.security.zero_knowledge_proof import (
    ZeroKnowledgeProof,
    SchnorrProof,
    PedersenCommitment,
    RangeProof,
    MembershipProof,
    ZKP_Simulator,  # Legacy class
)


@pytest.mark.security
class TestSchnorrProtocol:
    """Test Schnorr protocol for proving knowledge of discrete logarithm."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_key_generation(self, zkp):
        """Test Schnorr key pair generation."""
        private_key, public_key = zkp.schnorr_generate_keypair()

        # Verify private key is in valid range
        assert 0 < private_key < zkp.n

        # Verify public key is a valid point
        assert isinstance(public_key, tuple)
        assert len(public_key) == 2
        assert isinstance(public_key[0], int)
        assert isinstance(public_key[1], int)

        # Verify public key = private_key * G
        expected_public_key = zkp.curve.multiply(zkp.G, private_key)
        assert public_key == expected_public_key

    def test_prove_and_verify_knowledge(self, zkp):
        """Test proving and verifying knowledge of discrete log."""
        private_key, _ = zkp.schnorr_generate_keypair()

        # Generate proof
        public_key, proof = zkp.schnorr_prove_knowledge(private_key, "test message")

        # Verify proof structure
        assert isinstance(proof, SchnorrProof)
        assert isinstance(proof.commitment, int)
        assert isinstance(proof.challenge, int)
        assert isinstance(proof.response, int)

        # Verify proof is valid
        assert zkp.schnorr_verify_knowledge(public_key, proof, "test message")

    def test_proof_fails_with_wrong_public_key(self, zkp):
        """Test that proof verification fails with wrong public key."""
        private_key, _ = zkp.schnorr_generate_keypair()
        _, wrong_public_key = zkp.schnorr_generate_keypair()

        # Generate proof with correct key
        public_key, proof = zkp.schnorr_prove_knowledge(private_key, "test")

        # Verification should fail with wrong public key
        assert not zkp.schnorr_verify_knowledge(wrong_public_key, proof, "test")

    def test_proof_fails_with_wrong_message(self, zkp):
        """Test that proof verification fails with wrong message."""
        private_key, _ = zkp.schnorr_generate_keypair()

        # Generate proof with one message
        public_key, proof = zkp.schnorr_prove_knowledge(private_key, "message1")

        # Verification should fail with different message
        assert not zkp.schnorr_verify_knowledge(public_key, proof, "message2")

    def test_private_key_knowledge_helper(self, zkp):
        """Test helper method for proving private key knowledge."""
        private_key = secrets.randbelow(zkp.n - 1) + 1

        # Use helper method
        public_key, proof = zkp.prove_private_key_knowledge(private_key)

        # Verify using helper method
        assert zkp.verify_private_key_knowledge(public_key, proof)

    def test_multiple_proofs_different(self, zkp):
        """Test that multiple proofs for same key are different (randomized)."""
        private_key, _ = zkp.schnorr_generate_keypair()

        # Generate two proofs
        public_key1, proof1 = zkp.schnorr_prove_knowledge(private_key, "test")
        public_key2, proof2 = zkp.schnorr_prove_knowledge(private_key, "test")

        # Public keys should be the same
        assert public_key1 == public_key2

        # But proofs should be different (due to random nonce)
        assert proof1.commitment != proof2.commitment or \
               proof1.challenge != proof2.challenge or \
               proof1.response != proof2.response


@pytest.mark.security
class TestPedersenCommitments:
    """Test Pedersen commitment scheme."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_commit_to_value(self, zkp):
        """Test creating a commitment to a value."""
        value = 42

        commitment = zkp.pedersen_commit(value)

        # Verify commitment structure
        assert isinstance(commitment, PedersenCommitment)
        assert isinstance(commitment.commitment, tuple)
        assert len(commitment.commitment) == 2
        assert commitment.blinding_factor is not None
        assert 0 < commitment.blinding_factor < zkp.n

    def test_verify_commitment(self, zkp):
        """Test verifying a commitment."""
        value = 12345

        commitment = zkp.pedersen_commit(value)

        # Should verify with correct value
        assert zkp.pedersen_verify_commitment(commitment, value)

    def test_commitment_fails_wrong_value(self, zkp):
        """Test that commitment verification fails with wrong value."""
        value = 100

        commitment = zkp.pedersen_commit(value)

        # Should fail with wrong value
        assert not zkp.pedersen_verify_commitment(commitment, value + 1)
        assert not zkp.pedersen_verify_commitment(commitment, value - 1)

    def test_commitments_are_hiding(self, zkp):
        """Test that commitments hide the value (different each time)."""
        value = 999

        # Create two commitments to same value
        commitment1 = zkp.pedersen_commit(value)
        commitment2 = zkp.pedersen_commit(value)

        # Commitments should be different (due to random blinding factor)
        assert commitment1.commitment != commitment2.commitment

    def test_prove_knowledge_of_committed_value(self, zkp):
        """Test proving knowledge of a committed value."""
        value = 555

        commitment = zkp.pedersen_commit(value)
        proof = zkp.pedersen_prove_knowledge(commitment, value)

        # Verify proof structure
        assert isinstance(proof, dict)
        assert 'commitment_point' in proof
        assert 'R' in proof
        assert 'challenge' in proof
        assert 'response_v' in proof
        assert 'response_r' in proof

        # Verify commitment point matches
        assert proof['commitment_point'] == commitment.commitment

    def test_commitment_binding_property(self, zkp):
        """Test that commitments are binding (can't open to different value)."""
        value = 777

        commitment = zkp.pedersen_commit(value)

        # Try to verify with different values - should all fail
        for wrong_value in [value - 1, value + 1, 0, value * 2]:
            assert not zkp.pedersen_verify_commitment(commitment, wrong_value)


@pytest.mark.security
class TestRangeProofs:
    """Test range proof protocol."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_create_range_proof_valid(self, zkp):
        """Test creating a range proof for valid value."""
        value = 50
        min_val = 0
        max_val = 100

        proof = zkp.range_proof_create(value, min_val, max_val)

        # Verify proof created successfully
        assert proof is not None
        assert isinstance(proof, RangeProof)
        assert isinstance(proof.commitment, tuple)
        assert 'min_value' in proof.proof_data
        assert 'max_value' in proof.proof_data

    def test_range_proof_at_boundaries(self, zkp):
        """Test range proofs at boundary values."""
        min_val = 10
        max_val = 90

        # Test at minimum
        proof_min = zkp.range_proof_create(min_val, min_val, max_val)
        assert proof_min is not None

        # Test at maximum
        proof_max = zkp.range_proof_create(max_val, min_val, max_val)
        assert proof_max is not None

    def test_range_proof_out_of_range_fails(self, zkp):
        """Test that out-of-range values fail to create proof."""
        min_val = 10
        max_val = 90

        # Below minimum
        proof_low = zkp.range_proof_create(min_val - 1, min_val, max_val)
        assert proof_low is None

        # Above maximum
        proof_high = zkp.range_proof_create(max_val + 1, min_val, max_val)
        assert proof_high is None

    def test_verify_range_proof(self, zkp):
        """Test verifying a range proof."""
        value = 500
        max_val = 1000

        proof = zkp.range_proof_create(value, 0, max_val)
        assert proof is not None

        # Verify proof
        assert zkp.range_proof_verify(proof, value)

    def test_range_proof_fails_wrong_value(self, zkp):
        """Test that range proof verification fails with wrong value."""
        value = 50
        min_val = 0
        max_val = 100

        proof = zkp.range_proof_create(value, min_val, max_val)
        assert proof is not None

        # Should fail with values outside range
        assert not zkp.range_proof_verify(proof, min_val - 1)
        assert not zkp.range_proof_verify(proof, max_val + 1)

    def test_transaction_validity_proof(self, zkp):
        """Test proving transaction validity without revealing amount."""
        amount = 250
        max_balance = 1000

        # Create proof that amount is valid
        proof = zkp.prove_transaction_validity(amount, max_balance)

        assert proof is not None
        assert zkp.range_proof_verify(proof, amount)

    def test_transaction_validity_fails_overdraft(self, zkp):
        """Test that overdraft transaction fails to create proof."""
        amount = 1500  # More than max
        max_balance = 1000

        # Should fail to create proof
        proof = zkp.prove_transaction_validity(amount, max_balance)
        assert proof is None


@pytest.mark.security
class TestMembershipProofs:
    """Test set membership proof protocol."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_create_membership_proof(self, zkp):
        """Test creating a membership proof."""
        valid_set = [100, 200, 300, 400, 500]
        element = 300

        proof = zkp.membership_proof_create(element, valid_set)

        # Verify proof created
        assert proof is not None
        assert isinstance(proof, MembershipProof)
        assert 'commitments' in proof.proof_data
        assert 'ring_hash' in proof.proof_data
        assert 'set_size' in proof.proof_data

    def test_membership_proof_for_first_element(self, zkp):
        """Test membership proof for first element in set."""
        valid_set = [10, 20, 30, 40]
        element = 10

        proof = zkp.membership_proof_create(element, valid_set)
        assert proof is not None

        # Verify proof
        assert zkp.membership_proof_verify(proof, valid_set)

    def test_membership_proof_for_last_element(self, zkp):
        """Test membership proof for last element in set."""
        valid_set = [10, 20, 30, 40]
        element = 40

        proof = zkp.membership_proof_create(element, valid_set)
        assert proof is not None

        # Verify proof
        assert zkp.membership_proof_verify(proof, valid_set)

    def test_membership_proof_fails_non_member(self, zkp):
        """Test that non-member cannot create proof."""
        valid_set = [100, 200, 300]
        non_member = 999

        # Should fail to create proof
        proof = zkp.membership_proof_create(non_member, valid_set)
        assert proof is None

    def test_verify_membership_proof(self, zkp):
        """Test verifying a membership proof."""
        authorized_users = [1001, 1002, 1003, 1004, 1005]
        user_id = 1003

        proof = zkp.membership_proof_create(user_id, authorized_users)
        assert proof is not None

        # Verify proof
        assert zkp.membership_proof_verify(proof, authorized_users)

    def test_membership_proof_wrong_set_fails(self, zkp):
        """Test that proof fails with wrong set (different size)."""
        set1 = [100, 200, 300]
        set2 = [100, 200, 300, 400]  # Different size
        element = 100

        # Create proof for set1
        proof = zkp.membership_proof_create(element, set1)
        assert proof is not None

        # Should fail to verify with set2 (different size)
        # Note: Current implementation checks ring_hash which depends on commitments
        # A production implementation would have stronger verification
        assert not zkp.membership_proof_verify(proof, set2)

    def test_membership_proof_different_set_sizes_fails(self, zkp):
        """Test that proof fails with different set size."""
        set1 = [100, 200, 300]
        set2 = [100, 200, 300, 400]  # Different size
        element = 100

        # Create proof for set1
        proof = zkp.membership_proof_create(element, set1)
        assert proof is not None

        # Should fail to verify with different sized set
        assert not zkp.membership_proof_verify(proof, set2)


@pytest.mark.security
class TestUtilityFunctions:
    """Test utility functions."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_hash_to_scalar(self, zkp):
        """Test hashing data to scalar."""
        data = b"test data"

        scalar = zkp.hash_to_scalar(data)

        # Verify scalar is in valid range
        assert 0 <= scalar < zkp.n
        assert isinstance(scalar, int)

    def test_hash_to_scalar_deterministic(self, zkp):
        """Test that hash_to_scalar is deterministic."""
        data = b"test data"

        scalar1 = zkp.hash_to_scalar(data)
        scalar2 = zkp.hash_to_scalar(data)

        # Should produce same result
        assert scalar1 == scalar2

    def test_hash_to_scalar_different_data(self, zkp):
        """Test that different data produces different scalars."""
        data1 = b"test data 1"
        data2 = b"test data 2"

        scalar1 = zkp.hash_to_scalar(data1)
        scalar2 = zkp.hash_to_scalar(data2)

        # Should produce different results
        assert scalar1 != scalar2


@pytest.mark.security
class TestLegacyCompatibility:
    """Test legacy ZKP_Simulator for backwards compatibility."""

    @pytest.fixture
    def simulator(self):
        """Create legacy simulator instance."""
        return ZKP_Simulator()

    def test_legacy_generate_proof(self, simulator):
        """Test legacy proof generation."""
        secret = 12345
        statement = "test statement"

        proof, nonce = simulator.generate_proof(secret, statement)

        # Verify proof format
        assert isinstance(proof, str)
        assert isinstance(nonce, str)
        assert ':' in proof  # Should contain colons as separators

    def test_legacy_verify_proof(self, simulator):
        """Test legacy proof verification."""
        secret = 12345
        statement = "test statement"

        # Generate proof
        proof, nonce = simulator.generate_proof(secret, statement)

        # Verify proof
        is_valid = simulator.verify_proof(proof, statement, nonce, secret)
        assert is_valid

    def test_legacy_verify_fails_wrong_secret(self, simulator):
        """Test that legacy verification fails with wrong secret."""
        secret = 12345
        wrong_secret = 54321
        statement = "test statement"

        # Generate proof
        proof, nonce = simulator.generate_proof(secret, statement)

        # Should fail with wrong secret
        is_valid = simulator.verify_proof(proof, statement, nonce, wrong_secret)
        assert not is_valid


@pytest.mark.security
class TestZKPSecurityProperties:
    """Test security properties of ZKP protocols."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_schnorr_soundness(self, zkp):
        """Test that invalid Schnorr proofs are rejected (soundness)."""
        private_key, public_key = zkp.schnorr_generate_keypair()

        # Create valid proof
        _, valid_proof = zkp.schnorr_prove_knowledge(private_key, "test")

        # Modify proof (break soundness)
        invalid_proof = SchnorrProof(
            commitment=valid_proof.commitment,
            challenge=valid_proof.challenge,
            response=(valid_proof.response + 1) % zkp.n  # Wrong response
        )

        # Should reject invalid proof
        assert not zkp.schnorr_verify_knowledge(public_key, invalid_proof, "test")

    def test_pedersen_hiding(self, zkp):
        """Test hiding property of Pedersen commitments."""
        value1 = 100
        value2 = 999999  # Very different value

        # Create commitments
        comm1 = zkp.pedersen_commit(value1)
        comm2 = zkp.pedersen_commit(value2)

        # Commitment points should not reveal relationship between values
        # (Both are valid elliptic curve points with no obvious correlation)
        assert isinstance(comm1.commitment, tuple)
        assert isinstance(comm2.commitment, tuple)
        assert comm1.commitment != comm2.commitment

    def test_commitment_binding(self, zkp):
        """Test binding property - can't open to two different values."""
        value = 42

        commitment = zkp.pedersen_commit(value)

        # Only the correct value should verify
        assert zkp.pedersen_verify_commitment(commitment, value)

        # Try many other values - none should verify
        for wrong_value in range(0, 100):
            if wrong_value != value:
                assert not zkp.pedersen_verify_commitment(commitment, wrong_value)

    def test_zero_knowledge_property(self, zkp):
        """Test that proofs don't reveal the secret (zero-knowledge property)."""
        private_key, public_key = zkp.schnorr_generate_keypair()

        # Generate proof
        _, proof = zkp.schnorr_prove_knowledge(private_key, "test")

        # Proof should not contain the private key
        # (This is a basic check - in theory proofs reveal nothing)
        assert proof.commitment != private_key
        assert proof.challenge != private_key
        assert proof.response != private_key

        # Even if we know the proof values, we can't recover private_key
        # (discrete log is hard)


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def zkp(self):
        """Create ZKP instance."""
        return ZeroKnowledgeProof()

    def test_commit_to_zero(self, zkp):
        """Test committing to zero value."""
        commitment = zkp.pedersen_commit(0)

        assert commitment is not None
        assert zkp.pedersen_verify_commitment(commitment, 0)

    def test_commit_to_large_value(self, zkp):
        """Test committing to very large value."""
        large_value = zkp.n - 1  # Maximum value

        commitment = zkp.pedersen_commit(large_value)

        assert commitment is not None
        assert zkp.pedersen_verify_commitment(commitment, large_value)

    def test_range_proof_single_value(self, zkp):
        """Test range proof where min = max = value."""
        value = 42

        proof = zkp.range_proof_create(value, value, value)

        assert proof is not None
        assert zkp.range_proof_verify(proof, value)

    def test_membership_single_element_set(self, zkp):
        """Test membership proof with single-element set."""
        element = 123
        singleton_set = [element]

        proof = zkp.membership_proof_create(element, singleton_set)

        assert proof is not None
        assert zkp.membership_proof_verify(proof, singleton_set)

    def test_large_membership_set(self, zkp):
        """Test membership proof with large set."""
        large_set = list(range(100, 200))  # 100 elements
        element = 150

        proof = zkp.membership_proof_create(element, large_set)

        assert proof is not None
        assert zkp.membership_proof_verify(proof, large_set)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
