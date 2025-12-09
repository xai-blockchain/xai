"""
Unit tests for CSPRNG.

Coverage targets:
- Random byte length validation
- Range validation and bounds for generate_int
"""

import pytest

from xai.security.csprng import CSPRNG


def test_generate_bytes_length_and_validation():
    rng = CSPRNG()
    assert len(rng.generate_bytes(16)) == 16
    with pytest.raises(ValueError):
        rng.generate_bytes(0)


def test_generate_int_bounds_and_validation():
    rng = CSPRNG()
    val = rng.generate_int(1, 1)
    assert val == 1
    num = rng.generate_int(1, 10)
    assert 1 <= num <= 10
    with pytest.raises(ValueError):
        rng.generate_int(10, 1)
    with pytest.raises(ValueError):
        rng.generate_int(1.0, 2)
