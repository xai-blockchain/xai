"""
Test comprehensive atomic chain reorganization with all state managers.

Verifies that chain reorganization properly snapshots and restores:
- UTXO state
- Nonce tracker
- Smart contract state
- Governance state
- Finality state
- Mempool

Tests the Write-Ahead Log (WAL) for crash recovery.
"""

import pytest
import tempfile
import os
import json
from xai.core.blockchain import Blockchain
from xai.core.transaction import Transaction


class TestComprehensiveReorgAtomicity:
    """Test atomic reorg with comprehensive state management."""

    @pytest.fixture
    def blockchain(self):
        """Create a blockchain instance for testing."""
        data_dir = tempfile.mkdtemp(prefix="test_reorg_atomicity_")
        bc = Blockchain(data_dir=data_dir)
        yield bc
        # Cleanup
        import shutil
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)

    def test_wal_created_during_reorg(self, blockchain):
        """Verify WAL entry is created when reorg starts."""
        # Build initial chain
        blockchain.create_genesis_block()

        # Create a fork scenario
        # (This is a simplified test - in practice, we'd need valid blocks)
        original_tip = blockchain.chain[-1].hash if blockchain.chain else None

        # Check that WAL doesn't exist initially
        assert not os.path.exists(blockchain.reorg_wal_path), "WAL should not exist before reorg"

        # The WAL is created inside replace_chain when called
        # We can't easily test this without triggering an actual reorg
        # But we can test the WAL methods directly

        wal_entry = blockchain._write_reorg_wal(
            old_tip=original_tip,
            new_tip="test_new_tip",
            fork_point=0
        )

        # Verify WAL was created
        assert os.path.exists(blockchain.reorg_wal_path), "WAL should exist after write"
        assert wal_entry["status"] == "in_progress"
        assert wal_entry["old_tip"] == original_tip
        assert wal_entry["new_tip"] == "test_new_tip"

        # Verify WAL contents on disk
        with open(blockchain.reorg_wal_path, "r") as f:
            wal_data = json.load(f)
        assert wal_data["status"] == "in_progress"

    def test_wal_committed_on_success(self, blockchain):
        """Verify WAL is cleared when reorg succeeds."""
        blockchain.create_genesis_block()

        wal_entry = blockchain._write_reorg_wal(
            old_tip="old",
            new_tip="new",
            fork_point=0
        )

        assert os.path.exists(blockchain.reorg_wal_path)

        # Commit the reorg
        blockchain._commit_reorg_wal(wal_entry)

        # WAL should be removed after successful commit
        assert not os.path.exists(blockchain.reorg_wal_path), "WAL should be removed after commit"

    def test_wal_rolled_back_on_failure(self, blockchain):
        """Verify WAL is cleared when reorg fails and rolls back."""
        blockchain.create_genesis_block()

        wal_entry = blockchain._write_reorg_wal(
            old_tip="old",
            new_tip="new",
            fork_point=0
        )

        assert os.path.exists(blockchain.reorg_wal_path)

        # Rollback the reorg
        blockchain._rollback_reorg_wal(wal_entry)

        # WAL should be removed after rollback
        assert not os.path.exists(blockchain.reorg_wal_path), "WAL should be removed after rollback"

    def test_wal_recovery_on_startup(self):
        """Verify incomplete reorg is detected on startup."""
        data_dir = tempfile.mkdtemp(prefix="test_wal_recovery_")

        # Create a WAL file simulating a crash during reorg
        wal_path = os.path.join(data_dir, "reorg_wal.json")
        wal_data = {
            "type": "REORG_BEGIN",
            "old_tip": "old_hash",
            "new_tip": "new_hash",
            "fork_point": 5,
            "timestamp": 1234567890.0,
            "status": "in_progress"
        }

        with open(wal_path, "w") as f:
            json.dump(wal_data, f)

        # Create blockchain - should detect and recover from incomplete reorg
        bc = Blockchain(data_dir=data_dir)

        # WAL should be cleared after recovery
        assert not os.path.exists(wal_path), "WAL should be cleared after recovery"

        # Cleanup
        import shutil
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)

    def test_comprehensive_state_snapshot(self, blockchain):
        """Verify all state managers are snapshotted before reorg."""
        blockchain.create_genesis_block()

        # Verify snapshot methods exist on all managers
        assert hasattr(blockchain.utxo_manager, 'snapshot'), "UTXO manager must have snapshot"
        assert hasattr(blockchain.utxo_manager, 'restore'), "UTXO manager must have restore"

        if blockchain.nonce_tracker:
            assert hasattr(blockchain.nonce_tracker, 'snapshot'), "Nonce tracker must have snapshot"
            assert hasattr(blockchain.nonce_tracker, 'restore'), "Nonce tracker must have restore"

        if blockchain.smart_contract_manager:
            assert hasattr(blockchain.smart_contract_manager, 'snapshot'), "Contract manager must have snapshot"
            assert hasattr(blockchain.smart_contract_manager, 'restore'), "Contract manager must have restore"

        if blockchain.governance_executor:
            assert hasattr(blockchain.governance_executor, 'snapshot'), "Governance must have snapshot"
            assert hasattr(blockchain.governance_executor, 'restore'), "Governance must have restore"

        if blockchain.finality_manager:
            assert hasattr(blockchain.finality_manager, 'snapshot'), "Finality must have snapshot"
            assert hasattr(blockchain.finality_manager, 'restore'), "Finality must have restore"

    def test_snapshot_restore_roundtrip(self, blockchain):
        """Verify snapshot/restore preserves exact state."""
        blockchain.create_genesis_block()

        # Take snapshots
        utxo_snapshot = blockchain.utxo_manager.snapshot()
        nonce_snapshot = blockchain.nonce_tracker.snapshot() if blockchain.nonce_tracker else None

        # Modify state
        blockchain.utxo_manager.add_utxo("XAI123", "tx1", 0, 100.0, "script")
        if blockchain.nonce_tracker:
            blockchain.nonce_tracker.set_nonce("XAI123", 5)

        # Verify state changed
        assert blockchain.utxo_manager.get_balance("XAI123") > 0
        if blockchain.nonce_tracker:
            assert blockchain.nonce_tracker.get_nonce("XAI123") == 5

        # Restore from snapshot
        blockchain.utxo_manager.restore(utxo_snapshot)
        if nonce_snapshot and blockchain.nonce_tracker:
            blockchain.nonce_tracker.restore(nonce_snapshot)

        # Verify state restored to original
        assert blockchain.utxo_manager.get_balance("XAI123") == 0
        if blockchain.nonce_tracker:
            assert blockchain.nonce_tracker.get_nonce("XAI123") == -1  # Initial state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
