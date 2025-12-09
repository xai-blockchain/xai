"""
Unit tests for PartitionDetector.

Coverage targets:
- Full connectivity vs partition detection
- Validation of inputs for reachability reporting
"""

import pytest

from xai.network.partition_detector import PartitionDetector


def _detector():
    return PartitionDetector("self", ["A", "B", "C"])


def test_detects_no_partition_when_all_reachable():
    detector = _detector()
    detector.update_own_reachability(["A", "B", "C"])
    detector.report_peer_reachability("A", ["self", "B", "C"])
    detector.report_peer_reachability("B", ["self", "A", "C"])
    detector.report_peer_reachability("C", ["self", "A", "B"])
    assert detector.detect_partitions() is False


def test_detects_partition_when_subset_isolated():
    detector = _detector()
    detector.update_own_reachability(["A"])  # only A reachable
    detector.report_peer_reachability("A", ["self"])
    detector.report_peer_reachability("B", [])  # isolated
    detector.report_peer_reachability("C", [])  # isolated
    assert detector.detect_partitions() is True


def test_report_peer_validation():
    detector = _detector()
    with pytest.raises(ValueError):
        detector.report_peer_reachability("A", "not-a-list")
    detector.report_peer_reachability("unknown", ["self"])  # ignored but not crash
