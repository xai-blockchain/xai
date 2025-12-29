from pathlib import Path

import pytest

from xai.core.chain.block_header import BlockHeader
from xai.core.consensus.finality import (
    FinalityCertificate,
    FinalityManager,
    FinalityValidationError,
    ValidatorIdentity,
)


class DummyMetric:
    def __init__(self):
        self.value = 0
        self.observations = []

    def inc(self, amount: float = 1.0):
        self.value += amount

    def set(self, value: float):
        self.value = value

    def observe(self, value: float, labels=None):
        self.observations.append(value)


class DummyCollector:
    def __init__(self, metrics):
        self._metrics = metrics

    def get_metric(self, name):
        return self._metrics.get(name)


def _install_metrics_stub(monkeypatch):
    metrics = {
        name: DummyMetric()
        for name in [
            "xai_consensus_finalized_height",
            "xai_validator_votes_total",
            "xai_validator_double_sign_events_total",
            "xai_validator_misbehavior_reports_total",
        ]
    }
    wrapper = type("Wrapper", (), {})()
    wrapper._instance = DummyCollector(metrics)
    monkeypatch.setattr("xai.core.finality.MetricsCollector", wrapper, raising=False)
    return metrics


def _build_manager(tmp_path: Path, **kwargs) -> FinalityManager:
    validator = ValidatorIdentity(address="0xabc123", public_key="0xabc123", voting_power=1)
    return FinalityManager(data_dir=str(tmp_path), validators=[validator], quorum_threshold=1.0, **kwargs)


def _build_header(height: int = 5) -> BlockHeader:
    return BlockHeader(
        index=height,
        previous_hash="A" * 64,
        merkle_root="B" * 64,
        timestamp=1_700_000_000.0,
        difficulty=1,
        nonce=0,
    )


def test_finality_metrics_update_on_finalize(monkeypatch, tmp_path):
    metrics = _install_metrics_stub(monkeypatch)

    manager = _build_manager(tmp_path)
    assert metrics["xai_consensus_finalized_height"].value == 0

    certificate = FinalityCertificate(block_hash="a" * 64, block_height=5)
    manager._finalize_block(certificate)
    assert metrics["xai_consensus_finalized_height"].value == 5

    manager._persist_certificates()
    metrics["xai_consensus_finalized_height"].value = 0
    _build_manager(tmp_path)
    assert metrics["xai_consensus_finalized_height"].value == 5


def test_validator_vote_metric_increment(monkeypatch, tmp_path):
    metrics = _install_metrics_stub(monkeypatch)
    monkeypatch.setattr("xai.core.finality.verify_signature_hex", lambda *args, **kwargs: True)

    manager = _build_manager(tmp_path)

    class NoopDetector:
        def process_signed_block(self, **kwargs):
            return False, None

        def get_state(self):
            return {}

    manager.detector = NoopDetector()

    header = _build_header()
    manager.record_vote(validator_address="0xabc123", header=header, signature="0xdeadbeef")
    assert metrics["xai_validator_votes_total"].value == 1


def test_validator_double_sign_metrics(monkeypatch, tmp_path):
    metrics = _install_metrics_stub(monkeypatch)
    monkeypatch.setattr("xai.core.finality.verify_signature_hex", lambda *args, **kwargs: True)

    reports = []

    def misbehavior_cb(address, height, proof):
        reports.append((address, height, proof))

    manager = _build_manager(tmp_path, misbehavior_callback=misbehavior_cb)

    class DoubleSignDetector:
        def process_signed_block(self, **kwargs):
            return True, {"proof": "bad"}

        def get_state(self):
            return {}

    manager.detector = DoubleSignDetector()

    with pytest.raises(FinalityValidationError):
        manager.record_vote(validator_address="0xabc123", header=_build_header(), signature="0xdeadbeef")

    assert metrics["xai_validator_double_sign_events_total"].value == 1
    assert metrics["xai_validator_misbehavior_reports_total"].value == 1
    assert reports
