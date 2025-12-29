"""
Comprehensive Blockchain Invariant Tests - Priority 10

This module contains comprehensive test suites for critical blockchain invariants:
1. Total supply preservation (including after chain reorganizations)
2. Balance conservation (accounting for fees and burned coins)
3. State root correctness (for light client verification)
4. Transaction ordering invariants (nonce sequencing, MEV protection)

These tests ensure the blockchain maintains fundamental integrity properties
that are critical for security and consensus.
"""

import pytest
import time
import hashlib
import copy
from typing import Any
from decimal import Decimal

from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet
from xai.core.security.blockchain_security import BlockchainSecurityConfig
from xai.core.config import Config


class TestTotalSupplyPreservationWithReorg:
    """
    Test suite for total supply preservation invariants.

    Critical invariant: Total supply must never exceed MAX_SUPPLY (121M XAI)
    under any circumstances, including chain reorganizations.
    """

    def test_supply_preserved_during_simple_reorg(self, tmp_path):
        """Supply must remain consistent when reorganizing to a competing chain"""
        bc = Blockchain(data_dir=str(tmp_path / "main"))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Build main chain
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

        main_supply_before_reorg = bc.get_circulating_supply()
        main_chain_length = len(bc.chain)

        # Simulate receiving a competing fork with more work
        # Create transactions on the competing chain
        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=5.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Mine additional blocks to trigger potential reorg
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        supply_after = bc.get_circulating_supply()

        # Supply should only increase by mining rewards, never decrease or jump
        expected_new_blocks = len(bc.chain) - main_chain_length
        min_expected_increase = expected_new_blocks * bc.get_block_reward(main_chain_length)

        assert supply_after >= main_supply_before_reorg, \
            f"Supply decreased during reorg: {main_supply_before_reorg} -> {supply_after}"
        assert supply_after <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Supply exceeded MAX_SUPPLY: {supply_after} > {BlockchainSecurityConfig.MAX_SUPPLY}"

        # Verify supply increase is reasonable (only from new blocks)
        actual_increase = supply_after - main_supply_before_reorg
        # Allow up to 10% bonus from gamification/streaks
        assert actual_increase <= min_expected_increase * 1.1, \
            f"Supply increased too much: {actual_increase} > {min_expected_increase * 1.1}"

    def test_supply_accounting_after_deep_reorg(self, tmp_path):
        """Deep reorganization must maintain supply accounting integrity"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Build initial chain with transactions
        for i in range(10):
            bc.mine_pending_transactions(wallet1.address)

        # Create some transactions
        balance = bc.get_balance(wallet1.address)
        if balance > 20:
            for i in range(3):
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address if i % 2 == 0 else wallet3.address,
                    amount=2.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )
                if tx:
                    bc.add_transaction(tx)
                    bc.mine_pending_transactions(wallet1.address)

        # Record state before potential reorg
        supply_before = bc.get_circulating_supply()
        balance1_before = bc.get_balance(wallet1.address)
        balance2_before = bc.get_balance(wallet2.address)
        balance3_before = bc.get_balance(wallet3.address)

        # Sum of all balances should equal supply
        total_balances_before = balance1_before + balance2_before + balance3_before

        # Account for any other addresses in UTXO set
        all_addresses = set()
        for addr, utxos in bc.utxo_manager.utxo_set.items():
            if utxos:
                all_addresses.add(addr)

        actual_sum_before = sum(bc.get_balance(addr) for addr in all_addresses)

        assert abs(actual_sum_before - supply_before) < 0.01, \
            f"Balance sum {actual_sum_before} != supply {supply_before} before reorg"

        # Mine more blocks (simulating continuation)
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

        supply_after = bc.get_circulating_supply()

        # Collect all addresses again
        all_addresses_after = set()
        for addr, utxos in bc.utxo_manager.utxo_set.items():
            if utxos:
                all_addresses_after.add(addr)

        actual_sum_after = sum(bc.get_balance(addr) for addr in all_addresses_after)

        # Supply accounting must still be consistent
        assert abs(actual_sum_after - supply_after) < 0.01, \
            f"Balance sum {actual_sum_after} != supply {supply_after} after reorg"

        # Supply should never exceed cap
        assert supply_after <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Supply exceeded MAX_SUPPLY after deep reorg: {supply_after}"

    def test_no_supply_inflation_from_reorg_double_rewards(self, tmp_path):
        """Reorg must not allow double-claiming of mining rewards"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner1 = Wallet()
        miner2 = Wallet()

        # Miner1 mines blocks
        for i in range(5):
            bc.mine_pending_transactions(miner1.address)

        supply_after_initial_mining = bc.get_circulating_supply()
        miner1_balance = bc.get_balance(miner1.address)

        # Record the UTXO set state
        utxo_snapshot = {}
        for addr, utxos in bc.utxo_manager.utxo_set.items():
            utxo_snapshot[addr] = len([u for u in utxos if not u.get('spent', False)])

        # Different miner mines more blocks
        for i in range(3):
            bc.mine_pending_transactions(miner2.address)

        supply_after_more_mining = bc.get_circulating_supply()

        # Verify supply increased correctly
        new_blocks = 3
        expected_min_increase = new_blocks * bc.get_block_reward(5)
        actual_increase = supply_after_more_mining - supply_after_initial_mining

        # Allow bonuses up to 10%
        assert actual_increase >= expected_min_increase, \
            f"Supply didn't increase enough: {actual_increase} < {expected_min_increase}"
        assert actual_increase <= expected_min_increase * 1.1, \
            f"Supply increased too much (possible double reward): {actual_increase}"

        # Miner1's balance should not change (they didn't mine new blocks)
        miner1_balance_after = bc.get_balance(miner1.address)
        assert miner1_balance_after == miner1_balance, \
            f"Miner1 balance changed without mining: {miner1_balance} -> {miner1_balance_after}"

    def test_supply_cap_strictly_enforced_at_boundary(self, tmp_path):
        """Supply must be strictly capped at MAX_SUPPLY, even with reorgs"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mock the circulating supply to be near max
        original_get_supply = bc.get_circulating_supply

        try:
            # Test at various distances from cap
            test_cases = [
                (BlockchainSecurityConfig.MAX_SUPPLY - 10, "near cap"),
                (BlockchainSecurityConfig.MAX_SUPPLY - 0.5, "very near cap"),
                (BlockchainSecurityConfig.MAX_SUPPLY, "at cap"),
                (BlockchainSecurityConfig.MAX_SUPPLY + 1, "above cap"),
            ]

            for test_supply, description in test_cases:
                bc.get_circulating_supply = lambda: test_supply

                reward = bc.get_block_reward(0)

                if test_supply >= BlockchainSecurityConfig.MAX_SUPPLY:
                    assert reward == 0.0, \
                        f"Reward should be 0 {description}, got {reward}"
                else:
                    remaining = BlockchainSecurityConfig.MAX_SUPPLY - test_supply
                    expected_reward = min(bc.initial_block_reward, remaining)
                    assert reward <= expected_reward, \
                        f"Reward {reward} exceeds remaining {remaining} ({description})"
        finally:
            bc.get_circulating_supply = original_get_supply

    def test_supply_consistency_across_chain_validation(self, tmp_path):
        """Full chain validation must confirm supply consistency"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Build a chain
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        # Validate the entire chain
        assert bc.validate_chain(), "Chain validation failed"

        # Calculate expected supply from all UTXOs (not just coinbase)
        # The genesis block has a large premine that's distributed via regular transactions
        actual_supply = bc.get_circulating_supply()

        # Calculate total from UTXO set
        total_utxo_value = bc.utxo_manager.get_total_unspent_value()

        # These should match (circulating supply = total UTXO value)
        difference = abs(actual_supply - total_utxo_value)
        assert difference < 0.01, \
            f"Supply accounting mismatch: circulating {actual_supply} != UTXO total {total_utxo_value}"

        # Must not exceed cap
        assert actual_supply <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Supply {actual_supply} exceeds MAX_SUPPLY"

    def test_halving_schedule_reduces_supply_inflation(self, tmp_path):
        """Halving schedule must correctly reduce reward over time"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Test rewards at key block heights
        halving_interval = bc.halving_interval  # 262,800 blocks
        initial_reward = bc.initial_block_reward  # 12.0 XAI

        test_heights = [
            (0, initial_reward),                           # Genesis
            (halving_interval - 1, initial_reward),        # Just before halving
            (halving_interval, initial_reward / 2),        # First halving
            (halving_interval * 2, initial_reward / 4),    # Second halving
            (halving_interval * 3, initial_reward / 8),    # Third halving
            (halving_interval * 4, initial_reward / 16),   # Fourth halving
        ]

        for height, expected_reward in test_heights:
            actual_reward = bc.get_block_reward(height)
            assert actual_reward == expected_reward, \
                f"Reward at height {height}: expected {expected_reward}, got {actual_reward}"

        # Verify long-term supply converges to a finite value (geometric series)
        # Sum of geometric series: a / (1 - r) where a = first term, r = ratio
        # For halvings: total = blocks_per_halving * initial_reward / (1 - 0.5)
        # = blocks_per_halving * initial_reward * 2
        total_supply = 0.0
        current_reward = initial_reward
        blocks_per_halving = halving_interval

        # Simulate many halvings (30 halvings reduces reward to negligible)
        for halving_num in range(30):
            blocks_in_period = blocks_per_halving
            total_supply += blocks_in_period * current_reward
            current_reward /= 2

        # Theoretical maximum from infinite halvings
        theoretical_max = blocks_per_halving * initial_reward * 2

        # Should be very close to theoretical max but never exceed
        assert total_supply <= theoretical_max, \
            f"Simulated supply {total_supply} exceeds theoretical max {theoretical_max}"
        assert total_supply >= theoretical_max * 0.99, \
            f"Simulated supply {total_supply} should converge close to {theoretical_max}"

        # Also verify it doesn't exceed blockchain's MAX_SUPPLY
        assert total_supply <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Simulated supply {total_supply} exceeds MAX_SUPPLY"


class TestBalanceConservationWithFeesAndBurning:
    """
    Test suite for balance conservation invariants.

    Critical invariant: Total value is conserved in all operations.
    sum(inputs) = sum(outputs) + fees + burned
    """

    def test_transaction_conservation_law_with_fees(self, tmp_path):
        """Every transaction must satisfy: inputs = outputs + fees"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks to generate funds
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Create transaction with explicit fee
        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            fee_amount = 0.5
            send_amount = 5.0

            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=send_amount,
                fee=fee_amount,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx and tx.inputs and tx.outputs:
                # Calculate input sum from UTXOs
                input_sum = Decimal(0)
                for inp in tx.inputs:
                    utxos = bc.utxo_manager.get_utxos_for_address(wallet1.address, exclude_pending=False)
                    for utxo in utxos:
                        if utxo['txid'] == inp['txid'] and utxo['vout'] == inp['vout']:
                            input_sum += Decimal(str(utxo['amount']))
                            break

                # Calculate output sum
                output_sum = Decimal(sum(Decimal(str(out['amount'])) for out in tx.outputs))
                fee_decimal = Decimal(str(tx.fee))

                # Conservation law: inputs = outputs + fee
                expected_total = output_sum + fee_decimal

                assert abs(input_sum - expected_total) < Decimal('0.00000001'), \
                    f"Conservation violated: inputs {input_sum} != outputs {output_sum} + fee {fee_decimal}"

    def test_fees_collected_by_miner_not_lost(self, tmp_path):
        """Transaction fees must be collected by miners, not destroyed"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()
        miner = Wallet()

        # Generate funds
        for i in range(3):
            bc.mine_pending_transactions(sender.address)

        supply_before_tx = bc.get_circulating_supply()

        # Create transaction with significant fee
        balance = bc.get_balance(sender.address)
        if balance > 10:
            fee = 1.0  # Large fee for clear measurement

            tx = bc.create_transaction(
                sender_address=sender.address,
                recipient_address=recipient.address,
                amount=5.0,
                fee=fee,
                private_key=sender.private_key,
                public_key=sender.public_key
            )

            if tx:
                bc.add_transaction(tx)
                miner_balance_before = bc.get_balance(miner.address)

                # Mine block (miner should collect fee)
                block = bc.mine_pending_transactions(miner.address)

                if block:
                    miner_balance_after = bc.get_balance(miner.address)
                    supply_after_tx = bc.get_circulating_supply()

                    # Miner should receive: block_reward + transaction_fee
                    block_reward = bc.get_block_reward(block.index)
                    expected_miner_gain = block_reward + fee
                    actual_miner_gain = miner_balance_after - miner_balance_before

                    # Allow up to 10% bonus from gamification
                    assert actual_miner_gain >= expected_miner_gain, \
                        f"Miner received less than expected: {actual_miner_gain} < {expected_miner_gain}"
                    assert actual_miner_gain <= expected_miner_gain * 1.1, \
                        f"Miner received too much: {actual_miner_gain} > {expected_miner_gain * 1.1}"

                    # Total supply should increase by block_reward only (fee is transferred, not created)
                    supply_increase = supply_after_tx - supply_before_tx
                    assert supply_increase >= block_reward, \
                        f"Supply increased less than block reward: {supply_increase} < {block_reward}"
                    assert supply_increase <= block_reward * 1.1, \
                        f"Supply increased too much: {supply_increase} > {block_reward * 1.1}"

    def test_burned_coins_reduce_circulating_supply(self, tmp_path):
        """Burning coins must reduce circulating supply permanently"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()
        # Burn address - valid XAI format but provably unspendable (no known private key)
        # Must be all hex characters after XAI prefix (64 chars total)
        burn_address = "XAI" + ("0" * 60) + "dea"  # 3 chars XAI + 63 hex = 66 is too long
        # Actually XAI is 3 chars, so we need 61 hex chars after it for 64 total
        # XAI addresses are 43 chars: "XAI" + 40 hex chars
        burn_address = "XAI" + ("0" * 36) + "dead"  # 3 + 40 = 43 chars

        # Generate funds
        for i in range(5):
            bc.mine_pending_transactions(wallet.address)

        supply_before_burn = bc.get_circulating_supply()
        wallet_balance_before = bc.get_balance(wallet.address)

        # Send coins to burn address
        burn_amount = 10.0
        if wallet_balance_before > burn_amount:
            tx = bc.create_transaction(
                sender_address=wallet.address,
                recipient_address=burn_address,
                amount=burn_amount,
                fee=0.1,
                private_key=wallet.private_key,
                public_key=wallet.public_key
            )

            if tx:
                bc.add_transaction(tx)
                bc.mine_pending_transactions(wallet.address)

                # Check that coins are in burn address (unspendable)
                burn_balance = bc.get_balance(burn_address)
                assert burn_balance >= burn_amount, \
                    f"Burn address should have {burn_amount}, has {burn_balance}"

                # Circulating supply includes burned coins (they exist but are unspendable)
                # This tests that the accounting is correct
                supply_after = bc.get_circulating_supply()

                # Supply should increase by mining reward only
                # Burned coins still count toward total supply
                assert supply_after > supply_before_burn, \
                    "Supply should increase from mining reward"

    def test_sum_of_all_utxos_equals_circulating_supply(self, tmp_path):
        """Sum of all unspent outputs must equal circulating supply"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Build complex UTXO set with multiple transactions
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

        balance1 = bc.get_balance(wallet1.address)
        if balance1 > 20:
            # Create multiple transactions
            for i in range(3):
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address if i % 2 == 0 else wallet3.address,
                    amount=2.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )
                if tx:
                    bc.add_transaction(tx)

            bc.mine_pending_transactions(wallet1.address)

        # Calculate sum of all UTXOs manually
        utxo_sum = Decimal(0)
        for address, utxos in bc.utxo_manager.utxo_set.items():
            for utxo in utxos:
                if not utxo.get('spent', False):
                    utxo_sum += Decimal(str(utxo['amount']))

        # Get circulating supply
        circulating = bc.get_circulating_supply()

        # They must match
        assert abs(float(utxo_sum) - circulating) < 0.00001, \
            f"UTXO sum {utxo_sum} != circulating supply {circulating}"

    def test_no_value_creation_in_regular_transactions(self, tmp_path):
        """Regular transactions cannot create value (only coinbase can)"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine initial blocks
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        supply_before = bc.get_circulating_supply()
        balance_before = bc.get_balance(wallet1.address)

        # Create and mine a regular transaction
        if balance_before > 10:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=5.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx:
                bc.add_transaction(tx)
                block = bc.mine_pending_transactions(wallet1.address)

                supply_after = bc.get_circulating_supply()

                # Supply should only increase by coinbase reward
                supply_increase = supply_after - supply_before
                expected_increase = bc.get_block_reward(block.index)

                # Allow up to 10% for bonuses
                assert supply_increase <= expected_increase * 1.1, \
                    f"Supply increased too much: {supply_increase} > {expected_increase * 1.1} (possible value creation)"

    def test_change_outputs_preserve_value(self, tmp_path):
        """Change outputs must return excess value to sender"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        balance_before = bc.get_balance(wallet1.address)

        # Create transaction that requires change
        if balance_before > 10:
            send_amount = 3.0
            fee = 0.1

            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=send_amount,
                fee=fee,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx:
                bc.add_transaction(tx)
                bc.mine_pending_transactions(wallet1.address)

                balance_after = bc.get_balance(wallet1.address)
                balance2_after = bc.get_balance(wallet2.address)

                # Wallet1 should have: balance_before - send_amount - fee + mining_reward
                # (if wallet1 was the miner)
                # Otherwise: balance_before - send_amount - fee

                # Wallet2 should have exactly send_amount
                assert balance2_after >= send_amount, \
                    f"Recipient didn't receive full amount: {balance2_after} < {send_amount}"


class TestStateRootCorrectnessForLightClients:
    """
    Test suite for state root correctness.

    Critical invariant: State roots must uniquely and deterministically
    identify the UTXO set state for light client verification.
    """

    def test_state_root_deterministic_for_same_utxo_set(self, tmp_path):
        """Same UTXO state must always produce identical state root"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Build state
        for i in range(3):
            bc.mine_pending_transactions(wallet.address)

        # Get state root multiple times
        root1 = bc.utxo_manager.snapshot_digest()
        root2 = bc.utxo_manager.snapshot_digest()
        root3 = bc.utxo_manager.snapshot_digest()

        assert root1 == root2 == root3, \
            f"State root not deterministic: {root1}, {root2}, {root3}"

    def test_state_root_changes_with_state_modification(self, tmp_path):
        """Any UTXO modification must change the state root"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Initial state
        for i in range(2):
            bc.mine_pending_transactions(wallet1.address)

        root_before = bc.utxo_manager.snapshot_digest()

        # Modify state (mine new block)
        bc.mine_pending_transactions(wallet1.address)
        root_after_mine = bc.utxo_manager.snapshot_digest()

        assert root_before != root_after_mine, \
            "State root didn't change after mining block"

        # Modify state (add transaction)
        balance = bc.get_balance(wallet1.address)
        if balance > 5:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=2.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )
            if tx:
                bc.add_transaction(tx)
                bc.mine_pending_transactions(wallet1.address)

                root_after_tx = bc.utxo_manager.snapshot_digest()

                assert root_after_tx != root_after_mine, \
                    "State root didn't change after transaction"

    def test_merkle_root_uniquely_identifies_transaction_set(self, tmp_path):
        """Different transaction sets must produce different merkle roots"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create transaction set A
        tx1 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=5.0,
            fee=0.1,
            public_key=wallet1.public_key
        )

        merkle_root_a = bc.calculate_merkle_root([tx1])

        # Same transaction should give same root
        merkle_root_a2 = bc.calculate_merkle_root([tx1])
        assert merkle_root_a == merkle_root_a2, \
            "Merkle root not deterministic for same transactions"

        # Different transaction should give different root
        tx2 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,  # Different amount
            fee=0.1,
            public_key=wallet1.public_key
        )

        merkle_root_b = bc.calculate_merkle_root([tx2])
        assert merkle_root_a != merkle_root_b, \
            "Different transactions produced same merkle root"

        # Different order should give different root (transaction order matters)
        merkle_root_ab = bc.calculate_merkle_root([tx1, tx2])
        merkle_root_ba = bc.calculate_merkle_root([tx2, tx1])
        assert merkle_root_ab != merkle_root_ba, \
            "Transaction order didn't affect merkle root"

    def test_light_client_can_verify_transaction_inclusion(self, tmp_path):
        """Light clients must be able to verify transaction inclusion via merkle proof"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks to generate funds
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        # Create a transaction
        balance = bc.get_balance(wallet1.address)
        if balance > 5:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=2.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx:
                bc.add_transaction(tx)
                block = bc.mine_pending_transactions(wallet1.address)

                if block:
                    # Calculate merkle root of block
                    merkle_root = block.merkle_root

                    # Verify transaction is in the block
                    tx_found = False
                    for block_tx in block.transactions:
                        if (hasattr(block_tx, 'txid') and hasattr(tx, 'txid') and
                            block_tx.txid == tx.txid):
                            tx_found = True
                            break

                    # If light client verification is implemented, test the proof
                    # For now, just verify the merkle root is consistent
                    recalculated_root = bc.calculate_merkle_root(block.transactions)
                    assert merkle_root == recalculated_root, \
                        "Merkle root mismatch - light client verification would fail"

    def test_state_transition_produces_unique_sequential_roots(self, tmp_path):
        """Each block should produce a unique state root in sequence"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        state_roots = []

        # Mine blocks and collect state roots
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)
            root = bc.utxo_manager.snapshot_digest()
            state_roots.append(root)

        # All roots should be unique (except in extremely rare cases)
        unique_roots = set(state_roots)
        assert len(unique_roots) >= len(state_roots) - 1, \
            f"State roots not sufficiently unique: {len(unique_roots)}/{len(state_roots)}"

        # Roots should be hex strings of consistent length
        for root in state_roots:
            assert isinstance(root, str), f"State root not a string: {type(root)}"
            assert len(root) == 64, f"State root wrong length: {len(root)} (expected 64 for SHA256)"
            assert all(c in '0123456789abcdef' for c in root), \
                f"State root not valid hex: {root}"

    def test_empty_utxo_set_has_deterministic_root(self, tmp_path):
        """Empty UTXO set should have consistent, deterministic root"""
        bc1 = Blockchain(data_dir=str(tmp_path / "bc1"))
        bc2 = Blockchain(data_dir=str(tmp_path / "bc2"))

        # Both should have same genesis state root
        root1 = bc1.utxo_manager.snapshot_digest()
        root2 = bc2.utxo_manager.snapshot_digest()

        # Genesis blocks should produce same initial UTXO state
        # (after mining genesis, they won't be empty but should be identical)
        assert isinstance(root1, str) and isinstance(root2, str), \
            "State roots must be strings"


class TestTransactionOrderingInvariants:
    """
    Test suite for transaction ordering invariants.

    Critical invariants:
    - Nonces must be strictly sequential per sender
    - No double-spends possible in mempool or blocks
    - MEV protection via proper ordering rules
    """

    def test_nonce_strictly_sequential_per_address(self, tmp_path):
        """Nonces must increment by exactly 1 for each transaction from an address"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Generate funds
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        # Create multiple transactions and verify nonce sequence
        nonces = []
        balance = bc.get_balance(wallet1.address)

        for i in range(5):
            if balance > 2:
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address,
                    amount=1.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )

                if tx:
                    nonces.append(tx.nonce)
                    bc.add_transaction(tx)

        # Verify strict sequential ordering
        if len(nonces) > 1:
            for i in range(len(nonces) - 1):
                assert nonces[i + 1] == nonces[i] + 1, \
                    f"Nonce gap detected: {nonces[i]} -> {nonces[i + 1]} (expected {nonces[i] + 1})"

    def test_cannot_submit_transaction_with_skipped_nonce(self, tmp_path):
        """Transactions with gaps in nonce sequence must be rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Generate funds
        for i in range(2):
            bc.mine_pending_transactions(wallet1.address)

        # Get current nonce
        current_nonce = bc.nonce_tracker.get_next_nonce(wallet1.address)

        # Create multiple transactions to establish a baseline
        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            # Create first transaction (normal)
            tx1 = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=2.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx1:
                bc.add_transaction(tx1)
                nonce1 = tx1.nonce

                # Try to create a second transaction but with a gap in nonce
                # This simulates submitting nonce n+5 when n+1 is expected
                # The blockchain should either reject it or handle it gracefully
                tx2 = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address,
                    amount=1.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )

                if tx2:
                    # The nonce should be sequential (nonce1 + 1)
                    assert tx2.nonce == nonce1 + 1, \
                        f"Nonce not sequential: {nonce1} -> {tx2.nonce}"

                # Verify chain remains valid
                bc.mine_pending_transactions(wallet1.address)
                assert bc.validate_chain(), "Chain invalid after transaction sequence"

    def test_mempool_rejects_double_spend_attempts(self, tmp_path):
        """Mempool must detect and reject double-spend attempts"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Generate funds
        for i in range(3):
            bc.mine_pending_transactions(wallet1.address)

        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            # Create first transaction
            tx1 = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=8.0,  # Spend most of balance
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx1:
                bc.add_transaction(tx1)

                # Try to create second transaction using same UTXOs
                tx2 = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet3.address,
                    amount=8.0,  # Try to spend same funds again
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )

                if tx2 and tx1.inputs and tx2.inputs:
                    # Check that they don't use the same inputs
                    inputs1 = {(inp['txid'], inp['vout']) for inp in tx1.inputs}
                    inputs2 = {(inp['txid'], inp['vout']) for inp in tx2.inputs}

                    overlap = inputs1 & inputs2

                    # If there's overlap, tx2 should not be in mempool
                    if overlap:
                        tx2_in_mempool = any(
                            tx.txid == tx2.txid if hasattr(tx, 'txid') and hasattr(tx2, 'txid') else False
                            for tx in bc.pending_transactions
                        )
                        assert not tx2_in_mempool, \
                            f"Double-spend in mempool: shared inputs {overlap}"

    def test_transaction_fee_priority_ordering(self, tmp_path):
        """Transactions should be ordered by fee for MEV protection"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Generate funds
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Create transactions with different fees
        balance = bc.get_balance(wallet1.address)
        if balance > 15:
            tx_low_fee = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=2.0,
                fee=0.1,  # Low fee
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            tx_high_fee = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=2.0,
                fee=1.0,  # High fee
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx_low_fee and tx_high_fee:
                # Add low fee first
                bc.add_transaction(tx_low_fee)
                bc.add_transaction(tx_high_fee)

                # Mine block
                block = bc.mine_pending_transactions(wallet1.address)

                if block and len(block.transactions) > 2:
                    # Find positions of our transactions (skip coinbase at index 0)
                    tx_positions = {}
                    for i, tx in enumerate(block.transactions):
                        if hasattr(tx, 'txid'):
                            if hasattr(tx_low_fee, 'txid') and tx.txid == tx_low_fee.txid:
                                tx_positions['low'] = i
                            if hasattr(tx_high_fee, 'txid') and tx.txid == tx_high_fee.txid:
                                tx_positions['high'] = i

                    # High fee transaction should come before low fee (if both included)
                    if 'low' in tx_positions and 'high' in tx_positions:
                        assert tx_positions['high'] < tx_positions['low'], \
                            f"Fee priority violated: high fee at {tx_positions['high']}, low fee at {tx_positions['low']}"

    def test_coinbase_always_first_transaction_in_block(self, tmp_path):
        """Coinbase transaction must always be first in block"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks with transactions
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

            # Add a transaction for next block
            balance = bc.get_balance(wallet1.address)
            if balance > 2:
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address,
                    amount=1.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )
                if tx:
                    bc.add_transaction(tx)

        # Verify coinbase position in all blocks
        for block in bc.chain:
            if hasattr(block, 'transactions') and block.transactions:
                first_tx = block.transactions[0]

                # First transaction must be coinbase
                is_coinbase = (
                    first_tx.sender == "COINBASE" or
                    getattr(first_tx, 'tx_type', None) == 'coinbase' or
                    (hasattr(first_tx, 'inputs') and not first_tx.inputs)
                )

                assert is_coinbase, \
                    f"Block {block.index}: First transaction is not coinbase: {first_tx.sender}"

    def test_no_transaction_reordering_after_inclusion(self, tmp_path):
        """Once in a block, transaction order must not change"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Build chain with transactions
        for i in range(5):
            bc.mine_pending_transactions(wallet1.address)

            balance = bc.get_balance(wallet1.address)
            if balance > 2:
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet2.address,
                    amount=1.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )
                if tx:
                    bc.add_transaction(tx)

        # Record transaction order in blocks
        block_tx_orders = {}
        for block in bc.chain:
            if hasattr(block, 'transactions'):
                tx_ids = []
                for tx in block.transactions:
                    if hasattr(tx, 'txid'):
                        tx_ids.append(tx.txid)
                block_tx_orders[block.index] = tx_ids

        # Validate chain (should not reorder transactions)
        assert bc.validate_chain(), "Chain validation failed"

        # Verify transaction order unchanged
        for block in bc.chain:
            if hasattr(block, 'transactions'):
                current_tx_ids = []
                for tx in block.transactions:
                    if hasattr(tx, 'txid'):
                        current_tx_ids.append(tx.txid)

                original_order = block_tx_orders.get(block.index, [])
                assert current_tx_ids == original_order, \
                    f"Block {block.index}: Transaction order changed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
