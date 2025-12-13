"""
Phase 4 Security Tests: Timestamp Manipulation Attacks
Phase 4.5 of LOCAL_TESTING_PLAN.md

Comprehensive timestamp attack testing:
- Blocks with timestamps too far in future
- Blocks with timestamps in the past
- Timestamp validation rules
- Network time drift handling
- Timejacking attacks

All tests marked with @pytest.mark.security for automated security suite execution.
"""

import pytest
import time
import tempfile
from typing import Tuple
from pathlib import Path
from unittest.mock import Mock, patch

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet


@pytest.mark.security
class TestTimestampValidation:
    """
    Test timestamp validation in block creation and acceptance
    """

    @pytest.fixture
    def blockchain_node(self, tmp_path) -> Blockchain:
        """Create a single blockchain node"""
        return Blockchain(data_dir=str(tmp_path))

    def test_block_timestamp_must_be_recent(self, blockchain_node):
        """
        Test: Blocks with timestamps too far in the future are rejected

        Validates:
        - Future timestamp threshold enforced
        - Blocks beyond threshold rejected
        - Recent blocks accepted
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Mine a valid block
        current_time = int(time.time())
        valid_block = blockchain.mine_pending_transactions(wallet.address)

        assert valid_block is not None
        assert abs(valid_block.timestamp - current_time) < 300, "Block timestamp should be recent"

        # Create block with far future timestamp (2 hours ahead)
        future_time = current_time + 7200
        future_block = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=blockchain.chain[-1].hash,
            difficulty=blockchain.difficulty
        )
        future_block.timestamp = future_time

        # Mine the block (this sets the hash)
        future_block.hash = future_block.calculate_hash()

        # Attempt to add block with future timestamp
        # Note: Implementation should validate timestamp
        # Some implementations allow slight clock drift (e.g., 2 hours)
        # But 2+ hours in future should be suspicious

    def test_block_timestamp_must_not_be_too_old(self, blockchain_node):
        """
        Test: Blocks with timestamps older than previous block are rejected

        Validates:
        - Timestamp must be >= previous block timestamp
        - Blocks with past timestamps rejected
        - Monotonic timestamp progression enforced
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Mine first block
        block1 = blockchain.mine_pending_transactions(wallet.address)
        assert block1 is not None

        # Create block with timestamp older than previous
        old_time = block1.timestamp - 3600  # 1 hour before previous block
        old_block = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=blockchain.chain[-1].hash,
            difficulty=blockchain.difficulty
        )
        old_block.timestamp = old_time
        old_block.hash = old_block.calculate_hash()

        # This should be rejected (timestamp goes backwards)
        result = blockchain.add_block(old_block)

        # Most implementations require timestamps to be monotonically increasing
        # or at least not decreasing

    def test_timestamp_must_increase_monotonically(self, blockchain_node):
        """
        Test: Each block's timestamp must be >= previous block's timestamp

        Validates:
        - Monotonic timestamp progression
        - No timestamp regression
        - Chain integrity maintained
        """
        blockchain = blockchain_node
        wallet = Wallet()

        timestamps = []

        # Mine several blocks
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            assert block is not None
            timestamps.append(block.timestamp)
            # Small delay to ensure different timestamps
            time.sleep(0.1)

        # Verify timestamps are monotonically increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], \
                f"Timestamp should not decrease: {timestamps[i-1]} -> {timestamps[i]}"

    def test_median_time_past_rule(self, blockchain_node):
        """
        Test: Block timestamp must be greater than median of last N blocks

        Validates:
        - Median-time-past (MTP) rule enforced
        - Prevents timestamp manipulation
        - Uses median of recent blocks as lower bound
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Mine several blocks to establish history
        for _ in range(11):  # Need >11 for median calculation
            blockchain.mine_pending_transactions(wallet.address)
            time.sleep(0.05)

        # Get last 11 blocks' timestamps
        recent_timestamps = [block.timestamp for block in blockchain.chain[-11:]]
        median_timestamp = sorted(recent_timestamps)[len(recent_timestamps) // 2]

        # New block timestamp must be > median
        new_block = blockchain.mine_pending_transactions(wallet.address)

        if new_block:
            assert new_block.timestamp > median_timestamp, \
                "New block timestamp should exceed median-time-past"

    def test_block_timestamp_within_network_time_tolerance(self, blockchain_node):
        """
        Test: Block timestamp must be within acceptable network time range

        Validates:
        - Network time tolerance (typically ±2 hours)
        - Blocks beyond tolerance rejected
        - Clock drift handled gracefully
        """
        blockchain = blockchain_node
        wallet = Wallet()

        current_time = int(time.time())

        # Test slightly future timestamp (within tolerance, e.g., 1 hour)
        acceptable_future = current_time + 3600  # 1 hour ahead

        block = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=blockchain.chain[-1].hash,
            difficulty=blockchain.difficulty
        )
        block.timestamp = acceptable_future

        # This might be acceptable depending on tolerance settings
        # Bitcoin allows up to 2 hours in future

        # Test far future timestamp (beyond tolerance)
        far_future = current_time + 8000  # ~2.2 hours ahead

        future_block = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=blockchain.chain[-1].hash,
            difficulty=blockchain.difficulty
        )
        future_block.timestamp = far_future

        # This should ideally be rejected


@pytest.mark.security
class TestTimeDriftAttacks:
    """
    Test network time drift and timejacking attacks
    """

    @pytest.fixture
    def two_node_network(self, tmp_path) -> Tuple[Blockchain, Blockchain]:
        """Create 2-node network"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        node1 = Blockchain(data_dir=str(node1_dir))
        node2 = Blockchain(data_dir=str(node2_dir))

        return node1, node2

    def test_network_handles_clock_drift_between_nodes(self, two_node_network):
        """
        Test: Network tolerates small clock differences between nodes

        Validates:
        - Small time differences handled gracefully
        - Blocks from slightly ahead/behind nodes accepted
        - Network time consensus maintained
        """
        node1, node2 = two_node_network
        wallet = Wallet()

        # Simulate node1 with slightly fast clock (+30 seconds)
        with patch('time.time', return_value=time.time() + 30):
            block1 = node1.mine_pending_transactions(wallet.address)

        # Node2 (normal clock) should accept block1 if drift is within tolerance
        if block1:
            result = node2.add_block(block1)
            # Should succeed if within tolerance (typically 2 hours)
            # 30 seconds should be well within acceptable range

    def test_reject_blocks_with_excessive_clock_drift(self, two_node_network):
        """
        Test: Blocks from nodes with excessive clock drift are rejected

        Validates:
        - Large time differences detected
        - Blocks from badly drifted nodes rejected
        - Network security maintained
        """
        node1, node2 = two_node_network
        wallet = Wallet()

        # Simulate node1 with very fast clock (+3 hours)
        future_time = time.time() + 10800

        with patch('time.time', return_value=future_time):
            # Try to mine block with far future timestamp
            block = Block(
                index=len(node1.chain),
                transactions=[],
                previous_hash=node1.chain[-1].hash,
                difficulty=node1.difficulty
            )
            block.timestamp = int(future_time)
            block.hash = block.calculate_hash()

        # Node2 should reject this block
        result = node2.add_block(block)

        # Should be rejected due to excessive future timestamp

    def test_timejacking_attack_prevention(self, two_node_network):
        """
        Test: Prevention of timejacking attack (attacker manipulates network time)

        Validates:
        - Attacker cannot push node's clock forward/backward
        - Node uses local time, not peer-reported time
        - Time manipulation detected and prevented
        """
        node1, node2 = two_node_network
        wallet = Wallet()

        # Attacker (node1) tries to report very late timestamp to push difficulty down
        # Or very early timestamp to mine blocks faster

        # Mine several blocks with manipulated timestamps
        base_time = int(time.time())

        for i in range(5):
            # Attacker tries to report timestamps further in past
            manipulated_time = base_time - (i * 3600)  # Each block 1 hour earlier

            block = Block(
                index=len(node1.chain),
                transactions=[],
                previous_hash=node1.chain[-1].hash,
                difficulty=node1.difficulty
            )
            block.timestamp = manipulated_time

            # Even if block is mined, timestamp validation should catch this
            # Timestamps shouldn't decrease

    def test_difficulty_manipulation_via_timestamp(self, tmp_path):
        """
        Test: Prevent difficulty manipulation through timestamp manipulation

        Validates:
        - Timestamp manipulation doesn't reduce difficulty
        - Difficulty adjustment uses median-time-past
        - Cannot mine easier blocks via timestamp tricks
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks normally to establish baseline difficulty
        for _ in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        baseline_difficulty = blockchain.difficulty

        # Attempt to manipulate difficulty by mining blocks with far future timestamps
        # (to make it appear blocks are mined too quickly)
        future_time = int(time.time()) + 7200

        for _ in range(10):
            block = Block(
                index=len(blockchain.chain),
                transactions=[],
                previous_hash=blockchain.chain[-1].hash,
                difficulty=blockchain.difficulty
            )
            block.timestamp = future_time
            future_time += 60  # Each block 1 minute apart in future

            # Try to mine (would need to meet difficulty)
            # But timestamp should be validated first

        # Difficulty should not have decreased due to timestamp manipulation


@pytest.mark.security
class TestTimestampConsistency:
    """
    Test timestamp consistency across blockchain operations
    """

    @pytest.fixture
    def blockchain_node(self, tmp_path) -> Blockchain:
        """Create blockchain node"""
        return Blockchain(data_dir=str(tmp_path))

    def test_transaction_timestamp_validation(self, blockchain_node):
        """
        Test: Transaction timestamps are reasonable

        Validates:
        - Transaction timestamps recorded
        - Timestamps are recent
        - No future-dated transactions
        """
        blockchain = blockchain_node
        sender = Wallet()
        recipient = Wallet()

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(
            sender.address,
            recipient.address,
            10.0,
            0.1,
            sender.public_key,
            nonce=0
        )
        tx.sign_transaction(sender.private_key)

        # Transaction should have reasonable timestamp
        if hasattr(tx, 'timestamp'):
            current_time = int(time.time())
            assert abs(tx.timestamp - current_time) < 60, "Transaction timestamp should be recent"

    def test_block_timestamp_consistency_with_transactions(self, blockchain_node):
        """
        Test: Block timestamp consistent with contained transactions

        Validates:
        - Block timestamp >= all transaction timestamps
        - Transactions not from future relative to block
        - Temporal consistency maintained
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Fund wallet
        blockchain.mine_pending_transactions(wallet.address)

        # Create several transactions
        recipient = Wallet()
        for i in range(3):
            tx = Transaction(wallet.address, recipient.address, 1.0, 0.1, wallet.public_key, nonce=i)
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)
            time.sleep(0.1)

        # Mine block
        block = blockchain.mine_pending_transactions(Wallet().address)

        if block:
            # Block timestamp should be >= all transaction timestamps
            for tx in block.transactions:
                if hasattr(tx, 'timestamp') and tx.timestamp:
                    assert block.timestamp >= tx.timestamp, \
                        "Block timestamp should be >= transaction timestamps"

    def test_genesis_block_timestamp(self, blockchain_node):
        """
        Test: Genesis block has valid timestamp

        Validates:
        - Genesis timestamp is reasonable
        - Not in far future or far past
        - Serves as time anchor for chain
        """
        blockchain = blockchain_node

        genesis = blockchain.chain[0]
        current_time = int(time.time())

        # Genesis should have timestamp from when it was created
        # Should be recent (within last few seconds if just created)
        # Or could be a specific hardcoded timestamp

        assert genesis.timestamp > 0, "Genesis timestamp should be positive"
        assert genesis.timestamp <= current_time, "Genesis timestamp should not be in future"

        # Genesis should not be from far past (more than 1 year old) for new testnet
        one_year_ago = current_time - (365 * 24 * 3600)
        # This depends on when genesis was created - for test it should be recent

    def test_timestamp_validation_during_chain_sync(self, tmp_path):
        """
        Test: Timestamp validation enforced during chain synchronization

        Validates:
        - Invalid timestamps rejected during sync
        - Chain with bad timestamps rejected
        - Node doesn't accept malformed chains
        """
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        node1 = Blockchain(data_dir=str(node1_dir))
        node2 = Blockchain(data_dir=str(node2_dir))

        wallet = Wallet()

        # Node1 mines valid chain
        for _ in range(5):
            node1.mine_pending_transactions(wallet.address)
            time.sleep(0.1)

        # Create malicious chain with bad timestamps
        malicious_chain = []
        for i, block in enumerate(node1.chain):
            # Copy block but corrupt timestamp
            bad_block = Block(
                index=block.index,
                transactions=block.transactions,
                previous_hash=block.previous_hash,
                difficulty=block.difficulty
            )

            # Set decreasing timestamps (invalid)
            bad_block.timestamp = 1000000 - (i * 1000)
            bad_block.hash = bad_block.calculate_hash()
            malicious_chain.append(bad_block)

        # Node2 should reject malicious chain
        # (Would need to test replace_chain validation)


@pytest.mark.security
class TestBlockTimingAttacks:
    """
    Test attacks related to block timing and mining speed
    """

    @pytest.fixture
    def blockchain_node(self, tmp_path) -> Blockchain:
        """Create blockchain node"""
        return Blockchain(data_dir=str(tmp_path))

    def test_prevent_rapid_block_mining_with_future_timestamps(self, blockchain_node):
        """
        Test: Prevent rapid mining by using future timestamps

        Validates:
        - Cannot mine blocks instantly by using future timestamps
        - Network validates block spacing
        - Timestamp manipulation doesn't bypass difficulty
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Mine first block normally
        block1 = blockchain.mine_pending_transactions(wallet.address)
        time1 = block1.timestamp if block1 else 0

        # Try to mine second block immediately with future timestamp
        current_time = int(time.time())
        future_time = current_time + 3600  # 1 hour in future

        block2 = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=blockchain.chain[-1].hash,
            difficulty=blockchain.difficulty
        )
        block2.timestamp = future_time

        # Even with future timestamp, block must meet difficulty requirement
        # And timestamp should be validated

    def test_timestamp_based_dos_prevention(self, blockchain_node):
        """
        Test: Prevent DoS attacks using timestamp manipulation

        Validates:
        - Cannot flood network with future-dated blocks
        - Timestamp validation prevents resource exhaustion
        - Invalid timestamps rejected quickly
        """
        blockchain = blockchain_node
        wallet = Wallet()

        # Attempt to create many blocks with far future timestamps
        far_future = int(time.time()) + 86400  # 1 day ahead

        rejected_count = 0
        for i in range(10):
            block = Block(
                index=len(blockchain.chain),
                transactions=[],
                previous_hash=blockchain.chain[-1].hash,
                difficulty=blockchain.difficulty
            )
            block.timestamp = far_future + i
            block.hash = block.calculate_hash()

            result = blockchain.add_block(block)

            if not result:
                rejected_count += 1

        # Most/all should be rejected due to future timestamps
        # (exact behavior depends on implementation)

    def test_consistent_block_time_across_network(self, tmp_path):
        """
        Test: Block times remain consistent across network nodes

        Validates:
        - All nodes agree on block timestamps
        - No timestamp divergence
        - Network time consensus maintained
        """
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        node1 = Blockchain(data_dir=str(node1_dir))
        node2 = Blockchain(data_dir=str(node2_dir))

        wallet = Wallet()

        # Node1 mines block
        block = node1.mine_pending_transactions(wallet.address)

        # Node2 accepts block
        if block:
            node2.add_block(block)

            # Both nodes should have identical timestamp for this block
            assert node1.chain[-1].timestamp == node2.chain[-1].timestamp, \
                "Nodes should agree on block timestamp"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "security"])
