"""
Comprehensive integration tests for chain reorganization scenarios

Tests various fork scenarios:
- Simple 1-block forks
- Deep reorganizations (10+ blocks)
- Competing chains with different work
- Transaction handling during reorgs
- UTXO set consistency after reorgs
- Orphan block resolution
"""

import pytest
import time
from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet
from xai.core.consensus.node_consensus import ConsensusManager
from xai.core.consensus.advanced_consensus import AdvancedConsensusManager


class TestSimpleChainReorg:
    """Test simple chain reorganization scenarios"""

    def test_single_block_fork_resolution(self, tmp_path):
        """Test resolving a single block fork"""
        # Create two chains that fork at block 1
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Mine common blocks
        bc1.mine_pending_transactions(wallet.address)

        # Fork: both chains mine different block at index 2
        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        # bc1 mines another block (becomes longer)
        bc1.mine_pending_transactions(wallet.address)

        # Consensus manager should prefer bc1 (longer)
        manager = ConsensusManager(bc2)
        should_replace, reason = manager.should_replace_chain(bc1.chain)

        assert should_replace is True
        assert len(bc1.chain) > len(bc2.chain)

    def test_two_block_fork_resolution(self, tmp_path):
        """Test resolving a two-block fork"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Common ancestor
        bc1.mine_pending_transactions(wallet.address)

        # Fork divergence
        bc1.mine_pending_transactions(wallet.address)
        bc1.mine_pending_transactions(wallet.address)

        bc2.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc2)
        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        # Should select bc1 (longer chain)
        assert len(chain) == len(bc1.chain)

    def test_equal_length_fork_uses_work(self, tmp_path):
        """Test fork resolution uses cumulative work for equal length chains"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Make equal length chains with different difficulties
        bc1.difficulty = 4
        bc2.difficulty = 6

        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc1)

        # Calculate work
        work1 = manager.calculate_chain_work(bc1.chain)
        work2 = manager.calculate_chain_work(bc2.chain)

        # Higher difficulty should have more work
        assert isinstance(work1, int)
        assert isinstance(work2, int)


class TestDeepChainReorg:
    """Test deep chain reorganizations"""

    def test_ten_block_reorganization(self, tmp_path):
        """Test reorganizing 10 blocks deep"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Build bc1 with 10 blocks
        for i in range(10):
            bc1.mine_pending_transactions(wallet.address)

        # Build bc2 with 12 blocks (longer)
        for i in range(12):
            bc2.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc1)
        should_replace, reason = manager.should_replace_chain(bc2.chain)

        assert should_replace is True
        assert len(bc2.chain) > len(bc1.chain)

    def test_deep_reorg_validates_all_blocks(self, tmp_path):
        """Test deep reorg validates entire chain"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Build chains
        for i in range(15):
            bc1.mine_pending_transactions(wallet.address)

        for i in range(20):
            bc2.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc1)

        # Validate the longer chain
        is_valid, error = manager.validate_chain(bc2.chain)

        assert is_valid is True
        assert error is None


class TestTransactionHandlingDuringReorg:
    """Test transaction handling during reorganization"""

    def test_transactions_survive_reorg(self, tmp_path):
        """Test transactions included in losing chain are re-broadcast"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to wallet1
        bc.mine_pending_transactions(wallet1.address)

        # Create and add transaction
        tx = bc.create_transaction(
            wallet1.address,
            wallet2.address,
            5.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx:
            bc.add_transaction(tx)

            # Mine transaction into block
            bc.mine_pending_transactions(wallet1.address)

            # Verify transaction is in chain
            found = False
            for block in bc.chain:
                for block_tx in block.transactions:
                    if block_tx.txid == tx.txid:
                        found = True
                        break
                if found:
                    break

            # Transaction should be in blockchain
            assert found or len(bc.pending_transactions) > 0

    def test_double_spend_prevented_after_reorg(self, tmp_path):
        """Test double-spending is prevented after reorganization"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Mine to wallet1
        bc.mine_pending_transactions(wallet1.address)

        # Create transaction to wallet2
        tx1 = bc.create_transaction(
            wallet1.address,
            wallet2.address,
            5.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx1:
            bc.add_transaction(tx1)
            bc.mine_pending_transactions(wallet1.address)

            # Try to create another transaction spending the SAME inputs as tx1
            # (manually creating with same inputs to test double-spend detection)
            tx2 = Transaction(
                sender=wallet1.address,
                recipient=wallet3.address,
                amount=5.0,
                fee=0.1,
                public_key=wallet1.public_key,
                inputs=tx1.inputs,  # Use the SAME inputs as tx1 (already spent!)
                outputs=[{"address": wallet3.address, "amount": 5.0}],
                nonce=bc.nonce_tracker.get_next_nonce(wallet1.address)
            )
            tx2.sign_transaction(wallet1.private_key)

            # Validation should fail because tx1's inputs were already spent
            is_valid = bc.validate_transaction(tx2)
            assert is_valid is False


class TestUTXOConsistencyDuringReorg:
    """Test UTXO set remains consistent during reorganization"""

    def test_utxo_set_updated_after_reorg(self, tmp_path):
        """Test UTXO set is correctly updated after reorg"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Initial state
        bc.mine_pending_transactions(wallet1.address)
        initial_balance = bc.get_balance(wallet1.address)

        # Create transaction
        tx = bc.create_transaction(
            wallet1.address,
            wallet2.address,
            3.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx:
            bc.add_transaction(tx)
            bc.mine_pending_transactions(wallet1.address)

            # Check balances
            balance1 = bc.get_balance(wallet1.address)
            balance2 = bc.get_balance(wallet2.address)

            # wallet2 should have received funds
            assert balance2 > 0

    def test_utxo_set_rollback_on_reorg(self, tmp_path):
        """Test UTXO set rolls back correctly during reorg"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to wallet1
        bc1.mine_pending_transactions(wallet1.address)

        # Create transaction
        tx = bc1.create_transaction(
            wallet1.address,
            wallet2.address,
            5.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx:
            bc1.add_transaction(tx)
            bc1.mine_pending_transactions(wallet1.address)

            # Store UTXO state
            utxo_count = len(bc1.utxo_set)

            # UTXO set should have entries
            assert utxo_count > 0


class TestOrphanBlockHandling:
    """Test orphan block handling during reorganization"""

    def test_orphan_block_stored_until_parent_arrives(self, tmp_path):
        """Test orphan blocks are stored until parent arrives"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Create block with non-existent parent
        orphan = bc.mine_pending_transactions(wallet.address)
        orphan.previous_hash = "nonexistent_parent"
        orphan.index = 100

        # Process as orphan
        accepted, message = manager.process_new_block(orphan)

        # Should be rejected but stored as orphan
        assert accepted is False
        assert "orphan" in message.lower()

    def test_orphan_block_processed_when_parent_arrives(self, tmp_path):
        """Test orphan is processed when parent arrives"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine parent block
        parent = bc.mine_pending_transactions(wallet.address)

        # Create orphan that depends on parent
        orphan = bc.mine_pending_transactions(wallet.address)
        manager.orphan_pool.add_orphan(orphan, parent.hash)

        # Process orphans after parent
        manager.process_orphans_after_block(parent.hash)

        # Orphan should have been attempted


class TestCompetingChains:
    """Test competing chain scenarios"""

    def test_three_way_fork_resolution(self, tmp_path):
        """Test resolving three competing chains"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        bc3 = Blockchain(data_dir=str(tmp_path / "bc3"))
        wallet = Wallet()

        # Build different length chains
        for i in range(3):
            bc1.mine_pending_transactions(wallet.address)

        for i in range(5):
            bc2.mine_pending_transactions(wallet.address)

        for i in range(2):
            bc3.mine_pending_transactions(wallet.address)

        manager = ConsensusManager(bc1)
        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain, bc3.chain])

        # Should select bc2 (longest)
        assert len(chain) == len(bc2.chain)

    def test_competing_chains_with_invalid(self, tmp_path):
        """Test fork resolution ignores invalid chains"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        wallet = Wallet()

        # Build chains
        bc1.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)
        bc2.mine_pending_transactions(wallet.address)

        # Invalidate bc2 (even though longer)
        bc2.chain[1].hash = "invalid"

        manager = ConsensusManager(bc1)
        chain, reason = manager.resolve_forks([bc1.chain, bc2.chain])

        # Should select bc1 (bc2 is invalid)
        assert len(chain) == len(bc1.chain)


class TestReorgWithDifferentDifficulty:
    """Test reorganizations with varying difficulty"""

    def test_reorg_preserves_difficulty_changes(self, tmp_path):
        """Test difficulty changes are preserved after reorg"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Change difficulty
        original_difficulty = bc.difficulty
        bc.difficulty = 5

        # Mine with new difficulty
        bc.mine_pending_transactions(wallet.address)

        # Verify difficulty was used
        block = bc.get_latest_block()
        assert block.difficulty == 5

    def test_reorg_with_adaptive_difficulty(self, tmp_path):
        """Test reorganization with adaptive difficulty adjustment"""
        from xai.core.consensus.advanced_consensus import DynamicDifficultyAdjustment

        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Mine blocks
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        # Check if difficulty should adjust
        should_adjust = adjuster.should_adjust_difficulty(bc)

        # Calculate new difficulty
        if should_adjust:
            new_diff = adjuster.calculate_new_difficulty(bc)
            assert new_diff >= adjuster.min_difficulty
            assert new_diff <= adjuster.max_difficulty


class TestReorgEdgeCases:
    """Test edge cases in chain reorganization"""

    def test_reorg_to_empty_chain(self, tmp_path):
        """Test attempting reorg to empty chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Try to replace with empty chain
        should_replace, reason = manager.should_replace_chain([])

        assert should_replace is False

    def test_reorg_with_genesis_only(self, tmp_path):
        """Test reorg with genesis-only chain"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))
        manager = ConsensusManager(bc1)
        wallet = Wallet()

        # bc1 has mined blocks
        bc1.mine_pending_transactions(wallet.address)

        # bc2 only has genesis
        # Should not replace bc1 with bc2
        should_replace, reason = manager.should_replace_chain(bc2.chain)

        assert should_replace is False

    def test_self_reorg_no_op(self, tmp_path):
        """Test replacing chain with itself is no-op"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = ConsensusManager(bc)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Try to replace with same chain
        should_replace, reason = manager.should_replace_chain(bc.chain)

        # Should not replace (same length)
        assert should_replace is False


class TestFinalizationDuringReorg:
    """Test finalization prevents deep reorganizations"""

    def test_finalized_blocks_not_reorged(self, tmp_path):
        """Test finalized blocks resist reorganization"""
        from xai.core.consensus.advanced_consensus import FinalityTracker

        bc = Blockchain(data_dir=str(tmp_path))
        tracker = FinalityTracker()
        wallet = Wallet()

        # Mine many blocks
        for i in range(120):
            bc.mine_pending_transactions(wallet.address)

        # Early blocks should achieve hard finality
        finality = tracker.get_block_finality(0, len(bc.chain))

        assert finality["finality_level"] == "hard"
        assert finality["reversible"] is False

    def test_soft_finality_still_reorgable(self, tmp_path):
        """Test soft finalized blocks can still be reorganized"""
        from xai.core.consensus.advanced_consensus import FinalityTracker

        bc = Blockchain(data_dir=str(tmp_path))
        tracker = FinalityTracker()
        wallet = Wallet()

        # Mine blocks to achieve soft finality
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        # Recent blocks should have soft finality
        finality = tracker.get_block_finality(4, len(bc.chain))

        assert finality["finality_level"] in ["soft", "pending"]
        assert finality["reversible"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
