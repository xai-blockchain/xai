"""
Unit tests for Time Capsule module

Tests time-locked transactions, capsule management, and cross-chain support
"""

import pytest
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from xai.core.time_capsule import (
    TimeCapsule,
    TimeCapsuleManager,
    TimeCapsuleType,
    get_time_capsule_manager,
)


class MockTransaction:
    """Mock transaction for testing"""
    
    def __init__(self, sender, recipient, amount, tx_type="time_capsule_lock", metadata=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.tx_type = tx_type
        self.metadata = metadata or {}
        self.txid = f"tx_{sender}_{recipient}_{time.time()}"
    
    def sign_transaction(self, private_key):
        """Mock signing"""
        self.signature = f"sig_{private_key[:8]}"


class MockBlockchain:
    """Mock blockchain for testing"""
    
    def __init__(self):
        self.chain = []
        self.utxo_set = {}
        self.pending_transactions = []
    
    def get_balance(self, address):
        """Get balance for address"""
        utxos = self.utxo_set.get(address, [])
        return sum(u["amount"] for u in utxos if not u.get("spent", False))
    
    def add_utxo(self, address, amount):
        """Add UTXO for testing"""
        if address not in self.utxo_set:
            self.utxo_set[address] = []
        self.utxo_set[address].append({"amount": amount, "spent": False})


class TestTimeCapsule:
    """Test TimeCapsule class"""

    def test_init(self):
        """Test TimeCapsule initialization"""
        unlock_time = int(time.time()) + 3600
        capsule = TimeCapsule(
            capsule_id="test_capsule",
            creator="XAI_CREATOR",
            beneficiary="XAI_BENEFICIARY",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
            amount=100.0,
        )
        
        assert capsule.capsule_id == "test_capsule"
        assert capsule.creator == "XAI_CREATOR"
        assert capsule.beneficiary == "XAI_BENEFICIARY"
        assert capsule.unlock_time == unlock_time
        assert capsule.amount == 100.0
        assert capsule.claimed is False

    def test_is_unlocked_future(self):
        """Test is_unlocked returns False for future unlock time"""
        unlock_time = int(time.time()) + 3600
        capsule = TimeCapsule(
            capsule_id="test",
            creator="A",
            beneficiary="B",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
        )
        
        assert capsule.is_unlocked() is False

    def test_is_unlocked_past(self):
        """Test is_unlocked returns True for past unlock time"""
        unlock_time = int(time.time()) - 3600
        capsule = TimeCapsule(
            capsule_id="test",
            creator="A",
            beneficiary="B",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
        )
        
        assert capsule.is_unlocked() is True

    def test_time_remaining(self):
        """Test time_remaining calculation"""
        unlock_time = int(time.time()) + 7200
        capsule = TimeCapsule(
            capsule_id="test",
            creator="A",
            beneficiary="B",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
        )
        
        remaining = capsule.time_remaining()
        assert 7100 <= remaining <= 7200

    def test_days_remaining(self):
        """Test days_remaining calculation"""
        unlock_time = int(time.time()) + (3 * 86400)  # 3 days
        capsule = TimeCapsule(
            capsule_id="test",
            creator="A",
            beneficiary="B",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
        )
        
        days = capsule.days_remaining()
        assert 2.9 <= days <= 3.1

    def test_to_dict(self):
        """Test conversion to dictionary"""
        unlock_time = int(time.time()) + 3600
        capsule = TimeCapsule(
            capsule_id="test",
            creator="XAI_A",
            beneficiary="XAI_B",
            unlock_time=unlock_time,
            capsule_type=TimeCapsuleType.XAI_ONLY,
            amount=100.0,
            message="Test message",
        )
        
        data = capsule.to_dict()
        
        assert data["capsule_id"] == "test"
        assert data["creator"] == "XAI_A"
        assert data["beneficiary"] == "XAI_B"
        assert data["amount"] == 100.0
        assert data["message"] == "Test message"
        assert "unlock_date" in data
        assert "time_remaining_seconds" in data

    def test_from_dict(self):
        """Test reconstruction from dictionary"""
        unlock_time = int(time.time()) + 3600
        data = {
            "capsule_id": "test",
            "creator": "XAI_A",
            "beneficiary": "XAI_B",
            "unlock_time": unlock_time,
            "capsule_type": TimeCapsuleType.XAI_ONLY,
            "amount": 100.0,
            "coin_type": "XAI",
            "message": "Test",
            "htlc_details": {},
            "metadata": {},
            "created_time": int(time.time()),
            "claimed": False,
            "claimed_time": None,
        }
        
        capsule = TimeCapsule.from_dict(data)
        
        assert capsule.capsule_id == "test"
        assert capsule.creator == "XAI_A"
        assert capsule.amount == 100.0


class TestTimeCapsuleManager:
    """Test TimeCapsuleManager class"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_storage):
        """Create TimeCapsuleManager with temp storage"""
        blockchain = MockBlockchain()
        return TimeCapsuleManager(blockchain, storage_file=temp_storage)

    def test_init(self, temp_storage):
        """Test TimeCapsuleManager initialization"""
        blockchain = MockBlockchain()
        manager = TimeCapsuleManager(blockchain, storage_file=temp_storage)
        
        assert manager.blockchain == blockchain
        assert len(manager.capsules) == 0
        assert len(manager.user_capsules) == 0

    def test_capsule_address_deterministic(self, manager):
        """Test capsule address generation is deterministic"""
        address1 = manager.capsule_address("test_id")
        address2 = manager.capsule_address("test_id")
        
        assert address1 == address2
        assert address1.startswith("XAI")

    def test_capsule_address_unique(self, manager):
        """Test different capsule IDs generate different addresses"""
        address1 = manager.capsule_address("capsule_1")
        address2 = manager.capsule_address("capsule_2")
        
        assert address1 != address2

    def test_register_lock_transaction(self, manager):
        """Test registering a time capsule lock transaction"""
        unlock_time = int(time.time()) + 3600
        
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "test_capsule",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
                "message": "Future gift",
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        assert "test_capsule" in manager.capsules
        capsule = manager.capsules["test_capsule"]
        assert capsule.creator == "XAI_CREATOR"
        assert capsule.beneficiary == "XAI_BENEFICIARY"
        assert capsule.amount == 100.0

    def test_register_lock_transaction_past_unlock(self, manager):
        """Test registering transaction with past unlock time is ignored"""
        unlock_time = int(time.time()) - 3600  # Past
        
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "test_capsule",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        # Should not be registered
        assert "test_capsule" not in manager.capsules

    def test_get_unlockable_capsules(self, manager):
        """Test getting capsules ready to unlock"""
        current_time = time.time()
        
        # Register capsule with past unlock time
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "unlockable",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": int(current_time - 3600),
                "allow_past_unlock": True,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=current_time)
        
        # Manually set status to locked
        manager.capsules["unlockable"].metadata["status"] = "locked"
        
        unlockable = manager.get_unlockable_capsules(current_time=current_time)
        
        assert len(unlockable) == 1
        assert unlockable[0].capsule_id == "unlockable"

    def test_build_claim_transaction(self, manager):
        """Test building claim transaction"""
        unlock_time = int(time.time()) - 3600
        
        # Create and register capsule
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "claimable",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
                "allow_past_unlock": True,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        capsule = manager.capsules["claimable"]
        capsule.metadata["status"] = "locked"
        
        # Build claim transaction
        claim_tx = manager.build_claim_transaction(capsule)
        
        assert claim_tx is not None
        assert claim_tx.recipient == "XAI_BENEFICIARY"
        assert claim_tx.amount == 100.0
        assert claim_tx.tx_type == "time_capsule_claim"

    def test_build_claim_transaction_already_claimed(self, manager):
        """Test building claim transaction for already claimed capsule"""
        unlock_time = int(time.time()) - 3600
        
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "claimed",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
                "allow_past_unlock": True,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        capsule = manager.capsules["claimed"]
        capsule.metadata["status"] = "claimed"
        
        claim_tx = manager.build_claim_transaction(capsule)
        assert claim_tx is None

    def test_register_claim_transaction(self, manager):
        """Test registering claim transaction"""
        unlock_time = int(time.time()) - 3600
        
        # Create capsule
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "test",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
                "allow_past_unlock": True,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        # Register claim
        claim_tx = MockTransaction(
            sender="capsule_address",
            recipient="XAI_BENEFICIARY",
            amount=100.0,
            metadata={"capsule_id": "test"}
        )
        
        manager.register_claim_transaction(claim_tx, block_timestamp=time.time())
        
        capsule = manager.capsules["test"]
        assert capsule.metadata["status"] == "claimed"
        assert capsule.claimed is True

    def test_create_xai_capsule_insufficient_balance(self, manager):
        """Test creating capsule with insufficient balance"""
        unlock_time = int(time.time()) + 3600
        
        result = manager.create_xai_capsule(
            creator="XAI_POOR",
            beneficiary="XAI_B",
            amount=1000.0,
            unlock_time=unlock_time,
        )
        
        assert result["success"] is False
        assert "Insufficient balance" in result["error"]

    def test_create_xai_capsule_invalid_amount(self, manager):
        """Test creating capsule with invalid amount"""
        unlock_time = int(time.time()) + 3600
        
        result = manager.create_xai_capsule(
            creator="XAI_A",
            beneficiary="XAI_B",
            amount=-100.0,
            unlock_time=unlock_time,
        )
        
        assert result["success"] is False
        assert "positive" in result["error"]

    def test_create_xai_capsule_past_unlock_time(self, manager):
        """Test creating capsule with past unlock time"""
        unlock_time = int(time.time()) - 3600
        
        result = manager.create_xai_capsule(
            creator="XAI_A",
            beneficiary="XAI_B",
            amount=100.0,
            unlock_time=unlock_time,
        )
        
        assert result["success"] is False
        assert "future" in result["error"]

    def test_create_cross_chain_capsule_invalid_coin(self, manager):
        """Test creating cross-chain capsule with unsupported coin"""
        unlock_time = int(time.time()) + 3600
        
        result = manager.create_cross_chain_capsule(
            creator="XAI_A",
            beneficiary="XAI_B",
            coin_type="INVALID",
            amount=1.0,
            unlock_time=unlock_time,
            htlc_hash="hash123",
            origin_chain_tx="tx123",
        )
        
        assert result["success"] is False
        assert "Unsupported coin" in result["error"]

    def test_claim_capsule_not_found(self, manager):
        """Test claiming non-existent capsule"""
        result = manager.claim_capsule("nonexistent", "XAI_CLAIMER")
        
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_claim_capsule_still_locked(self, manager):
        """Test claiming capsule that's still locked"""
        unlock_time = int(time.time()) + 3600
        
        # Create locked capsule
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "locked",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        result = manager.claim_capsule("locked", "XAI_BENEFICIARY")
        
        assert result["success"] is False
        assert "locked" in result["error"]

    def test_claim_capsule_wrong_beneficiary(self, manager):
        """Test claiming capsule by wrong beneficiary"""
        unlock_time = int(time.time()) - 3600
        
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "test",
                "beneficiary": "XAI_BENEFICIARY",
                "unlock_time": unlock_time,
                "allow_past_unlock": True,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        result = manager.claim_capsule("test", "XAI_WRONG")
        
        assert result["success"] is False
        assert "Only" in result["error"]

    def test_get_user_capsules(self, manager):
        """Test getting capsules for a user"""
        unlock_time = int(time.time()) + 3600
        
        tx = MockTransaction(
            sender="XAI_USER",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "user_capsule",
                "beneficiary": "XAI_USER",
                "unlock_time": unlock_time,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        capsules = manager.get_user_capsules("XAI_USER")
        
        assert len(capsules) > 0
        assert capsules[0]["capsule_id"] == "user_capsule"

    def test_get_user_capsules_empty(self, manager):
        """Test getting capsules for user with none"""
        capsules = manager.get_user_capsules("XAI_NOCAPSULES")
        assert len(capsules) == 0

    def test_get_capsule(self, manager):
        """Test getting specific capsule details"""
        unlock_time = int(time.time()) + 3600
        
        tx = MockTransaction(
            sender="XAI_CREATOR",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "detail_test",
                "beneficiary": "XAI_B",
                "unlock_time": unlock_time,
            }
        )
        
        manager.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        capsule_data = manager.get_capsule("detail_test")
        
        assert capsule_data is not None
        assert capsule_data["capsule_id"] == "detail_test"
        assert "metadata" in capsule_data

    def test_get_capsule_not_found(self, manager):
        """Test getting non-existent capsule"""
        capsule_data = manager.get_capsule("nonexistent")
        assert capsule_data is None

    def test_get_statistics(self, manager):
        """Test getting capsule statistics"""
        current_time = time.time()
        
        # Create various capsules
        for i in range(3):
            unlock_time = int(current_time + (i * 3600))
            tx = MockTransaction(
                sender=f"XAI_{i}",
                recipient="capsule_address",
                amount=100.0 * (i + 1),
                metadata={
                    "capsule_id": f"capsule_{i}",
                    "beneficiary": f"XAI_B{i}",
                    "unlock_time": unlock_time,
                }
            )
            manager.register_lock_transaction(tx, block_height=100+i, block_timestamp=current_time)
        
        stats = manager.get_statistics()
        
        assert stats["total_capsules"] >= 3
        assert stats["total_locked_value"] >= 600.0
        assert "claimed" in stats
        assert "still_locked" in stats

    def test_persistence(self, temp_storage):
        """Test that capsules persist across manager instances"""
        blockchain = MockBlockchain()
        manager1 = TimeCapsuleManager(blockchain, storage_file=temp_storage)
        
        unlock_time = int(time.time()) + 3600
        tx = MockTransaction(
            sender="XAI_A",
            recipient="capsule_address",
            amount=100.0,
            metadata={
                "capsule_id": "persist_test",
                "beneficiary": "XAI_B",
                "unlock_time": unlock_time,
            }
        )
        
        manager1.register_lock_transaction(tx, block_height=100, block_timestamp=time.time())
        
        # Create new manager with same storage
        manager2 = TimeCapsuleManager(blockchain, storage_file=temp_storage)
        
        assert "persist_test" in manager2.capsules
        assert manager2.capsules["persist_test"].amount == 100.0


def test_get_time_capsule_manager():
    """Test factory function"""
    blockchain = MockBlockchain()
    manager = get_time_capsule_manager(blockchain)
    
    assert isinstance(manager, TimeCapsuleManager)
    assert manager.blockchain == blockchain
