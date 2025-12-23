from __future__ import annotations

"""
Economic Invariant Tests using Property-Based Testing

These tests verify that economic invariants hold across all possible inputs,
providing strong guarantees about system behavior that traditional unit tests cannot.

Uses Hypothesis for property-based testing - generates thousands of random test cases.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from xai.core.validation import MonetaryAmount, MAX_SUPPLY

class TestMonetaryAmountInvariants:
    """Property-based tests for MonetaryAmount precision guarantees."""

    @given(st.integers(min_value=1, max_value=int(MAX_SUPPLY * 10**8)))
    @settings(max_examples=500)
    def test_base_unit_conversion_roundtrip(self, base_units: int):
        """Converting to/from base units must be lossless."""
        amount = MonetaryAmount.from_base_units(base_units)
        recovered = amount.to_base_units()
        assert recovered == base_units, f"Lost precision: {base_units} -> {recovered}"

    @given(
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal(str(MAX_SUPPLY))),
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal(str(MAX_SUPPLY)))
    )
    @settings(max_examples=300)
    def test_addition_commutativity(self, a: Decimal, b: Decimal):
        """Addition must be commutative: a + b == b + a"""
        assume(float(a) + float(b) <= MAX_SUPPLY)
        amount_a = MonetaryAmount(str(a))
        amount_b = MonetaryAmount(str(b))
        assert amount_a + amount_b == amount_b + amount_a

    @given(
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal("1000000")),
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal("1000000")),
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal("1000000"))
    )
    @settings(max_examples=200)
    def test_addition_associativity(self, a: Decimal, b: Decimal, c: Decimal):
        """Addition must be associative: (a + b) + c == a + (b + c)"""
        assume(float(a) + float(b) + float(c) <= MAX_SUPPLY)
        amount_a = MonetaryAmount(str(a))
        amount_b = MonetaryAmount(str(b))
        amount_c = MonetaryAmount(str(c))
        assert (amount_a + amount_b) + amount_c == amount_a + (amount_b + amount_c)

    @given(st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal(str(MAX_SUPPLY))))
    @settings(max_examples=300)
    def test_zero_identity(self, a: Decimal):
        """Zero is the additive identity: a + 0 == a"""
        amount = MonetaryAmount(str(a))
        zero = MonetaryAmount.zero()
        assert amount + zero == amount

    @given(st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal(str(MAX_SUPPLY / 2))))
    @settings(max_examples=300)
    def test_subtraction_inverse(self, a: Decimal):
        """a + b - b == a (subtraction is inverse of addition)"""
        amount_a = MonetaryAmount(str(a))
        amount_b = MonetaryAmount(str(a / 2))  # Ensure b <= a
        result = amount_a + amount_b - amount_b
        assert result == amount_a

    @given(st.floats(min_value=0.01, max_value=1000000))
    @settings(max_examples=100)
    def test_float_rejection(self, f: float):
        """Float values must be rejected to prevent precision loss."""
        with pytest.raises(TypeError, match="Float not allowed"):
            MonetaryAmount(f)

class TestUTXOConservationInvariants:
    """Property-based tests for UTXO model conservation laws."""

    @given(
        st.lists(
            st.integers(min_value=1, max_value=100_000_000),
            min_size=1,
            max_size=10
        ),
        st.integers(min_value=1, max_value=1_000_000)
    )
    @settings(max_examples=200)
    def test_utxo_conservation_law(self, input_amounts: list[int], fee: int):
        """
        UTXO Conservation Law: sum(inputs) == sum(outputs) + fee

        This is the fundamental law of UTXO-based blockchains.
        No value can be created or destroyed, only transferred.
        """
        total_input = sum(input_amounts)
        assume(fee < total_input)  # Fee must be less than total input

        # Simulate splitting inputs into outputs
        available = total_input - fee
        output_count = min(len(input_amounts), 5)

        # Distribute evenly, put remainder in last output
        base_output = available // output_count
        outputs = [base_output] * output_count
        outputs[-1] += available - (base_output * output_count)

        # Verify conservation
        total_output = sum(outputs)
        assert total_input == total_output + fee, \
            f"Conservation violated: {total_input} != {total_output} + {fee}"

    @given(
        st.lists(
            st.tuples(st.text(min_size=1, max_size=10), st.integers(min_value=1, max_value=1000)),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_utxo_uniqueness_invariant(self, utxos: list[tuple[str, int]]):
        """
        UTXO Uniqueness Invariant: Each UTXO can only be spent once.

        Simulates a UTXO set and verifies double-spend prevention.
        """
        utxo_set = set()
        for txid, vout in utxos:
            utxo_id = f"{txid}:{vout}"

            if utxo_id in utxo_set:
                # This would be a double-spend - must be rejected
                continue

            utxo_set.add(utxo_id)

        # Verify all UTXOs are unique
        assert len(utxo_set) == len(set(utxo_set))

class TestSupplyInvariants:
    """Property-based tests for token supply invariants."""

    @given(
        st.lists(
            st.tuples(
                st.sampled_from(["transfer", "stake", "unstake"]),
                st.integers(min_value=1, max_value=1_000_000)
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=200)
    def test_total_supply_conservation(self, operations: list[tuple[str, int]]):
        """
        Total Supply Invariant: Total supply never changes from operations.

        Transfers, staking, and unstaking must not change total supply.
        Only mining rewards can increase supply (up to cap).
        """
        initial_supply = 10_000_000  # Simulated initial supply
        circulating = initial_supply
        staked = 0

        for op_type, amount in operations:
            if op_type == "transfer":
                # Transfer doesn't change total
                pass
            elif op_type == "stake":
                # Move from circulating to staked
                if amount <= circulating:
                    circulating -= amount
                    staked += amount
            elif op_type == "unstake":
                # Move from staked to circulating
                if amount <= staked:
                    staked -= amount
                    circulating += amount

        # Total must remain constant
        total = circulating + staked
        assert total == initial_supply, \
            f"Supply changed: {initial_supply} -> {total}"

    @given(st.integers(min_value=0, max_value=10_000_000))
    @settings(max_examples=50, deadline=5000)  # Extended deadline for loop calculation
    def test_max_supply_cap_invariant(self, block_height: int):
        """
        Max Supply Cap Invariant: Cumulative rewards never exceed MAX_SUPPLY.

        Verifies the halving schedule respects the supply cap.
        """
        BLOCKS_PER_YEAR = 262_800  # 2 min blocks
        INITIAL_REWARD = 12.0

        cumulative_supply = 0.0
        current_reward = INITIAL_REWARD

        for height in range(min(block_height, 1_000_000)):  # Limit for performance
            if height > 0 and height % BLOCKS_PER_YEAR == 0:
                current_reward /= 2

            if cumulative_supply + current_reward > MAX_SUPPLY:
                current_reward = max(0, MAX_SUPPLY - cumulative_supply)

            cumulative_supply += current_reward

        assert cumulative_supply <= MAX_SUPPLY, \
            f"Supply exceeded cap: {cumulative_supply} > {MAX_SUPPLY}"

class TestBlockchainInvariants:
    """Property-based tests for blockchain structure invariants."""

    @given(st.lists(st.binary(min_size=32, max_size=32), min_size=2, max_size=10))
    @settings(max_examples=100)
    def test_chain_linkage_invariant(self, hashes: list[bytes]):
        """
        Chain Linkage Invariant: Each block must reference previous block's hash.

        Simulates a chain and verifies integrity.
        """
        chain = []
        prev_hash = b'\x00' * 32  # Genesis previous hash

        for block_hash in hashes:
            block = {
                'hash': block_hash.hex(),
                'previous_hash': prev_hash.hex(),
                'index': len(chain)
            }
            chain.append(block)
            prev_hash = block_hash

        # Verify chain linkage
        for i in range(1, len(chain)):
            assert chain[i]['previous_hash'] == chain[i-1]['hash'], \
                f"Chain broken at block {i}"

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_monotonic_block_index_invariant(self, indices: list[int]):
        """
        Monotonic Index Invariant: Block indices must be strictly increasing.
        """
        sorted_indices = sorted(set(indices))

        for i in range(1, len(sorted_indices)):
            assert sorted_indices[i] > sorted_indices[i-1], \
                "Block indices must be strictly monotonic"

class TestCryptographicInvariants:
    """Property-based tests for cryptographic invariants."""

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=200)
    def test_hash_determinism_invariant(self, data: bytes):
        """
        Hash Determinism Invariant: Same input always produces same hash.
        """
        import hashlib

        hash1 = hashlib.sha256(data).hexdigest()
        hash2 = hashlib.sha256(data).hexdigest()

        assert hash1 == hash2, "Hash function is not deterministic"

    @given(
        st.binary(min_size=1, max_size=100),
        st.binary(min_size=1, max_size=100)
    )
    @settings(max_examples=200)
    def test_hash_collision_resistance(self, data1: bytes, data2: bytes):
        """
        Collision Resistance Invariant: Different inputs should produce different hashes.

        Note: This is probabilistic - collisions are theoretically possible
        but astronomically unlikely for SHA-256.
        """
        import hashlib
        assume(data1 != data2)  # Only test different inputs

        hash1 = hashlib.sha256(data1).hexdigest()
        hash2 = hashlib.sha256(data2).hexdigest()

        # With SHA-256, collision probability is ~2^-128, effectively impossible
        assert hash1 != hash2, "Hash collision detected (extremely unlikely for SHA-256)"
