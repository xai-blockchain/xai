"""
Performance and stress tests for XAI Blockchain

Tests blockchain performance under load, scalability, and stress conditions
"""

import pytest
import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Add core directory to path

from aixn.core.blockchain import Blockchain, Transaction
from aixn.core.wallet import Wallet


@pytest.mark.slow
class TestBlockchainScalability:
    """Test blockchain scalability"""

    def test_large_chain_validation(self):
        """Test validation of large blockchain"""
        bc = Blockchain()
        miner = Wallet()

        # Mine many blocks
        num_blocks = 100

        start_time = time.time()

        for i in range(num_blocks):
            bc.mine_pending_transactions(miner.address)

        mining_time = time.time() - start_time

        # Validate entire chain
        start_time = time.time()
        is_valid = bc.validate_chain()
        validation_time = time.time() - start_time

        assert is_valid
        print(f"\nMined {num_blocks} blocks in {mining_time:.2f}s")
        print(f"Validated chain in {validation_time:.2f}s")

        # Validation should be reasonably fast
        assert validation_time < 10  # Should validate 100 blocks in under 10 seconds

    def test_many_transactions_per_block(self):
        """Test block with many transactions"""
        bc = Blockchain()
        miner = Wallet()

        num_transactions = 50
        recipients = [Wallet() for _ in range(num_transactions)]
        # Create unique senders so each transaction can reserve its own UTXO
        senders = [Wallet() for _ in range(num_transactions)]

        # Give each sender a single UTXO (coinbase reward)
        for sender in senders:
            bc.mine_pending_transactions(sender.address)

        for sender, recipient in zip(senders, recipients):
            tx = Transaction(sender.address, recipient.address, 0.1, 0.01)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            assert bc.add_transaction(tx)

        # Mine block with all transactions
        start_time = time.time()
        block = bc.mine_pending_transactions(miner.address)
        mining_time = time.time() - start_time

        print(f"\nMined block with {len(block.transactions)} transactions in {mining_time:.2f}s")

        # Verify all transactions processed
        for recipient in recipients:
            balance = bc.get_balance(recipient.address)
            assert balance == 0.1

    def test_utxo_set_growth(self):
        """Test UTXO set handling with growth"""
        bc = Blockchain()
        wallets = [Wallet() for _ in range(20)]

        # Create many UTXOs
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Check UTXO set size
        total_utxos = sum(len(utxos) for utxos in bc.utxo_set.values())

        print(f"\nTotal UTXOs: {total_utxos}")
        assert total_utxos > 0


@pytest.mark.slow
class TestTransactionThroughput:
    """Test transaction processing throughput"""

    def test_transaction_creation_speed(self):
        """Test transaction creation performance"""
        sender = Wallet()
        recipients = [Wallet() for _ in range(100)]

        start_time = time.time()

        transactions = []
        for recipient in recipients:
            tx = Transaction(sender.address, recipient.address, 1.0, 0.24)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            transactions.append(tx)

        creation_time = time.time() - start_time

        print(f"\nCreated 100 transactions in {creation_time:.2f}s")
        print(f"Rate: {100/creation_time:.2f} tx/s")

        # Should create transactions quickly
        assert creation_time < 5

    def test_transaction_validation_speed(self):
        """Test transaction validation performance"""
        bc = Blockchain()
        sender = Wallet()
        recipients = [Wallet() for _ in range(50)]

        # Give sender balance
        bc.mine_pending_transactions(sender.address)
        bc.mine_pending_transactions(sender.address)

        # Create transactions
        transactions = []
        for recipient in recipients:
            tx = Transaction(sender.address, recipient.address, 0.1, 0.01)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            transactions.append(tx)

        # Validate all
        start_time = time.time()

        valid_count = 0
        for tx in transactions:
            if bc.validate_transaction(tx):
                valid_count += 1

        validation_time = time.time() - start_time

        print(f"\nValidated {valid_count} transactions in {validation_time:.2f}s")
        print(f"Rate: {valid_count/validation_time:.2f} tx/s")

    def test_signature_verification_speed(self):
        """Test signature verification performance"""
        wallet = Wallet()
        message = "Test message for signing"

        # Create signatures
        signatures = [wallet.sign_message(f"{message}_{i}") for i in range(100)]

        # Verify all
        start_time = time.time()

        verified_count = sum(
            1
            for i, sig in enumerate(signatures)
            if wallet.verify_signature(f"{message}_{i}", sig, wallet.public_key)
        )

        verification_time = time.time() - start_time

        print(f"\nVerified {verified_count} signatures in {verification_time:.2f}s")
        print(f"Rate: {verified_count/verification_time:.2f} signatures/s")

        assert verified_count == 100


@pytest.mark.slow
class TestConcurrency:
    """Test concurrent operations"""

    def test_concurrent_transaction_creation(self):
        """Test concurrent transaction creation"""
        bc = Blockchain()
        senders = [Wallet() for _ in range(10)]
        recipient = Wallet()

        # Give all senders balance
        for sender in senders:
            bc.mine_pending_transactions(sender.address)

        # Create transactions concurrently
        def create_and_add_tx(sender):
            tx = Transaction(sender.address, recipient.address, 1.0, 0.1)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            bc.add_transaction(tx)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_add_tx, sender) for sender in senders]
            for future in futures:
                future.result()

        concurrent_time = time.time() - start_time

        print(f"\nCreated 10 concurrent transactions in {concurrent_time:.2f}s")

        # Should handle concurrent operations
        assert len(bc.pending_transactions) <= 10

    def test_concurrent_balance_queries(self):
        """Test concurrent balance queries"""
        bc = Blockchain()
        wallets = [Wallet() for _ in range(20)]

        # Mine to create balances
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Query balances concurrently
        def get_balance(wallet):
            return bc.get_balance(wallet.address)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=20) as executor:
            balances = list(executor.map(get_balance, wallets))

        query_time = time.time() - start_time

        print(f"\nQueried 20 balances concurrently in {query_time:.2f}s")

        # All queries should succeed
        assert len(balances) == 20
        assert all(b > 0 for b in balances)


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage patterns"""

    def test_chain_memory_growth(self):
        """Test memory usage with chain growth"""
        bc = Blockchain()
        miner = Wallet()

        initial_chain_length = len(bc.chain)

        # Mine blocks
        for _ in range(50):
            bc.mine_pending_transactions(miner.address)

        final_chain_length = len(bc.chain)

        print(f"\nChain grew from {initial_chain_length} to {final_chain_length} blocks")

        # Chain should grow linearly
        assert final_chain_length == initial_chain_length + 50

    def test_utxo_set_memory(self):
        """Test UTXO set memory usage"""
        bc = Blockchain()
        wallets = [Wallet() for _ in range(30)]

        # Create UTXOs
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        utxo_count = sum(len(utxos) for utxos in bc.utxo_set.values())

        print(f"\nUTXO set contains {utxo_count} entries")

        assert utxo_count > 0

    def test_mempool_memory(self):
        """Test mempool memory usage"""
        bc = Blockchain()
        sender = Wallet()
        recipients = [Wallet() for _ in range(100)]

        # Give sender balance
        for _ in range(5):
            bc.mine_pending_transactions(sender.address)

        # Fill mempool
        for recipient in recipients:
            tx = Transaction(sender.address, recipient.address, 0.1, 0.01)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            bc.add_transaction(tx)

        mempool_size = len(bc.pending_transactions)

        print(f"\nMempool contains {mempool_size} transactions")

        # Mempool should contain pending transactions
        assert mempool_size <= 100


@pytest.mark.slow
class TestStressConditions:
    """Test blockchain under stress conditions"""

    def test_rapid_block_mining(self):
        """Test rapid consecutive block mining"""
        bc = Blockchain()
        miner = Wallet()

        num_blocks = 20

        start_time = time.time()

        for _ in range(num_blocks):
            bc.mine_pending_transactions(miner.address)

        total_time = time.time() - start_time

        print(f"\nMined {num_blocks} blocks in {total_time:.2f}s")
        print(f"Average: {total_time/num_blocks:.2f}s per block")

        # Chain should be valid
        assert bc.validate_chain()
        assert len(bc.chain) == num_blocks + 1  # +1 for genesis

    def test_transaction_spam(self):
        """Test handling transaction spam"""
        bc = Blockchain()
        spammer = Wallet()
        victims = [Wallet() for _ in range(50)]

        # Give spammer balance
        for _ in range(3):
            bc.mine_pending_transactions(spammer.address)

        # Spam many transactions
        spam_count = 0
        for victim in victims:
            tx = Transaction(spammer.address, victim.address, 0.01, 0.01)
            tx.public_key = spammer.public_key
            tx.sign_transaction(spammer.private_key)
            bc.add_transaction(tx)
            spam_count += 1

        print(f"\nAdded {spam_count} spam transactions")

        # System should handle spam gracefully
        assert len(bc.pending_transactions) <= spam_count

    def test_large_transaction_batch(self):
        """Test processing large batch of transactions"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()

        # Give sender large balance
        for _ in range(10):
            bc.mine_pending_transactions(sender.address)

        # Create large batch
        batch_size = 100
        recipients = [Wallet() for _ in range(batch_size)]

        start_time = time.time()

        for recipient in recipients:
            tx = Transaction(sender.address, recipient.address, 0.1, 0.01)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            bc.add_transaction(tx)

        batch_time = time.time() - start_time

        print(f"\nCreated batch of {batch_size} transactions in {batch_time:.2f}s")

        # Mine batch
        start_time = time.time()
        bc.mine_pending_transactions(miner.address)
        mining_time = time.time() - start_time

        print(f"Mined batch in {mining_time:.2f}s")


@pytest.mark.slow
class TestLongRunning:
    """Test long-running operations"""

    def test_extended_mining_session(self):
        """Test extended mining session"""
        bc = Blockchain()
        miners = [Wallet() for _ in range(3)]

        blocks_per_miner = 10

        start_time = time.time()

        for miner in miners:
            for _ in range(blocks_per_miner):
                bc.mine_pending_transactions(miner.address)

        total_time = time.time() - start_time

        total_blocks = len(miners) * blocks_per_miner

        print(f"\nMined {total_blocks} blocks by {len(miners)} miners in {total_time:.2f}s")

        # Chain should remain valid
        assert bc.validate_chain()

        # All miners should have rewards
        for miner in miners:
            assert bc.get_balance(miner.address) > 0

    def test_chain_resilience(self):
        """Test chain resilience over many operations"""
        bc = Blockchain()
        wallets = [Wallet() for _ in range(5)]

        # Perform many operations
        for round_num in range(10):
            # Mine blocks
            for wallet in wallets:
                bc.mine_pending_transactions(wallet.address)

            # Create transactions
            for i in range(len(wallets) - 1):
                sender = wallets[i]
                recipient = wallets[i + 1]

                tx = Transaction(sender.address, recipient.address, 0.5, 0.1)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                bc.add_transaction(tx)

            # Mine transaction block
            bc.mine_pending_transactions(wallets[0].address)

        # Chain should remain valid after many operations
        assert bc.validate_chain()

        print(f"\nChain length after stress test: {len(bc.chain)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
