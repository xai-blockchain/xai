"""
Unit tests for ForkDetector.

Coverage targets:
- Peer reporting and agreement thresholds
- Validation of inputs for chain heads
"""

import pytest

from xai.blockchain.fork_detector import ForkDetector


def _detector():
    return ForkDetector("node", {"hash": "h0", "height": 1})


def test_reports_and_detects_fork():
    fd = _detector()
    fd.report_peer_chain_head("p1", {"hash": "h0", "height": 1})
    fd.report_peer_chain_head("p2", {"hash": "hX", "height": 2})
    assert fd.check_for_forks(consensus_threshold=0.6) is True
    assert fd.check_for_forks(consensus_threshold=0.4) is False


def test_update_chain_head_and_validation():
    fd = _detector()
    fd.update_node_chain_head({"hash": "h1", "height": 2})
    assert fd.current_chain_head["hash"] == "h1"
    with pytest.raises(ValueError):
        fd.report_peer_chain_head("", {"hash": "h", "height": 1})
    with pytest.raises(ValueError):
        fd.update_node_chain_head({"hash": "h"})
