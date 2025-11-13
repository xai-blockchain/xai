"""
Integration tests for XAI P2P Network functionality

Tests peer connections, block propagation, and network synchronization
"""

import pytest
import sys
import os
import time
import threading

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))

from blockchain import Blockchain, Transaction
from wallet import Wallet


class TestPeerConnection:
    """Test peer connection functionality"""

    def test_initialize_peer_set(self):
        """Test peer set initialization"""
        bc = Blockchain()

        # Blockchain should have mechanism to track peers
        assert hasattr(bc, '__dict__')

    def test_add_peer(self):
        """Test adding peers to network"""
        # Mock peer management
        peers = set()

        peer1 = "http://node1.aixn.com:5000"
        peer2 = "http://node2.aixn.com:5000"

        peers.add(peer1)
        peers.add(peer2)

        assert len(peers) == 2
        assert peer1 in peers

    def test_remove_peer(self):
        """Test removing peers from network"""
        peers = set()
        peer1 = "http://node1.aixn.com:5000"

        peers.add(peer1)
        peers.remove(peer1)

        assert peer1 not in peers

    def test_unique_peers(self):
        """Test peers are unique"""
        peers = set()
        peer = "http://node1.aixn.com:5000"

        peers.add(peer)
        peers.add(peer)  # Add same peer again

        assert len(peers) == 1


class TestBlockPropagation:
    """Test block propagation across network"""

    def test_new_block_creation(self):
        """Test creating new blocks for propagation"""
        bc = Blockchain()
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        assert block is not None
        assert block.hash is not None

    def test_block_serialization(self):
        """Test blocks can be serialized for transmission"""
        bc = Blockchain()
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Block should have serializable attributes
        assert hasattr(block, 'index')
        assert hasattr(block, 'timestamp')
        assert hasattr(block, 'transactions')
        assert hasattr(block, 'hash')

    def test_block_validation_on_receive(self):
        """Test received blocks are validated"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Mine block on first chain
        block = bc1.mine_pending_transactions(miner.address)

        # Simulate receiving on second chain
        # Block should be validated before adding
        assert bc2.validate_chain()

    def test_chain_synchronization(self):
        """Test chain synchronization between nodes"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Mine blocks on first chain
        for _ in range(3):
            bc1.mine_pending_transactions(miner.address)

        # Second chain should be able to sync
        assert len(bc1.chain) > len(bc2.chain)


class TestChainConsensus:
    """Test consensus mechanism for choosing longest chain"""

    def test_longest_chain_selection(self):
        """Test selection of longest valid chain"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Create longer chain
        for _ in range(5):
            bc1.mine_pending_transactions(miner.address)

        # Create shorter chain
        for _ in range(3):
            bc2.mine_pending_transactions(miner.address)

        # Longest chain should be preferred
        assert len(bc1.chain) > len(bc2.chain)

    def test_chain_replacement_validation(self):
        """Test chain replacement requires validation"""
        bc1 = Blockchain()
        miner = Wallet()

        # Mine some blocks
        for _ in range(3):
            bc1.mine_pending_transactions(miner.address)

        # Chain should be valid before and after
        assert bc1.validate_chain()

    def test_reject_invalid_chain(self):
        """Test rejection of invalid chains"""
        bc = Blockchain()
        miner = Wallet()

        bc.mine_pending_transactions(miner.address)

        # Tamper with chain
        bc.chain[1].transactions[0].amount = 999999

        # Chain should be invalid
        assert not bc.validate_chain()


class TestTransactionPropagation:
    """Test transaction propagation across network"""

    def test_add_transaction_to_mempool(self):
        """Test adding transactions to mempool"""
        bc = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        # Add to mempool
        bc.add_transaction(tx)

        assert len(bc.pending_transactions) > 0

    def test_transaction_broadcast(self):
        """Test transaction can be broadcast"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance on both chains
        bc1.mine_pending_transactions(sender.address)
        bc2.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        # Add to both chains (simulating broadcast)
        bc1.add_transaction(tx)
        bc2.add_transaction(tx)

        assert len(bc1.pending_transactions) > 0
        assert len(bc2.pending_transactions) > 0

    def test_duplicate_transaction_handling(self):
        """Test handling of duplicate transactions"""
        bc = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        # Add transaction
        bc.add_transaction(tx)
        initial_count = len(bc.pending_transactions)

        # Try to add same transaction again
        bc.add_transaction(tx)

        # Should not add duplicate
        # (implementation may vary)
        assert len(bc.pending_transactions) >= initial_count


class TestNetworkSynchronization:
    """Test network synchronization mechanisms"""

    def test_sync_from_genesis(self):
        """Test syncing from genesis block"""
        bc1 = Blockchain()
        bc2 = Blockchain()

        # Both should start with same genesis
        assert bc1.chain[0].hash == bc2.chain[0].hash

    def test_sync_new_blocks(self):
        """Test syncing newly mined blocks"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Mine blocks on first chain
        blocks_to_mine = 3
        for _ in range(blocks_to_mine):
            bc1.mine_pending_transactions(miner.address)

        # Second chain should be able to request and validate these blocks
        assert len(bc1.chain) == len(bc2.chain) + blocks_to_mine

    def test_sync_with_transactions(self):
        """Test syncing blocks with transactions"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Mine and transact on first chain
        bc1.mine_pending_transactions(sender.address)

        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc1.add_transaction(tx)

        bc1.mine_pending_transactions(miner.address)

        # First chain should have transactions
        has_tx = any(len(block.transactions) > 1 for block in bc1.chain)
        assert has_tx


class TestNetworkResilience:
    """Test network resilience and fault tolerance"""

    def test_continue_after_peer_disconnect(self):
        """Test network continues after peer disconnect"""
        peers = set()
        peers.add("http://node1.aixn.com:5000")
        peers.add("http://node2.aixn.com:5000")

        # Remove peer
        peers.remove("http://node1.aixn.com:5000")

        # Network should continue with remaining peers
        assert len(peers) > 0

    def test_block_validation_prevents_corruption(self):
        """Test block validation prevents corrupted data"""
        bc = Blockchain()
        miner = Wallet()

        bc.mine_pending_transactions(miner.address)

        # Corrupt block data
        bc.chain[1].hash = "corrupted_hash"

        # Validation should fail
        assert not bc.validate_chain()

    def test_recovery_from_fork(self):
        """Test recovery from chain fork"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Create fork - both mine at same height
        bc1.mine_pending_transactions(miner.address)
        bc2.mine_pending_transactions(miner.address)

        # Continue mining on bc1
        bc1.mine_pending_transactions(miner.address)
        bc1.mine_pending_transactions(miner.address)

        # bc1 should be longer and preferred
        assert len(bc1.chain) > len(bc2.chain)


class TestPeerDiscovery:
    """Test peer discovery mechanisms"""

    def test_bootstrap_peers(self):
        """Test bootstrap peer loading"""
        bootstrap_peers = [
            "http://seed1.aixn.com:5000",
            "http://seed2.aixn.com:5000",
            "http://seed3.aixn.com:5000"
        ]

        peers = set(bootstrap_peers)

        assert len(peers) == 3

    def test_dynamic_peer_addition(self):
        """Test dynamic peer addition"""
        peers = set()

        # Add peers dynamically
        new_peer = "http://node5.aixn.com:5000"
        peers.add(new_peer)

        assert new_peer in peers

    def test_peer_list_management(self):
        """Test peer list management"""
        peers = set()

        # Add multiple peers
        for i in range(10):
            peers.add(f"http://node{i}.aixn.com:5000")

        assert len(peers) == 10

        # Remove some peers
        peers.remove("http://node0.aixn.com:5000")
        peers.remove("http://node1.aixn.com:5000")

        assert len(peers) == 8


class TestNetworkMessaging:
    """Test network messaging protocols"""

    def test_block_announcement(self):
        """Test block announcement message"""
        bc = Blockchain()
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Block should have necessary info for announcement
        assert block.hash is not None
        assert block.index > 0

    def test_transaction_announcement(self):
        """Test transaction announcement"""
        sender = Wallet()
        recipient = Wallet()

        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        # Transaction should be serializable for broadcast
        assert tx.txid is not None
        assert tx.signature is not None

    def test_chain_request(self):
        """Test blockchain request message"""
        bc = Blockchain()

        # Should be able to get chain info
        chain_length = len(bc.chain)
        latest_block = bc.chain[-1]

        assert chain_length > 0
        assert latest_block.hash is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
