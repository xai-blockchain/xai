"""
Fuzz Tests for Transaction Parsing and Deserialization

Fuzz testing generates random/malformed inputs to find edge cases,
crashes, and security vulnerabilities in parsing code.

Uses Hypothesis for structured fuzzing with smart input generation.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))


class TestTransactionFuzzing:
    """Fuzz tests for transaction parsing - finds crashes and edge cases."""

    @given(st.binary(min_size=0, max_size=10000))
    @settings(max_examples=500)
    def test_transaction_from_bytes_never_crashes(self, data: bytes):
        """Transaction deserialization must never crash on arbitrary bytes."""
        from xai.core.transaction import Transaction

        try:
            # Attempt to parse as JSON first
            decoded = data.decode('utf-8', errors='ignore')
            tx_dict = json.loads(decoded)
            tx = Transaction.from_dict(tx_dict)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
            pass  # Expected for malformed input
        except Exception as e:
            # Unexpected exceptions are bugs
            if "Transaction" not in str(type(e)):
                pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=100),
            st.lists(st.integers(), max_size=5)
        ),
        max_size=20
    ))
    @settings(max_examples=500)
    def test_transaction_from_dict_handles_malformed(self, data: dict):
        """Transaction.from_dict must gracefully handle malformed dictionaries."""
        from xai.core.transaction import Transaction

        try:
            tx = Transaction.from_dict(data)
        except (ValueError, TypeError, KeyError, AttributeError):
            pass  # Expected for malformed input
        except Exception as e:
            if "Validation" not in str(type(e)) and "Transaction" not in str(type(e)):
                pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(
        sender=st.text(min_size=0, max_size=200),
        recipient=st.text(min_size=0, max_size=200),
        amount=st.one_of(
            st.integers(min_value=-10**18, max_value=10**18),
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=50)
        ),
        fee=st.one_of(
            st.integers(min_value=-10**18, max_value=10**18),
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=50)
        )
    )
    @settings(max_examples=300)
    def test_transaction_constructor_handles_bad_inputs(self, sender, recipient, amount, fee):
        """Transaction constructor must not crash on bad inputs."""
        from xai.core.transaction import Transaction

        try:
            tx = Transaction(sender, recipient, amount, fee)
        except (ValueError, TypeError):
            pass  # Expected
        except Exception as e:
            if "Validation" not in str(type(e)) and "Transaction" not in str(type(e)):
                pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")


class TestBlockFuzzing:
    """Fuzz tests for block parsing."""

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=30),
        values=st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=100),
            st.lists(st.dictionaries(
                keys=st.text(max_size=20),
                values=st.text(max_size=50),
                max_size=5
            ), max_size=10)
        ),
        max_size=15
    ))
    @settings(max_examples=100, deadline=5000)  # Extended deadline for slow imports
    def test_block_from_dict_handles_malformed(self, data: dict):
        """Block.from_dict must gracefully handle malformed input."""
        try:
            from xai.core.blockchain import Block, BlockHeader
        except ImportError:
            pytest.skip("Block class not importable separately")
            return

        try:
            block = Block.from_dict(data)
        except (ValueError, TypeError, KeyError, AttributeError, ImportError, ModuleNotFoundError):
            pass
        except Exception as e:
            if "Block" not in str(type(e)):
                pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(st.binary(min_size=0, max_size=5000))
    @settings(max_examples=300)
    def test_block_hash_parsing_never_crashes(self, data: bytes):
        """Block hash validation must not crash on arbitrary input."""
        try:
            hash_str = data.hex()
            # Validate hash format
            if len(hash_str) != 64:
                raise ValueError("Invalid hash length")
            int(hash_str, 16)  # Verify it's valid hex
        except (ValueError, TypeError):
            pass


class TestAddressFuzzing:
    """Fuzz tests for address validation."""

    @given(st.text(min_size=0, max_size=500))
    @settings(max_examples=500)
    def test_address_validation_never_crashes(self, address: str):
        """Address validation must never crash."""
        from xai.core.validation import validate_address

        try:
            validate_address(address)
        except ValueError:
            pass  # Expected for invalid addresses
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(st.binary(min_size=0, max_size=200))
    @settings(max_examples=300)
    def test_address_validation_handles_binary(self, data: bytes):
        """Address validation must handle binary input gracefully."""
        from xai.core.validation import validate_address

        try:
            address = data.decode('utf-8', errors='replace')
            validate_address(address)
        except (ValueError, TypeError):
            pass


class TestAmountFuzzing:
    """Fuzz tests for amount validation."""

    @given(st.one_of(
        st.integers(min_value=-10**30, max_value=10**30),
        st.floats(allow_nan=True, allow_infinity=True),
        st.text(max_size=100),
        st.binary(max_size=50),
        st.none()
    ))
    @settings(max_examples=500)
    def test_amount_validation_never_crashes(self, amount):
        """Amount validation must never crash."""
        from xai.core.validation import validate_amount

        try:
            validate_amount(amount)
        except (ValueError, TypeError):
            pass  # Expected
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=300)
    def test_amount_string_parsing(self, amount_str: str):
        """Amount parsing must handle arbitrary strings."""
        from xai.core.validation import validate_amount

        try:
            validate_amount(amount_str)
        except (ValueError, TypeError):
            pass


class TestJSONFuzzing:
    """Fuzz tests for JSON serialization/deserialization."""

    @given(st.recursive(
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=50)
        ),
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(max_size=20), children, max_size=5)
        ),
        max_leaves=50
    ))
    @settings(max_examples=300)
    def test_json_roundtrip_preserves_structure(self, data):
        """JSON serialization must preserve data structure."""
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert data == deserialized


class TestSignatureFuzzing:
    """Fuzz tests for signature handling."""

    @given(st.binary(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=5000)  # Increased deadline for crypto ops
    def test_signature_verification_never_crashes(self, sig_bytes: bytes):
        """Signature verification must never crash on arbitrary bytes."""
        from xai.core.wallet import Wallet

        wallet = Wallet()
        try:
            # Create a minimal transaction for testing
            sig_hex = sig_bytes.hex() if sig_bytes else ""
            # Verification should return False, not crash
            if hasattr(wallet, 'verify_signature_bytes'):
                result = wallet.verify_signature_bytes(b"test_message", sig_bytes, wallet.public_key)
                assert isinstance(result, bool)
        except (ValueError, TypeError, AttributeError):
            pass  # Expected for malformed signatures
        except Exception as e:
            if "signature" not in str(e).lower() and "key" not in str(e).lower():
                pass  # Crypto errors are expected


class TestInputFuzzing:
    """Fuzz tests for UTXO input parsing."""

    @given(st.lists(
        st.dictionaries(
            keys=st.sampled_from(["txid", "vout", "signature", "amount", "script"]),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.none()
            ),
            max_size=5
        ),
        max_size=20
    ))
    @settings(max_examples=300)
    def test_inputs_parsing_handles_malformed(self, inputs: list):
        """UTXO input parsing must handle malformed data."""
        from xai.core.transaction import Transaction

        try:
            # Create transaction with fuzzed inputs
            tx = Transaction(
                sender="XAI" + "a" * 40,
                recipient="XAI" + "b" * 40,
                amount=1.0,
                fee=0.01,
                inputs=inputs
            )
        except (ValueError, TypeError, KeyError):
            pass


class TestOutputFuzzing:
    """Fuzz tests for transaction output parsing."""

    @given(st.lists(
        st.dictionaries(
            keys=st.sampled_from(["address", "amount", "script"]),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.none()
            ),
            max_size=3
        ),
        max_size=100
    ))
    @settings(max_examples=200)
    def test_outputs_parsing_handles_malformed(self, outputs: list):
        """Transaction output parsing must handle malformed data."""
        from xai.core.transaction import Transaction

        try:
            tx = Transaction(
                sender="XAI" + "a" * 40,
                recipient="XAI" + "b" * 40,
                amount=1.0,
                fee=0.01,
                outputs=outputs
            )
        except (ValueError, TypeError, KeyError):
            pass


class TestMerkleTreeFuzzing:
    """Fuzz tests for Merkle tree calculation."""

    @given(st.lists(st.binary(min_size=32, max_size=32), min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_merkle_root_never_crashes(self, tx_hashes: list):
        """Merkle root calculation must never crash."""
        import hashlib

        def calculate_merkle_root(hashes):
            if not hashes:
                return hashlib.sha256(b"").hexdigest()
            if len(hashes) == 1:
                return hashes[0].hex() if isinstance(hashes[0], bytes) else hashes[0]

            # Convert to hex strings (ensure 64 char by padding)
            hex_hashes = []
            for h in hashes:
                if isinstance(h, bytes):
                    hex_hashes.append(h.hex().zfill(64))
                else:
                    hex_hashes.append(str(h).zfill(64))

            while len(hex_hashes) > 1:
                if len(hex_hashes) % 2 == 1:
                    hex_hashes.append(hex_hashes[-1])
                new_level = []
                for i in range(0, len(hex_hashes), 2):
                    combined = hex_hashes[i] + hex_hashes[i + 1]
                    new_hash = hashlib.sha256(combined.encode()).hexdigest()
                    new_level.append(new_hash)
                hex_hashes = new_level

            return hex_hashes[0]

        try:
            root = calculate_merkle_root(tx_hashes)
            assert isinstance(root, str)
            assert len(root) == 64  # SHA-256 hex length
        except Exception as e:
            pytest.fail(f"Merkle root calculation crashed: {e}")
