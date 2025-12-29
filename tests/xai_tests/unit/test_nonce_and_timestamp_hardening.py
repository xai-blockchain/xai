from datetime import datetime, timezone

import pytest

from xai.core.transactions.nonce_tracker import NonceTracker
from xai.core.security.security_validation import SecurityValidator, ValidationError


def test_nonce_tracker_enforces_strict_sequence(tmp_path):
    """Nonce tracker should reject duplicate or out-of-order nonces."""
    tracker = NonceTracker(data_dir=str(tmp_path))
    address = "XAI1234567890abcdef1234567890abcdef12345678"

    # New address expects nonce 0
    assert tracker.validate_nonce(address, 0)
    tracker.increment_nonce(address, 0)

    # Nonce 0 should be invalid again
    assert not tracker.validate_nonce(address, 0)

    # Next expected nonce is 1
    assert tracker.get_next_nonce(address) == 1
    assert tracker.validate_nonce(address, 1)
    tracker.increment_nonce(address, 1)

    # Again, reusing nonce 1 should fail
    assert not tracker.validate_nonce(address, 1)

    # Reserving a higher nonce advances the effective value
    tracker.reserve_nonce(address, 3)
    assert tracker.get_next_nonce(address) == 4


def test_validate_timestamp_rejects_excessive_drift():
    """Timestamp validation should reject values too far in the future or past."""
    validator = SecurityValidator()
    current = datetime.now(timezone.utc).timestamp()

    # Acceptable timestamp (current time)
    assert validator.validate_timestamp(current) == current

    # Too far in the future (> 2 hours)
    future = current + 7200 + 1
    with pytest.raises(ValidationError):
        validator.validate_timestamp(future)

    # Too far in the past (before year 2000)
    with pytest.raises(ValidationError):
        validator.validate_timestamp(946684800 - 1)
