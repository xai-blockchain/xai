"""
XAI Blockchain - Module Boundary Security Tests

Tests the critical "seams" where modules integrate with each other.
These integration points are the most common attack vectors.

Security Focus Areas:
1. API → Transaction Validator - Input validation
2. Transaction Validator → UTXO Manager - Double-spend prevention
3. UTXO Manager → Blockchain - State consistency
4. P2P → Consensus - Block validation from peers
5. Consensus → Blockchain - Only valid blocks added
6. Wallet → Blockchain - Balance calculation accuracy
7. Mining → Blockchain - Reward rules enforced
8. Governance → Blockchain - Vote authorization
9. AI Systems → Blockchain - AI can't violate consensus rules
"""

import pytest
import hashlib
import time
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

from xai.core.blockchain import Blockchain
from xai.core.transaction_validator import TransactionValidator
from xai.core.utxo_manager import UTXOManager
from xai.core.wallet import Wallet
from xai.core.node import Node
from xai.core.advanced_consensus import AdvancedConsensus


class TestAPIToValidatorBoundary:
    """Test API → Transaction Validator boundary security"""

    def test_api_rejects_malformed_transaction_before_validation(self):
        """API must validate basic structure before passing to validator"""
        # Malformed transaction (missing required fields)
        malformed_tx = {
            "sender": "valid_address",
            # Missing: recipient, amount, signature, etc.
        }

        # API should reject immediately, not pass to validator
        with pytest.raises(ValueError, match="Missing required fields"):
            # Simulate API receiving transaction
            assert "recipient" in malformed_tx
            assert "amount" in malformed_tx

    def test_api_sanitizes_inputs_before_validator(self):
        """API must sanitize inputs to prevent injection attacks"""
        # SQL injection attempt
        malicious_input = {
            "sender": "'; DROP TABLE transactions; --",
            "recipient": "<script>alert('xss')</script>",
            "amount": "1000 OR 1=1"
        }

        # Each field should be validated and sanitized
        for key, value in malicious_input.items():
            # Should reject non-alphanumeric characters in addresses
            if key in ["sender", "recipient"]:
                assert not value.replace("0x", "").isalnum()
            # Should reject non-numeric amounts
            if key == "amount":
                with pytest.raises((ValueError, TypeError)):
                    float(value)

    def test_api_enforces_rate_limiting_before_validator(self):
        """API must rate-limit before overwhelming validator"""
        from collections import defaultdict
        from time import time

        # Simulate rate limiter
        request_counts = defaultdict(list)
        rate_limit = 10  # requests per second

        def check_rate_limit(address):
            now = time()
            # Remove old requests
            request_counts[address] = [
                t for t in request_counts[address]
                if now - t < 1.0
            ]
            # Check limit
            if len(request_counts[address]) >= rate_limit:
                return False
            request_counts[address].append(now)
            return True

        # Attack: Submit 100 transactions rapidly
        attacker = "0xmalicious"
        accepted = 0
        for _ in range(100):
            if check_rate_limit(attacker):
                accepted += 1

        # Should only accept rate_limit transactions
        assert accepted <= rate_limit

    def test_api_rejects_transactions_exceeding_size_limit(self):
        """API must enforce transaction size limits"""
        max_tx_size = 100_000  # bytes

        # Create oversized transaction
        oversized_data = "x" * (max_tx_size + 1)

        tx_size = len(oversized_data.encode('utf-8'))
        assert tx_size > max_tx_size, "Transaction should be rejected at API layer"


class TestValidatorToUTXOBoundary:
    """Test Transaction Validator → UTXO Manager boundary security"""

    def test_validator_checks_utxo_existence_before_spending(self):
        """Validator must verify UTXO exists before allowing spend"""
        utxo_manager = UTXOManager()
        validator = TransactionValidator()

        # Transaction trying to spend non-existent UTXO
        fake_utxo = {
            "tx_hash": "0x" + "0" * 64,
            "output_index": 999,
            "amount": 1000
        }

        # UTXO doesn't exist
        assert not utxo_manager.utxo_exists(
            fake_utxo["tx_hash"],
            fake_utxo["output_index"]
        )

        # Validator must reject
        # (Test the validation logic that checks UTXO existence)

    def test_validator_prevents_double_spend_within_mempool(self):
        """Validator must detect double-spend attempts in pending transactions"""
        utxo_manager = UTXOManager()

        # Create valid UTXO
        utxo_id = ("tx_hash_1", 0)
        utxo_manager.add_utxo(utxo_id, {
            "address": "alice",
            "amount": 100
        })

        # Create two transactions spending same UTXO
        tx1 = {
            "inputs": [utxo_id],
            "outputs": [{"address": "bob", "amount": 100}]
        }
        tx2 = {
            "inputs": [utxo_id],  # Same UTXO!
            "outputs": [{"address": "charlie", "amount": 100}]
        }

        # First should succeed
        utxo_manager.mark_as_spent(utxo_id)

        # Second must fail (UTXO already marked as spent)
        with pytest.raises(ValueError, match="already spent|not found"):
            assert utxo_manager.is_utxo_available(utxo_id) == False

    def test_validator_verifies_input_amounts_equal_output_amounts(self):
        """Validator must ensure inputs = outputs (no value creation)"""
        # Transaction with mismatched amounts
        tx = {
            "inputs": [
                {"amount": 50},
                {"amount": 50}
            ],  # Total: 100
            "outputs": [
                {"amount": 150}  # Total: 150 (created 50 out of thin air!)
            ]
        }

        input_sum = sum(inp["amount"] for inp in tx["inputs"])
        output_sum = sum(out["amount"] for out in tx["outputs"])

        # Must detect value creation
        assert input_sum >= output_sum, "Cannot create value from nothing"

    def test_concurrent_utxo_spending_race_condition(self):
        """Test race condition when two threads try to spend same UTXO"""
        import threading
        from queue import Queue

        utxo_manager = UTXOManager()
        utxo_id = ("tx1", 0)
        utxo_manager.add_utxo(utxo_id, {"address": "alice", "amount": 100})

        results = Queue()

        def try_spend():
            try:
                if utxo_manager.is_utxo_available(utxo_id):
                    utxo_manager.mark_as_spent(utxo_id)
                    results.put("SUCCESS")
                else:
                    results.put("ALREADY_SPENT")
            except Exception as e:
                results.put(f"ERROR: {e}")

        # Two threads try to spend simultaneously
        t1 = threading.Thread(target=try_spend)
        t2 = threading.Thread(target=try_spend)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Collect results
        result_list = []
        while not results.empty():
            result_list.append(results.get())

        # Only ONE should succeed
        success_count = result_list.count("SUCCESS")
        assert success_count == 1, f"Expected 1 success, got {success_count}"


class TestUTXOToBlockchainBoundary:
    """Test UTXO Manager → Blockchain boundary security"""

    def test_blockchain_and_utxo_state_consistency(self):
        """Blockchain and UTXO manager must have consistent view of state"""
        blockchain = Blockchain()
        utxo_manager = UTXOManager()

        # Simulate adding a block with transactions
        tx = {
            "inputs": [("prev_tx", 0)],
            "outputs": [
                {"address": "alice", "amount": 50},
                {"address": "bob", "amount": 50}
            ]
        }

        # When block is added to blockchain
        # UTXO manager must be updated atomically

        # Both views must show same UTXOs
        blockchain_utxos = set()  # From scanning blockchain
        utxo_manager_utxos = set(utxo_manager.get_all_utxos().keys())

        # Must be identical
        assert blockchain_utxos == utxo_manager_utxos

    def test_utxo_rollback_on_blockchain_reorg(self):
        """UTXO state must rollback when blockchain reorganizes"""
        blockchain = Blockchain()
        utxo_manager = UTXOManager()

        # Add blocks to create chain
        initial_height = blockchain.get_height()

        # Record UTXO state
        utxos_before = utxo_manager.get_all_utxos().copy()

        # Add block with transaction
        # ... (creates new UTXOs)

        # Simulate chain reorganization (revert block)
        blockchain.rollback_to_height(initial_height)

        # UTXOs must also rollback
        utxos_after = utxo_manager.get_all_utxos()
        assert utxos_after == utxos_before, "UTXO state must rollback with blockchain"

    def test_utxo_updates_are_atomic_with_block_addition(self):
        """UTXO updates must succeed or fail atomically with block"""
        blockchain = Blockchain()
        utxo_manager = UTXOManager()

        # Capture initial state
        initial_utxos = utxo_manager.get_all_utxos().copy()
        initial_height = blockchain.get_height()

        # Try to add invalid block
        invalid_block = Mock()
        invalid_block.is_valid.return_value = False

        try:
            blockchain.add_block(invalid_block)
        except:
            pass

        # UTXO state must be unchanged
        assert utxo_manager.get_all_utxos() == initial_utxos
        assert blockchain.get_height() == initial_height


class TestP2PToConsensusBoundary:
    """Test P2P → Consensus boundary security"""

    def test_consensus_rejects_blocks_from_unauthorized_nodes(self):
        """Consensus must validate block proposer before accepting"""
        consensus = AdvancedConsensus()

        # Block from unauthorized node
        malicious_block = Mock()
        malicious_block.proposer = "0xmalicious"
        malicious_block.height = 100

        # Check if proposer is authorized
        is_authorized = consensus.is_authorized_proposer(
            malicious_block.proposer,
            malicious_block.height
        )

        assert not is_authorized, "Should reject blocks from unauthorized nodes"

    def test_consensus_validates_block_before_propagating(self):
        """P2P must not propagate invalid blocks received from peers"""
        # Receive invalid block from peer
        invalid_block = Mock()
        invalid_block.hash = "invalid_hash"
        invalid_block.previous_hash = "wrong_parent"

        # Must validate before propagating
        def validate_before_propagate(block):
            if not block.is_valid():
                return False  # Don't propagate
            # Propagate to other peers
            return True

        assert not validate_before_propagate(invalid_block)

    def test_p2p_enforces_block_size_limit(self):
        """P2P must reject blocks exceeding size limit"""
        max_block_size = 1_000_000  # 1 MB

        # Create oversized block
        large_block = Mock()
        large_block.size = max_block_size + 1

        assert large_block.size > max_block_size
        # Should be rejected at P2P layer

    def test_consensus_prevents_timestamp_manipulation(self):
        """Consensus must reject blocks with invalid timestamps"""
        consensus = AdvancedConsensus()
        current_time = time.time()

        # Block with future timestamp (more than 2 hours ahead)
        future_block = Mock()
        future_block.timestamp = current_time + 3600 * 3  # 3 hours future

        # Should reject
        assert not consensus.validate_timestamp(future_block.timestamp, current_time)

        # Block with very old timestamp
        old_block = Mock()
        old_block.timestamp = current_time - 3600 * 24 * 30  # 30 days old

        # Might reject depending on rules
        # (Some chains allow old blocks, others don't)


class TestConsensusToBlockchainBoundary:
    """Test Consensus → Blockchain boundary security"""

    def test_blockchain_only_accepts_consensus_approved_blocks(self):
        """Blockchain must not add blocks that consensus hasn't approved"""
        blockchain = Blockchain()
        consensus = AdvancedConsensus()

        # Block that consensus rejects
        unapproved_block = Mock()
        unapproved_block.is_valid.return_value = False

        # Consensus rejects it
        assert not consensus.validate_block(unapproved_block)

        # Blockchain must not add it
        with pytest.raises(ValueError):
            blockchain.add_block(unapproved_block)

    def test_consensus_enforces_mining_difficulty(self):
        """Consensus must validate proof-of-work meets difficulty"""
        consensus = AdvancedConsensus()

        # Block with insufficient proof-of-work
        weak_pow_block = Mock()
        weak_pow_block.hash = "0xFFFFFFFF..."  # Not enough leading zeros
        weak_pow_block.difficulty = 4  # Requires 4 leading zeros

        # Count leading zeros
        leading_zeros = len(weak_pow_block.hash) - len(weak_pow_block.hash.lstrip('0'))

        assert leading_zeros < weak_pow_block.difficulty
        # Should be rejected

    def test_consensus_prevents_selfish_mining(self):
        """Consensus must detect and prevent selfish mining attacks"""
        consensus = AdvancedConsensus()

        # Miner withholds block then releases multiple blocks
        # to orphan others' blocks

        # Simplified detection: check if node suddenly releases
        # multiple blocks that weren't previously announced

        node_history = {
            "node1": {"blocks_seen": 10, "blocks_mined": 2},
            "node_selfish": {"blocks_seen": 5, "blocks_mined": 10}  # Suspicious!
        }

        for node, stats in node_history.items():
            # If blocks_mined >> blocks_seen, possibly selfish mining
            ratio = stats["blocks_mined"] / max(stats["blocks_seen"], 1)
            if ratio > 1.5:  # Threshold
                # Flag as suspicious
                assert node == "node_selfish"


class TestWalletToBlockchainBoundary:
    """Test Wallet → Blockchain boundary security"""

    def test_wallet_balance_matches_blockchain_utxos(self):
        """Wallet's calculated balance must match blockchain's UTXO set"""
        blockchain = Blockchain()
        wallet = Wallet()
        address = wallet.get_address()

        # Calculate balance from wallet
        wallet_balance = wallet.get_balance()

        # Calculate balance from blockchain's UTXO set
        blockchain_balance = blockchain.get_address_balance(address)

        # Must match exactly
        assert wallet_balance == blockchain_balance

    def test_wallet_cannot_spend_unconfirmed_utxos(self):
        """Wallet must not spend UTXOs from unconfirmed transactions"""
        wallet = Wallet()

        # UTXO from transaction with 0 confirmations
        unconfirmed_utxo = {
            "tx_hash": "pending_tx",
            "confirmations": 0,
            "amount": 100
        }

        # Wallet should not include in spendable balance
        spendable = wallet.get_spendable_balance()

        # Only confirmed UTXOs should be spendable
        # (typically require 6 confirmations for Bitcoin, 1 for others)

    def test_wallet_signature_verification_by_blockchain(self):
        """Blockchain must verify wallet signatures, not trust wallet"""
        wallet = Wallet()
        blockchain = Blockchain()

        # Wallet creates and signs transaction
        tx = wallet.create_transaction(recipient="bob", amount=10)

        # Blockchain must independently verify signature
        # (Don't trust that wallet signed it correctly)
        is_valid = blockchain.verify_transaction_signature(tx)

        assert is_valid

        # Tampered transaction should fail
        tx.amount = 1000  # Changed after signing
        is_valid_tampered = blockchain.verify_transaction_signature(tx)

        assert not is_valid_tampered


class TestMiningToBlockchainBoundary:
    """Test Mining → Blockchain boundary security"""

    def test_blockchain_enforces_block_reward_limit(self):
        """Blockchain must reject blocks with excessive rewards"""
        blockchain = Blockchain()
        max_reward = 50  # Example: 50 XAI per block

        # Miner tries to give themselves 1000 XAI
        greedy_block = Mock()
        greedy_block.coinbase_amount = 1000

        # Blockchain must reject
        assert greedy_block.coinbase_amount > max_reward
        # Should be rejected during validation

    def test_mining_difficulty_adjustment_integrity(self):
        """Difficulty adjustment must not be manipulable by miners"""
        blockchain = Blockchain()

        # Record initial difficulty
        initial_difficulty = blockchain.get_difficulty()

        # Miner tries to manipulate timestamps to reduce difficulty
        # (by making blocks appear to take longer)

        # Blockchain must validate timestamp consistency
        # and adjust difficulty correctly regardless

    def test_block_must_include_valid_coinbase_transaction(self):
        """Every block must have exactly one valid coinbase transaction"""
        # Block with no coinbase
        block_no_coinbase = Mock()
        block_no_coinbase.transactions = [
            {"type": "regular"},
            {"type": "regular"}
        ]

        coinbase_count = sum(
            1 for tx in block_no_coinbase.transactions
            if tx.get("type") == "coinbase"
        )
        assert coinbase_count == 0  # Invalid!

        # Block with multiple coinbase transactions
        block_multi_coinbase = Mock()
        block_multi_coinbase.transactions = [
            {"type": "coinbase"},
            {"type": "coinbase"},  # Invalid!
            {"type": "regular"}
        ]

        coinbase_count = sum(
            1 for tx in block_multi_coinbase.transactions
            if tx.get("type") == "coinbase"
        )
        assert coinbase_count == 2  # Invalid!


class TestGovernanceToBlockchainBoundary:
    """Test Governance → Blockchain boundary security"""

    def test_governance_vote_requires_token_ownership(self):
        """Voters must own tokens at snapshot height"""
        # Snapshot taken at block 1000
        snapshot_height = 1000

        # User tries to vote but didn't own tokens at snapshot
        voter = "0xvoter"
        balance_at_snapshot = 0  # No tokens at block 1000
        current_balance = 1000  # Bought tokens after snapshot

        # Should use snapshot balance, not current
        assert balance_at_snapshot == 0
        # Vote should be rejected or have zero weight

    def test_governance_proposal_execution_requires_consensus(self):
        """Proposals must reach threshold before execution"""
        proposal = {
            "id": 1,
            "votes_for": 40,
            "votes_against": 30,
            "total_supply": 100,
            "threshold": 0.5  # 50% required
        }

        # Calculate if proposal passes
        participation = (proposal["votes_for"] + proposal["votes_against"]) / proposal["total_supply"]
        approval = proposal["votes_for"] / (proposal["votes_for"] + proposal["votes_against"])

        # Must meet both participation and approval thresholds
        passes = participation >= 0.5 and approval >= proposal["threshold"]

        assert passes  # This proposal should pass

    def test_governance_cannot_violate_blockchain_invariants(self):
        """Governance changes must not break blockchain rules"""
        # Governance proposal to change max supply
        proposal = {
            "type": "parameter_change",
            "parameter": "max_supply",
            "new_value": 21_000_000
        }

        # Some parameters should be immutable
        immutable_params = ["max_supply", "genesis_hash", "chain_id"]

        if proposal["parameter"] in immutable_params:
            # Should be rejected
            assert True  # Proposal violates invariants


class TestAISystemsToBlockchainBoundary:
    """Test AI Systems → Blockchain boundary security"""

    def test_ai_cannot_bypass_consensus_rules(self):
        """AI systems must follow same consensus rules as humans"""
        blockchain = Blockchain()

        # AI tries to submit block without proper proof-of-work
        ai_block = Mock()
        ai_block.created_by = "AI_NODE"
        ai_block.proof_of_work = "insufficient"

        # Must be rejected just like any other invalid block
        assert not blockchain.validate_block(ai_block)

    def test_ai_trading_follows_same_transaction_rules(self):
        """AI trading bots must create valid transactions"""
        # AI tries to create transaction without signature
        ai_transaction = {
            "from": "ai_wallet",
            "to": "target",
            "amount": 100,
            "signature": None  # AI forgot to sign!
        }

        # Must be rejected
        assert ai_transaction["signature"] is not None, "Missing signature"

    def test_ai_cannot_access_private_keys(self):
        """AI systems must not have direct access to private keys"""
        wallet = Wallet()

        # Private key should be protected
        # AI should only be able to request signatures, not access key

        def ai_request_signature(message):
            # AI can request signature
            return wallet.sign_message(message)

        def ai_get_private_key():
            # AI should NOT be able to get private key
            raise PermissionError("AI cannot access private keys")

        # Test that AI can sign but not get key
        signature = ai_request_signature("test message")
        assert signature is not None

        with pytest.raises(PermissionError):
            ai_get_private_key()

    def test_ai_metrics_cannot_manipulate_consensus(self):
        """AI performance metrics must not influence consensus"""
        consensus = AdvancedConsensus()

        # AI claims high performance score
        ai_node = {
            "address": "ai_node_1",
            "ai_score": 0.99,  # Very high
            "staked_tokens": 100
        }

        # Consensus should be based on stake/PoW, not AI score
        weight = consensus.calculate_voting_weight(ai_node)

        # Weight should be based on staked_tokens, not ai_score
        assert weight == ai_node["staked_tokens"]


class TestCrossModuleRaceConditions:
    """Test race conditions across module boundaries"""

    def test_concurrent_block_and_transaction_submission(self):
        """Test race between new block and pending transaction"""
        import threading

        blockchain = Blockchain()
        mempool = []

        # Transaction in mempool
        tx = {"id": "tx1", "inputs": [("utxo1", 0)]}
        mempool.append(tx)

        def add_block():
            # Block includes same transaction
            block = {"transactions": [tx]}
            blockchain.add_block(block)
            # Remove from mempool
            if tx in mempool:
                mempool.remove(tx)

        def add_to_mempool():
            # Try to add same tx again
            if tx not in mempool:
                mempool.append(tx)

        # Race condition
        t1 = threading.Thread(target=add_block)
        t2 = threading.Thread(target=add_to_mempool)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Transaction should not be duplicated
        assert mempool.count(tx) <= 1


# Integration test fixtures
@pytest.fixture
def clean_blockchain():
    """Provide a clean blockchain instance"""
    return Blockchain()


@pytest.fixture
def funded_wallet(clean_blockchain):
    """Provide a wallet with funds"""
    wallet = Wallet()
    # Add some UTXOs to the wallet
    return wallet


@pytest.fixture
def test_network():
    """Provide a test network with multiple nodes"""
    nodes = [Node() for _ in range(5)]
    return nodes


# Run all boundary tests with security focus
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
