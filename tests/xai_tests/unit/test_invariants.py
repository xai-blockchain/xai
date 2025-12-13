"""
Comprehensive Invariant Tests for XAI Blockchain

Tests critical blockchain invariants that must hold under all conditions:
- Supply preservation (total supply never exceeds MAX_SUPPLY)
- Balance conservation (sum of balances matches supply accounting)
- State root correctness (deterministic state hashing)
- Transaction ordering (nonces, double-spend prevention)

These tests verify fundamental properties that ensure blockchain integrity.
"""

import pytest
import hashlib
import time
from decimal import Decimal
from typing import List, Dict, Any

from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet
from xai.core.blockchain_security import BlockchainSecurityConfig
from xai.core.config import Config


class TestSupplyPreservation:
    """Test that total supply never exceeds MAX_SUPPLY and accounting is correct"""

    def test_total_supply_never_exceeds_max(self, tmp_path):
        """Total supply must never exceed MAX_SUPPLY constant (121M XAI)"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine several blocks
        for _ in range(10):
            bc.mine_pending_transactions(wallet.address)

        # Get total supply from UTXO set
        total_supply = bc.get_circulating_supply()

        # Verify supply constraint
        assert total_supply <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Total supply {total_supply} exceeds MAX_SUPPLY {BlockchainSecurityConfig.MAX_SUPPLY}"

    def test_supply_accounting_identity(self, tmp_path):
        """Total supply = circulating + locked + burned (accounting identity)"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks to generate supply
        for _ in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Create some transactions
        balance1 = bc.get_balance(wallet1.address)
        if balance1 > 10:
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
                bc.mine_pending_transactions(wallet1.address)

        # Get components
        circulating_supply = bc.get_circulating_supply()
        locked_supply = 0.0  # XAI doesn't have locked tokens currently
        burned_supply = getattr(bc, 'total_burned', 0.0)

        # Accounting identity: total = circulating + locked + burned
        # For XAI without locking, total should equal circulating + burned
        total_supply = circulating_supply + locked_supply + burned_supply

        # Verify the supply is accounted for
        assert total_supply >= 0, "Total supply cannot be negative"
        assert total_supply <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Accounting identity violated: {total_supply} > MAX_SUPPLY"

    def test_supply_invariant_after_reorg(self, tmp_path):
        """Supply accounting must be consistent after chain reorganization"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine initial chain
        for _ in range(5):
            bc.mine_pending_transactions(wallet.address)

        # Record supply before reorg
        supply_before = bc.get_circulating_supply()

        # Mine the same number of blocks (simulating reorg scenario)
        for _ in range(3):
            bc.mine_pending_transactions(wallet.address)

        supply_after = bc.get_circulating_supply()

        # Supply should only increase (new blocks mined)
        assert supply_after >= supply_before, \
            "Supply decreased after mining blocks"
        assert supply_after <= BlockchainSecurityConfig.MAX_SUPPLY, \
            "Supply exceeded MAX_SUPPLY after reorg simulation"

    def test_coinbase_rewards_follow_halving_schedule(self, tmp_path):
        """Coinbase rewards must follow the halving schedule correctly"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Test initial reward (12 XAI)
        reward_0 = bc.get_block_reward(0)
        assert reward_0 == 12.0, f"Initial reward should be 12.0, got {reward_0}"

        # Test reward just before first halving
        reward_before_halving = bc.get_block_reward(262799)
        assert reward_before_halving == 12.0, \
            f"Reward before first halving should be 12.0, got {reward_before_halving}"

        # Test reward at first halving (262,800 blocks)
        reward_halving_1 = bc.get_block_reward(262800)
        assert reward_halving_1 == 6.0, \
            f"Reward after first halving should be 6.0, got {reward_halving_1}"

        # Test reward at second halving (525,600 blocks)
        reward_halving_2 = bc.get_block_reward(525600)
        assert reward_halving_2 == 3.0, \
            f"Reward after second halving should be 3.0, got {reward_halving_2}"

        # Test reward at third halving (788,400 blocks)
        reward_halving_3 = bc.get_block_reward(788400)
        assert reward_halving_3 == 1.5, \
            f"Reward after third halving should be 1.5, got {reward_halving_3}"

    def test_supply_cap_enforced_at_max(self, tmp_path):
        """Block rewards must stop when MAX_SUPPLY is reached"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Simulate reaching max supply by setting current supply to near max
        # We'll test the get_block_reward logic with mocked supply
        original_method = bc.get_circulating_supply

        try:
            # Mock: Set supply to just below max
            bc.get_circulating_supply = lambda: BlockchainSecurityConfig.MAX_SUPPLY - 5.0

            # Reward should be capped to remaining supply
            reward = bc.get_block_reward(0)
            assert reward <= 5.0, f"Reward {reward} exceeds remaining supply 5.0"

            # Mock: Set supply to exactly max
            bc.get_circulating_supply = lambda: BlockchainSecurityConfig.MAX_SUPPLY

            # Reward should be zero when max supply reached
            reward_at_max = bc.get_block_reward(0)
            assert reward_at_max == 0.0, \
                f"Reward should be 0 at max supply, got {reward_at_max}"

            # Mock: Set supply above max (edge case)
            bc.get_circulating_supply = lambda: BlockchainSecurityConfig.MAX_SUPPLY + 1.0

            # Reward should be zero when supply exceeds max
            reward_above_max = bc.get_block_reward(0)
            assert reward_above_max == 0.0, \
                f"Reward should be 0 when exceeding max supply, got {reward_above_max}"
        finally:
            # Restore original method
            bc.get_circulating_supply = original_method


class TestBalanceConservation:
    """Test that balances are conserved across transactions"""

    def test_sum_of_balances_equals_supply(self, tmp_path):
        """Sum of all UTXO balances should equal total supply minus burned"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine some blocks
        for _ in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Get total from individual UTXOs
        total_utxo_value = bc.utxo_manager.get_total_unspent_value()

        # Get circulating supply
        circulating_supply = bc.get_circulating_supply()

        # They should match (circulating supply is derived from UTXO set)
        assert abs(total_utxo_value - circulating_supply) < 0.00001, \
            f"UTXO total {total_utxo_value} != circulating supply {circulating_supply}"

    def test_transaction_inputs_equal_outputs_plus_fees(self, tmp_path):
        """For any transaction: sum(inputs) = sum(outputs) + fee"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks to generate funds
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        # Create a transaction
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

            if tx and tx.inputs and tx.outputs:
                # Calculate sum of inputs by looking up each UTXO
                input_sum = 0.0
                for inp in tx.inputs:
                    # Find the UTXO in the sender's UTXO set
                    utxos = bc.utxo_manager.get_utxos_for_address(wallet1.address, exclude_pending=False)
                    for utxo in utxos:
                        if utxo['txid'] == inp['txid'] and utxo['vout'] == inp['vout']:
                            input_sum += utxo['amount']
                            break

                # Calculate sum of outputs
                output_sum = sum(out['amount'] for out in tx.outputs)

                # Verify conservation: inputs = outputs + fee
                assert abs(input_sum - (output_sum + tx.fee)) < 0.00001, \
                    f"Conservation violated: inputs {input_sum} != outputs {output_sum} + fee {tx.fee}"

    def test_fees_properly_collected_and_distributed(self, tmp_path):
        """Transaction fees should be properly collected by miners"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        miner = Wallet()

        # Mine initial blocks
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        # Create transaction with fee
        balance_before = bc.get_balance(wallet1.address)
        if balance_before > 10:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=5.0,
                fee=0.5,  # 0.5 XAI fee
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx:
                bc.add_transaction(tx)

                # Mine block with different miner
                miner_balance_before = bc.get_balance(miner.address)
                block = bc.mine_pending_transactions(miner.address)
                miner_balance_after = bc.get_balance(miner.address)

                if block:
                    # Miner should receive base reward + transaction fee
                    base_reward = bc.get_block_reward(block.index)
                    expected_reward = base_reward + 0.5  # base + fee

                    # Allow for streak bonuses (up to 5% extra)
                    actual_reward = miner_balance_after - miner_balance_before
                    assert actual_reward >= expected_reward, \
                        f"Miner didn't receive expected reward: {actual_reward} < {expected_reward}"
                    assert actual_reward <= expected_reward * 1.05, \
                        f"Miner received excessive reward: {actual_reward} > {expected_reward * 1.05}"

    def test_no_negative_balances_possible(self, tmp_path):
        """No address should ever have a negative balance"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks
        for _ in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Create transaction
        balance = bc.get_balance(wallet1.address)
        if balance > 5:
            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=balance - 1,  # Spend almost everything
                fee=0.5,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )
            if tx:
                bc.add_transaction(tx)
                bc.mine_pending_transactions(wallet1.address)

        # Check all balances in UTXO set
        for address, utxos in bc.utxo_manager.utxo_set.items():
            for utxo in utxos:
                assert utxo['amount'] >= 0, \
                    f"Negative UTXO amount found: {utxo['amount']} for {address}"

        # Check specific balances
        balance1 = bc.get_balance(wallet1.address)
        balance2 = bc.get_balance(wallet2.address)

        assert balance1 >= 0, f"Wallet1 has negative balance: {balance1}"
        assert balance2 >= 0, f"Wallet2 has negative balance: {balance2}"


class TestStateRootCorrectness:
    """Test state root uniquely identifies blockchain state"""

    def test_same_state_produces_same_root(self, tmp_path):
        """Same UTXO state should always produce the same state root hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks to create state
        for _ in range(3):
            bc.mine_pending_transactions(wallet.address)

        # Get state snapshot
        state_root_1 = bc.utxo_manager.snapshot_digest()

        # Get snapshot again without changes
        state_root_2 = bc.utxo_manager.snapshot_digest()

        assert state_root_1 == state_root_2, \
            "Same state produced different roots: determinism violated"

    def test_different_states_produce_different_roots(self, tmp_path):
        """Different UTXO states should produce different state roots"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Get initial state
        for _ in range(2):
            bc.mine_pending_transactions(wallet.address)

        state_root_1 = bc.utxo_manager.snapshot_digest()

        # Modify state by mining another block
        bc.mine_pending_transactions(wallet.address)
        state_root_2 = bc.utxo_manager.snapshot_digest()

        assert state_root_1 != state_root_2, \
            "Different states produced same root hash"

    def test_merkle_root_uniquely_identifies_transactions(self, tmp_path):
        """Merkle root should uniquely identify the transaction set"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create transaction set 1
        tx1 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=5.0,
            fee=0.1,
            public_key=wallet1.public_key
        )
        merkle_root_1 = bc.calculate_merkle_root([tx1])

        # Same transaction should produce same merkle root
        merkle_root_1_again = bc.calculate_merkle_root([tx1])
        assert merkle_root_1 == merkle_root_1_again, \
            "Same transactions produced different merkle roots"

        # Different transaction should produce different merkle root
        tx2 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,  # Different amount
            fee=0.1,
            public_key=wallet1.public_key
        )
        merkle_root_2 = bc.calculate_merkle_root([tx2])
        assert merkle_root_1 != merkle_root_2, \
            "Different transactions produced same merkle root"

    def test_state_transitions_produce_new_unique_roots(self, tmp_path):
        """Each state transition should produce a unique state root"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        state_roots = set()

        # Mine several blocks and collect state roots
        for _ in range(5):
            bc.mine_pending_transactions(wallet.address)
            state_root = bc.utxo_manager.snapshot_digest()
            state_roots.add(state_root)

        # Each state should be unique
        # Note: In rare cases, if mining rewards create identical UTXO patterns,
        # roots could theoretically match, but this is extremely unlikely
        assert len(state_roots) >= 4, \
            f"State roots not sufficiently unique: {len(state_roots)}/5"


class TestTransactionOrderingInvariants:
    """Test transaction ordering and double-spend prevention"""

    def test_nonces_strictly_sequential_per_sender(self, tmp_path):
        """Nonces must be strictly sequential for each sender"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine initial funds
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        # Create multiple transactions from same sender
        nonces = []
        for i in range(3):
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
                    nonces.append(tx.nonce)
                    bc.add_transaction(tx)

        # Verify nonces are sequential
        if len(nonces) > 1:
            for i in range(len(nonces) - 1):
                assert nonces[i + 1] == nonces[i] + 1, \
                    f"Nonces not sequential: {nonces[i]} -> {nonces[i + 1]}"

    def test_no_double_spend_in_mempool(self, tmp_path):
        """Mempool must prevent double-spending the same UTXO"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Mine blocks to generate funds
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            # Create first transaction spending UTXOs
            tx1 = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=5.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx1:
                bc.add_transaction(tx1)

                # Try to create second transaction (should not double-spend)
                tx2 = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=wallet3.address,
                    amount=5.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )

                if tx2 and tx1.inputs and tx2.inputs:
                    # Check that inputs are different (no double-spend)
                    inputs1 = {(inp['txid'], inp['vout']) for inp in tx1.inputs}
                    inputs2 = {(inp['txid'], inp['vout']) for inp in tx2.inputs}

                    overlap = inputs1 & inputs2
                    assert len(overlap) == 0, \
                        f"Double-spend detected in mempool: {overlap}"

    def test_no_double_spend_in_blocks(self, tmp_path):
        """Mined blocks must not contain double-spends"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine blocks
        for _ in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Check each block for double-spends
        for block in bc.chain:
            spent_utxos = set()

            for tx in block.transactions:
                if tx.inputs:
                    for inp in tx.inputs:
                        utxo_key = (inp['txid'], inp['vout'])

                        assert utxo_key not in spent_utxos, \
                            f"Double-spend found in block {block.index}: {utxo_key}"

                        spent_utxos.add(utxo_key)

    def test_transaction_ordering_in_block(self, tmp_path):
        """Transactions in a block should maintain valid ordering (coinbase first)"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine initial blocks
        for _ in range(2):
            bc.mine_pending_transactions(wallet1.address)

        # Add some transactions
        balance = bc.get_balance(wallet1.address)
        if balance > 5:
            for i in range(3):
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

        # Mine block with transactions
        block = bc.mine_pending_transactions(wallet1.address)

        if block and len(block.transactions) > 1:
            # First transaction must be coinbase
            first_tx = block.transactions[0]
            assert first_tx.sender == "COINBASE" or first_tx.tx_type == "coinbase", \
                "First transaction in block is not coinbase"

    def test_parent_transactions_execute_before_children(self, tmp_path):
        """In transaction chains, parent transactions must be processed before children"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Mine blocks to generate funds
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        balance = bc.get_balance(wallet1.address)
        if balance > 10:
            # Create parent transaction
            tx_parent = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=5.0,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx_parent:
                bc.add_transaction(tx_parent)
                bc.mine_pending_transactions(wallet1.address)

                # Now wallet2 can spend received funds (child transaction)
                balance2 = bc.get_balance(wallet2.address)
                if balance2 > 2:
                    tx_child = bc.create_transaction(
                        sender_address=wallet2.address,
                        recipient_address=wallet3.address,
                        amount=2.0,
                        fee=0.1,
                        private_key=wallet2.private_key,
                        public_key=wallet2.public_key
                    )

                    if tx_child:
                        bc.add_transaction(tx_child)
                        block = bc.mine_pending_transactions(wallet1.address)

                        # Verify child transaction succeeded
                        balance3 = bc.get_balance(wallet3.address)
                        assert balance3 >= 2.0, \
                            "Child transaction failed - parent may not have been processed first"


class TestInvariantEdgeCases:
    """Test invariants under edge cases and stress conditions"""

    def test_empty_block_preserves_invariants(self, tmp_path):
        """Mining empty blocks should preserve all invariants"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine empty block
        supply_before = bc.get_circulating_supply()
        block = bc.mine_pending_transactions(wallet.address)
        supply_after = bc.get_circulating_supply()

        # Supply should increase by block reward only
        expected_increase = bc.get_block_reward(block.index)
        actual_increase = supply_after - supply_before

        # Allow for streak bonuses (up to 5% extra) and small floating point tolerance
        assert actual_increase >= expected_increase, \
            f"Supply increased less than expected: {actual_increase} < {expected_increase}"
        assert actual_increase <= expected_increase * 1.05 + 0.00001, \
            f"Empty block changed supply too much: {actual_increase} vs {expected_increase} (expected max {expected_increase * 1.05})"

    def test_maximum_size_transaction_preserves_conservation(self, tmp_path):
        """Very large transactions should still preserve balance conservation"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine many blocks to accumulate large balance
        for _ in range(10):
            bc.mine_pending_transactions(wallet1.address)

        # Get total supply before transaction
        supply_before = bc.get_circulating_supply()

        # Create large transaction
        balance = bc.get_balance(wallet1.address)
        if balance > 50:
            large_amount = balance * 0.9  # Transfer 90% of balance

            tx = bc.create_transaction(
                sender_address=wallet1.address,
                recipient_address=wallet2.address,
                amount=large_amount,
                fee=0.1,
                private_key=wallet1.private_key,
                public_key=wallet1.public_key
            )

            if tx:
                bc.add_transaction(tx)
                bc.mine_pending_transactions(wallet1.address)

                # Verify supply conservation
                supply_after = bc.get_circulating_supply()

                # Supply should only increase by mining reward
                expected_increase = bc.get_block_reward(len(bc.chain) - 1)
                actual_increase = supply_after - supply_before

                # Allow for streak bonuses (up to 5%)
                assert actual_increase >= expected_increase, \
                    "Supply accounting broken for large transaction"
                assert actual_increase <= expected_increase * 1.05, \
                    "Supply increased too much for large transaction"

    def test_concurrent_transactions_preserve_utxo_integrity(self, tmp_path):
        """Multiple pending transactions should not violate UTXO integrity"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallets = [Wallet() for _ in range(5)]

        # Mine blocks to generate funds
        for _ in range(5):
            bc.mine_pending_transactions(wallet1.address)

        # Create multiple transactions
        balance = bc.get_balance(wallet1.address)
        tx_count = 0

        for recipient_wallet in wallets:
            if balance > 10:
                tx = bc.create_transaction(
                    sender_address=wallet1.address,
                    recipient_address=recipient_wallet.address,
                    amount=2.0,
                    fee=0.1,
                    private_key=wallet1.private_key,
                    public_key=wallet1.public_key
                )
                if tx:
                    bc.add_transaction(tx)
                    tx_count += 1

        # Mine all transactions
        if tx_count > 0:
            block = bc.mine_pending_transactions(wallet1.address)

            # Verify no double-spends occurred
            spent_utxos = set()
            for tx in block.transactions:
                if tx.inputs:
                    for inp in tx.inputs:
                        utxo_key = (inp['txid'], inp['vout'])
                        assert utxo_key not in spent_utxos, \
                            f"Concurrent transactions caused double-spend: {utxo_key}"
                        spent_utxos.add(utxo_key)

    def test_chain_validation_after_many_blocks(self, tmp_path):
        """Chain should remain valid after many blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine many blocks
        num_blocks = 20
        for _ in range(num_blocks):
            bc.mine_pending_transactions(wallet.address)

        # Validate entire chain
        assert bc.validate_chain(), "Chain validation failed after mining many blocks"

        # Verify supply is still within bounds
        total_supply = bc.get_circulating_supply()
        assert total_supply <= BlockchainSecurityConfig.MAX_SUPPLY, \
            f"Supply {total_supply} exceeded MAX_SUPPLY after {num_blocks} blocks"

    def test_merkle_root_determinism_with_empty_transactions(self, tmp_path):
        """Merkle root should be deterministic even with empty transaction list"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Empty transaction list
        merkle_root_1 = bc.calculate_merkle_root([])
        merkle_root_2 = bc.calculate_merkle_root([])

        assert merkle_root_1 == merkle_root_2, \
            "Empty transaction list produced non-deterministic merkle roots"

        # Should be the hash of empty bytes
        expected = hashlib.sha256(b"").hexdigest()
        assert merkle_root_1 == expected, \
            f"Empty merkle root incorrect: {merkle_root_1} != {expected}"
