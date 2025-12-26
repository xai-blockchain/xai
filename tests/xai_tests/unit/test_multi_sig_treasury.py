"""
Comprehensive tests for MultiSigTreasury module.

Tests cover:
- Treasury initialization with M-of-N threshold
- Deposit operations with category tracking
- Transaction submission, approval, and execution
- Signature collection and verification
- Fund allocation tracking
- Error handling and edge cases
"""

import time
import threading
from typing import Any

import pytest


@pytest.fixture
def basic_treasury():
    """Create a basic 2-of-3 treasury."""
    from xai.treasury.multi_sig_treasury import MultiSigTreasury
    owners = ["alice", "bob", "charlie"]
    treasury = MultiSigTreasury(owners, threshold=2, require_signatures=False)
    treasury.deposit(1000.0)
    return treasury


@pytest.fixture
def signature_treasury():
    """Create a 2-of-3 treasury requiring signatures."""
    from xai.treasury.multi_sig_treasury import MultiSigTreasury
    owners = ["alice", "bob", "charlie"]
    treasury = MultiSigTreasury(owners, threshold=2, require_signatures=True)
    treasury.deposit(1000.0)
    return treasury


# ============= Initialization Tests =============


class TestMultiSigTreasuryInit:
    """Tests for treasury initialization."""

    def test_init_with_valid_params(self):
        """Test treasury initializes with valid parameters."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        owners = ["alice", "bob", "charlie"]
        treasury = MultiSigTreasury(owners, threshold=2)

        assert len(treasury.owners) == 3
        assert treasury.threshold == 2
        assert treasury.balance == 0.0

    def test_init_normalizes_owner_addresses(self):
        """Test owner addresses are normalized to lowercase."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        owners = ["ALICE", "Bob", "CHARLIE"]
        treasury = MultiSigTreasury(owners, threshold=2)

        assert treasury.owners == ["alice", "bob", "charlie"]

    def test_init_sorts_owners(self):
        """Test owner addresses are sorted."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        owners = ["charlie", "alice", "bob"]
        treasury = MultiSigTreasury(owners, threshold=2)

        assert treasury.owners == ["alice", "bob", "charlie"]

    def test_init_empty_owners_raises(self):
        """Test empty owners list raises error."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        with pytest.raises(ValueError, match="empty"):
            MultiSigTreasury([], threshold=1)

    def test_init_threshold_too_low_raises(self):
        """Test threshold below 1 raises error."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        with pytest.raises(ValueError):
            MultiSigTreasury(["alice", "bob"], threshold=0)

    def test_init_threshold_too_high_raises(self):
        """Test threshold above owner count raises error."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        with pytest.raises(ValueError):
            MultiSigTreasury(["alice", "bob"], threshold=3)

    def test_init_creates_fund_categories(self):
        """Test fund allocation categories are initialized."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        treasury = MultiSigTreasury(["alice"], threshold=1)

        assert "development" in treasury.fund_allocations
        assert "marketing" in treasury.fund_allocations
        assert "operations" in treasury.fund_allocations
        assert "reserve" in treasury.fund_allocations
        assert "other" in treasury.fund_allocations


# ============= Deposit Tests =============


class TestMultiSigTreasuryDeposit:
    """Tests for deposit operations."""

    def test_deposit_increases_balance(self, basic_treasury):
        """Test deposit increases treasury balance."""
        initial = basic_treasury.balance
        basic_treasury.deposit(500.0)
        assert basic_treasury.balance == initial + 500.0

    def test_deposit_tracks_category(self, basic_treasury):
        """Test deposit tracks fund category."""
        basic_treasury.deposit(200.0, category="development")
        assert basic_treasury.fund_allocations["development"] == 200.0

    def test_deposit_default_category(self, basic_treasury):
        """Test deposit uses reserve category by default."""
        initial_reserve = basic_treasury.fund_allocations["reserve"]
        basic_treasury.deposit(100.0)
        assert basic_treasury.fund_allocations["reserve"] == initial_reserve + 100.0

    def test_deposit_unknown_category_uses_other(self, basic_treasury):
        """Test unknown category defaults to 'other'."""
        basic_treasury.deposit(100.0, category="unknown_category")
        assert basic_treasury.fund_allocations["other"] == 100.0

    def test_deposit_zero_raises(self, basic_treasury):
        """Test zero deposit raises error."""
        with pytest.raises(ValueError, match="positive"):
            basic_treasury.deposit(0)

    def test_deposit_negative_raises(self, basic_treasury):
        """Test negative deposit raises error."""
        with pytest.raises(ValueError, match="positive"):
            basic_treasury.deposit(-100.0)


class TestMultiSigTreasuryBalance:
    """Tests for balance operations."""

    def test_get_balance(self, basic_treasury):
        """Test getting treasury balance."""
        assert basic_treasury.get_balance() == 1000.0

    def test_get_fund_breakdown(self, basic_treasury):
        """Test getting fund breakdown."""
        basic_treasury.deposit(200.0, "development")
        basic_treasury.deposit(100.0, "marketing")

        breakdown = basic_treasury.get_fund_breakdown()

        assert breakdown["total"] == 1300.0
        assert breakdown["development"] == 200.0
        assert breakdown["marketing"] == 100.0
        assert "allocated" in breakdown


# ============= Transaction Submission Tests =============


class TestMultiSigTreasurySubmission:
    """Tests for transaction submission."""

    def test_submit_transaction_returns_id(self, basic_treasury):
        """Test submission returns transaction ID."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        assert tx_id == "tx_1"

    def test_submit_transaction_increments_id(self, basic_treasury):
        """Test transaction IDs increment."""
        id1 = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        id2 = basic_treasury.submit_transaction("bob", "0xRecipient", 50.0)
        assert id1 == "tx_1"
        assert id2 == "tx_2"

    def test_submit_transaction_creates_entry(self, basic_treasury):
        """Test submission creates correct entry."""
        tx_id = basic_treasury.submit_transaction(
            "alice", "0xRecipient", 100.0, "Test payment", "development"
        )

        tx = basic_treasury.pending_transactions[tx_id]
        assert tx["proposer"] == "alice"
        assert tx["recipient"] == "0xrecipient"  # Normalized
        assert tx["amount"] == 100.0
        assert tx["description"] == "Test payment"
        assert tx["category"] == "development"
        assert tx["executed"] is False

    def test_submit_transaction_generates_hash(self, basic_treasury):
        """Test submission generates transaction hash."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        tx = basic_treasury.pending_transactions[tx_id]
        assert "tx_hash" in tx
        assert len(tx["tx_hash"]) == 64  # SHA256 hex

    def test_submit_non_owner_raises(self, basic_treasury):
        """Test submission by non-owner raises error."""
        with pytest.raises(ValueError, match="not an authorized owner"):
            basic_treasury.submit_transaction("dave", "0xRecipient", 100.0)

    def test_submit_empty_recipient_raises(self, basic_treasury):
        """Test submission with empty recipient raises error."""
        with pytest.raises(ValueError, match="empty"):
            basic_treasury.submit_transaction("alice", "", 100.0)

    def test_submit_zero_amount_raises(self, basic_treasury):
        """Test submission with zero amount raises error."""
        with pytest.raises(ValueError, match="positive"):
            basic_treasury.submit_transaction("alice", "0xRecipient", 0)

    def test_submit_exceeds_balance_raises(self, basic_treasury):
        """Test submission exceeding balance raises error."""
        with pytest.raises(ValueError, match="Insufficient"):
            basic_treasury.submit_transaction("alice", "0xRecipient", 5000.0)


# ============= Approval Tests =============


class TestMultiSigTreasuryApproval:
    """Tests for transaction approval."""

    def test_approve_transaction(self, basic_treasury):
        """Test approving a transaction."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)

        tx = basic_treasury.pending_transactions[tx_id]
        assert "bob" in tx["approvals"]

    def test_approve_by_non_owner_raises(self, basic_treasury):
        """Test approval by non-owner raises error."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)

        with pytest.raises(ValueError, match="not an authorized owner"):
            basic_treasury.approve_transaction("dave", tx_id)

    def test_approve_nonexistent_tx_raises(self, basic_treasury):
        """Test approval of nonexistent transaction raises error."""
        with pytest.raises(ValueError, match="not found"):
            basic_treasury.approve_transaction("alice", "tx_999")

    def test_approve_executed_tx_raises(self, basic_treasury):
        """Test approval of executed transaction raises error."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        with pytest.raises(ValueError, match="not found"):
            basic_treasury.approve_transaction("alice", tx_id)

    def test_duplicate_approval_ignored(self, basic_treasury):
        """Test duplicate approvals are ignored."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("bob", tx_id)  # Duplicate

        tx = basic_treasury.pending_transactions[tx_id]
        assert len(tx["approvals"]) == 1


class TestMultiSigTreasurySignatureRequired:
    """Tests for signature requirement."""

    def test_approve_without_signature_raises(self, signature_treasury):
        """Test approval without signature raises when required."""
        tx_id = signature_treasury.submit_transaction("alice", "0xRecipient", 100.0)

        with pytest.raises(ValueError, match="Signature required"):
            signature_treasury.approve_transaction("bob", tx_id)

    def test_approve_with_signature_succeeds(self, signature_treasury):
        """Test approval with signature succeeds."""
        tx_id = signature_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        signature_treasury.approve_transaction("bob", tx_id, signature="bob_sig_123")

        tx = signature_treasury.pending_transactions[tx_id]
        assert "bob" in tx["approvals"]
        assert tx["signatures"]["bob"] == "bob_sig_123"


# ============= Execution Tests =============


class TestMultiSigTreasuryExecution:
    """Tests for transaction execution."""

    def test_execute_with_threshold_met(self, basic_treasury):
        """Test execution when threshold is met."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)

        basic_treasury.execute_transaction("alice", tx_id)

        assert basic_treasury.get_balance() == 900.0
        assert tx_id not in basic_treasury.pending_transactions

    def test_execute_records_to_history(self, basic_treasury):
        """Test execution records transaction to history."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        executed = basic_treasury.get_executed_transactions()
        assert len(executed) == 1
        assert executed[0]["tx_id"] == tx_id

    def test_execute_insufficient_approvals_raises(self, basic_treasury):
        """Test execution with insufficient approvals raises error."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)

        with pytest.raises(ValueError, match="not have enough approvals"):
            basic_treasury.execute_transaction("alice", tx_id)

    def test_execute_non_owner_raises(self, basic_treasury):
        """Test execution by non-owner raises error."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)

        with pytest.raises(ValueError, match="not an authorized owner"):
            basic_treasury.execute_transaction("dave", tx_id)

    def test_execute_nonexistent_tx_raises(self, basic_treasury):
        """Test execution of nonexistent transaction raises error."""
        with pytest.raises(ValueError, match="not found"):
            basic_treasury.execute_transaction("alice", "tx_999")

    def test_execute_already_executed_raises(self, basic_treasury):
        """Test execution of already executed transaction raises error."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        with pytest.raises(ValueError, match="not found"):
            basic_treasury.execute_transaction("bob", tx_id)

    def test_execute_insufficient_balance_raises(self, basic_treasury):
        """Test execution with insufficient balance raises error."""
        # Create and approve a transaction
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 500.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)

        # Drain the treasury through another transaction
        tx_id2 = basic_treasury.submit_transaction("alice", "0xOther", 700.0)
        basic_treasury.approve_transaction("bob", tx_id2)
        basic_treasury.approve_transaction("charlie", tx_id2)
        basic_treasury.execute_transaction("alice", tx_id2)

        # Now try to execute the first transaction
        with pytest.raises(ValueError, match="Insufficient"):
            basic_treasury.execute_transaction("alice", tx_id)


class TestMultiSigTreasurySignatureExecution:
    """Tests for signature verification during execution."""

    def test_execute_insufficient_signatures_raises(self, signature_treasury):
        """Test execution fails without enough signatures."""
        tx_id = signature_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        signature_treasury.approve_transaction("bob", tx_id, signature="sig_bob")
        # Only one signature, need 2

        with pytest.raises(ValueError, match="not have enough approvals"):
            signature_treasury.execute_transaction("alice", tx_id)

    def test_execute_with_signatures_succeeds(self, signature_treasury):
        """Test execution succeeds with enough signatures."""
        tx_id = signature_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        signature_treasury.approve_transaction("bob", tx_id, signature="sig_bob")
        signature_treasury.approve_transaction("charlie", tx_id, signature="sig_charlie")

        signature_treasury.execute_transaction("alice", tx_id)

        assert signature_treasury.get_balance() == 900.0


# ============= Transaction Status Tests =============


class TestMultiSigTreasuryStatus:
    """Tests for transaction status queries."""

    def test_get_pending_transactions(self, basic_treasury):
        """Test getting pending transactions."""
        basic_treasury.submit_transaction("alice", "0xRecipient1", 100.0)
        basic_treasury.submit_transaction("bob", "0xRecipient2", 200.0)

        pending = basic_treasury.get_pending_transactions()

        assert len(pending) == 2
        assert pending[0]["amount"] == 100.0
        assert pending[1]["amount"] == 200.0

    def test_get_transaction_status_pending(self, basic_treasury):
        """Test getting status of pending transaction."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)

        status = basic_treasury.get_transaction_status(tx_id)

        assert status["status"] == "pending"
        assert status["approval_count"] == 1
        assert status["threshold"] == 2
        assert status["ready_to_execute"] is False

    def test_get_transaction_status_ready(self, basic_treasury):
        """Test getting status of ready transaction."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)

        status = basic_treasury.get_transaction_status(tx_id)

        assert status["approval_count"] == 2
        assert status["ready_to_execute"] is True

    def test_get_transaction_status_executed(self, basic_treasury):
        """Test getting status of executed transaction."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        status = basic_treasury.get_transaction_status(tx_id)

        assert status["status"] == "executed"

    def test_get_transaction_status_nonexistent_raises(self, basic_treasury):
        """Test getting status of nonexistent transaction raises error."""
        with pytest.raises(ValueError, match="not found"):
            basic_treasury.get_transaction_status("tx_999")


class TestMultiSigTreasuryExecutedTransactions:
    """Tests for executed transactions queries."""

    def test_get_executed_transactions_empty(self, basic_treasury):
        """Test getting executed transactions when empty."""
        executed = basic_treasury.get_executed_transactions()
        assert executed == []

    def test_get_executed_transactions_with_limit(self, basic_treasury):
        """Test getting executed transactions with limit."""
        for i in range(5):
            tx_id = basic_treasury.submit_transaction("alice", f"0xRecipient{i}", 10.0)
            basic_treasury.approve_transaction("bob", tx_id)
            basic_treasury.approve_transaction("charlie", tx_id)
            basic_treasury.execute_transaction("alice", tx_id)

        executed = basic_treasury.get_executed_transactions(limit=3)
        assert len(executed) == 3


# ============= Fund Allocation Tests =============


class TestMultiSigTreasuryFundAllocation:
    """Tests for fund allocation tracking."""

    def test_execution_reduces_category_allocation(self, basic_treasury):
        """Test execution reduces fund category allocation."""
        basic_treasury.deposit(500.0, "development")

        tx_id = basic_treasury.submit_transaction(
            "alice", "0xRecipient", 200.0, category="development"
        )
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        assert basic_treasury.fund_allocations["development"] == 300.0

    def test_execution_caps_at_zero_for_category(self, basic_treasury):
        """Test execution doesn't go negative for category."""
        tx_id = basic_treasury.submit_transaction(
            "alice", "0xRecipient", 100.0, category="marketing"
        )
        basic_treasury.approve_transaction("bob", tx_id)
        basic_treasury.approve_transaction("charlie", tx_id)
        basic_treasury.execute_transaction("alice", tx_id)

        assert basic_treasury.fund_allocations["marketing"] == 0.0


# ============= Edge Cases Tests =============


class TestMultiSigTreasuryEdgeCases:
    """Tests for edge cases."""

    def test_1_of_1_treasury(self):
        """Test 1-of-1 multisig treasury."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        treasury = MultiSigTreasury(["alice"], threshold=1, require_signatures=False)
        treasury.deposit(1000.0)

        tx_id = treasury.submit_transaction("alice", "0xRecipient", 100.0)
        treasury.approve_transaction("alice", tx_id)
        treasury.execute_transaction("alice", tx_id)

        assert treasury.get_balance() == 900.0

    def test_n_of_n_treasury(self):
        """Test N-of-N multisig treasury (all must approve)."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        owners = ["alice", "bob", "charlie"]
        treasury = MultiSigTreasury(owners, threshold=3, require_signatures=False)
        treasury.deposit(1000.0)

        tx_id = treasury.submit_transaction("alice", "0xRecipient", 100.0)
        treasury.approve_transaction("alice", tx_id)
        treasury.approve_transaction("bob", tx_id)

        # Should fail without charlie's approval
        with pytest.raises(ValueError, match="not have enough"):
            treasury.execute_transaction("alice", tx_id)

        treasury.approve_transaction("charlie", tx_id)
        treasury.execute_transaction("alice", tx_id)

        assert treasury.get_balance() == 900.0

    def test_case_insensitive_owner_matching(self, basic_treasury):
        """Test owner matching is case insensitive."""
        tx_id = basic_treasury.submit_transaction("ALICE", "0xRecipient", 100.0)
        basic_treasury.approve_transaction("BOB", tx_id)
        basic_treasury.approve_transaction("Charlie", tx_id)

        basic_treasury.execute_transaction("aLiCe", tx_id)

        assert basic_treasury.get_balance() == 900.0

    def test_concurrent_approvals(self, basic_treasury):
        """Test concurrent approvals are handled correctly."""
        tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 100.0)

        def approve(owner):
            time.sleep(0.01)
            basic_treasury.approve_transaction(owner, tx_id)

        threads = [
            threading.Thread(target=approve, args=("bob",)),
            threading.Thread(target=approve, args=("charlie",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tx = basic_treasury.pending_transactions[tx_id]
        assert len(tx["approvals"]) == 2


class TestMultiSigTreasuryHashGeneration:
    """Tests for transaction hash generation."""

    def test_hash_is_deterministic(self, basic_treasury):
        """Test hash generation is deterministic."""
        tx_id = "tx_test"
        recipient = "0xRecipient"
        amount = 100.0
        nonce = 12345

        hash1 = basic_treasury._generate_tx_hash(tx_id, recipient, amount, nonce)
        hash2 = basic_treasury._generate_tx_hash(tx_id, recipient, amount, nonce)

        assert hash1 == hash2

    def test_hash_changes_with_input(self, basic_treasury):
        """Test hash changes with different inputs."""
        nonce = 12345

        hash1 = basic_treasury._generate_tx_hash("tx_1", "0xA", 100.0, nonce)
        hash2 = basic_treasury._generate_tx_hash("tx_2", "0xA", 100.0, nonce)
        hash3 = basic_treasury._generate_tx_hash("tx_1", "0xB", 100.0, nonce)
        hash4 = basic_treasury._generate_tx_hash("tx_1", "0xA", 200.0, nonce)

        assert len({hash1, hash2, hash3, hash4}) == 4  # All unique


class TestMultiSigTreasuryThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_deposits(self):
        """Test concurrent deposits are safe."""
        from xai.treasury.multi_sig_treasury import MultiSigTreasury

        treasury = MultiSigTreasury(["alice"], threshold=1)

        def deposit():
            for _ in range(100):
                treasury.deposit(1.0)

        threads = [threading.Thread(target=deposit) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert treasury.get_balance() == 1000.0

    def test_concurrent_transaction_submissions(self, basic_treasury):
        """Test concurrent transaction submissions."""
        submitted_ids = []
        lock = threading.Lock()

        def submit():
            for _ in range(10):
                tx_id = basic_treasury.submit_transaction("alice", "0xRecipient", 1.0)
                with lock:
                    submitted_ids.append(tx_id)

        threads = [threading.Thread(target=submit) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(submitted_ids) == 50
        assert len(set(submitted_ids)) == 50  # All unique


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
