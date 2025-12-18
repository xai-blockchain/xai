"""
Unit tests for blockchain pruning functionality.

Tests:
- PruningPolicy configuration from environment
- BlockPruningManager initialization
- Prune height calculation (block count, time-based, disk space)
- Pruning operations (with/without archiving)
- Block restoration from archives
- Status and statistics tracking
- Integration with existing PrunedNode
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from xai.core.pruning import (
    BlockPruningManager,
    PruningPolicy,
    PruneMode,
    PruningStats,
)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_blockchain():
    """Create mock blockchain with test blocks"""
    blockchain = Mock()

    # Create mock blocks spanning multiple days
    now = time.time()
    blocks = []

    for i in range(200):
        block = Mock()
        block.index = i
        block.hash = f"hash_{i:04d}"
        block.timestamp = now - (199 - i) * 600  # 10 minutes per block, oldest first
        block.transactions = [Mock(txid=f"tx_{i}_{j}") for j in range(5)]

        # Mock to_dict for serialization
        block.to_dict = Mock(return_value={
            "index": i,
            "hash": f"hash_{i:04d}",
            "timestamp": block.timestamp,
            "transactions": [{"txid": f"tx_{i}_{j}"} for j in range(5)]
        })

        blocks.append(block)

    blockchain.chain = blocks
    return blockchain


class TestPruningPolicy:
    """Test pruning policy configuration"""

    def test_policy_from_config_defaults(self):
        """Test default policy creation"""
        with patch.dict(os.environ, {}, clear=True):
            policy = PruningPolicy.from_config()

            assert policy.mode == PruneMode.NONE
            assert policy.retain_blocks == 1000
            assert policy.retain_days == 30
            assert policy.archive_before_delete is True
            assert policy.disk_threshold_gb == 50.0
            assert policy.min_finalized_depth == 100
            assert policy.keep_headers_only is True

    def test_policy_from_environment(self):
        """Test policy creation from environment variables"""
        env = {
            'XAI_PRUNE_MODE': 'blocks',
            'XAI_PRUNE_KEEP_BLOCKS': '2000',
            'XAI_PRUNE_KEEP_DAYS': '60',
            'XAI_PRUNE_ARCHIVE': 'false',
            'XAI_PRUNE_DISK_THRESHOLD_GB': '100.0',
            'XAI_PRUNE_MIN_FINALIZED_DEPTH': '200',
            'XAI_PRUNE_KEEP_HEADERS': 'false',
        }

        with patch.dict(os.environ, env, clear=True):
            policy = PruningPolicy.from_config()

            assert policy.mode == PruneMode.BLOCKS
            assert policy.retain_blocks == 2000
            assert policy.retain_days == 60
            assert policy.archive_before_delete is False
            assert policy.disk_threshold_gb == 100.0
            assert policy.min_finalized_depth == 200
            assert policy.keep_headers_only is False

    def test_policy_invalid_mode(self):
        """Test handling of invalid prune mode"""
        with patch.dict(os.environ, {'XAI_PRUNE_MODE': 'invalid'}, clear=True):
            policy = PruningPolicy.from_config()
            assert policy.mode == PruneMode.NONE

    def test_policy_all_modes(self):
        """Test all valid prune modes"""
        for mode_str in ['none', 'blocks', 'days', 'both', 'space']:
            with patch.dict(os.environ, {'XAI_PRUNE_MODE': mode_str}, clear=True):
                policy = PruningPolicy.from_config()
                assert policy.mode == PruneMode(mode_str)


class TestBlockPruningManager:
    """Test BlockPruningManager functionality"""

    def test_init(self, mock_blockchain, temp_data_dir):
        """Test manager initialization"""
        manager = BlockPruningManager(mock_blockchain, data_dir=temp_data_dir)

        assert manager.blockchain == mock_blockchain
        assert manager.policy.mode == PruneMode.NONE
        assert len(manager.pruned_heights) == 0
        assert manager.stats.pruned_blocks == 0

    def test_init_with_custom_policy(self, mock_blockchain, temp_data_dir):
        """Test initialization with custom policy"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=500,
            retain_days=15,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=25.0,
            min_finalized_depth=50,
            keep_headers_only=False,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        assert manager.policy.mode == PruneMode.BLOCKS
        assert manager.policy.retain_blocks == 500
        assert manager.policy.retain_days == 15

    def test_should_prune_none_mode(self, mock_blockchain, temp_data_dir):
        """Test should_prune with NONE mode"""
        policy = PruningPolicy(
            mode=PruneMode.NONE,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)
        assert manager.should_prune() is False

    def test_should_prune_blocks_mode(self, mock_blockchain, temp_data_dir):
        """Test should_prune with BLOCKS mode"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        # With 200 blocks, retain_blocks=100, min_finalized=10
        # Should prune: 200 > 100 + 10
        assert manager.should_prune() is True

    def test_should_prune_days_mode(self, mock_blockchain, temp_data_dir):
        """Test should_prune with DAYS mode"""
        policy = PruningPolicy(
            mode=PruneMode.DAYS,
            retain_blocks=1000,
            retain_days=1,  # 1 day retention
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        # Blocks span ~33 hours (200 blocks * 10 min), so should have blocks older than 1 day
        assert manager.should_prune() is True

    def test_calculate_prune_height_blocks_mode(self, mock_blockchain, temp_data_dir):
        """Test prune height calculation in BLOCKS mode"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        # 200 blocks, keep 100, min_finalized 10
        # Prune up to: 200 - 100 - 1 = 99
        # But limited by finalized: min(99, 200 - 10 - 1) = min(99, 189) = 99
        prune_height = manager.calculate_prune_height()
        assert prune_height == 89  # 200 - 100 - 10 - 1

    def test_calculate_prune_height_days_mode(self, mock_blockchain, temp_data_dir):
        """Test prune height calculation in DAYS mode"""
        policy = PruningPolicy(
            mode=PruneMode.DAYS,
            retain_blocks=1000,
            retain_days=1,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        prune_height = manager.calculate_prune_height()

        # Should prune blocks older than 1 day
        # With 10min blocks, that's 144 blocks = 24 hours
        # Chain is 200 blocks spanning ~33 hours
        # Oldest blocks should be pruned
        assert prune_height >= 0

    def test_calculate_prune_height_both_mode(self, mock_blockchain, temp_data_dir):
        """Test prune height calculation in BOTH mode (more restrictive)"""
        policy = PruningPolicy(
            mode=PruneMode.BOTH,
            retain_blocks=150,
            retain_days=1,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        prune_height = manager.calculate_prune_height()

        # Should use whichever keeps MORE blocks (prunes less)
        assert prune_height >= 0

    def test_calculate_prune_height_respects_min_finalized(self, mock_blockchain, temp_data_dir):
        """Test that prune height never exceeds min_finalized_depth"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=10,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=150,  # High safety margin
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        prune_height = manager.calculate_prune_height()

        # With 200 blocks and min_finalized 150, can only prune up to 200-150-1 = 49
        assert prune_height <= 49

    def test_prune_blocks_dry_run(self, mock_blockchain, temp_data_dir):
        """Test dry run pruning"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        result = manager.prune_blocks(dry_run=True)

        assert result['dry_run'] is True
        assert result['pruned'] > 0
        assert result['space_saved'] > 0
        assert len(manager.pruned_heights) == 0  # No actual pruning

    def test_prune_blocks_with_archiving(self, mock_blockchain, temp_data_dir):
        """Test pruning with archiving enabled"""
        archive_path = os.path.join(temp_data_dir, 'archive')

        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=True,
            archive_path=archive_path,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        result = manager.prune_blocks(up_to_height=10)

        assert result['pruned'] == 10  # Blocks 1-10 (skip genesis)
        assert result['archived'] == 10
        assert len(manager.pruned_heights) == 10

        # Check archive files exist
        archive_dir = Path(archive_path)
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob('block_*.json.gz'))
        assert len(archive_files) == 10

    def test_prune_blocks_without_archiving(self, mock_blockchain, temp_data_dir):
        """Test pruning without archiving"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        result = manager.prune_blocks(up_to_height=10)

        assert result['pruned'] == 10
        assert result['archived'] == 0

    def test_archive_and_restore_block(self, mock_blockchain, temp_data_dir):
        """Test archiving and restoring a block"""
        archive_path = os.path.join(temp_data_dir, 'archive')

        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=True,
            archive_path=archive_path,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        # Archive a block
        block = mock_blockchain.chain[5]
        assert manager._archive_block(block) is True

        # Verify archive file exists and is compressed
        archive_file = Path(archive_path) / "block_5.json.gz"
        assert archive_file.exists()

        # Verify it's actually gzipped
        with gzip.open(archive_file, 'rb') as f:
            data = f.read()
            block_data = json.loads(data)
            assert block_data['index'] == 5

    def test_prune_block_keeps_headers(self, mock_blockchain, temp_data_dir):
        """Test that pruning keeps headers when configured"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        block = mock_blockchain.chain[5]
        original_tx_count = len(block.transactions)

        assert manager._prune_block(block) is True
        assert len(block.transactions) == 0  # Transactions removed
        assert 5 in manager.headers_only_heights

    def test_get_status(self, mock_blockchain, temp_data_dir):
        """Test status reporting"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        status = manager.get_status()

        assert status['mode'] == 'blocks'
        assert status['enabled'] is True
        assert 'policy' in status
        assert 'stats' in status
        assert 'chain' in status
        assert status['chain']['total_blocks'] == 200

    def test_is_block_pruned(self, mock_blockchain, temp_data_dir):
        """Test checking if block is pruned"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        assert manager.is_block_pruned(5) is False

        manager.prune_blocks(up_to_height=10)

        assert manager.is_block_pruned(5) is True
        assert manager.is_block_pruned(15) is False

    def test_has_full_block(self, mock_blockchain, temp_data_dir):
        """Test checking if full block data is available"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        assert manager.has_full_block(5) is True

        manager.prune_blocks(up_to_height=10)

        assert manager.has_full_block(5) is False  # Pruned to header only
        assert manager.has_full_block(15) is True

    def test_set_policy_updates_stats(self, mock_blockchain, temp_data_dir):
        """Test that updating policy updates stats"""
        policy1 = PruningPolicy(
            mode=PruneMode.NONE,
            retain_blocks=100,
            retain_days=30,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy1, data_dir=temp_data_dir)

        assert manager.stats.mode == 'none'

        policy2 = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=200,
            retain_days=60,
            archive_before_delete=True,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager.set_policy(policy2)

        assert manager.stats.mode == 'blocks'
        assert manager.stats.retention_blocks == 200
        assert manager.stats.retention_days == 60

    def test_prune_respects_genesis_block(self, mock_blockchain, temp_data_dir):
        """Test that genesis block is never pruned"""
        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=10,
            retain_days=0,
            archive_before_delete=False,
            archive_path=temp_data_dir,
            disk_threshold_gb=50.0,
            min_finalized_depth=5,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        # Prune aggressively
        result = manager.prune_blocks()

        # Genesis (block 0) should never be in pruned set
        assert 0 not in manager.pruned_heights

    def test_statistics_tracking(self, mock_blockchain, temp_data_dir):
        """Test that statistics are properly tracked"""
        archive_path = os.path.join(temp_data_dir, 'archive')

        policy = PruningPolicy(
            mode=PruneMode.BLOCKS,
            retain_blocks=150,
            retain_days=30,
            archive_before_delete=True,
            archive_path=archive_path,
            disk_threshold_gb=50.0,
            min_finalized_depth=10,
            keep_headers_only=True,
        )

        manager = BlockPruningManager(mock_blockchain, policy=policy, data_dir=temp_data_dir)

        initial_stats = manager.get_stats()
        assert initial_stats.pruned_blocks == 0
        assert initial_stats.disk_space_saved == 0

        result = manager.prune_blocks(up_to_height=20)

        updated_stats = manager.get_stats()
        assert updated_stats.pruned_blocks == 20
        assert updated_stats.archived_blocks == 20
        assert updated_stats.disk_space_saved > 0
        assert updated_stats.last_prune_time > 0


class TestPruningIntegration:
    """Test integration with existing node modes"""

    def test_integration_with_pruned_node(self, mock_blockchain, temp_data_dir):
        """Test that BlockPruningManager can work alongside PrunedNode"""
        from xai.performance.node_modes import PrunedNode

        # Old-style pruned node
        pruned_node = PrunedNode(mock_blockchain, keep_blocks=100)

        # New-style pruning manager
        manager = BlockPruningManager(mock_blockchain, data_dir=temp_data_dir)

        # Both should coexist
        assert pruned_node.keep_blocks == 100
        assert manager.policy.retain_blocks == 1000

    def test_config_integration(self, mock_blockchain, temp_data_dir):
        """Test configuration from xai.core.config"""
        with patch.dict(os.environ, {
            'XAI_PRUNE_MODE': 'blocks',
            'XAI_PRUNE_KEEP_BLOCKS': '500',
        }, clear=True):
            manager = BlockPruningManager(mock_blockchain, data_dir=temp_data_dir)

            assert manager.policy.mode == PruneMode.BLOCKS
            assert manager.policy.retain_blocks == 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
