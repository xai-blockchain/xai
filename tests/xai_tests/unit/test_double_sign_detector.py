"""
Unit tests for DoubleSignDetector.

Coverage targets:
- Double-sign detection and proof generation
- Re-signing same block is allowed
- Input validation and state snapshot/restore
"""

import pytest

from xai.blockchain.double_sign_detector import DoubleSignDetector


def test_detects_double_sign_and_generates_proof():
    detector = DoubleSignDetector()
    detected, proof = detector.process_signed_block("val", 1, "hash1")
    assert detected is False
    assert proof is None

    detected, proof = detector.process_signed_block("val", 1, "hash2")
    assert detected is True
    assert proof["validator_id"] == "val"
    assert proof["block_height"] == 1
    assert len(proof["conflicting_signatures"]) == 2


def test_resign_same_block_no_double_sign():
    detector = DoubleSignDetector()
    detector.process_signed_block("val", 2, "hash")
    detected, proof = detector.process_signed_block("val", 2, "hash")
    assert detected is False
    assert proof is None


def test_snapshot_and_restore_state():
    detector = DoubleSignDetector()
    detector.process_signed_block("val", 3, "h3")
    state = detector.get_state()

    new_detector = DoubleSignDetector()
    new_detector.restore_state(state)
    # Should detect double sign on restored state
    detected, _ = new_detector.process_signed_block("val", 3, "different")
    assert detected is True


def test_invalid_inputs_raise():
    detector = DoubleSignDetector()
    with pytest.raises(ValueError):
        detector.process_signed_block("", 1, "h")
    with pytest.raises(ValueError):
        detector.process_signed_block("v", -1, "h")
    with pytest.raises(ValueError):
        detector.process_signed_block("v", 1, "")
