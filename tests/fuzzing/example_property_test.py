from __future__ import annotations

"""
Property-Based Testing Examples for XAI Blockchain

This module demonstrates property-based testing using Hypothesis to validate
invariants and properties that should always hold in the XAI Blockchain system.

Property-based testing differs from example-based testing by:
1. Testing general properties instead of specific examples
2. Automatically generating diverse test cases
3. Shrinking failures to minimal reproducible examples
4. Discovering edge cases humans might miss

Test Categories:
1. Cryptographic Properties - Determinism, reversibility
2. Transaction Properties - Conservation, validation
3. Blockchain Properties - Consensus, immutability
4. Arithmetic Properties - Overflow protection, precision

Dependencies:
- hypothesis: Property-based testing framework

Usage:
    pytest tests/fuzzing/example_property_test.py -v
"""

import hashlib
from decimal import Decimal

import pytest
from hypothesis import assume, given, strategies as st, settings, Phase, example
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

# ============================================================================
# CUSTOM STRATEGIES
# ============================================================================

# Strategy for valid blockchain addresses (simplified)
@st.composite
def blockchain_address(draw):
    """Generate valid blockchain addresses."""
    return '0x' + ''.join(draw(st.lists(
        st.sampled_from('0123456789abcdef'),
        min_size=40,
        max_size=40
    )))

# Strategy for valid amounts (positive integers)
valid_amount = st.integers(min_value=1, max_value=2**32 - 1)

# Strategy for wallet balances
valid_balance = st.integers(min_value=0, max_value=2**64 - 1)

# ============================================================================
# CRYPTOGRAPHIC PROPERTIES
# ============================================================================

class TestCryptographicProperties:
    """
    Property-based tests for cryptographic functions.

    These tests verify fundamental properties that cryptographic
    operations must satisfy.
    """

    @given(st.binary(min_size=1, max_size=10000))
    def test_hash_determinism(self, data: bytes):
        """
        Property: Hash function is deterministic.

        The same input should always produce the same hash output.
        """
        hash1 = hashlib.sha256(data).hexdigest()
        hash2 = hashlib.sha256(data).hexdigest()

        assert hash1 == hash2, "Hash function must be deterministic"

    @given(st.binary(min_size=1, max_size=10000))
    def test_hash_length_consistency(self, data: bytes):
        """
        Property: Hash output length is constant.

        SHA256 should always produce 256-bit (64 hex character) output
        regardless of input size.
        """
        hash_output = hashlib.sha256(data).hexdigest()

        assert len(hash_output) == 64, "SHA256 hash must be 64 hex characters"
        assert all(c in '0123456789abcdef' for c in hash_output)

    @given(st.binary(min_size=1, max_size=1000), st.binary(min_size=1, max_size=1000))
    def test_hash_collision_resistance(self, data1: bytes, data2: bytes):
        """
        Property: Different inputs produce different hashes (collision resistance).

        While SHA256 collisions theoretically exist, they should not be
        found in random testing.
        """
        assume(data1 != data2)  # Only test different inputs

        hash1 = hashlib.sha256(data1).hexdigest()
        hash2 = hashlib.sha256(data2).hexdigest()

        assert hash1 != hash2, "Different inputs should produce different hashes"

    @given(st.binary(min_size=32, max_size=32))
    @example(b'\x00' * 32)  # Test specific edge case
    @example(b'\xff' * 32)  # Test specific edge case
    def test_signature_key_length(self, private_key: bytes):
        """
        Property: Private keys have correct length.

        Private keys should be exactly 32 bytes (256 bits).
        """
        # Verify private key is correct length
        assert len(private_key) == 32

        # Simulate key validation
        is_valid = self._mock_validate_private_key(private_key)
        assert isinstance(is_valid, bool)

    @given(
        st.binary(min_size=1, max_size=1000),
        st.binary(min_size=32, max_size=32)
    )
    def test_signature_verification_roundtrip(self, message: bytes, private_key: bytes):
        """
        Property: Sign -> Verify roundtrip always succeeds with correct key.

        If we sign a message and then verify with the corresponding public key,
        verification should always succeed.
        """
        # Mock implementation
        signature = self._mock_sign(message, private_key)
        public_key = self._mock_derive_public_key(private_key)

        # Verification should succeed
        is_valid = self._mock_verify(message, signature, public_key)
        assert is_valid is True

    @given(
        st.binary(min_size=1, max_size=1000),
        st.binary(min_size=32, max_size=32),
        st.binary(min_size=32, max_size=32)
    )
    def test_signature_verification_wrong_key_fails(
        self, message: bytes, private_key: bytes, wrong_private_key: bytes
    ):
        """
        Property: Signature verification fails with wrong key.

        A signature created with one key should not verify with a different key.
        """
        assume(private_key != wrong_private_key)

        signature = self._mock_sign(message, private_key)
        wrong_public_key = self._mock_derive_public_key(wrong_private_key)

        # Verification should fail
        is_valid = self._mock_verify(message, signature, wrong_public_key)
        assert is_valid is False

    # Mock cryptographic functions for demonstration
    def _mock_validate_private_key(self, key: bytes) -> bool:
        return len(key) == 32

    def _mock_sign(self, message: bytes, private_key: bytes) -> bytes:
        return hashlib.sha256(message + private_key).digest()

    def _mock_derive_public_key(self, private_key: bytes) -> bytes:
        return hashlib.sha256(private_key).digest()

    def _mock_verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        # Simplified verification
        return len(signature) == 32 and len(public_key) == 32

# ============================================================================
# TRANSACTION PROPERTIES
# ============================================================================

class TestTransactionProperties:
    """
    Property-based tests for transaction processing.

    Tests invariants that must hold for all transactions.
    """

    @given(blockchain_address(), blockchain_address(), valid_amount)
    def test_transaction_fields_preserved(self, sender: str, receiver: str, amount: int):
        """
        Property: Transaction fields are preserved after creation.

        Created transaction should contain exactly the fields provided.
        """
        assume(sender != receiver)  # Sender and receiver should be different

        transaction = self._create_transaction(sender, receiver, amount)

        assert transaction["sender"] == sender
        assert transaction["receiver"] == receiver
        assert transaction["amount"] == amount

    @given(
        st.lists(
            st.tuples(blockchain_address(), blockchain_address(), valid_amount),
            min_size=1,
            max_size=10
        ),
        valid_balance
    )
    def test_balance_conservation(self, transfers: list[tuple[str, str, int]], initial_total: int):
        """
        Property: Total balance is conserved across transfers.

        The sum of all wallet balances before transfers should equal
        the sum after transfers (conservation of value).
        """
        # Setup wallets with initial balances
        wallets = self._create_wallets_with_balance(initial_total, len(transfers) * 2)

        total_before = sum(wallets.values())

        # Execute transfers (mock implementation)
        for sender_addr, receiver_addr, amount in transfers:
            if sender_addr in wallets and wallets.get(sender_addr, 0) >= amount:
                wallets[sender_addr] -= amount
                wallets[receiver_addr] = wallets.get(receiver_addr, 0) + amount

        total_after = sum(wallets.values())

        # Total should be conserved
        assert total_before == total_after, "Balance must be conserved"

    @given(valid_balance, valid_amount)
    def test_transfer_insufficient_balance_fails(self, balance: int, transfer_amount: int):
        """
        Property: Transfer fails when balance is insufficient.

        Attempting to transfer more than the available balance should fail.
        """
        assume(transfer_amount > balance)

        result = self._mock_transfer(
            balance=balance,
            amount=transfer_amount
        )

        assert result["success"] is False
        assert "insufficient" in result["error"].lower()

    @given(valid_amount, valid_amount)
    def test_transaction_amount_addition_no_overflow(self, amount1: int, amount2: int):
        """
        Property: Transaction amounts don't overflow when combined.

        Adding transaction amounts should not cause integer overflow.
        """
        assume(amount1 + amount2 < 2**64)  # Assume max safe integer

        total = amount1 + amount2

        assert total >= amount1
        assert total >= amount2
        assert total == amount1 + amount2

    @given(blockchain_address(), blockchain_address(), valid_amount)
    def test_transaction_hash_uniqueness(self, sender: str, receiver: str, amount: int):
        """
        Property: Each transaction has a unique hash.

        Transactions with different details should have different hashes.
        """
        tx1 = self._create_transaction(sender, receiver, amount)
        tx1_hash = self._compute_transaction_hash(tx1)

        # Create different transaction
        tx2 = self._create_transaction(receiver, sender, amount)
        tx2_hash = self._compute_transaction_hash(tx2)

        if tx1 != tx2:
            assert tx1_hash != tx2_hash

    # Helper methods
    def _create_transaction(self, sender: str, receiver: str, amount: int) -> dict:
        """Create a mock transaction."""
        return {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "timestamp": 1234567890
        }

    def _create_wallets_with_balance(self, total: int, num_wallets: int) -> dict:
        """Create wallets with distributed balance."""
        wallets = {}
        amount_per_wallet = total // num_wallets if num_wallets > 0 else 0

        for i in range(num_wallets):
            address = f"0x{'0' * 39}{i}"
            wallets[address] = amount_per_wallet

        return wallets

    def _mock_transfer(self, balance: int, amount: int) -> dict:
        """Mock transfer execution."""
        if amount > balance:
            return {"success": False, "error": "Insufficient balance"}
        return {"success": True, "new_balance": balance - amount}

    def _compute_transaction_hash(self, transaction: dict) -> str:
        """Compute transaction hash."""
        tx_str = str(sorted(transaction.items()))
        return hashlib.sha256(tx_str.encode()).hexdigest()

# ============================================================================
# BLOCKCHAIN PROPERTIES
# ============================================================================

class TestBlockchainProperties:
    """
    Property-based tests for blockchain structure and consensus.

    Tests fundamental blockchain invariants.
    """

    @given(st.lists(valid_amount, min_size=1, max_size=100))
    def test_merkle_root_determinism(self, transaction_amounts: list[int]):
        """
        Property: Merkle root is deterministic.

        The same set of transactions should always produce the same Merkle root.
        """
        # Create transactions
        transactions = [
            {"amount": amt, "id": i}
            for i, amt in enumerate(transaction_amounts)
        ]

        root1 = self._compute_merkle_root(transactions)
        root2 = self._compute_merkle_root(transactions)

        assert root1 == root2, "Merkle root must be deterministic"

    @given(st.lists(valid_amount, min_size=1, max_size=50))
    def test_block_hash_includes_all_transactions(self, transaction_amounts: list[int]):
        """
        Property: Block hash changes if any transaction changes.

        Modifying any transaction should change the block hash.
        """
        transactions = [{"amount": amt} for amt in transaction_amounts]

        original_hash = self._compute_block_hash(transactions)

        # Modify one transaction
        if transactions:
            modified_transactions = transactions.copy()
            modified_transactions[0] = {"amount": modified_transactions[0]["amount"] + 1}

            modified_hash = self._compute_block_hash(modified_transactions)

            assert original_hash != modified_hash

    @given(
        st.integers(min_value=0, max_value=1000000),
        st.lists(valid_amount, min_size=0, max_size=10)
    )
    def test_block_number_sequential(self, previous_block_number: int, transactions: list[int]):
        """
        Property: Block numbers are sequential.

        New blocks should have block number = previous block number + 1.
        """
        new_block = self._create_block(
            previous_block_number=previous_block_number,
            transactions=transactions
        )

        assert new_block["number"] == previous_block_number + 1

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=2, max_size=10))
    def test_chain_difficulty_monotonic(self, difficulties: list[int]):
        """
        Property: Chain difficulty never decreases significantly.

        Difficulty adjustments should be gradual and generally upward
        (in a growing network).
        """
        # Simulate difficulty adjustment
        adjusted_difficulties = []

        for i, difficulty in enumerate(difficulties):
            if i == 0:
                adjusted_difficulties.append(difficulty)
            else:
                # Difficulty can increase or decrease, but not drastically
                prev_difficulty = adjusted_difficulties[-1]
                max_adjustment = prev_difficulty // 2  # Max 50% change

                new_difficulty = max(
                    prev_difficulty - max_adjustment,
                    min(prev_difficulty + max_adjustment, difficulty)
                )
                adjusted_difficulties.append(new_difficulty)

        # Check adjustments are gradual
        for i in range(1, len(adjusted_difficulties)):
            ratio = adjusted_difficulties[i] / adjusted_difficulties[i-1]
            assert 0.5 <= ratio <= 2.0, "Difficulty change too drastic"

    # Helper methods
    def _compute_merkle_root(self, transactions: list[dict]) -> str:
        """Compute Merkle root of transactions."""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        # Simplified Merkle root (hash of all transaction hashes)
        tx_hashes = [
            hashlib.sha256(str(tx).encode()).hexdigest()
            for tx in transactions
        ]

        combined = ''.join(sorted(tx_hashes))
        return hashlib.sha256(combined.encode()).hexdigest()

    def _compute_block_hash(self, transactions: list[dict]) -> str:
        """Compute block hash."""
        merkle_root = self._compute_merkle_root(transactions)
        return hashlib.sha256(merkle_root.encode()).hexdigest()

    def _create_block(self, previous_block_number: int, transactions: list[int]) -> dict:
        """Create a mock block."""
        return {
            "number": previous_block_number + 1,
            "transactions": transactions,
            "previous_hash": "0" * 64
        }

# ============================================================================
# ARITHMETIC PROPERTIES
# ============================================================================

class TestArithmeticProperties:
    """
    Property-based tests for arithmetic operations.

    Tests overflow protection and precision handling.
    """

    @given(valid_amount, valid_amount)
    def test_addition_commutative(self, a: int, b: int):
        """
        Property: Addition is commutative.

        a + b should equal b + a.
        """
        assert a + b == b + a

    @given(valid_amount, valid_amount, valid_amount)
    def test_addition_associative(self, a: int, b: int, c: int):
        """
        Property: Addition is associative.

        (a + b) + c should equal a + (b + c).
        """
        # Check no overflow
        assume(a + b + c < 2**64)

        assert (a + b) + c == a + (b + c)

    @given(valid_balance, valid_amount)
    def test_subtraction_non_negative(self, balance: int, amount: int):
        """
        Property: Wallet balances never go negative.

        Subtraction should be prevented if result would be negative.
        """
        if amount > balance:
            # Should reject or handle gracefully
            result = self._safe_subtract(balance, amount)
            assert result["success"] is False
        else:
            result = self._safe_subtract(balance, amount)
            assert result["success"] is True
            assert result["value"] >= 0

    @given(
        st.decimals(min_value=0, max_value=1000000, places=8),
        st.decimals(min_value=0, max_value=1000000, places=8)
    )
    def test_decimal_precision_preserved(self, amount1: Decimal, amount2: Decimal):
        """
        Property: Decimal precision is preserved in calculations.

        Financial calculations should maintain precision (8 decimal places).
        """
        total = amount1 + amount2

        # Check precision is maintained
        assert total.as_tuple().exponent >= -8

    @given(valid_amount, st.integers(min_value=1, max_value=100))
    def test_fee_calculation_reasonable(self, amount: int, fee_percentage: int):
        """
        Property: Transaction fees are reasonable.

        Fee should be less than amount and proportional to percentage.
        """
        fee = (amount * fee_percentage) // 100

        assert fee >= 0
        assert fee <= amount
        assert fee <= (amount * fee_percentage) / 100

    # Helper methods
    def _safe_subtract(self, balance: int, amount: int) -> dict:
        """Safely subtract amount from balance."""
        if amount > balance:
            return {"success": False, "error": "Insufficient balance"}

        return {"success": True, "value": balance - amount}

# ============================================================================
# STATEFUL PROPERTY TESTING
# ============================================================================

class WalletStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for wallet operations.

    This tests wallet behavior across sequences of operations,
    maintaining invariants throughout.
    """

    def __init__(self):
        super().__init__()
        self.balances = {}
        self.total_supply = 0

    @rule(address=blockchain_address(), amount=valid_amount)
    def create_wallet(self, address: str, amount: int):
        """Create a new wallet with initial balance."""
        if address not in self.balances:
            self.balances[address] = amount
            self.total_supply += amount

    @rule(
        sender=blockchain_address(),
        receiver=blockchain_address(),
        amount=valid_amount
    )
    def transfer(self, sender: str, receiver: str, amount: int):
        """Transfer between wallets."""
        assume(sender != receiver)
        assume(sender in self.balances)

        if self.balances.get(sender, 0) >= amount:
            self.balances[sender] -= amount
            self.balances[receiver] = self.balances.get(receiver, 0) + amount

    @rule(address=blockchain_address())
    def check_balance(self, address: str):
        """Check wallet balance."""
        balance = self.balances.get(address, 0)
        assert balance >= 0, "Balance should never be negative"

    @invariant()
    def total_supply_preserved(self):
        """Invariant: Total supply is preserved."""
        current_total = sum(self.balances.values())
        assert current_total == self.total_supply, "Total supply must be preserved"

    @invariant()
    def all_balances_non_negative(self):
        """Invariant: All balances are non-negative."""
        assert all(balance >= 0 for balance in self.balances.values())

# Test the state machine
TestWalletState = WalletStateMachine.TestCase

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    """
    Run property-based tests with specific configurations.

    Usage:
        python -m tests.fuzzing.example_property_test
    """
    pytest.main([__file__, "-v", "--tb=short"])
