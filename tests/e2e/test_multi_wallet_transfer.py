"""
End-to-end test: Multi-wallet transfer scenarios

Tests complex transfer patterns involving multiple wallets
and various transaction flows.
"""

import pytest
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestMultiWalletTransfers:
    """Test complex multi-wallet transfer scenarios"""

    def test_simple_three_wallet_transfer(self, e2e_blockchain_dir):
        """Test simple transfer: A -> B -> C"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallet_a = Wallet()
        wallet_b = Wallet()
        wallet_c = Wallet()

        # Fund A
        blockchain.mine_pending_transactions(wallet_a.address)

        # A -> B
        tx1 = blockchain.create_transaction(
            wallet_a.address,
            wallet_b.address,
            10.0,
            1.0,
            wallet_a.private_key,
            wallet_a.public_key
        )
        blockchain.add_transaction(tx1)
        blockchain.mine_pending_transactions(Wallet().address)

        assert blockchain.get_balance(wallet_b.address) == 10.0

        # B -> C
        tx2 = blockchain.create_transaction(
            wallet_b.address,
            wallet_c.address,
            5.0,
            0.5,
            wallet_b.private_key,
            wallet_b.public_key
        )
        blockchain.add_transaction(tx2)
        blockchain.mine_pending_transactions(Wallet().address)

        assert blockchain.get_balance(wallet_c.address) == 5.0

    def test_star_topology_transfers(self, e2e_blockchain_dir):
        """Test star topology: Center wallet -> Multiple satellites"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Center wallet
        center = Wallet()
        # Satellite wallets
        satellites = [Wallet() for _ in range(5)]

        # Fund center
        blockchain.mine_pending_transactions(center.address)
        center_balance = blockchain.get_balance(center.address)

        # Distribute to all satellites
        amount_per_satellite = center_balance / (len(satellites) + 1)
        for satellite in satellites:
            tx = blockchain.create_transaction(
                center.address,
                satellite.address,
                amount_per_satellite,
                0.1,
                center.private_key,
                center.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # All satellites should have received funds
        for satellite in satellites:
            assert blockchain.get_balance(satellite.address) > 0

    def test_mesh_topology_transfers(self, e2e_blockchain_dir):
        """Test mesh topology: Fully connected wallet network"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallets = [Wallet() for _ in range(4)]

        # Fund all wallets
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        # Each wallet sends to 2 others
        transfers = [
            (wallets[0], wallets[1], 1.0),
            (wallets[0], wallets[2], 1.0),
            (wallets[1], wallets[2], 1.0),
            (wallets[1], wallets[3], 1.0),
            (wallets[2], wallets[3], 1.0),
            (wallets[3], wallets[0], 1.0),
        ]

        for sender, recipient, amount in transfers:
            tx = blockchain.create_transaction(
                sender.address,
                recipient.address,
                amount,
                0.1,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Verify chain validity
        assert blockchain.validate_chain()

    def test_round_robin_distribution(self, e2e_blockchain_dir):
        """Test round-robin distribution from one wallet to many"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        source = Wallet()
        recipients = [Wallet() for _ in range(10)]

        # Fund source
        blockchain.mine_pending_transactions(source.address)

        # Distribute to all recipients in round-robin
        amount = 1.0
        for i, recipient in enumerate(recipients):
            tx = blockchain.create_transaction(
                source.address,
                recipient.address,
                amount,
                0.1,
                source.private_key,
                source.public_key
            )
            blockchain.add_transaction(tx)

            # Mine every 3 transactions to test partial blocks
            if (i + 1) % 3 == 0:
                blockchain.mine_pending_transactions(Wallet().address)

        # Mine remaining transactions
        blockchain.mine_pending_transactions(Wallet().address)

        # All recipients should have received
        for recipient in recipients:
            balance = blockchain.get_balance(recipient.address)
            assert balance > 0

    def test_sequential_pooling(self, e2e_blockchain_dir):
        """Test sequential pooling: Multiple wallets -> One"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        contributors = [Wallet() for _ in range(5)]
        pool = Wallet()

        # Fund all contributors
        for wallet in contributors:
            blockchain.mine_pending_transactions(wallet.address)

        # All contribute to pool
        for contributor in contributors:
            tx = blockchain.create_transaction(
                contributor.address,
                pool.address,
                2.0,
                0.1,
                contributor.private_key,
                contributor.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Pool should have all contributions
        pool_balance = blockchain.get_balance(pool.address)
        expected = 2.0 * len(contributors)
        assert pool_balance == expected

    def test_multi_level_distribution(self, e2e_blockchain_dir):
        """Test multi-level distribution: A -> {B, C} -> {D, E, F, G}"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Level 1
        root = Wallet()

        # Level 2
        level2 = [Wallet() for _ in range(2)]

        # Level 3
        level3 = [Wallet() for _ in range(4)]

        # Fund root
        blockchain.mine_pending_transactions(root.address)

        # Root -> Level 2
        for wallet in level2:
            tx = blockchain.create_transaction(
                root.address,
                wallet.address,
                5.0,
                0.5,
                root.private_key,
                root.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Level 2 -> Level 3
        for i, wallet in enumerate(level2):
            # Each level 2 wallet sends to 2 level 3 wallets
            for j in range(2):
                recipient = level3[i * 2 + j]
                tx = blockchain.create_transaction(
                    wallet.address,
                    recipient.address,
                    2.0,
                    0.2,
                    wallet.private_key,
                    wallet.public_key
                )
                blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Verify all level 3 wallets have funds
        for wallet in level3:
            assert blockchain.get_balance(wallet.address) > 0

    def test_bulk_micropaymants(self, e2e_blockchain_dir):
        """Test bulk micropayments from source to many recipients"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        source = Wallet()
        recipients = [Wallet() for _ in range(50)]

        # Fund source
        blockchain.mine_pending_transactions(source.address)

        # Send micropayments
        micropayment = 0.1
        for recipient in recipients:
            tx = blockchain.create_transaction(
                source.address,
                recipient.address,
                micropayment,
                0.01,
                source.private_key,
                source.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Each recipient should have micropayment
        for recipient in recipients:
            balance = blockchain.get_balance(recipient.address)
            assert balance == micropayment

    def test_rapid_sequential_transfers(self, e2e_blockchain_dir):
        """Test rapid sequential transfers between wallets"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallets = [Wallet() for _ in range(5)]

        # Fund first wallet
        blockchain.mine_pending_transactions(wallets[0].address)

        # Rapid sequential transfers
        current_holder = wallets[0]
        for i in range(1, len(wallets)):
            tx = blockchain.create_transaction(
                current_holder.address,
                wallets[i].address,
                5.0,
                0.5,
                current_holder.private_key,
                current_holder.public_key
            )
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(Wallet().address)
            current_holder = wallets[i]

        # Final holder should have funds
        assert blockchain.get_balance(current_holder.address) > 0

    def test_circular_transfers(self, e2e_blockchain_dir):
        """Test circular transfers: A -> B -> C -> A"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallet_a = Wallet()
        wallet_b = Wallet()
        wallet_c = Wallet()

        # Fund A
        blockchain.mine_pending_transactions(wallet_a.address)
        initial_a = blockchain.get_balance(wallet_a.address)

        # A -> B
        tx1 = blockchain.create_transaction(
            wallet_a.address,
            wallet_b.address,
            5.0,
            0.5,
            wallet_a.private_key,
            wallet_a.public_key
        )
        blockchain.add_transaction(tx1)
        blockchain.mine_pending_transactions(Wallet().address)

        # B -> C
        tx2 = blockchain.create_transaction(
            wallet_b.address,
            wallet_c.address,
            4.0,
            0.5,
            wallet_b.private_key,
            wallet_b.public_key
        )
        blockchain.add_transaction(tx2)
        blockchain.mine_pending_transactions(Wallet().address)

        # C -> A (close circle)
        tx3 = blockchain.create_transaction(
            wallet_c.address,
            wallet_a.address,
            3.0,
            0.25,
            wallet_c.private_key,
            wallet_c.public_key
        )
        blockchain.add_transaction(tx3)
        blockchain.mine_pending_transactions(Wallet().address)

        # Verify final state
        final_a = blockchain.get_balance(wallet_a.address)
        # A lost (5.0 + 0.5) but received 3.0
        assert final_a == initial_a - 5.0 - 0.5 + 3.0

    def test_multi_wallet_spending_pattern(self, e2e_blockchain_dir):
        """Test various spending patterns from multiple sources"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        spenders = [Wallet() for _ in range(5)]
        receiver = Wallet()

        # Fund all spenders
        for spender in spenders:
            blockchain.mine_pending_transactions(spender.address)

        # Various spending patterns
        spending_amounts = [
            [1.0, 2.0, 3.0],           # Spender 0: 3 txs
            [5.0],                      # Spender 1: 1 tx
            [0.5, 0.5, 0.5, 0.5],      # Spender 2: 4 txs
            [10.0],                     # Spender 3: 1 tx
            [0.1] * 20,                 # Spender 4: 20 txs
        ]

        for spender, amounts in zip(spenders, spending_amounts):
            for amount in amounts:
                tx = blockchain.create_transaction(
                    spender.address,
                    receiver.address,
                    amount,
                    0.05,
                    spender.private_key,
                    spender.public_key
                )
                blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Receiver should have all funds
        receiver_balance = blockchain.get_balance(receiver.address)
        assert receiver_balance > 0

        # Chain should be valid
        assert blockchain.validate_chain()

    def test_wallet_consolidation(self, e2e_blockchain_dir):
        """Test consolidating funds from multiple wallets to one"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        wallets = [Wallet() for _ in range(10)]

        # Fund all wallets
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        # Get total before consolidation
        total_before = sum(
            blockchain.get_balance(w.address) for w in wallets
        )

        # Consolidate to first wallet
        for wallet in wallets[1:]:
            balance = blockchain.get_balance(wallet.address)
            if balance > 0.2:  # Leave room for fee
                tx = blockchain.create_transaction(
                    wallet.address,
                    wallets[0].address,
                    balance - 0.2,
                    0.1,
                    wallet.private_key,
                    wallet.public_key
                )
                blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # First wallet should have most funds
        consolidated = blockchain.get_balance(wallets[0].address)
        total_after = sum(
            blockchain.get_balance(w.address) for w in wallets
        )

        # Total should be less (fees paid)
        assert total_after < total_before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
