"""
End-to-end test: User trading journey

Complete flow: Wallet creation -> Receive funds -> Send transaction -> 
Receive payment -> Check final balance
"""

import pytest
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestUserJourneyTrading:
    """Test complete user trading workflow"""

    def test_user_creates_wallet(self):
        """User creates a new wallet"""
        wallet = Wallet()

        assert wallet.address is not None
        assert wallet.public_key is not None
        assert wallet.private_key is not None
        assert wallet.address.startswith("XAI")

    def test_user_receives_funds(self, e2e_blockchain_dir):
        """User receives funds from another user"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        sender = Wallet()
        recipient = Wallet()

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Sender sends to recipient
        tx = blockchain.create_transaction(
            sender.address,
            recipient.address,
            10.0,
            1.0,
            sender.private_key,
            sender.public_key
        )
        blockchain.add_transaction(tx)

        # Mine to confirm
        blockchain.mine_pending_transactions(Wallet().address)

        # Recipient checks balance
        balance = blockchain.get_balance(recipient.address)
        assert balance == 10.0

    def test_user_complete_trading_flow(self, e2e_blockchain_dir):
        """Complete trading flow: create wallet, receive, send, receive, check balance"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # User 1: Alice creates wallet
        alice = Wallet()

        # User 2: Bob creates wallet
        bob = Wallet()

        # User 3: Carol creates wallet
        carol = Wallet()

        # Step 1: Blockchain operator funds Alice
        blockchain.mine_pending_transactions(alice.address)
        alice_initial = blockchain.get_balance(alice.address)
        assert alice_initial > 0

        # Step 2: Alice sends to Bob
        tx1 = blockchain.create_transaction(
            alice.address,
            bob.address,
            5.0,
            0.5,
            alice.private_key,
            alice.public_key
        )
        blockchain.add_transaction(tx1)
        blockchain.mine_pending_transactions(Wallet().address)

        bob_balance = blockchain.get_balance(bob.address)
        assert bob_balance == 5.0

        # Step 3: Bob sends to Carol
        tx2 = blockchain.create_transaction(
            bob.address,
            carol.address,
            3.0,
            0.5,
            bob.private_key,
            bob.public_key
        )
        blockchain.add_transaction(tx2)
        blockchain.mine_pending_transactions(Wallet().address)

        carol_balance = blockchain.get_balance(carol.address)
        assert carol_balance == 3.0

        # Step 4: Carol sends back to Alice
        tx3 = blockchain.create_transaction(
            carol.address,
            alice.address,
            2.0,
            0.25,
            carol.private_key,
            carol.public_key
        )
        blockchain.add_transaction(tx3)
        blockchain.mine_pending_transactions(Wallet().address)

        # Final check
        alice_final = blockchain.get_balance(alice.address)
        bob_final = blockchain.get_balance(bob.address)
        carol_final = blockchain.get_balance(carol.address)

        # Verify conservation of value (minus fees)
        total_fees = 0.5 + 0.5 + 0.25
        assert (alice_final + bob_final + carol_final) == (alice_initial - total_fees)

    def test_user_multiple_transactions_same_day(self, e2e_blockchain_dir):
        """User performs multiple transactions in sequence"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        user1 = Wallet()
        user2 = Wallet()
        user3 = Wallet()

        # Fund user1
        blockchain.mine_pending_transactions(user1.address)
        initial_balance = blockchain.get_balance(user1.address)

        # Multiple transactions
        transactions = []
        amounts = [1.0, 2.0, 1.5, 0.5]

        for amount in amounts:
            tx = blockchain.create_transaction(
                user1.address,
                user2.address if len(transactions) % 2 == 0 else user3.address,
                amount,
                0.1,
                user1.private_key,
                user1.public_key
            )
            transactions.append(tx)
            blockchain.add_transaction(tx)

        # Mine all transactions
        blockchain.mine_pending_transactions(Wallet().address)

        # Check final balance
        total_sent = sum(amounts)
        total_fees = 0.1 * len(amounts)
        expected_balance = initial_balance - total_sent - total_fees

        user1_final = blockchain.get_balance(user1.address)
        assert user1_final == expected_balance

    def test_user_trading_multiple_pairs(self, e2e_blockchain_dir):
        """User trades with multiple trading pairs"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Create multiple wallets
        users = [Wallet() for _ in range(5)]

        # Fund all users
        for user in users:
            blockchain.mine_pending_transactions(user.address)

        initial_balances = [blockchain.get_balance(u.address) for u in users]

        # Create trading relationships
        trading_pairs = [
            (users[0], users[1], 2.0),
            (users[1], users[2], 1.5),
            (users[2], users[3], 1.0),
            (users[3], users[4], 0.5),
            (users[4], users[0], 0.25),
        ]

        for sender, recipient, amount in trading_pairs:
            tx = blockchain.create_transaction(
                sender.address,
                recipient.address,
                amount,
                0.1,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine all transactions
        blockchain.mine_pending_transactions(Wallet().address)

        # Verify chain validity
        assert blockchain.validate_chain()

    def test_user_trading_with_partial_amounts(self, e2e_blockchain_dir):
        """User trades with fractional amounts"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        alice = Wallet()
        bob = Wallet()

        # Fund alice
        blockchain.mine_pending_transactions(alice.address)

        # Trade fractional amounts
        fractional_amounts = [0.123, 0.456, 0.789]

        for i, amount in enumerate(fractional_amounts):
            tx = blockchain.create_transaction(
                alice.address,
                bob.address,
                amount,
                0.001,
                alice.private_key,
                alice.public_key
            )
            blockchain.add_transaction(tx)

        # Mine
        blockchain.mine_pending_transactions(Wallet().address)

        # Verify balance
        bob_balance = blockchain.get_balance(bob.address)
        expected = sum(fractional_amounts)
        assert abs(bob_balance - expected) < 0.0001  # Allow for floating point

    def test_user_trading_rapid_succession(self, e2e_blockchain_dir):
        """User sends multiple transactions in rapid succession"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        sender = Wallet()
        recipients = [Wallet() for _ in range(10)]

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Send to 10 recipients rapidly
        for recipient in recipients:
            tx = blockchain.create_transaction(
                sender.address,
                recipient.address,
                0.5,
                0.05,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine to confirm all
        blockchain.mine_pending_transactions(Wallet().address)

        # Verify all received
        for recipient in recipients:
            balance = blockchain.get_balance(recipient.address)
            assert balance == 0.5

    def test_user_trading_chain_operations(self, e2e_blockchain_dir):
        """User performs chained trading operations"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Trading chain: A -> B -> C -> D -> E
        wallets = [Wallet() for _ in range(5)]

        # Fund first wallet
        blockchain.mine_pending_transactions(wallets[0].address)
        balance = blockchain.get_balance(wallets[0].address)

        # Chain transactions
        send_amount = balance / 4
        current_wallet = wallets[0]

        for next_wallet in wallets[1:]:
            tx = blockchain.create_transaction(
                current_wallet.address,
                next_wallet.address,
                send_amount,
                0.2,
                current_wallet.private_key,
                current_wallet.public_key
            )
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(Wallet().address)
            current_wallet = next_wallet

        # Final wallet should have received
        assert blockchain.get_balance(wallets[-1].address) > 0

    def test_user_trading_bidirectional(self, e2e_blockchain_dir):
        """User engages in bidirectional trading"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        alice = Wallet()
        bob = Wallet()

        # Fund both users
        blockchain.mine_pending_transactions(alice.address)
        blockchain.mine_pending_transactions(bob.address)

        initial_alice = blockchain.get_balance(alice.address)
        initial_bob = blockchain.get_balance(bob.address)

        # Alice sends to Bob
        tx1 = blockchain.create_transaction(
            alice.address,
            bob.address,
            5.0,
            0.5,
            alice.private_key,
            alice.public_key
        )
        blockchain.add_transaction(tx1)
        blockchain.mine_pending_transactions(Wallet().address)

        # Bob sends back to Alice
        tx2 = blockchain.create_transaction(
            bob.address,
            alice.address,
            3.0,
            0.5,
            bob.private_key,
            bob.public_key
        )
        blockchain.add_transaction(tx2)
        blockchain.mine_pending_transactions(Wallet().address)

        # Check final balances
        final_alice = blockchain.get_balance(alice.address)
        final_bob = blockchain.get_balance(bob.address)

        # Alice: initial - 5 (sent) - 0.5 (fee) + 3 (received) = initial - 2.5
        assert final_alice == initial_alice - 2.5
        # Bob: initial - 3 (sent) - 0.5 (fee) + 5 (received) = initial + 1.5
        assert final_bob == initial_bob + 1.5


class TestTradingEdgeCases:
    """Test edge cases in trading"""

    def test_trading_minimum_amount(self, e2e_blockchain_dir):
        """Test trading with minimum amount"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        sender = Wallet()
        recipient = Wallet()

        blockchain.mine_pending_transactions(sender.address)

        # Send minimum amount
        tx = blockchain.create_transaction(
            sender.address,
            recipient.address,
            0.001,  # Very small amount
            0.0001,
            sender.private_key,
            sender.public_key
        )
        blockchain.add_transaction(tx)
        blockchain.mine_pending_transactions(Wallet().address)

        assert blockchain.get_balance(recipient.address) > 0

    def test_trading_max_precision(self, e2e_blockchain_dir):
        """Test trading with maximum precision decimals"""
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        sender = Wallet()
        recipient = Wallet()

        blockchain.mine_pending_transactions(sender.address)

        # Send with many decimal places
        tx = blockchain.create_transaction(
            sender.address,
            recipient.address,
            3.141592653589793,
            0.123456789,
            sender.private_key,
            sender.public_key
        )
        blockchain.add_transaction(tx)
        blockchain.mine_pending_transactions(Wallet().address)

        balance = blockchain.get_balance(recipient.address)
        assert balance > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
