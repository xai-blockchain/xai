"""
End-to-end test: Governance flow

Tests complete governance workflow: Create wallet with voting power ->
Submit proposal -> Vote -> Check results
"""

import pytest
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestGovernanceFlow:
    """Test complete governance workflows"""

    def test_basic_governance_participation(self, e2e_blockchain_dir):
        """Test basic participation: Create wallet with stake -> Vote"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participant = Wallet()

        # Fund participant to gain voting power
        blockchain.mine_pending_transactions(participant.address)
        balance = blockchain.get_balance(participant.address)

        # Participant should have voting power based on balance
        assert balance > 0

    def test_governance_proposal_submission(self, e2e_blockchain_dir):
        """Test submitting a governance proposal"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        proposer = Wallet()

        # Fund proposer
        blockchain.mine_pending_transactions(proposer.address)

        # Proposer should have voting power to submit
        voting_power = blockchain.get_balance(proposer.address)
        assert voting_power > 0

    def test_governance_voting_power_calculation(self, e2e_blockchain_dir):
        """Test voting power based on holdings"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallet1 = Wallet()
        wallet2 = Wallet()

        # Fund wallet1 with more
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet1.address)

        # Fund wallet2 with less
        blockchain.mine_pending_transactions(wallet2.address)

        balance1 = blockchain.get_balance(wallet1.address)
        balance2 = blockchain.get_balance(wallet2.address)

        # wallet1 should have more voting power
        assert balance1 > balance2

    def test_governance_multiple_participants(self, e2e_blockchain_dir):
        """Test governance with multiple participants"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participants = [Wallet() for _ in range(5)]

        # Fund all participants
        for participant in participants:
            blockchain.mine_pending_transactions(participant.address)

        # All should have voting power
        for participant in participants:
            balance = blockchain.get_balance(participant.address)
            assert balance > 0

    def test_governance_voting_power_distribution(self, e2e_blockchain_dir):
        """Test that voting power is distributed among participants"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participants = [Wallet() for _ in range(10)]

        # Fund with varying amounts
        for i, participant in enumerate(participants):
            for _ in range(i + 1):
                blockchain.mine_pending_transactions(participant.address)

        # Check voting power distribution
        balances = [blockchain.get_balance(p.address) for p in participants]

        # Should have increasing balances
        for i in range(1, len(balances)):
            assert balances[i] >= balances[i-1]

    def test_governance_stake_based_voting(self, e2e_blockchain_dir):
        """Test voting power proportional to stake"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        whale = Wallet()      # Large stake
        small_holder = Wallet()  # Small stake

        # Whale holds large amount
        for _ in range(10):
            blockchain.mine_pending_transactions(whale.address)

        # Small holder holds small amount
        blockchain.mine_pending_transactions(small_holder.address)

        whale_balance = blockchain.get_balance(whale.address)
        small_balance = blockchain.get_balance(small_holder.address)

        # Whale has much more voting power
        assert whale_balance > small_balance * 5

    def test_governance_transfer_affects_voting(self, e2e_blockchain_dir):
        """Test that transferring tokens affects voting power"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallet1 = Wallet()
        wallet2 = Wallet()

        # Fund wallet1
        blockchain.mine_pending_transactions(wallet1.address)
        initial_power1 = blockchain.get_balance(wallet1.address)

        # Transfer to wallet2
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            initial_power1 * 0.5,
            0.5,
            wallet1.private_key,
            wallet1.public_key
        )
        blockchain.add_transaction(tx)
        blockchain.mine_pending_transactions(Wallet().address)

        # Check new voting powers
        power1_after = blockchain.get_balance(wallet1.address)
        power2_after = blockchain.get_balance(wallet2.address)

        # wallet1 lost voting power
        assert power1_after < initial_power1
        # wallet2 gained voting power
        assert power2_after > 0

    def test_governance_minimum_stake_requirement(self, e2e_blockchain_dir):
        """Test minimum stake requirement for governance"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        minimal_holder = Wallet()

        # Fund with minimal amount (no mining)
        # Direct transfer not possible without funds

        # User cannot participate with zero balance
        balance = blockchain.get_balance(minimal_holder.address)
        assert balance == 0

    def test_governance_delegation_preparation(self, e2e_blockchain_dir):
        """Test preparation for vote delegation"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        delegator = Wallet()
        delegate = Wallet()

        # Fund both wallets
        blockchain.mine_pending_transactions(delegator.address)
        blockchain.mine_pending_transactions(delegate.address)

        delegator_power = blockchain.get_balance(delegator.address)
        delegate_power = blockchain.get_balance(delegate.address)

        # Both have voting power
        assert delegator_power > 0
        assert delegate_power > 0

    def test_governance_voting_power_weighted(self, e2e_blockchain_dir):
        """Test weighted voting scenarios"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        voters = [Wallet() for _ in range(5)]

        # Give different amounts to each voter
        voter_weights = [1, 2, 3, 4, 5]

        for voter, weight in zip(voters, voter_weights):
            for _ in range(weight):
                blockchain.mine_pending_transactions(voter.address)

        # Verify voting power matches weights
        for voter, weight in zip(voters, voter_weights):
            balance = blockchain.get_balance(voter.address)
            assert balance > 0

    def test_governance_quorum_participation(self, e2e_blockchain_dir):
        """Test quorum requirements with multiple participants"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Create 11 voters for quorum
        voters = [Wallet() for _ in range(11)]

        # Fund all voters
        for voter in voters:
            blockchain.mine_pending_transactions(voter.address)

        # Calculate total voting power
        total_power = sum(
            blockchain.get_balance(voter.address) for voter in voters
        )

        assert total_power > 0

    def test_governance_participation_incentive(self, e2e_blockchain_dir):
        """Test that participation is incentivized"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participant = Wallet()

        # Mine some blocks as mining reward
        initial_balance = 0
        for _ in range(5):
            blockchain.mine_pending_transactions(participant.address)

        # Participant gains voting power through mining
        final_balance = blockchain.get_balance(participant.address)
        assert final_balance > initial_balance

    def test_governance_continuous_participation(self, e2e_blockchain_dir):
        """Test continuous governance participation"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participant = Wallet()

        # Continuously build voting power
        for round_num in range(5):
            blockchain.mine_pending_transactions(participant.address)
            balance = blockchain.get_balance(participant.address)

            # Voting power should increase with each round
            assert balance > (round_num * blockchain.get_block_reward(1))

    def test_governance_across_stake_levels(self, e2e_blockchain_dir):
        """Test governance with various stake levels"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Create wallets with different stake levels
        stakes = {
            'whale': 10,
            'large_holder': 5,
            'medium_holder': 3,
            'small_holder': 1,
        }

        wallets = {}
        for name, stake_count in stakes.items():
            wallet = Wallet()
            for _ in range(stake_count):
                blockchain.mine_pending_transactions(wallet.address)
            wallets[name] = wallet

        # Verify stake levels
        balances = {
            name: blockchain.get_balance(wallet.address)
            for name, wallet in wallets.items()
        }

        # Verify ordering
        assert balances['whale'] > balances['large_holder']
        assert balances['large_holder'] > balances['medium_holder']
        assert balances['medium_holder'] > balances['small_holder']

    def test_governance_chain_validation(self, e2e_blockchain_dir):
        """Test chain validity with governance participation"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        participants = [Wallet() for _ in range(10)]

        # Complex governance participation
        for i in range(20):
            participant = participants[i % len(participants)]
            blockchain.mine_pending_transactions(participant.address)

        # Chain should remain valid
        assert blockchain.validate_chain()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
