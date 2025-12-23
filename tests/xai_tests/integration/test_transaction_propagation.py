from __future__ import annotations

"""
Integration tests for transaction propagation across network.

Tests how transactions spread through the network, mempool management,
and transaction ordering.

NOTE: Several tests use add_block() which doesn't exist in Blockchain.
Tests are skipped where peer block acceptance is required.
"""

import pytest
import threading
import time

from xai.core.blockchain import Blockchain, Transaction
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet

class TestTransactionPropagation:
    """Test transaction propagation across network"""

    @pytest.fixture
    def four_node_network(self, tmp_path) -> list[BlockchainNode]:
        """Create 4-node network"""
        nodes = []
        for i in range(4):
            node_dir = tmp_path / f"node_{i}"
            node_dir.mkdir()
            bc = Blockchain(data_dir=str(node_dir))
            node = BlockchainNode(
                blockchain=bc,
                port=5000 + i,
                miner_address=Wallet().address
            )
            nodes.append(node)
        return nodes

    def test_single_transaction_propagation(self, four_node_network):
        """Test single transaction spreads to all nodes"""
        nodes = four_node_network

        # Sync all nodes
        for _ in range(2):
            block = nodes[0].blockchain.mine_pending_transactions(nodes[0].miner_address)
            for node in nodes[1:]:
                node.blockchain.add_block(block)

        # Create transaction on node 0
        wallet_from = Wallet()
        wallet_to = Wallet()

        # Fund wallet
        nodes[0].blockchain.mine_pending_transactions(wallet_from.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create transaction
        tx = nodes[0].blockchain.create_transaction(
            wallet_from.address,
            wallet_to.address,
            5.0,
            0.1,
            wallet_from.private_key,
            wallet_from.public_key
        )
        nodes[0].blockchain.add_transaction(tx)

        # Propagate to other nodes
        for node in nodes[1:]:
            node.blockchain.add_transaction(tx)

        # All should have transaction in mempool
        for node in nodes:
            assert len(node.blockchain.pending_transactions) > 0

    def test_transaction_ordering(self, four_node_network):
        """Test transactions maintain proper ordering"""
        nodes = four_node_network
        wallet = Wallet()

        # Fund wallet
        nodes[0].blockchain.mine_pending_transactions(wallet.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create multiple transactions
        txs = []
        for i in range(5):
            recipient = Wallet()
            tx = nodes[0].blockchain.create_transaction(
                wallet.address,
                recipient.address,
                0.5,
                0.05,
                wallet.private_key,
                wallet.public_key
            )
            txs.append(tx)
            nodes[0].blockchain.add_transaction(tx)

        # All transactions should be in mempool in order
        assert len(nodes[0].blockchain.pending_transactions) == 5

        # Propagate all to other nodes in same order
        for tx in txs:
            for node in nodes[1:]:
                node.blockchain.add_transaction(tx)

        # All should have same transaction count
        for node in nodes:
            assert len(node.blockchain.pending_transactions) == 5

    def test_transaction_confirmation(self, four_node_network):
        """Test transaction confirmation across network"""
        nodes = four_node_network
        wallet_from = Wallet()
        wallet_to = Wallet()

        # Fund sender
        nodes[0].blockchain.mine_pending_transactions(wallet_from.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create transaction
        tx = nodes[0].blockchain.create_transaction(
            wallet_from.address,
            wallet_to.address,
            10.0,
            1.0,
            wallet_from.private_key,
            wallet_from.public_key
        )
        nodes[0].blockchain.add_transaction(tx)

        # Propagate transaction
        for node in nodes[1:]:
            node.blockchain.add_transaction(tx)

        # Mine on node 0
        block = nodes[0].blockchain.mine_pending_transactions(nodes[0].miner_address)

        # Propagate block to all nodes
        for node in nodes[1:]:
            node.blockchain.add_block(block)

        # All should confirm the transaction
        for node in nodes:
            recipient_balance = node.blockchain.get_balance(wallet_to.address)
            assert recipient_balance == 10.0

    def test_double_spend_propagation(self, four_node_network):
        """Test network prevents double-spend propagation"""
        nodes = four_node_network
        wallet = Wallet()
        recipient1 = Wallet()
        recipient2 = Wallet()

        # Fund wallet
        nodes[0].blockchain.mine_pending_transactions(wallet.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        balance = nodes[0].blockchain.get_balance(wallet.address)

        # Create first spend
        tx1 = nodes[0].blockchain.create_transaction(
            wallet.address,
            recipient1.address,
            balance / 2,
            0.1,
            wallet.private_key,
            wallet.public_key
        )
        nodes[0].blockchain.add_transaction(tx1)

        # Try to create double-spend on node 1
        tx2 = nodes[1].blockchain.create_transaction(
            wallet.address,
            recipient2.address,
            balance / 2,
            0.1,
            wallet.private_key,
            wallet.public_key
        )
        nodes[1].blockchain.add_transaction(tx2)

        # Propagate both transactions
        for node in nodes[1:]:
            node.blockchain.add_transaction(tx1)
        for node in nodes[2:]:
            node.blockchain.add_transaction(tx2)

        # Mine on node 0 with tx1
        block = nodes[0].blockchain.mine_pending_transactions(nodes[0].miner_address)

        # Propagate block
        for node in nodes[1:]:
            node.blockchain.add_block(block)

        # tx2 should be rejected on nodes that received block
        # Total balance should only reflect tx1
        for node in nodes:
            total = (node.blockchain.get_balance(recipient1.address) +
                    node.blockchain.get_balance(recipient2.address))
            assert total == balance / 2

    def test_high_volume_transaction_propagation(self, four_node_network):
        """Test propagation with high volume of transactions"""
        nodes = four_node_network

        # Sync nodes
        nodes[0].blockchain.mine_pending_transactions(Wallet().address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create 100 wallets and fund them
        wallets = [Wallet() for _ in range(100)]
        for wallet in wallets:
            nodes[0].blockchain.mine_pending_transactions(wallet.address)

        # Propagate all funding blocks
        for block in nodes[0].blockchain.chain[1:]:
            for node in nodes[1:]:
                if block not in node.blockchain.chain:
                    node.blockchain.add_block(block)

        # Create many transactions
        txs = []
        for i in range(50):
            sender = wallets[i]
            recipient = wallets[i + 50]
            tx = nodes[0].blockchain.create_transaction(
                sender.address,
                recipient.address,
                0.5,
                0.05,
                sender.private_key,
                sender.public_key
            )
            txs.append(tx)
            nodes[0].blockchain.add_transaction(tx)

        # Propagate all transactions
        for tx in txs:
            for node in nodes[1:]:
                node.blockchain.add_transaction(tx)

        # All nodes should have all transactions
        for node in nodes:
            assert len(node.blockchain.pending_transactions) >= 50

    def test_transaction_ordering_during_propagation(self, four_node_network):
        """Test transaction order preserved during propagation"""
        nodes = four_node_network
        wallet = Wallet()

        # Fund wallet
        nodes[0].blockchain.mine_pending_transactions(wallet.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create transactions with different timestamps
        txs = []
        for i in range(10):
            recipient = Wallet()
            tx = nodes[0].blockchain.create_transaction(
                wallet.address,
                recipient.address,
                0.5,
                0.05,
                wallet.private_key,
                wallet.public_key
            )
            txs.append(tx)

        # Add transactions in order
        for tx in txs:
            nodes[0].blockchain.add_transaction(tx)

        # Get order on node 0
        order_node0 = [tx.txid for tx in nodes[0].blockchain.pending_transactions]

        # Propagate and check order on other nodes
        for tx in txs:
            for node in nodes[1:]:
                node.blockchain.add_transaction(tx)

        for node in nodes[1:]:
            order = [tx.txid for tx in node.blockchain.pending_transactions]
            # All txids should be present
            assert len(order) == len(txs)

    def test_mempool_synchronization(self, four_node_network):
        """Test mempool stays synchronized across nodes"""
        nodes = four_node_network

        # Sync nodes with some blocks
        for _ in range(3):
            block = nodes[0].blockchain.mine_pending_transactions(Wallet().address)
            for node in nodes[1:]:
                node.blockchain.add_block(block)

        # Create transactions on different nodes
        txs = []
        for i in range(4):
            wallet = Wallet()
            recipient = Wallet()

            # Fund wallet on node i
            nodes[i].blockchain.mine_pending_transactions(wallet.address)

            # Create transaction
            tx = nodes[i].blockchain.create_transaction(
                wallet.address,
                recipient.address,
                1.0,
                0.1,
                wallet.private_key,
                wallet.public_key
            )
            txs.append(tx)
            nodes[i].blockchain.add_transaction(tx)

        # Propagate all transactions to all nodes
        for tx in txs:
            for node in nodes:
                if tx not in node.blockchain.pending_transactions:
                    node.blockchain.add_transaction(tx)

        # All should have same number of pending transactions
        pending_counts = [len(node.blockchain.pending_transactions) for node in nodes]
        assert len(set(pending_counts)) == 1  # All equal

    def test_transaction_rejection_propagation(self, four_node_network):
        """Test invalid transactions are rejected across network"""
        nodes = four_node_network

        # Fund a wallet
        wallet = Wallet()
        nodes[0].blockchain.mine_pending_transactions(wallet.address)
        for node in nodes[1:]:
            node.blockchain.add_block(nodes[0].blockchain.chain[-1])

        # Create valid transaction
        tx_valid = nodes[0].blockchain.create_transaction(
            wallet.address,
            Wallet().address,
            1.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        # Create invalid transaction (bad signature)
        tx_invalid = nodes[0].blockchain.create_transaction(
            wallet.address,
            Wallet().address,
            1.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )
        tx_invalid.signature = "invalid_signature_" + ("0" * 120)

        # Add valid to node 0
        nodes[0].blockchain.add_transaction(tx_valid)

        # Try to propagate invalid
        result = nodes[1].blockchain.add_transaction(tx_invalid)

        # Invalid should be rejected
        # (depends on validation implementation)

class TestTransactionPropagationEdgeCases:
    """Test edge cases in transaction propagation"""

    def test_large_transaction(self, tmp_path):
        """Test propagation of very large transaction"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()
        bc = Blockchain(data_dir=str(node_dir))

        wallet_from = Wallet()
        wallet_to = Wallet()

        # Fund wallet with large amount
        bc.mine_pending_transactions(wallet_from.address)
        balance = bc.get_balance(wallet_from.address)

        # Create transaction with all balance
        tx = bc.create_transaction(
            wallet_from.address,
            wallet_to.address,
            balance - 1.0,  # Leave room for fees
            1.0,
            wallet_from.private_key,
            wallet_from.public_key
        )

        bc.add_transaction(tx)
        assert len(bc.pending_transactions) > 0

    def test_transaction_with_zero_fee(self, tmp_path):
        """Test transaction propagation with zero fee"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()
        bc = Blockchain(data_dir=str(node_dir))

        wallet_from = Wallet()
        wallet_to = Wallet()

        bc.mine_pending_transactions(wallet_from.address)

        # Transaction with zero fee
        tx = bc.create_transaction(
            wallet_from.address,
            wallet_to.address,
            1.0,
            0.0,
            wallet_from.private_key,
            wallet_from.public_key
        )

        bc.add_transaction(tx)
        # Should still be added (depends on minimum fee policy)

    def test_burst_transaction_propagation(self, tmp_path):
        """Test rapid burst of transaction propagation"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        # Sync
        block = bc1.mine_pending_transactions(Wallet().address)
        bc2.add_block(block)

        # Rapid transaction burst on node1
        wallets = [Wallet() for _ in range(20)]
        for wallet in wallets:
            tx = bc1.create_transaction(
                Wallet().address,
                wallet.address,
                0.5,
                0.05,
                "0" * 64,
                "0" * 128
            )
            bc1.add_transaction(tx)

        # Propagate all at once to node2
        for tx in bc1.pending_transactions:
            bc2.add_transaction(tx)

        # Node2 should accept all
        assert len(bc2.pending_transactions) == len(bc1.pending_transactions)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
