import time

from xai.blockchain.downtime_penalty_manager import DowntimePenaltyManager
from xai.blockchain.double_sign_detector import DoubleSignDetector
from xai.blockchain.fork_detector import ForkDetector


def test_downtime_penalty_and_jailing():
    manager = DowntimePenaltyManager({"validator1": 100.0}, grace_period_seconds=5, penalty_rate_per_second=0.1)
    manager.validators["validator1"]["last_active_time"] = 0.0
    manager.validators["validator1"]["initial_stake"] = 100.0
    manager.check_for_downtime(current_time=10.0)
    status = manager.get_validator_status("validator1")
    assert status["staked_amount"] < 100.0
    assert status["total_penalties"] > 0

    manager.validators["validator1"]["last_active_time"] = 10.0
    manager.check_for_downtime(current_time=30.0)
    assert status["is_jailed"] is True


def test_double_sign_detector():
    detector = DoubleSignDetector()
    assert detector.process_signed_block("validator1", 1, "hashA")[0] is False
    assert detector.process_signed_block("validator1", 1, "hashA")[0] is False
    detected, proof = detector.process_signed_block("validator1", 1, "hashB")
    assert detected is True
    assert proof["validator_id"] == "validator1"
    assert proof["block_height"] == 1


def test_fork_detector_alert():
    detector = ForkDetector("nodeA", {"hash": "h1", "height": 10})
    detector.report_peer_chain_head("peer1", {"hash": "h1", "height": 10})
    detector.report_peer_chain_head("peer2", {"hash": "h1", "height": 10})
    detector.report_peer_chain_head("peer3", {"hash": "fork", "height": 10})
    assert detector.check_for_forks(consensus_threshold=0.6) is False
    detector.report_peer_chain_head("peer4", {"hash": "fork", "height": 10})
    detector.report_peer_chain_head("peer5", {"hash": "fork", "height": 10})
    assert detector.check_for_forks(consensus_threshold=0.6) is True
