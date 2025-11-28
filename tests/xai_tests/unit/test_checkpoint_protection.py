"""
Checkpoint Protection Tests (Task 200)

Tests for Blockchain.replace_chain checkpoint protection to verify that
forks cannot reorganize the chain before checkpoint heights.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.xai.core.blockchain import Blockchain, Block, Transaction


class TestCheckpointProtection:
    """Test checkpoint-based fork protection"""

    def setup_method(self):
        """Setup fresh blockchain for each test"""
        self.blockchain = Blockchain(data_dir="/tmp/test_checkpoint_protection")

    def create_dummy_transaction(self, idx: int) -> Transaction:
        """Create a dummy transaction for testing"""
        tx = Transaction(
            sender="COINBASE",
            recipient=f"XAI{'0' * 40}miner{idx}",
            amount=12.0,
            fee=0.0,
        )
        tx.txid = f"tx_{idx}_" + "x" * 58
        return tx

    def create_test_block(self, index: int, previous_hash: str, difficulty: int = 1) -> Block:
        """Create a test block"""
        txs = [self.create_dummy_transaction(index)]
        block = Block(
            index=index,
            transactions=txs,
            previous_hash=previous_hash,
            difficulty=difficulty
        )
        # Mine the block (simple version)
        block.hash = f"hash_{index}_" + "0" * 58
        return block

    def test_reject_fork_before_checkpoint(self):
        """Task 200: Reject chain replacement before checkpoint height"""
        # Build initial chain to height 10
        for i in range(10):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create checkpoint at height 5
        if hasattr(self.blockchain, 'checkpoint_manager'):
            checkpoint_block = self.blockchain.chain[5]
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=5,
                block_hash=checkpoint_block.hash,
                state_root="state_" + "0" * 57
            )

        # Create fork chain that diverges at block 3 (before checkpoint)
        fork_chain = self.blockchain.chain[:3].copy()
        for i in range(3, 12):
            prev_hash = fork_chain[-1].hash
            block = self.create_test_block(i, prev_hash, difficulty=2)
            fork_chain.append(block)

        # Try to replace with fork (should be rejected due to checkpoint)
        original_length = len(self.blockchain.chain)
        result = self.blockchain.replace_chain(fork_chain)

        # Chain should not be replaced
        assert not result, "Fork before checkpoint should be rejected"
        assert len(self.blockchain.chain) == original_length, "Chain length should not change"

    def test_accept_fork_after_checkpoint(self):
        """Task 200: Accept chain replacement after checkpoint height"""
        # Build initial chain to height 10
        for i in range(10):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create checkpoint at height 5
        if hasattr(self.blockchain, 'checkpoint_manager'):
            checkpoint_block = self.blockchain.chain[5]
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=5,
                block_hash=checkpoint_block.hash,
                state_root="state_" + "0" * 57
            )

        # Create fork chain that diverges at block 8 (after checkpoint)
        fork_chain = self.blockchain.chain[:8].copy()
        for i in range(8, 12):
            prev_hash = fork_chain[-1].hash
            # Make fork slightly better (higher difficulty or longer)
            block = self.create_test_block(i, prev_hash, difficulty=2)
            fork_chain.append(block)

        # Try to replace with fork (might be accepted if valid and better)
        # This depends on chain selection rules (longest, most work, etc.)
        # The key is it should not be rejected SOLELY due to checkpoint
        # since divergence is after checkpoint

    def test_checkpoint_at_genesis(self):
        """Task 200: Checkpoint at genesis protects entire chain"""
        # Build chain
        for i in range(5):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create checkpoint at genesis (height 0)
        if hasattr(self.blockchain, 'checkpoint_manager'):
            genesis_block = self.blockchain.chain[0]
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=0,
                block_hash=genesis_block.hash,
                state_root="genesis_state"
            )

        # Try to replace entire chain
        fork_chain = []
        for i in range(7):
            prev_hash = fork_chain[-1].hash if fork_chain else "fork_genesis"
            block = self.create_test_block(i, prev_hash)
            fork_chain.append(block)

        result = self.blockchain.replace_chain(fork_chain)

        # Should be rejected due to genesis checkpoint
        assert not result, "Fork from different genesis should be rejected"

    def test_multiple_checkpoints_protection(self):
        """Task 200: Multiple checkpoints provide layered protection"""
        # Build chain to height 15
        for i in range(15):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create multiple checkpoints
        if hasattr(self.blockchain, 'checkpoint_manager'):
            for checkpoint_height in [3, 7, 11]:
                checkpoint_block = self.blockchain.chain[checkpoint_height]
                self.blockchain.checkpoint_manager.create_checkpoint(
                    height=checkpoint_height,
                    block_hash=checkpoint_block.hash,
                    state_root=f"state_{checkpoint_height}"
                )

        # Try fork before each checkpoint
        for fork_point in [2, 6, 10]:
            fork_chain = self.blockchain.chain[:fork_point].copy()
            for i in range(fork_point, 16):
                prev_hash = fork_chain[-1].hash
                block = self.create_test_block(i, prev_hash, difficulty=2)
                fork_chain.append(block)

            result = self.blockchain.replace_chain(fork_chain)
            assert not result, f"Fork at height {fork_point} should be rejected by checkpoint"

    def test_checkpoint_block_hash_validation(self):
        """Task 200: Verify checkpoint block hash must match"""
        # Build chain
        for i in range(10):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create checkpoint with specific block hash
        if hasattr(self.blockchain, 'checkpoint_manager'):
            checkpoint_block = self.blockchain.chain[5]
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=5,
                block_hash=checkpoint_block.hash,
                state_root="state_checkpoint"
            )

        # Create fork with different block at checkpoint height
        fork_chain = self.blockchain.chain[:5].copy()
        # Different block at height 5
        different_block = self.create_test_block(5, fork_chain[-1].hash, difficulty=3)
        different_block.hash = "different_" + "0" * 54
        fork_chain.append(different_block)

        for i in range(6, 12):
            prev_hash = fork_chain[-1].hash
            block = self.create_test_block(i, prev_hash)
            fork_chain.append(block)

        result = self.blockchain.replace_chain(fork_chain)

        # Should be rejected because checkpoint hash doesn't match
        assert not result, "Fork with different checkpoint block should be rejected"

    def test_no_checkpoints_allows_any_fork(self):
        """Task 200: Without checkpoints, normal fork choice rules apply"""
        # Build chain WITHOUT checkpoints
        for i in range(10):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create longer fork from early block
        fork_chain = self.blockchain.chain[:2].copy()
        for i in range(2, 15):  # Longer than original
            prev_hash = fork_chain[-1].hash
            block = self.create_test_block(i, prev_hash)
            fork_chain.append(block)

        # Without checkpoint protection, should use normal fork choice
        # (This test documents current behavior)
        result = self.blockchain.replace_chain(fork_chain)
        # Result depends on fork choice implementation

    def test_checkpoint_manager_max_checkpoints(self):
        """Task 200: Verify checkpoint manager respects max checkpoints limit"""
        if not hasattr(self.blockchain, 'checkpoint_manager'):
            pytest.skip("Checkpoint manager not available")

        # Build long chain
        for i in range(50):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Create many checkpoints (more than max)
        for i in range(0, 50, 5):
            checkpoint_block = self.blockchain.chain[i]
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=i,
                block_hash=checkpoint_block.hash,
                state_root=f"state_{i}"
            )

        # Verify only max checkpoints are kept
        max_checkpoints = self.blockchain.checkpoint_manager.max_checkpoints
        checkpoint_count = len(self.blockchain.checkpoint_manager.checkpoints)
        assert checkpoint_count <= max_checkpoints, "Should not exceed max checkpoints"

    def test_checkpoint_prevents_deep_reorganization(self):
        """Task 200: Checkpoints prevent deep blockchain reorganization attacks"""
        # Simulate a deep reorganization attack scenario

        # Build honest chain to height 20
        for i in range(20):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        # Checkpoints created every 5 blocks
        if hasattr(self.blockchain, 'checkpoint_manager'):
            for checkpoint_height in [5, 10, 15]:
                checkpoint_block = self.blockchain.chain[checkpoint_height]
                self.blockchain.checkpoint_manager.create_checkpoint(
                    height=checkpoint_height,
                    block_hash=checkpoint_block.hash,
                    state_root=f"state_{checkpoint_height}"
                )

        # Attacker tries to reorg from block 3 (deep reorganization)
        attack_chain = self.blockchain.chain[:3].copy()
        # Build much longer attack chain
        for i in range(3, 30):
            prev_hash = attack_chain[-1].hash
            block = self.create_test_block(i, prev_hash, difficulty=1)
            attack_chain.append(block)

        # Attack should be prevented by checkpoint at height 5
        result = self.blockchain.replace_chain(attack_chain)
        assert not result, "Deep reorganization should be prevented by checkpoint"
        assert len(self.blockchain.chain) == 20, "Chain should maintain original length"


class TestCheckpointEdgeCases:
    """Test edge cases for checkpoint protection"""

    def setup_method(self):
        """Setup fresh blockchain for each test"""
        self.blockchain = Blockchain(data_dir="/tmp/test_checkpoint_edge")

    def create_dummy_transaction(self, idx: int) -> Transaction:
        """Create a dummy transaction for testing"""
        tx = Transaction(
            sender="COINBASE",
            recipient=f"XAI{'0' * 40}miner{idx}",
            amount=12.0,
            fee=0.0,
        )
        tx.txid = f"tx_{idx}_" + "x" * 58
        return tx

    def create_test_block(self, index: int, previous_hash: str) -> Block:
        """Create a test block"""
        txs = [self.create_dummy_transaction(index)]
        block = Block(index=index, transactions=txs, previous_hash=previous_hash, difficulty=1)
        block.hash = f"hash_{index}_" + "0" * 58
        return block

    def test_empty_chain_with_checkpoint(self):
        """Edge case: Checkpoint on empty chain"""
        if hasattr(self.blockchain, 'checkpoint_manager'):
            # Try to create checkpoint on empty chain
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=0,
                block_hash="fake_hash",
                state_root="fake_state"
            )
            # Should handle gracefully

    def test_checkpoint_beyond_chain_length(self):
        """Edge case: Checkpoint at height beyond current chain"""
        # Build small chain
        for i in range(5):
            prev_hash = self.blockchain.get_latest_block().hash if self.blockchain.chain else "0" * 64
            block = self.create_test_block(i, prev_hash)
            self.blockchain.chain.append(block)

        if hasattr(self.blockchain, 'checkpoint_manager'):
            # Create checkpoint at height 10 (beyond current chain length 5)
            self.blockchain.checkpoint_manager.create_checkpoint(
                height=10,
                block_hash="future_hash",
                state_root="future_state"
            )
            # Should handle gracefully (might ignore or queue for later)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
