import random

import pytest

from xai.blockchain.downtime_penalty_manager import DowntimePenaltyManager
from xai.blockchain.emergency_pause import EmergencyPauseManager, AUTOMATED_CALLER
from xai.blockchain.relayer_staking import RelayerStakingManager
from xai.blockchain.slashing import SlashingManager, ValidatorStake
from xai.security.circuit_breaker import CircuitBreaker


class ManualClock:
    def __init__(self, start: int):
        self.current = start

    def now(self) -> int:
        return self.current

    def advance(self, seconds: int):
        self.current += seconds


@pytest.mark.parametrize("iterations", [250])
def test_downtime_penalty_randomized(iterations):
    clock = ManualClock(start=1_700_000_000)
    manager = DowntimePenaltyManager(
        {"val_a": 1000.0, "val_b": 2000.0, "val_c": 1500.0},
        grace_period_seconds=5,
        penalty_rate_per_second=0.001,
        time_provider=clock.now,
    )

    validators = list(manager.validators.keys())
    rng = random.Random(42)

    for _ in range(iterations):
        clock.advance(rng.randint(0, 8))
        action = rng.choice(["activity", "check"])
        target = rng.choice(validators)
        if action == "activity":
            manager.record_activity(target)
        else:
            manager.check_for_downtime()

    for info in manager.validators.values():
        assert info["staked_amount"] >= 0
        if info["is_jailed"]:
            assert info["staked_amount"] <= info["initial_stake"] * 0.5


def test_emergency_pause_state_machine():
    cb = CircuitBreaker(name="audit", failure_threshold=2, recovery_timeout_seconds=2)
    clock = ManualClock(start=1_700_000_000)
    manager = EmergencyPauseManager("0xAdmin", circuit_breaker=cb, time_provider=clock.now)

    rng = random.Random(123)
    for _ in range(100):
        action = rng.choice(["manual_pause", "manual_unpause", "cb_failure", "cb_success", "auto_check"])
        if action == "manual_pause":
            try:
                manager.pause_operations("0xAdmin", "chaos test")
            except PermissionError:
                pytest.fail("Authorized pause should not fail")
        elif action == "manual_unpause":
            try:
                manager.unpause_operations("0xAdmin", "resume")
            except PermissionError:
                pytest.fail("Authorized unpause should not fail")
        elif action == "cb_failure":
            cb.record_failure()
        elif action == "cb_success":
            cb.record_success()
        else:
            manager.check_and_auto_pause()
        clock.advance(1)

    status = manager.get_status()
    assert set(status.keys()) == {"is_paused", "paused_by", "paused_timestamp", "reason", "circuit_breaker_state"}
    if status["paused_by"] == AUTOMATED_CALLER:
        assert status["is_paused"] is True


def test_relayer_staking_randomized_unbonding():
    slashing_manager = SlashingManager()
    slashing_manager.add_validator_stake(ValidatorStake("0xRelayer", 1500))
    clock = ManualClock(start=1_700_000_000)
    manager = RelayerStakingManager(
        slashing_manager,
        min_bond=500,
        unbonding_period_seconds=5,
        time_provider=clock.now,
    )
    manager.bond_stake("0xRelayer", 1000)

    rng = random.Random(7)
    for _ in range(50):
        action = rng.choice(["bond", "unbond", "finalize", "slash"])
        if action == "bond":
            try:
                manager.bond_stake("0xRelayer", 100)
            except ValueError:
                pass
        elif action == "unbond":
            try:
                manager.unbond_stake("0xRelayer")
            except ValueError:
                pass
        elif action == "finalize":
            try:
                manager.finalize_unbonding("0xRelayer")
            except ValueError:
                pass
        else:
            manager.slash_relayer("0xRelayer", "double_signing")
        clock.advance(rng.randint(0, 3))

    relayer = manager.relay_pool.get("0xRelayer")
    assert relayer is not None
    assert relayer.bonded_amount >= 0
