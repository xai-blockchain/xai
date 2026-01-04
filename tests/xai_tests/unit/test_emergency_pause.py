import time

from xai.blockchain.emergency_pause import EmergencyPauseManager
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


def test_manual_pause_and_unpause(tmp_path):
    cb = CircuitBreaker("pause-cb", failure_threshold=2, recovery_timeout_seconds=1)
    manager = EmergencyPauseManager(
        "0xAdmin",
        circuit_breaker=cb,
        db_path=tmp_path / "pause.db",
    )
    assert manager.get_status()["is_paused"] is False

    manager.pause_operations("0xAdmin", "manual test")
    assert manager.is_paused() is True
    status = manager.get_status()
    assert status["paused_by"] == "0xAdmin"

    manager.unpause_operations("0xAdmin", "resolved")
    assert manager.is_paused() is False


def test_unauthorized_access_rejected(tmp_path):
    manager = EmergencyPauseManager("0xAdmin", db_path=tmp_path / "pause.db")
    try:
        manager.pause_operations("0xEvil")
    except PermissionError:
        pass
    else:
        assert False, "Unauthorized pause should raise PermissionError"


def test_circuit_breaker_auto_pause_and_unpause(tmp_path):
    cb = CircuitBreaker("auto", failure_threshold=1, recovery_timeout_seconds=1)
    manager = EmergencyPauseManager(
        "0xAdmin",
        circuit_breaker=cb,
        db_path=tmp_path / "pause.db",
    )

    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    manager.check_and_auto_pause()
    assert manager.is_paused() is True
    assert manager.get_status()["paused_by"] == "0xAutomatedSystem"

    time.sleep(1.1)
    if cb.allow_request():
        cb.record_success()
    manager.check_and_auto_pause()
    assert manager.is_paused() is False
