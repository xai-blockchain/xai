"""
Unit tests for common EVM precompile handlers (0x01-0x09).

Coverage targets:
- Dispatch through execute_precompile
- Gas accounting and out-of-gas rejection
- Correct hashing/identity and modular exponentiation outputs
- Input validation for BLAKE2f
"""

import hashlib

import pytest

from xai.core.vm.evm.executor import EVMPrecompiles
from xai.core.vm.exceptions import VMExecutionError


def test_sha256_dispatch_and_output():
    """SHA256 precompile returns correct digest and gas usage."""
    data = b"abc"
    output, gas_used = EVMPrecompiles.execute_precompile("0x02", data, gas=1000)

    expected_gas = 60 + 12 * ((len(data) + 31) // 32)
    assert gas_used == expected_gas
    assert output == hashlib.sha256(data).digest()


def test_identity_precompile_out_of_gas():
    """Identity precompile rejects when supplied gas is insufficient."""
    with pytest.raises(VMExecutionError, match="Out of gas for IDENTITY"):
        EVMPrecompiles.execute_precompile("0x04", b"\x01\x02", gas=10)


def test_modexp_precompile_result_and_gas():
    """MODEXP precompile computes modular exponentiation with length headers."""
    base = (2).to_bytes(1, "big")
    exp = (5).to_bytes(1, "big")
    mod = (13).to_bytes(1, "big")

    header = (
        len(base).to_bytes(32, "big")
        + len(exp).to_bytes(32, "big")
        + len(mod).to_bytes(32, "big")
    )
    payload = header + base + exp + mod

    output, gas_used = EVMPrecompiles.execute_precompile("0x05", payload, gas=500)

    assert gas_used == 200  # max(200, max_len^2 * exp_len / 3) with 1-byte inputs
    assert output == pow(2, 5, 13).to_bytes(len(mod), "big")


def test_identity_precompile_success_gas_calculation():
    """Identity precompile copies data and charges per-32-byte chunk."""
    data = b"\x00" * 64
    output, gas_used = EVMPrecompiles.execute_precompile("0x04", data, gas=100)

    expected_gas = 15 + 3 * ((len(data) + 31) // 32)
    assert gas_used == expected_gas
    assert output == data


def test_blake2f_rejects_invalid_length():
    """BLAKE2F precompile enforces 213-byte input length."""
    with pytest.raises(VMExecutionError, match="BLAKE2f input must be 213 bytes"):
        EVMPrecompiles.execute_precompile("0x09", b"short", gas=1000)


def test_ecrecover_out_of_gas_and_zero_output():
    """ECRECOVER charges 3000 gas; below threshold raises; result is zeroed buffer."""
    with pytest.raises(VMExecutionError, match="Out of gas for ECRECOVER"):
        EVMPrecompiles.execute_precompile("0x01", b"", gas=1000)

    output, gas_used = EVMPrecompiles.execute_precompile("0x01", b"", gas=5000)
    assert gas_used == 3000
    assert output == b"\x00" * 32


def test_ripemd160_padding_and_gas():
    """RIPEMD160 result is left-padded to 32 bytes and honors gas schedule."""
    data = b"abc"
    output, gas_used = EVMPrecompiles.execute_precompile("0x03", data, gas=5000)
    expected_gas = 600 + 120 * ((len(data) + 31) // 32)
    assert gas_used == expected_gas
    assert output.endswith(hashlib.new("ripemd160", data).digest())
    assert len(output) == 32


def test_modexp_zero_modulus_returns_zero():
    """MODEXP with zero modulus returns zero bytes."""
    base = (5).to_bytes(1, "big")
    exp = (3).to_bytes(1, "big")
    mod = (0).to_bytes(1, "big")
    header = (
        len(base).to_bytes(32, "big")
        + len(exp).to_bytes(32, "big")
        + len(mod).to_bytes(32, "big")
    )
    payload = header + base + exp + mod

    output, gas_used = EVMPrecompiles.execute_precompile("0x05", payload, gas=10_000)
    assert gas_used >= 200
    assert output == b"\x00"


def test_modexp_short_payload_is_padded_and_processed():
    """Payload shorter than 96 bytes is zero-padded before parsing lengths."""
    payload = b"\x00" * 10
    output, gas_used = EVMPrecompiles.execute_precompile("0x05", payload, gas=10_000)
    assert gas_used >= 200
    assert output == b""


def test_blake2f_out_of_gas():
    """BLAKE2f raises when supplied gas below rounds cost."""
    rounds = (5).to_bytes(4, "little")
    h = b"\x00" * 64
    m = b"\x00" * 128
    t = b"\x00" * 16
    f = b"\x00"
    payload = rounds + h + m + t + f
    with pytest.raises(VMExecutionError, match="Out of gas for BLAKE2F"):
        EVMPrecompiles.execute_precompile("0x09", payload, gas=10)


def test_blake2f_invalid_rounds_rejected():
    """BLAKE2f rounds of zero are invalid."""
    payload = b"\x00\x00\x00\x00" + b"\x00" * 208 + b"\x00"
    with pytest.raises(VMExecutionError, match="Invalid BLAKE2f rounds"):
        EVMPrecompiles.execute_precompile("0x09", payload, gas=5000)


def test_identity_out_of_gas_for_large_payload():
    """Identity precompile fails when gas less than required for data length."""
    data = b"\x00" * 1024
    required_gas = 15 + 3 * ((len(data) + 31) // 32)
    with pytest.raises(VMExecutionError, match="Out of gas for IDENTITY"):
        EVMPrecompiles.execute_precompile("0x04", data, gas=required_gas - 1)
    output, gas_used = EVMPrecompiles.execute_precompile("0x04", data, gas=required_gas)
    assert output == data
    assert gas_used == required_gas


def test_blake2f_invalid_flag_rejected():
    """BLAKE2f finalization flag must be 0 or 1."""
    rounds = (2).to_bytes(4, "little")
    h = b"\x00" * 64
    m = b"\x00" * 128
    t = b"\x00" * 16
    f = b"\x02"  # invalid flag
    payload = rounds + h + m + t + f
    with pytest.raises(VMExecutionError, match="Invalid BLAKE2f flag"):
        EVMPrecompiles.execute_precompile("0x09", payload, gas=5000)


def test_modexp_out_of_gas_for_large_lengths():
    """MODEXP gas cost scales with length and errors when gas too low."""
    base_len = (1024).to_bytes(32, "big")
    exp_len = (1024).to_bytes(32, "big")
    mod_len = (1024).to_bytes(32, "big")
    header = base_len + exp_len + mod_len
    payload = header + b"\x01" * (1024 * 3)
    with pytest.raises(VMExecutionError, match="Out of gas for MODEXP"):
        EVMPrecompiles.execute_precompile("0x05", payload, gas=1000)


def test_modexp_zero_lengths_returns_empty():
    """Zero lengths should return empty result without error when gas sufficient."""
    header = b"\x00" * 96
    output, gas_used = EVMPrecompiles.execute_precompile("0x05", header, gas=1000)
    assert output == b""
    assert gas_used >= 200
