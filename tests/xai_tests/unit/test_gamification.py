"""
Unit tests for Gamification module

Tests airdrops, streaks, treasure hunts, fee refunds, and time capsules
"""

import pytest
import time
import tempfile
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from xai.core.governance.gamification import (
    AirdropManager,
    StreakTracker,
    TreasureHuntManager,
    FeeRefundCalculator,
    TimeCapsuleManager,
    initialize_gamification,
)


class MockBlock:
    """Mock block for testing"""
    
    def __init__(self, index=0, transactions=None, block_hash="test_hash"):
        self.index = index
        self.transactions = transactions or []
        self.hash = block_hash
        self.timestamp = time.time()


class MockTransaction:
    """Mock transaction for testing"""
    
    def __init__(self, sender, recipient, fee=0.0):
        self.sender = sender
        self.recipient = recipient
        self.fee = fee


class MockBlockchain:
    """Mock blockchain for testing"""
    
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self._mempool_size_kb = None
    
    def add_block(self, transactions):
        """Add block with transactions"""
        block = MockBlock(
            index=len(self.chain),
            transactions=transactions,
            block_hash=f"block_{len(self.chain)}"
        )
        self.chain.append(block)

    def get_balance(self, address):
        return 0.0

    def get_chain_length(self):
        return len(self.chain)

    def get_block_by_index(self, index):
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def get_latest_block_hash(self):
        return self.chain[-1].hash if self.chain else "0" * 64

    def get_pending_transactions(self):
        return list(self.pending_transactions)

    def add_transaction_to_mempool(self, transaction):
        self.pending_transactions.append(transaction)
        return True

    def get_mempool_size_kb(self):
        return self._mempool_size_kb

    def set_mempool_size_kb(self, value):
        self._mempool_size_kb = value


@pytest.fixture
def blockchain():
    return MockBlockchain()


class TestAirdropManager:
    """Test airdrop management"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir, blockchain):
        """Create AirdropManager with temp storage"""
        return AirdropManager(blockchain_interface=blockchain, data_dir=temp_dir)

    def test_init(self, manager):
        """Test AirdropManager initialization"""
        assert len(manager.airdrop_history) == 0
        assert manager.airdrop_file.parent.exists()

    def test_should_trigger_airdrop_block_100(self, manager):
        """Test airdrop triggers at block 100"""
        assert manager.should_trigger_airdrop(100) is True

    def test_should_trigger_airdrop_block_200(self, manager):
        """Test airdrop triggers at block 200"""
        assert manager.should_trigger_airdrop(200) is True

    def test_should_trigger_airdrop_block_99(self, manager):
        """Test airdrop doesn't trigger at block 99"""
        assert manager.should_trigger_airdrop(99) is False

    def test_should_trigger_airdrop_block_101(self, manager):
        """Test airdrop doesn't trigger at block 101"""
        assert manager.should_trigger_airdrop(101) is False

    def test_get_active_addresses(self, manager, blockchain):
        """Test getting active addresses from blockchain"""
        # Add blocks with transactions
        blockchain.add_block([
            MockTransaction("XAI_A", "XAI_B"),
            MockTransaction("XAI_C", "XAI_D"),
        ])
        blockchain.add_block([
            MockTransaction("XAI_E", "XAI_F"),
        ])

        active = manager.get_active_addresses()
        
        assert len(active) == 6
        assert "XAI_A" in active
        assert "COINBASE" not in active
        assert "GENESIS" not in active

    def test_get_active_addresses_excludes_system(self, manager, blockchain):
        """Test that COINBASE and GENESIS are excluded"""
        blockchain.add_block([
            MockTransaction("COINBASE", "XAI_A"),
            MockTransaction("XAI_B", "XAI_C"),
        ])

        active = manager.get_active_addresses()
        
        assert "COINBASE" not in active
        assert "GENESIS" not in active
        assert "XAI_A" in active

    def test_select_airdrop_winners(self, manager):
        """Test selecting random winners"""
        addresses = [f"XAI_{i}" for i in range(20)]
        
        winners = manager.select_airdrop_winners(addresses, count=10, seed="test")
        
        assert len(winners) == 10
        assert all(w in addresses for w in winners)

    def test_select_airdrop_winners_deterministic(self, manager):
        """Test winner selection is deterministic with same seed"""
        addresses = [f"XAI_{i}" for i in range(20)]
        
        winners1 = manager.select_airdrop_winners(addresses, count=10, seed="test")
        winners2 = manager.select_airdrop_winners(addresses, count=10, seed="test")
        
        assert winners1 == winners2

    def test_select_airdrop_winners_limited_addresses(self, manager):
        """Test winner selection with fewer addresses than count"""
        addresses = ["XAI_A", "XAI_B", "XAI_C"]
        
        winners = manager.select_airdrop_winners(addresses, count=10)
        
        assert len(winners) == 3

    def test_calculate_airdrop_amounts(self, manager):
        """Test calculating airdrop amounts"""
        winners = ["XAI_A", "XAI_B", "XAI_C"]
        
        amounts = manager.calculate_airdrop_amounts(winners, seed="test")
        
        assert len(amounts) == 3
        for address, amount in amounts.items():
            assert 1.0 <= amount <= 10.0

    def test_execute_airdrop(self, manager, blockchain):
        """Test executing airdrop"""
        # Add blocks with active addresses
        for i in range(10):
            blockchain.add_block([
                MockTransaction(f"XAI_{i}", f"XAI_{i+10}"),
            ])

        result = manager.execute_airdrop(100, "block_hash_100")
        
        assert result is not None
        assert len(result) <= 10
        assert len(manager.airdrop_history) == 1

    def test_execute_airdrop_wrong_block(self, manager):
        """Test airdrop doesn't execute at wrong block"""
        result = manager.execute_airdrop(99, "block_hash_99")
        
        assert result is None

    def test_execute_airdrop_no_active_addresses(self, manager):
        """Test airdrop with no active addresses"""
        result = manager.execute_airdrop(100, "block_hash_100")
        
        assert result is None

    def test_get_recent_airdrops(self, manager, blockchain):
        """Test getting recent airdrop history"""
        # Execute multiple airdrops
        for i in range(5):
            blockchain.add_block([MockTransaction(f"XAI_{i}", f"XAI_{i+10}")])

        manager.execute_airdrop(100, "hash1")
        manager.execute_airdrop(200, "hash2")
        
        recent = manager.get_recent_airdrops(limit=10)
        
        assert len(recent) == 2

    def test_get_user_airdrop_history(self, manager):
        """Test getting user's airdrop history"""
        # Manually add airdrop history
        manager.airdrop_history.append({
            "block_height": 100,
            "timestamp": time.time(),
            "winners": {"XAI_USER": 5.0},
        })
        
        history = manager.get_user_airdrop_history("XAI_USER")
        
        assert len(history) == 1
        assert history[0]["amount"] == 5.0


class TestStreakTracker:
    """Test mining streak tracking"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def tracker(self, temp_dir):
        """Create StreakTracker with temp storage"""
        return StreakTracker(data_dir=temp_dir)

    def test_init(self, tracker):
        """Test StreakTracker initialization"""
        assert len(tracker.miner_streaks) == 0

    def test_update_miner_streak_new_miner(self, tracker):
        """Test updating streak for new miner"""
        tracker.update_miner_streak("XAI_MINER", time.time())
        
        assert "XAI_MINER" in tracker.miner_streaks
        assert tracker.miner_streaks["XAI_MINER"]["current_streak"] == 1

    def test_update_miner_streak_consecutive_day(self, tracker):
        """Test updating streak for consecutive day"""
        current_time = time.time()
        yesterday = current_time - 86400
        
        tracker.update_miner_streak("XAI_MINER", yesterday)
        tracker.update_miner_streak("XAI_MINER", current_time)
        
        assert tracker.miner_streaks["XAI_MINER"]["current_streak"] == 2

    def test_update_miner_streak_broken(self, tracker):
        """Test streak broken after missing a day"""
        current_time = time.time()
        two_days_ago = current_time - (2 * 86400)
        
        tracker.update_miner_streak("XAI_MINER", two_days_ago)
        tracker.update_miner_streak("XAI_MINER", current_time)
        
        # Streak should reset to 1
        assert tracker.miner_streaks["XAI_MINER"]["current_streak"] == 1

    def test_update_miner_streak_same_day(self, tracker):
        """Test updating streak on same day doesn't change streak"""
        current_time = time.time()
        
        tracker.update_miner_streak("XAI_MINER", current_time)
        initial_streak = tracker.miner_streaks["XAI_MINER"]["current_streak"]
        
        tracker.update_miner_streak("XAI_MINER", current_time + 3600)
        
        assert tracker.miner_streaks["XAI_MINER"]["current_streak"] == initial_streak

    def test_get_streak_bonus(self, tracker):
        """Test calculating streak bonus"""
        # Manually set streak
        current_day = datetime.now().strftime("%Y-%m-%d")
        tracker.miner_streaks["XAI_MINER"] = {
            "current_streak": 5,
            "longest_streak": 5,
            "last_mining_day": current_day,
            "total_blocks_mined": 10,
            "mining_days": [],
        }
        
        bonus = tracker.get_streak_bonus("XAI_MINER")
        
        assert bonus == 0.05  # 5% bonus

    def test_get_streak_bonus_capped(self, tracker):
        """Test streak bonus is capped at 20%"""
        current_day = datetime.now().strftime("%Y-%m-%d")
        tracker.miner_streaks["XAI_MINER"] = {
            "current_streak": 50,
            "longest_streak": 50,
            "last_mining_day": current_day,
            "total_blocks_mined": 100,
            "mining_days": [],
        }
        
        bonus = tracker.get_streak_bonus("XAI_MINER")
        
        assert bonus == 0.20  # Capped at 20%

    def test_apply_streak_bonus(self, tracker):
        """Test applying streak bonus to reward"""
        current_day = datetime.now().strftime("%Y-%m-%d")
        tracker.miner_streaks["XAI_MINER"] = {
            "current_streak": 10,
            "longest_streak": 10,
            "last_mining_day": current_day,
            "total_blocks_mined": 20,
            "mining_days": [],
        }
        
        base_reward = 100.0
        final_reward, bonus_amount = tracker.apply_streak_bonus("XAI_MINER", base_reward)
        
        assert final_reward == 110.0  # 100 + 10% bonus
        assert bonus_amount == 10.0

    def test_get_miner_stats(self, tracker):
        """Test getting miner statistics"""
        current_day = datetime.now().strftime("%Y-%m-%d")
        tracker.miner_streaks["XAI_MINER"] = {
            "current_streak": 7,
            "longest_streak": 10,
            "last_mining_day": current_day,
            "total_blocks_mined": 50,
            "mining_days": [],
        }
        
        stats = tracker.get_miner_stats("XAI_MINER")
        
        assert stats is not None
        assert stats["current_streak"] == 7
        assert stats["bonus_percent"] == pytest.approx(7.0)

    def test_get_miner_stats_not_found(self, tracker):
        """Test getting stats for non-existent miner"""
        stats = tracker.get_miner_stats("XAI_UNKNOWN")
        
        assert stats is None

    def test_get_leaderboard(self, tracker):
        """Test getting streak leaderboard"""
        # Add multiple miners
        for i in range(5):
            tracker.miner_streaks[f"XAI_{i}"] = {
                "current_streak": i + 1,
                "longest_streak": i + 1,
                "total_blocks_mined": (i + 1) * 10,
                "last_mining_day": "2025-01-01",
                "mining_days": [],
            }
        
        leaderboard = tracker.get_leaderboard(limit=3, sort_by="current_streak")
        
        assert len(leaderboard) == 3
        assert leaderboard[0]["current_streak"] >= leaderboard[1]["current_streak"]


class TestTreasureHuntManager:
    """Test treasure hunt management"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir, blockchain):
        """Create TreasureHuntManager with temp storage"""
        return TreasureHuntManager(blockchain_interface=blockchain, data_dir=temp_dir)

    def test_init(self, manager):
        """Test TreasureHuntManager initialization"""
        assert len(manager.treasures) == 0

    def test_create_treasure_hunt_hash(self, manager):
        """Test creating hash-based treasure hunt"""
        answer_hash = hashlib.sha256("secret_answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
            hint="Think of a secret word",
        )
        
        assert treasure_id in manager.treasures
        assert manager.treasures[treasure_id]["status"] == "active"

    def test_verify_solution_hash_correct(self, manager):
        """Test verifying correct hash solution"""
        answer_hash = hashlib.sha256("correct_answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        is_correct = manager.verify_solution(treasure_id, "correct_answer")
        
        assert is_correct is True

    def test_verify_solution_hash_wrong(self, manager):
        """Test verifying wrong hash solution"""
        answer_hash = hashlib.sha256("correct_answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        is_correct = manager.verify_solution(treasure_id, "wrong_answer")
        
        assert is_correct is False

    def test_verify_solution_math(self, manager):
        """Test verifying math puzzle solution"""
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="math",
            puzzle_data={"answer": 42},
        )
        
        assert manager.verify_solution(treasure_id, "42") is True
        assert manager.verify_solution(treasure_id, "41") is False

    def test_claim_treasure_success(self, manager):
        """Test successful treasure claim"""
        answer_hash = hashlib.sha256("answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        success, amount = manager.claim_treasure(treasure_id, "XAI_CLAIMER", "answer")
        
        assert success is True
        assert amount == 100.0
        assert manager.treasures[treasure_id]["status"] == "claimed"

    def test_claim_treasure_wrong_solution(self, manager):
        """Test claiming treasure with wrong solution"""
        answer_hash = hashlib.sha256("answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        success, amount = manager.claim_treasure(treasure_id, "XAI_CLAIMER", "wrong")
        
        assert success is False
        assert amount is None

    def test_claim_treasure_already_claimed(self, manager):
        """Test claiming already claimed treasure"""
        answer_hash = hashlib.sha256("answer".encode()).hexdigest()
        
        treasure_id = manager.create_treasure_hunt(
            creator_address="XAI_CREATOR",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        # First claim
        manager.claim_treasure(treasure_id, "XAI_CLAIMER1", "answer")
        
        # Second claim attempt
        success, amount = manager.claim_treasure(treasure_id, "XAI_CLAIMER2", "answer")
        
        assert success is False

    def test_get_active_treasures(self, manager):
        """Test getting active treasures"""
        answer_hash = hashlib.sha256("answer".encode()).hexdigest()
        
        # Create active treasure
        tid1 = manager.create_treasure_hunt(
            creator_address="XAI_A",
            amount=100.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        
        # Create and claim treasure
        tid2 = manager.create_treasure_hunt(
            creator_address="XAI_B",
            amount=50.0,
            puzzle_type="hash",
            puzzle_data={"answer_hash": answer_hash},
        )
        manager.claim_treasure(tid2, "XAI_CLAIMER", "answer")
        
        active = manager.get_active_treasures()
        
        assert len(active) == 1
        assert active[0]["id"] == tid1


class TestFeeRefundCalculator:
    """Test fee refund calculator"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def calculator(self, temp_dir, blockchain):
        """Create FeeRefundCalculator with temp storage"""
        return FeeRefundCalculator(blockchain_interface=blockchain, data_dir=temp_dir)

    def test_init(self, calculator):
        """Test FeeRefundCalculator initialization"""
        assert calculator.LOW_CONGESTION_THRESHOLD == 5
        assert calculator.MED_CONGESTION_THRESHOLD == 10

    def test_calculate_refund_rate_low_congestion(self, calculator, blockchain):
        """Test refund rate for low congestion"""
        blockchain.pending_transactions = [object()] * 3
        blockchain.set_mempool_size_kb(None)
        rate = calculator.calculate_refund_rate()
        
        assert rate == 0.50  # 50% refund

    def test_calculate_refund_rate_medium_congestion(self, calculator, blockchain):
        """Test refund rate for medium congestion"""
        blockchain.pending_transactions = [object()] * 7
        blockchain.set_mempool_size_kb(None)
        rate = calculator.calculate_refund_rate()
        
        assert rate == 0.25  # 25% refund

    def test_calculate_refund_rate_high_congestion(self, calculator, blockchain):
        """Test refund rate for high congestion"""
        blockchain.pending_transactions = [object()] * 15
        blockchain.set_mempool_size_kb(None)
        rate = calculator.calculate_refund_rate()
        
        assert rate == 0.0  # No refund

    def test_calculate_refunds_for_block(self, calculator, blockchain):
        """Test calculating refunds for a block"""
        transactions = [
            MockTransaction("COINBASE", "XAI_MINER", fee=0.0),
            MockTransaction("XAI_A", "XAI_B", fee=1.0),
            MockTransaction("XAI_C", "XAI_D", fee=2.0),
        ]
        
        block = MockBlock(transactions=transactions)

        blockchain.pending_transactions = [object()] * 3
        blockchain.set_mempool_size_kb(None)
        refunds = calculator.calculate_refunds_for_block(block)
        
        assert len(refunds) == 2
        assert refunds["XAI_A"] == 0.5  # 50% of 1.0
        assert refunds["XAI_C"] == 1.0  # 50% of 2.0

    def test_calculate_refunds_no_refund(self, calculator, blockchain):
        """Test no refunds during high congestion"""
        transactions = [
            MockTransaction("COINBASE", "XAI_MINER", fee=0.0),
            MockTransaction("XAI_A", "XAI_B", fee=1.0),
        ]
        block = MockBlock(transactions=transactions)

        blockchain.pending_transactions = [object()] * 20
        blockchain.set_mempool_size_kb(None)
        refunds = calculator.calculate_refunds_for_block(block)
        
        assert len(refunds) == 0

    def test_process_refunds(self, calculator, blockchain):
        """Test processing refunds with history"""
        transactions = [
            MockTransaction("COINBASE", "XAI_MINER", fee=0.0),
            MockTransaction("XAI_A", "XAI_B", fee=1.0),
        ]
        block = MockBlock(transactions=transactions)

        blockchain.pending_transactions = [object()] * 3
        blockchain.set_mempool_size_kb(None)
        refunds = calculator.process_refunds(block)
        
        assert len(refunds) == 1
        assert len(calculator.refund_history) == 1

    def test_get_user_refund_history(self, calculator, blockchain):
        """Test getting user refund history"""
        transactions = [
            MockTransaction("COINBASE", "XAI_MINER", fee=0.0),
            MockTransaction("XAI_USER", "XAI_B", fee=1.0),
        ]
        block = MockBlock(transactions=transactions)

        blockchain.pending_transactions = [object()] * 3
        blockchain.set_mempool_size_kb(None)
        calculator.process_refunds(block)
        
        history = calculator.get_user_refund_history("XAI_USER")
        
        assert len(history) == 1
        assert history[0]["amount"] == 0.5

    def test_get_refund_stats(self, calculator, blockchain):
        """Test getting overall refund statistics"""
        transactions = [
            MockTransaction("COINBASE", "XAI_MINER", fee=0.0),
            MockTransaction("XAI_A", "XAI_B", fee=1.0),
        ]
        block = MockBlock(transactions=transactions)

        blockchain.pending_transactions = [object()] * 3
        blockchain.set_mempool_size_kb(None)
        calculator.process_refunds(block)
        
        stats = calculator.get_refund_stats()
        
        assert stats["total_refunds"] == 1
        assert stats["total_amount"] == 0.5


def test_initialize_gamification(tmp_path, blockchain):
    """Test initializing all gamification managers"""
    managers = initialize_gamification(blockchain_interface=blockchain, data_dir=str(tmp_path))
    
    assert "airdrop" in managers
    assert "streak" in managers
    assert "treasure" in managers
    assert "fee_refund" in managers
    assert "time_capsule" in managers
    
    assert isinstance(managers["airdrop"], AirdropManager)
    assert isinstance(managers["streak"], StreakTracker)
    assert isinstance(managers["treasure"], TreasureHuntManager)
    assert isinstance(managers["fee_refund"], FeeRefundCalculator)
    assert isinstance(managers["time_capsule"], TimeCapsuleManager)
