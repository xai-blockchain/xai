"""
Test blockchain fork handling atomicity and state restoration.

Ensures that partial fork failures don't corrupt UTXO or nonce state.
"""

import pytest
from unittest.mock import patch
from xai.core.blockchain import Blockchain
from xai.core.utxo_manager import UTXOManager
from xai.core.nonce_tracker import NonceTracker


class TestBlockchainForkAtomicity:
    """Test that fork handling is atomic and restores state on failure."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a test blockchain."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain_test"))
        bc.create_genesis_block()
        # Build a small chain for testing
        test_wallet_address = "XAI" + "a" * 40  # Valid XAI address format
        for i in range(5):
            block = bc.mine_pending_transactions(test_wallet_address)
            if block:
                bc._add_block_to_chain(block)
        return bc

    def test_replace_chain_atomicity_with_utxo_failure(self, blockchain):
        """Test that replace_chain properly restores UTXO state on failure."""
        # Capture state before reorg attempt
        initial_chain_length = len(blockchain.chain)
        initial_utxo_digest = blockchain.utxo_manager.snapshot_digest()
        initial_utxo_stats = blockchain.utxo_manager.get_stats()

        # Create a candidate chain (fork from block 2)
        candidate_chain = [blockchain.chain[i].header if hasattr(blockchain.chain[i], 'header')
                          else blockchain.chain[i] for i in range(3)]

        # Mock the UTXO processing to fail partway through
        original_process = blockchain.utxo_manager.process_transaction_inputs
        call_count = [0]

        def failing_process(tx):
            call_count[0] += 1
            if call_count[0] > 2:  # Fail after a few successful calls
                raise Exception("Simulated UTXO processing failure")
            return original_process(tx)

        with patch.object(blockchain.utxo_manager, 'process_transaction_inputs', side_effect=failing_process):
            # Attempt replace_chain - should fail and restore
            result = blockchain.replace_chain(candidate_chain)

            assert result is False, "replace_chain should fail with simulated UTXO error"

        # Verify state was restored
        assert len(blockchain.chain) == initial_chain_length, "Chain length changed after failed reorg"
        final_utxo_digest = blockchain.utxo_manager.snapshot_digest()
        final_utxo_stats = blockchain.utxo_manager.get_stats()

        assert final_utxo_digest == initial_utxo_digest, "UTXO state corrupted after failed reorg"
        assert final_utxo_stats == initial_utxo_stats, "UTXO stats changed after failed reorg"

    def test_replace_chain_atomicity_with_nonce_failure(self, blockchain):
        """Test that replace_chain properly restores nonce state on failure."""
        # Set up nonce state
        test_address = "test_address_456"
        blockchain.nonce_tracker.set_nonce(test_address, 10)
        initial_nonce = blockchain.nonce_tracker.get_nonce(test_address)

        # Capture state
        initial_chain_length = len(blockchain.chain)
        initial_utxo_digest = blockchain.utxo_manager.snapshot_digest()

        # Create a candidate chain (shorter to trigger equal-length fork choice)
        candidate_chain = [blockchain.chain[i].header if hasattr(blockchain.chain[i], 'header')
                          else blockchain.chain[i] for i in range(3)]

        # Mock _rebuild_nonce_tracker to fail
        def failing_rebuild(chain):
            blockchain.nonce_tracker.set_nonce(test_address, 9999)  # Corrupt state
            raise Exception("Nonce tracker rebuild failed")

        with patch.object(blockchain, '_rebuild_nonce_tracker', side_effect=failing_rebuild):
            # Attempt replace_chain - should fail and restore
            result = blockchain.replace_chain(candidate_chain)

            assert result is False, "replace_chain should fail when nonce rebuild fails"

        # Verify nonce was restored
        final_nonce = blockchain.nonce_tracker.get_nonce(test_address)
        assert final_nonce == initial_nonce, \
            f"Nonce not restored: expected {initial_nonce}, got {final_nonce}"

        # Verify chain and UTXOs weren't modified
        assert len(blockchain.chain) == initial_chain_length, "Chain changed after failed reorg"
        final_utxo_digest = blockchain.utxo_manager.snapshot_digest()
        assert final_utxo_digest == initial_utxo_digest, "UTXO state changed after failed reorg"

    def test_utxo_manager_snapshot_restore_functionality(self):
        """Test UTXOManager snapshot/restore methods work correctly."""
        utxo_mgr = UTXOManager()

        # Add some UTXOs
        utxo_mgr.add_utxo("addr1", "tx1", 0, 100.0, "script1")
        utxo_mgr.add_utxo("addr2", "tx2", 0, 200.0, "script2")
        utxo_mgr.mark_utxo_spent("addr1", "tx1", 0)

        # Take snapshot
        snapshot = utxo_mgr.snapshot()

        # Modify state
        utxo_mgr.add_utxo("addr3", "tx3", 0, 300.0, "script3")
        utxo_mgr.mark_utxo_spent("addr2", "tx2", 0)

        # Verify state changed
        assert utxo_mgr.get_balance("addr3") == 300.0
        assert utxo_mgr.get_balance("addr2") == 0.0

        # Restore snapshot
        utxo_mgr.restore(snapshot)

        # Verify restoration
        assert utxo_mgr.get_balance("addr3") == 0.0, "New UTXO not removed"
        assert utxo_mgr.get_balance("addr2") == 200.0, "Spent UTXO not restored"
        assert utxo_mgr.get_balance("addr1") == 0.0, "Originally spent UTXO incorrectly restored"

    def test_nonce_tracker_snapshot_restore_functionality(self, tmp_path):
        """Test NonceTracker snapshot/restore methods work correctly."""
        nonce_tracker = NonceTracker(data_dir=str(tmp_path / "nonces"))

        # Set some nonces
        nonce_tracker.set_nonce("addr1", 5)
        nonce_tracker.set_nonce("addr2", 10)
        nonce_tracker.reserve_nonce("addr1", 6)

        # Take snapshot
        snapshot = nonce_tracker.snapshot()

        # Modify state
        nonce_tracker.set_nonce("addr1", 20)
        nonce_tracker.set_nonce("addr3", 15)

        # Verify changes
        assert nonce_tracker.get_nonce("addr1") == 20
        assert nonce_tracker.get_nonce("addr3") == 15

        # Restore snapshot
        nonce_tracker.restore(snapshot)

        # Verify restoration
        assert nonce_tracker.get_nonce("addr1") == 5, "Nonce not restored"
        assert nonce_tracker.get_nonce("addr2") == 10, "Nonce changed"
        assert nonce_tracker.get_nonce("addr3") == -1, "New nonce not removed"
        assert nonce_tracker.pending_nonces.get("addr1") == 6, "Pending nonce not restored"

    def test_replace_chain_success_doesnt_restore(self, blockchain):
        """Test that successful replace_chain doesn't restore state."""
        # Build a longer alternative chain
        alt_chain = [blockchain.chain[0].header if hasattr(blockchain.chain[0], 'header') else blockchain.chain[0]]

        test_wallet = "XAI" + "b" * 40  # Valid XAI address format
        # Create blocks on the alternative chain
        for i in range(1, 8):  # Longer than original chain (6 blocks)
            block = blockchain.mine_pending_transactions(test_wallet)
            if block:
                alt_chain.append(block.header if hasattr(block, 'header') else block)
                blockchain.storage._save_block_to_disk(block)

        initial_utxo_digest = blockchain.utxo_manager.snapshot_digest()

        # Replace with longer chain - should succeed
        result = blockchain.replace_chain(alt_chain)

        assert result is True, "replace_chain should succeed with valid longer chain"

        # Verify state was updated (not restored to initial)
        final_utxo_digest = blockchain.utxo_manager.snapshot_digest()
        assert final_utxo_digest != initial_utxo_digest, "UTXO state should be updated on successful reorg"
        assert len(blockchain.chain) == 8, "Chain should be updated to new length"
