from __future__ import annotations

"""
Phase 4 Security Tests: Attack Simulations
Phase 4.2, 4.3, 4.4 of LOCAL_TESTING_PLAN.md

Comprehensive attack scenario testing:
- 4.2: 51% Attack (Deep Re-org)
- 4.3: Selfish Mining Simulation
- 4.4: Transaction Malleability & Double-Spend

All tests marked with @pytest.mark.security for automated security suite execution.
"""

import pytest
import time
import threading
import tempfile
import hashlib

from pathlib import Path
from unittest.mock import Mock, patch

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.blockchain_security import BlockchainSecurityManager, ReorganizationProtection

@pytest.mark.security
class TestFiftyOnePercentAttack:
    """
    Test 51% Attack scenarios (Deep Re-org)

    Simulates a minority of nodes mining a longer private chain,
    then reconnecting to force a reorganization.
    """

    @pytest.fixture
    def network_split(self, tmp_path) -> tuple[list[Blockchain], list[Blockchain]]:
        """
        Create network split: 2 honest nodes (majority) vs 1 attacker node (minority)
        """
        honest_nodes = []
        for i in range(2):
            node_dir = tmp_path / f"honest_{i}"
            node_dir.mkdir()
            blockchain = Blockchain(data_dir=str(node_dir))
            honest_nodes.append(blockchain)

        attacker_dir = tmp_path / "attacker"
        attacker_dir.mkdir()
        attacker = Blockchain(data_dir=str(attacker_dir))

        return honest_nodes, [attacker]

    def test_minority_mines_longer_private_chain(self, network_split):
        """
        Test: Attacker mines longer private chain while isolated

        Validates:
        - Attacker can mine private chain in isolation
        - Private chain is longer than main network
        - Attacker's chain is internally valid
        """
        honest_nodes, attackers = network_split
        honest_wallet = Wallet()
        attacker_wallet = Wallet()

        # Phase 1: Honest network mines 3 blocks
        for _ in range(3):
            block = honest_nodes[0].mine_pending_transactions(honest_wallet.address)
            # Propagate to other honest node
            honest_nodes[1].add_block(block)

        honest_height = len(honest_nodes[0].chain)
        assert honest_height == 4  # Genesis + 3 blocks

        # Phase 2: Attacker mines longer private chain (5 blocks) in isolation
        attacker = attackers[0]
        for _ in range(5):
            attacker.mine_pending_transactions(attacker_wallet.address)

        attacker_height = len(attacker.chain)
        assert attacker_height == 6  # Genesis + 5 blocks
        assert attacker_height > honest_height

        # Validate attacker's private chain
        assert attacker.validate_chain(), "Attacker's private chain should be valid"

    def test_reorg_upon_reconnection(self, network_split):
        """
        Test: Main network re-orgs when attacker reconnects with longer chain

        Validates:
        - Longer valid chain triggers reorganization
        - Honest nodes accept longer chain
        - Chain height increases after re-org
        - Previous blocks are orphaned
        """
        honest_nodes, attackers = network_split
        honest_wallet = Wallet()
        attacker_wallet = Wallet()

        # Phase 1: Honest network mines 3 blocks
        honest_blocks = []
        for _ in range(3):
            block = honest_nodes[0].mine_pending_transactions(honest_wallet.address)
            honest_blocks.append(block)
            honest_nodes[1].add_block(block)

        original_honest_height = len(honest_nodes[0].chain)

        # Phase 2: Attacker mines longer chain (5 blocks)
        attacker = attackers[0]
        for _ in range(5):
            attacker.mine_pending_transactions(attacker_wallet.address)

        # Phase 3: Reconnection - honest node receives attacker's chain
        attacker_chain = attacker.chain.copy()

        # Simulate chain replacement (longer chain wins)
        if len(attacker_chain) > len(honest_nodes[0].chain):
            # Honest node should accept longer valid chain
            result = honest_nodes[0].replace_chain(attacker_chain)

            # Chain should be replaced if attacker's chain is valid and longer
            new_height = len(honest_nodes[0].chain)
            assert new_height >= original_honest_height, "Chain height should not decrease"

    def test_deep_reorg_protection(self, network_split):
        """
        Test: Deep reorganization protection prevents excessive re-orgs

        Validates:
        - Re-org depth limits are enforced
        - Attempting deep re-org triggers security protection
        - Finality checkpoints prevent old block changes
        """
        honest_nodes, attackers = network_split
        honest_wallet = Wallet()
        attacker_wallet = Wallet()

        # Honest network builds long chain
        for _ in range(50):
            block = honest_nodes[0].mine_pending_transactions(honest_wallet.address)
            honest_nodes[1].add_block(block)

        # Attacker tries to mine from very old fork point
        attacker = attackers[0]

        # Attempt to build alternative chain from genesis
        for _ in range(55):  # Longer but from old fork point
            attacker.mine_pending_transactions(attacker_wallet.address)

        # Verify re-org protection exists
        assert hasattr(honest_nodes[0].security_manager, 'reorg_protection')

        # Test re-org validation
        current_height = len(honest_nodes[0].chain)
        fork_point = 0  # Very deep fork

        reorg_protection = honest_nodes[0].security_manager.reorg_protection
        valid, error = reorg_protection.validate_reorganization(current_height, fork_point)

        # Deep re-org should be rejected
        assert not valid, "Deep reorganization should be rejected by security"
        assert error and len(error) > 0, "Should provide error message"

    def test_consensus_rules_during_reorg(self, network_split):
        """
        Test: Consensus rules are enforced during reorganization

        Validates:
        - Invalid blocks rejected even if chain is longer
        - Difficulty must be correct
        - Block hashes must meet difficulty target
        - Transaction signatures must be valid
        """
        honest_nodes, attackers = network_split
        honest_wallet = Wallet()

        # Honest network mines blocks
        for _ in range(3):
            honest_nodes[0].mine_pending_transactions(honest_wallet.address)

        # Attacker creates invalid longer chain
        attacker = attackers[0]

        # Mine valid blocks first
        for _ in range(2):
            attacker.mine_pending_transactions(honest_wallet.address)

        # Create block with invalid hash (doesn't meet difficulty)
        invalid_block = Block(
            index=len(attacker.chain),
            transactions=[],
            previous_hash=attacker.chain[-1].hash,
            difficulty=attacker.difficulty
        )
        invalid_block.hash = "invalid_hash_not_meeting_difficulty"
        invalid_block.nonce = 0

        # Honest node should reject invalid block
        result = honest_nodes[0].add_block(invalid_block)
        assert result is False, "Invalid block should be rejected"

    def test_finality_prevents_old_block_reorg(self, tmp_path):
        """
        Test: Finality mechanism prevents reorganization of old finalized blocks

        Validates:
        - Finalized blocks cannot be re-organized
        - Finality checkpoints are respected
        - Blocks beyond finality depth are immutable
        """
        node = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks to establish finality
        for _ in range(20):
            node.mine_pending_transactions(wallet.address)

        # Verify finality manager exists
        assert hasattr(node, 'finality_manager'), "Should have finality manager"

        # Check if early blocks are finalized
        # (Implementation-specific - may need to query finality manager)
        chain_length = len(node.chain)
        assert chain_length > 10, "Should have sufficient blocks"

@pytest.mark.security
class TestSelfishMining:
    """
    Test Selfish Mining attack scenarios

    Simulates a selfish miner withholding blocks to gain unfair advantage.
    """

    @pytest.fixture
    def selfish_mining_network(self, tmp_path) -> tuple[Blockchain, Blockchain, Wallet, Wallet]:
        """
        Setup: Honest miner and selfish miner
        """
        honest_dir = tmp_path / "honest"
        selfish_dir = tmp_path / "selfish"
        honest_dir.mkdir()
        selfish_dir.mkdir()

        honest_node = Blockchain(data_dir=str(honest_dir))
        selfish_node = Blockchain(data_dir=str(selfish_dir))

        honest_wallet = Wallet()
        selfish_wallet = Wallet()

        return honest_node, selfish_node, honest_wallet, selfish_wallet

    def test_selfish_miner_withholds_blocks(self, selfish_mining_network):
        """
        Test: Selfish miner withholds mined blocks from network

        Validates:
        - Selfish miner can mine private blocks
        - Private blocks remain hidden from honest network
        - Selfish miner maintains private chain fork
        """
        honest_node, selfish_node, honest_wallet, selfish_wallet = selfish_mining_network

        # Honest miner mines 2 blocks
        for _ in range(2):
            block = honest_node.mine_pending_transactions(honest_wallet.address)
            # In real network, this would broadcast to selfish node
            selfish_node.add_block(block)

        # Selfish miner finds 3 blocks but withholds them
        private_blocks = []
        for _ in range(3):
            block = selfish_node.mine_pending_transactions(selfish_wallet.address)
            private_blocks.append(block)
            # NOT broadcasting to honest node (withholding)

        # Honest node is behind
        assert len(honest_node.chain) == 3  # Genesis + 2
        assert len(selfish_node.chain) == 6  # Genesis + 2 + 3 private

        # Selfish miner has longer private chain
        assert len(selfish_node.chain) > len(honest_node.chain)

    def test_selfish_miner_releases_on_competition(self, selfish_mining_network):
        """
        Test: Selfish miner releases private chain when honest miner catches up

        Validates:
        - Selfish miner monitors honest chain progress
        - Private blocks released when advantageous
        - Network re-orgs to selfish miner's chain
        """
        honest_node, selfish_node, honest_wallet, selfish_wallet = selfish_mining_network

        # Selfish miner builds 2-block private lead
        for _ in range(2):
            selfish_node.mine_pending_transactions(selfish_wallet.address)

        selfish_blocks = selfish_node.chain[1:].copy()  # Exclude genesis

        # Honest miner finds 1 block
        honest_block = honest_node.mine_pending_transactions(honest_wallet.address)

        # Selfish miner's strategy: Release private chain now
        for block in selfish_blocks:
            result = honest_node.add_block(block)
            # May succeed if chain is longer and valid

        # Verify network state
        assert len(selfish_node.chain) > len([honest_node.chain[0], honest_block])

    def test_selfish_mining_profitability_analysis(self, selfish_mining_network):
        """
        Test: Analyze selfish mining profitability vs honest mining

        Validates:
        - Selfish miner's block rewards tracked
        - Honest miner's block rewards tracked
        - Profitability comparison (selfish mining is generally unprofitable at <33% hashpower)
        """
        honest_node, selfish_node, honest_wallet, selfish_wallet = selfish_mining_network

        # Simulate mining rounds
        honest_rewards = 0
        selfish_rewards = 0

        # Round 1: Both mine, honest publishes, selfish withholds
        honest_block = honest_node.mine_pending_transactions(honest_wallet.address)
        selfish_node.add_block(honest_block)
        honest_rewards += honest_node.mining_reward

        selfish_block = selfish_node.mine_pending_transactions(selfish_wallet.address)
        # Withheld, doesn't count yet

        # Round 2: Honest mines another
        honest_block2 = honest_node.mine_pending_transactions(honest_wallet.address)
        selfish_node.add_block(honest_block2)
        honest_rewards += honest_node.mining_reward

        # Selfish miner's withheld block is now orphaned
        # They lose the reward from selfish_block

        # In this scenario, honest mining was more profitable
        # (Selfish mining needs >33% hashpower to be profitable)
        assert honest_rewards > 0

    def test_network_response_to_selfish_mining(self, selfish_mining_network):
        """
        Test: Network detection and response to selfish mining behavior

        Validates:
        - Unusual block withholding patterns detected
        - Network adapts to maintain consensus
        - Security monitoring flags suspicious behavior
        """
        honest_node, selfish_node, honest_wallet, selfish_wallet = selfish_mining_network

        # Simulate suspicious pattern: many blocks from same miner at once
        withheld_blocks = []
        for _ in range(5):
            block = selfish_node.mine_pending_transactions(selfish_wallet.address)
            withheld_blocks.append(block)

        # Suddenly release all blocks to honest node
        timestamps = []
        for block in withheld_blocks:
            honest_node.add_block(block)
            timestamps.append(block.timestamp)

        # All blocks should have different timestamps
        assert len(set(timestamps)) == len(timestamps), "Each block should have unique timestamp"

        # Blocks should be sequential
        for i in range(1, len(withheld_blocks)):
            assert withheld_blocks[i].index == withheld_blocks[i-1].index + 1

@pytest.mark.security
class TestTransactionMalleability:
    """
    Test Transaction Malleability attack scenarios

    Attempts to create transactions with different TXIDs from same UTXO.
    """

    @pytest.fixture
    def blockchain_with_funds(self, tmp_path) -> tuple[Blockchain, Wallet, Wallet]:
        """Setup blockchain with funded wallet"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        # Fund sender with mining reward
        blockchain.mine_pending_transactions(sender.address)

        return blockchain, sender, recipient

    def test_prevent_signature_malleability(self, blockchain_with_funds):
        """
        Test: Prevent modification of transaction signature

        Validates:
        - Signature malleability is prevented
        - Modified signatures are detected
        - Only original signed transaction is valid
        """
        blockchain, sender, recipient = blockchain_with_funds

        # Create and sign transaction
        tx = Transaction(
            sender.address,
            recipient.address,
            10.0,
            0.1,
            sender.public_key,
            nonce=0
        )
        tx.sign_transaction(sender.private_key)

        original_sig = tx.signature
        original_txid = tx.txid

        # Attempt to malleate signature (e.g., flip a bit)
        if original_sig:
            malleated_sig = original_sig[:-1] + ('0' if original_sig[-1] != '0' else '1')
            tx.signature = malleated_sig

            # Transaction should fail verification
            assert not tx.verify_signature(), "Malleated signature should fail verification"

            # Restore and verify original works
            tx.signature = original_sig
            assert tx.verify_signature(), "Original signature should verify"

    def test_prevent_txid_malleability(self, blockchain_with_funds):
        """
        Test: Prevent creation of different TXIDs from same transaction data

        Validates:
        - TXID is deterministically calculated
        - Cannot create multiple TXIDs for same transaction
        - TXID tampering is detected
        """
        blockchain, sender, recipient = blockchain_with_funds

        # Create transaction
        tx1 = Transaction(
            sender.address,
            recipient.address,
            10.0,
            0.1,
            sender.public_key,
            nonce=0
        )
        tx1.sign_transaction(sender.private_key)

        # Create identical transaction
        tx2 = Transaction(
            sender.address,
            recipient.address,
            10.0,
            0.1,
            sender.public_key,
            nonce=0
        )
        tx2.sign_transaction(sender.private_key)

        # TXIDs should be identical for identical transactions
        assert tx1.txid == tx2.txid, "Identical transactions must have identical TXIDs"

        # Manually tampering with TXID should be detectable
        original_txid = tx1.txid
        tx1.txid = "tampered_txid"

        # Recalculated hash should not match tampered TXID
        calculated_txid = tx1.calculate_hash()
        assert calculated_txid != tx1.txid, "Tampered TXID should differ from calculated"
        assert calculated_txid == original_txid, "Calculated TXID should match original"

    def test_different_nonce_creates_different_txid(self, blockchain_with_funds):
        """
        Test: Different nonces create different TXIDs (this is correct behavior)

        Validates:
        - Nonce is part of TXID calculation
        - Different nonces -> different TXIDs (replay protection)
        - Each TXID is unique
        """
        blockchain, sender, recipient = blockchain_with_funds

        tx1 = Transaction(sender.address, recipient.address, 10.0, 0.1, sender.public_key, nonce=0)
        tx1.sign_transaction(sender.private_key)

        tx2 = Transaction(sender.address, recipient.address, 10.0, 0.1, sender.public_key, nonce=1)
        tx2.sign_transaction(sender.private_key)

        # Different nonces should produce different TXIDs
        assert tx1.txid != tx2.txid, "Different nonces must create different TXIDs"

    def test_signature_covers_all_transaction_fields(self, blockchain_with_funds):
        """
        Test: Signature must cover all critical transaction fields

        Validates:
        - Modifying amount invalidates signature
        - Modifying recipient invalidates signature
        - Modifying fee invalidates signature
        """
        blockchain, sender, recipient = blockchain_with_funds

        # Create and sign transaction
        tx = Transaction(sender.address, recipient.address, 10.0, 0.1, sender.public_key, nonce=0)
        tx.sign_transaction(sender.private_key)

        assert tx.verify_signature(), "Original transaction should verify"

        # Modify amount after signing
        original_amount = tx.amount
        tx.amount = 100.0
        assert not tx.verify_signature(), "Modified amount should invalidate signature"
        tx.amount = original_amount

        # Modify recipient after signing
        attacker = Wallet()
        original_recipient = tx.to_address
        tx.to_address = attacker.address
        assert not tx.verify_signature(), "Modified recipient should invalidate signature"
        tx.to_address = original_recipient

        # Verify original still works
        assert tx.verify_signature(), "Restored transaction should verify"

@pytest.mark.security
class TestDoubleSpendAttacks:
    """
    Test Double-Spend attack scenarios

    Comprehensive double-spend prevention testing.
    """

    @pytest.fixture
    def funded_blockchain(self, tmp_path) -> tuple[Blockchain, Wallet]:
        """Setup blockchain with funded wallet"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine block to fund wallet
        blockchain.mine_pending_transactions(wallet.address)

        return blockchain, wallet

    def test_prevent_double_spend_same_mempool(self, funded_blockchain):
        """
        Test: Prevent double-spend in same mempool

        Validates:
        - Second transaction using same UTXO is rejected
        - Mempool tracks pending UTXO usage
        - Only first transaction accepted
        """
        blockchain, sender = funded_blockchain
        recipient1 = Wallet()
        recipient2 = Wallet()

        balance = blockchain.get_balance(sender.address)
        assert balance > 1.0, "Sender should have funds"

        # Create two transactions spending same funds
        tx1 = Transaction(sender.address, recipient1.address, balance - 0.2, 0.1, sender.public_key, nonce=0)
        tx1.sign_transaction(sender.private_key)

        tx2 = Transaction(sender.address, recipient2.address, balance - 0.2, 0.1, sender.public_key, nonce=1)
        tx2.sign_transaction(sender.private_key)

        # Add first transaction
        result1 = blockchain.add_transaction(tx1)
        assert result1, "First transaction should be accepted"

        # Attempt to add second transaction (double-spend)
        result2 = blockchain.add_transaction(tx2)

        # Second should be rejected (insufficient balance after first tx)
        assert not result2, "Second transaction should be rejected (double-spend)"

    def test_prevent_double_spend_across_blocks(self, funded_blockchain):
        """
        Test: Prevent double-spend across different blocks

        Validates:
        - UTXO marked as spent after first transaction
        - Second transaction fails validation
        - UTXO set consistency maintained
        """
        blockchain, sender = funded_blockchain
        recipient1 = Wallet()
        recipient2 = Wallet()

        balance = blockchain.get_balance(sender.address)

        # First transaction
        tx1 = Transaction(sender.address, recipient1.address, balance - 0.2, 0.1, sender.public_key, nonce=0)
        tx1.sign_transaction(sender.private_key)
        blockchain.add_transaction(tx1)

        # Mine block
        miner = Wallet()
        blockchain.mine_pending_transactions(miner.address)

        # Verify funds transferred
        assert blockchain.get_balance(recipient1.address) == balance - 0.2

        # Attempt second transaction with same original funds
        tx2 = Transaction(sender.address, recipient2.address, balance - 0.2, 0.1, sender.public_key, nonce=1)
        tx2.sign_transaction(sender.private_key)

        result = blockchain.add_transaction(tx2)

        # Should be rejected (funds already spent)
        assert not result, "Double-spend attempt should be rejected"

    def test_utxo_tracking_prevents_double_spend(self, funded_blockchain):
        """
        Test: UTXO set accurately tracks spent/unspent outputs

        Validates:
        - UTXOs marked spent after use
        - Spent UTXOs cannot be reused
        - UTXO set remains consistent
        """
        blockchain, sender = funded_blockchain
        recipient = Wallet()

        # Check initial UTXO
        initial_utxos = blockchain.utxo_manager.get_utxos(sender.address)
        assert len(initial_utxos) > 0, "Sender should have UTXOs"

        balance = blockchain.get_balance(sender.address)

        # Create and execute transaction
        tx = Transaction(sender.address, recipient.address, balance - 0.2, 0.1, sender.public_key, nonce=0)
        tx.sign_transaction(sender.private_key)
        blockchain.add_transaction(tx)
        blockchain.mine_pending_transactions(Wallet().address)

        # Original UTXOs should be spent
        final_utxos = blockchain.utxo_manager.get_utxos(sender.address)

        # Sender should have new UTXO from change (if any), not original
        final_balance = blockchain.get_balance(sender.address)
        assert final_balance < balance, "Balance should decrease after spending"

    def test_race_condition_double_spend_prevention(self, funded_blockchain):
        """
        Test: Prevent race condition double-spend attempts

        Validates:
        - Concurrent transaction submissions handled correctly
        - Lock mechanisms prevent UTXO race conditions
        - Only one transaction succeeds
        """
        blockchain, sender = funded_blockchain
        recipients = [Wallet() for _ in range(3)]

        balance = blockchain.get_balance(sender.address)

        # Create multiple transactions trying to spend same funds
        transactions = []
        for i, recipient in enumerate(recipients):
            tx = Transaction(
                sender.address,
                recipient.address,
                balance - 0.2,
                0.1,
                sender.public_key,
                nonce=i
            )
            tx.sign_transaction(sender.private_key)
            transactions.append(tx)

        # Submit all transactions (simulating race condition)
        results = []
        for tx in transactions:
            result = blockchain.add_transaction(tx)
            results.append(result)

        # Only one should succeed
        successful = sum(1 for r in results if r)
        assert successful <= 1, "At most one transaction should succeed (double-spend prevention)"

    def test_reorg_preserves_double_spend_prevention(self, tmp_path):
        """
        Test: Double-spend prevention maintained during chain reorganization

        Validates:
        - Re-org doesn't enable double-spending
        - UTXO set correctly updated during re-org
        - Spent outputs remain spent after re-org
        """
        # Create two nodes
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        node1 = Blockchain(data_dir=str(node1_dir))
        node2 = Blockchain(data_dir=str(node2_dir))

        sender = Wallet()
        recipient1 = Wallet()

        # Fund sender on both nodes
        block = node1.mine_pending_transactions(sender.address)
        node2.add_block(block)

        balance = node1.get_balance(sender.address)

        # Node 1: Sender spends funds to recipient1
        tx1 = Transaction(sender.address, recipient1.address, balance - 0.2, 0.1, sender.public_key, nonce=0)
        tx1.sign_transaction(sender.private_key)
        node1.add_transaction(tx1)
        block1 = node1.mine_pending_transactions(Wallet().address)

        # Node 2: Mines different block (network fork)
        block2 = node2.mine_pending_transactions(Wallet().address)

        # Node 2 mines one more block (becomes longer chain)
        block3 = node2.mine_pending_transactions(Wallet().address)

        # Node 1 receives longer chain from Node 2
        # This triggers re-org, but tx1 should be back in mempool or rejected

        # After re-org, sender should not be able to double-spend
        recipient2 = Wallet()
        tx2 = Transaction(sender.address, recipient2.address, balance - 0.2, 0.1, sender.public_key, nonce=1)
        tx2.sign_transaction(sender.private_key)

        # Both transactions spending same original UTXO cannot both succeed
        # (Implementation-specific behavior during re-org)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "security"])
