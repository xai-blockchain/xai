import pytest

from xai.core.vm.evm.executor import EVMPrecompiles
from xai.core.vm.exceptions import VMExecutionError


def _build_valid_point_eval_payload() -> bytes:
    """Return a valid POINT_EVALUATION payload for a constant polynomial."""
    versioned_hash = "01cdcb18824446fa3041b29d7d3b5abc4152b417cb6814d7fd1852fa2511a64e"
    z = "00000000000000000000000000000003a0c92075c0dbf3b8acbc5f96ce3f0ad2"
    y = "0000000000000000000000000000000000000000000000000000000000000005"
    commitment = "b0e7791fb972fe014159aa33a98622da3cdc98ff707965e536d8636b5fcc5ac7a91a8c46e59a00dca575af0f18fb13dc"
    proof = "c0" + "0" * 94  # Point at infinity encoding
    return bytes.fromhex(versioned_hash + z + y + commitment + proof)


def test_point_evaluation_precompile_succeeds() -> None:
    payload = _build_valid_point_eval_payload()
    output, gas_used = EVMPrecompiles._point_evaluation(payload, gas=80_000)

    expected_output = (
        EVMPrecompiles._KZG_FIELD_ELEMENTS_PER_BLOB.to_bytes(32, "big")
        + EVMPrecompiles._KZG_BLS_MODULUS.to_bytes(32, "big")
    )
    assert gas_used == EVMPrecompiles._KZG_POINT_EVAL_GAS
    assert output == expected_output


def test_point_evaluation_precompile_requires_exact_length() -> None:
    with pytest.raises(VMExecutionError, match="exactly 192 bytes"):
        EVMPrecompiles._point_evaluation(b"\x00" * 10, gas=80_000)


def test_point_evaluation_precompile_rejects_mismatched_hash() -> None:
    payload = bytearray(_build_valid_point_eval_payload())
    payload[0] ^= 0xFF

    with pytest.raises(VMExecutionError, match="Commitment/versioned hash mismatch"):
        EVMPrecompiles._point_evaluation(bytes(payload), gas=80_000)


def test_point_evaluation_precompile_rejects_non_canonical_field() -> None:
    payload = bytearray(_build_valid_point_eval_payload())
    modulus_bytes = EVMPrecompiles._KZG_BLS_MODULUS.to_bytes(32, "big")
    payload[64:96] = modulus_bytes  # Replace y with bls modulus (non-canonical)

    with pytest.raises(VMExecutionError, match="non-canonical field elements"):
        EVMPrecompiles._point_evaluation(bytes(payload), gas=80_000)
