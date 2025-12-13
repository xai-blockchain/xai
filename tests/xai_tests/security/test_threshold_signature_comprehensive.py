"""
Comprehensive tests for Threshold Signature Scheme (TSS) security module.

Tests distributed key generation, threshold signing, signature combination,
participant management, and security properties.
"""

import pytest
from xai.security.threshold_signature import ThresholdSignatureScheme


@pytest.mark.security
class TestThresholdSignatureInitialization:
    """Test TSS initialization and configuration"""

    def test_init_valid_params(self):
        """Test initialization with valid parameters"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        assert tss.n_participants == 5
        assert tss.t_threshold == 3
        assert len(tss.private_key_shares) == 0
        assert tss.public_key == 0
        assert len(tss.message_signatures) == 0

    def test_init_threshold_equals_participants(self):
        """Test initialization with threshold equal to participants"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=5)
        assert tss.n_participants == 5
        assert tss.t_threshold == 5

    def test_init_threshold_one(self):
        """Test initialization with threshold of 1"""
        tss = ThresholdSignatureScheme(n_participants=10, t_threshold=1)
        assert tss.t_threshold == 1

    def test_init_threshold_greater_than_participants_raises_error(self):
        """Test that threshold > participants raises ValueError"""
        with pytest.raises(ValueError, match="Threshold .* must be between 1 and total participants"):
            ThresholdSignatureScheme(n_participants=3, t_threshold=4)

    def test_init_threshold_zero_raises_error(self):
        """Test that threshold of 0 raises ValueError"""
        with pytest.raises(ValueError, match="Threshold .* must be between 1 and total participants"):
            ThresholdSignatureScheme(n_participants=5, t_threshold=0)

    def test_init_negative_threshold_raises_error(self):
        """Test that negative threshold raises ValueError"""
        with pytest.raises(ValueError, match="Threshold .* must be between 1 and total participants"):
            ThresholdSignatureScheme(n_participants=5, t_threshold=-1)


@pytest.mark.security
class TestKeyShareGeneration:
    """Test distributed key share generation"""

    def test_generate_key_shares(self):
        """Test generating key shares for participants"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        assert len(tss.private_key_shares) == 5
        assert tss.public_key != 0

    def test_generate_key_shares_all_participants_have_shares(self):
        """Test that all participants receive key shares"""
        tss = ThresholdSignatureScheme(n_participants=7, t_threshold=4)
        tss.generate_key_shares()

        for i in range(1, 8):
            assert i in tss.private_key_shares

    def test_generate_key_shares_unique(self):
        """Test that all key shares are unique"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        shares = list(tss.private_key_shares.values())
        assert len(shares) == len(set(shares))

    def test_generate_key_shares_public_key_set(self):
        """Test that public key is set after generation"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)
        assert tss.public_key == 0
        tss.generate_key_shares()
        assert tss.public_key != 0

    def test_generate_key_shares_multiple_times(self):
        """Test generating key shares multiple times"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)

        tss.generate_key_shares()
        first_public_key = tss.public_key
        first_shares = dict(tss.private_key_shares)

        tss.generate_key_shares()
        second_public_key = tss.public_key
        second_shares = dict(tss.private_key_shares)

        # Should generate different keys
        assert first_public_key != second_public_key
        assert first_shares != second_shares

    def test_generate_key_shares_large_group(self):
        """Test key generation for large group"""
        tss = ThresholdSignatureScheme(n_participants=100, t_threshold=67)
        tss.generate_key_shares()

        assert len(tss.private_key_shares) == 100


@pytest.mark.security
class TestSignatureShares:
    """Test participant signature share generation"""

    def test_sign_share_success(self):
        """Test successful signature share creation"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "Test message"
        sig_share = tss.sign_share(1, message)

        assert sig_share is not None
        assert isinstance(sig_share, int)

    def test_sign_share_invalid_participant_raises_error(self):
        """Test signing with invalid participant raises ValueError"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        with pytest.raises(ValueError, match="does not have a key share"):
            tss.sign_share(10, "message")

    def test_sign_share_different_messages_different_signatures(self):
        """Test that different messages produce different signature shares"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        sig1 = tss.sign_share(1, "message1")
        sig2 = tss.sign_share(1, "message2")

        assert sig1 != sig2

    def test_sign_share_same_message_deterministic(self):
        """Test that signing same message produces same signature share"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        sig1 = tss.sign_share(1, "message")
        sig2 = tss.sign_share(1, "message")

        assert sig1 == sig2

    def test_sign_share_different_participants_different_shares(self):
        """Test that different participants produce different shares for same message"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "common message"
        sig1 = tss.sign_share(1, message)
        sig2 = tss.sign_share(2, message)

        assert sig1 != sig2

    def test_sign_share_all_participants_can_sign(self):
        """Test that all participants can create signature shares"""
        tss = ThresholdSignatureScheme(n_participants=7, t_threshold=4)
        tss.generate_key_shares()

        message = "message for all"
        signatures = []

        for i in range(1, 8):
            sig = tss.sign_share(i, message)
            signatures.append(sig)

        assert len(signatures) == 7
        assert len(set(signatures)) == 7

    def test_sign_share_stores_in_message_signatures(self):
        """Test that signature shares are stored correctly"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "stored message"
        tss.sign_share(1, message)

        assert message in tss.message_signatures
        assert 1 in tss.message_signatures[message]

    def test_sign_share_empty_message(self):
        """Test signing empty message"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)
        tss.generate_key_shares()

        sig = tss.sign_share(1, "")
        assert sig is not None

    def test_sign_share_long_message(self):
        """Test signing long message"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)
        tss.generate_key_shares()

        long_message = "x" * 10000
        sig = tss.sign_share(1, long_message)
        assert sig is not None


@pytest.mark.security
class TestSignatureCombination:
    """Test combining signature shares"""

    def test_combine_shares_success(self):
        """Test successful signature combination"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "test message"
        signed_shares = {}
        for i in range(1, 4):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined_sig = tss.combine_shares(message, signed_shares)
        assert combined_sig is not None

    def test_combine_shares_insufficient_raises_error(self):
        """Test that insufficient shares raises ValueError"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "test message"
        signed_shares = {}
        for i in range(1, 3):  # Only 2 shares, need 3
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        with pytest.raises(ValueError, match="Not enough signature shares"):
            tss.combine_shares(message, signed_shares)

    def test_combine_shares_exact_threshold(self):
        """Test combining exactly threshold number of shares"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "exact threshold"
        signed_shares = {}
        for i in range(1, 4):  # Exactly 3 shares
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined_sig = tss.combine_shares(message, signed_shares)
        assert combined_sig is not None

    def test_combine_shares_more_than_threshold(self):
        """Test combining more than threshold shares"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "more shares"
        signed_shares = {}
        for i in range(1, 6):  # All 5 shares
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined_sig = tss.combine_shares(message, signed_shares)
        assert combined_sig is not None

    def test_combine_shares_wrong_message_raises_error(self):
        """Test combining shares for wrong message raises error"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message1 = "first message"
        signed_shares = {}
        for i in range(1, 4):
            sig = tss.sign_share(i, message1)
            signed_shares[i] = sig

        with pytest.raises(ValueError, match="No signatures recorded for message"):
            tss.combine_shares("different message", signed_shares)

    def test_combine_shares_different_participant_subsets(self):
        """Test that different participant subsets can combine signatures"""
        tss = ThresholdSignatureScheme(n_participants=7, t_threshold=4)
        tss.generate_key_shares()

        message = "subset test"

        # Get all signatures
        all_sigs = {}
        for i in range(1, 8):
            sig = tss.sign_share(i, message)
            all_sigs[i] = sig

        # Combine with subset 1-4
        subset1 = {i: all_sigs[i] for i in range(1, 5)}
        combined1 = tss.combine_shares(message, subset1)

        # Combine with subset 4-7
        subset2 = {i: all_sigs[i] for i in range(4, 8)}
        combined2 = tss.combine_shares(message, subset2)

        assert combined1 is not None
        assert combined2 is not None


@pytest.mark.security
class TestThresholdVariations:
    """Test different threshold configurations"""

    def test_threshold_2_of_3(self):
        """Test 2-of-3 threshold signature"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)
        tss.generate_key_shares()

        message = "2-of-3"
        signed_shares = {}
        for i in range(1, 3):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined = tss.combine_shares(message, signed_shares)
        assert combined is not None

    def test_threshold_5_of_7(self):
        """Test 5-of-7 threshold signature"""
        tss = ThresholdSignatureScheme(n_participants=7, t_threshold=5)
        tss.generate_key_shares()

        message = "5-of-7"
        signed_shares = {}
        for i in range(1, 6):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined = tss.combine_shares(message, signed_shares)
        assert combined is not None

    def test_threshold_n_of_n(self):
        """Test n-of-n threshold (all participants required)"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=5)
        tss.generate_key_shares()

        message = "all required"
        signed_shares = {}
        for i in range(1, 6):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined = tss.combine_shares(message, signed_shares)
        assert combined is not None

    def test_threshold_1_of_n(self):
        """Test 1-of-n threshold (any participant sufficient)"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=1)
        tss.generate_key_shares()

        message = "one sufficient"
        sig = tss.sign_share(3, message)
        signed_shares = {3: sig}

        combined = tss.combine_shares(message, signed_shares)
        assert combined is not None


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_single_participant(self):
        """Test TSS with single participant"""
        tss = ThresholdSignatureScheme(n_participants=1, t_threshold=1)
        tss.generate_key_shares()

        message = "solo"
        sig = tss.sign_share(1, message)
        combined = tss.combine_shares(message, {1: sig})

        assert combined is not None

    def test_large_participant_group(self):
        """Test TSS with large participant group"""
        tss = ThresholdSignatureScheme(n_participants=50, t_threshold=30)
        tss.generate_key_shares()

        assert len(tss.private_key_shares) == 50

    def test_unicode_message(self):
        """Test signing unicode message"""
        tss = ThresholdSignatureScheme(n_participants=3, t_threshold=2)
        tss.generate_key_shares()

        message = "测试消息 🔐"
        signed_shares = {}
        for i in range(1, 3):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        combined = tss.combine_shares(message, signed_shares)
        assert combined is not None

    def test_multiple_messages_same_participants(self):
        """Test signing multiple different messages"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        messages = ["msg1", "msg2", "msg3"]
        for msg in messages:
            signed_shares = {}
            for i in range(1, 4):
                sig = tss.sign_share(i, msg)
                signed_shares[i] = sig

            combined = tss.combine_shares(msg, signed_shares)
            assert combined is not None

    def test_participant_id_boundary(self):
        """Test that participant IDs start from 1"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        # IDs should be 1-5, not 0-4
        assert 0 not in tss.private_key_shares
        assert 1 in tss.private_key_shares
        assert 5 in tss.private_key_shares
        assert 6 not in tss.private_key_shares


@pytest.mark.security
class TestSecurityProperties:
    """Test security-related properties"""

    def test_private_key_shares_distributed(self):
        """Test that private key is distributed among shares"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        # No single share should equal the public key
        for share in tss.private_key_shares.values():
            assert share != tss.public_key

    def test_signature_shares_different_per_participant(self):
        """Test that each participant produces unique signature share"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        message = "security test"
        shares = []
        for i in range(1, 6):
            sig = tss.sign_share(i, message)
            shares.append(sig)

        # All shares should be unique
        assert len(shares) == len(set(shares))

    def test_cannot_forge_with_fewer_shares(self):
        """Test that fewer than threshold shares cannot produce valid signature"""
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=4)
        tss.generate_key_shares()

        message = "forge test"
        # Get only 3 shares (less than threshold of 4)
        signed_shares = {}
        for i in range(1, 4):
            sig = tss.sign_share(i, message)
            signed_shares[i] = sig

        # Should raise error
        with pytest.raises(ValueError):
            tss.combine_shares(message, signed_shares)


@pytest.mark.security
class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_multi_sig_wallet_scenario(self):
        """Test multi-signature wallet scenario"""
        # 3-of-5 multisig wallet
        tss = ThresholdSignatureScheme(n_participants=5, t_threshold=3)
        tss.generate_key_shares()

        # Create transaction
        transaction = "transfer 100 coins to Alice"

        # 3 participants approve
        approvals = {}
        for participant_id in [1, 3, 5]:
            sig = tss.sign_share(participant_id, transaction)
            approvals[participant_id] = sig

        # Combine signatures
        final_signature = tss.combine_shares(transaction, approvals)
        assert final_signature is not None

    def test_distributed_oracle_scenario(self):
        """Test distributed oracle signing"""
        # 7-of-10 oracle nodes
        tss = ThresholdSignatureScheme(n_participants=10, t_threshold=7)
        tss.generate_key_shares()

        # Oracle price data
        price_data = "BTC/USD: 45000"

        # 7 oracle nodes sign
        oracle_sigs = {}
        for i in range(1, 8):
            sig = tss.sign_share(i, price_data)
            oracle_sigs[i] = sig

        # Combine oracle signatures
        oracle_signature = tss.combine_shares(price_data, oracle_sigs)
        assert oracle_signature is not None

    def test_governance_voting_scenario(self):
        """Test governance voting with threshold signatures"""
        # 51-of-100 governance threshold
        tss = ThresholdSignatureScheme(n_participants=100, t_threshold=51)
        tss.generate_key_shares()

        proposal = "Upgrade protocol to v2.0"

        # 51 validators approve
        approvals = {}
        for i in range(1, 52):
            sig = tss.sign_share(i, proposal)
            approvals[i] = sig

        # Combine votes
        governance_sig = tss.combine_shares(proposal, approvals)
        assert governance_sig is not None

    def test_key_ceremony_scenario(self):
        """Test distributed key generation ceremony"""
        # 5-of-9 for secure key generation
        tss = ThresholdSignatureScheme(n_participants=9, t_threshold=5)
        tss.generate_key_shares()

        # Verify all participants have shares
        assert len(tss.private_key_shares) == 9

        # Verify threshold works
        message = "master key derivation"
        sigs = {}
        for i in range(1, 6):
            sig = tss.sign_share(i, message)
            sigs[i] = sig

        combined = tss.combine_shares(message, sigs)
        assert combined is not None
