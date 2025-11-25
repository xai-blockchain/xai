import pytest

from xai.blockchain.mev_redistributor import MEVRedistributor
from xai.blockchain.pool_creation_manager import PoolCreationManager


class ManualClock:
    def __init__(self, start_time: int):
        self.current_time = start_time

    def now(self) -> int:
        return self.current_time

    def advance(self, seconds: int):
        self.current_time += seconds


def test_mev_capture_and_redistribution_flow():
    manager = MEVRedistributor(redistribution_percentage=60.0)
    manager.capture_mev(100.0)
    manager.capture_mev(50.0)

    users = {"0xA": 1.0, "0xB": 3.0}
    redistributed = manager.redistribute_mev(users)

    assert redistributed["0xA"] == pytest.approx(22.5)
    assert redistributed["0xB"] == pytest.approx(67.5)
    assert manager.total_mev_captured == pytest.approx(60.0)  # 150 captured - 90 redistributed
    assert manager.total_mev_redistributed == pytest.approx(90.0)


def test_mev_redistribution_edge_cases():
    manager = MEVRedistributor(redistribution_percentage=50.0)
    manager.capture_mev(0.0)
    assert manager.redistribute_mev({}) == {}
    assert manager.redistribute_mev({"0xA": 0.0, "0xB": 0.0}) == {}
    manager.capture_mev(100.0)
    assert manager.redistribute_mev({"0xA": -1.0}) == {}


def test_pool_creation_success_and_failures():
    clock = ManualClock(start_time=1_700_000_000)
    manager = PoolCreationManager(
        min_initial_liquidity=500.0,
        whitelisted_tokens=["ETH", "USDC", "DAI"],
        time_provider=clock.now,
    )

    pool_id = manager.create_pool("eth", "usdc", 1_000.0, "0xCreator")
    assert pool_id == "pool_ETH_USDC"
    info = manager.get_pool_info("eth", "usdc")
    assert info["timestamp"] == clock.now()
    assert info["creator"] == "0xCreator"

    with pytest.raises(ValueError):
        manager.create_pool("ETH", "USDC", 800.0, "0xOther")
    with pytest.raises(ValueError):
        manager.create_pool("ETH", "ETH", 1_000.0, "0xCreator")
    with pytest.raises(ValueError):
        manager.create_pool("ETH", "SHIB", 1_000.0, "0xCreator")
    with pytest.raises(ValueError):
        manager.create_pool("ETH", "DAI", 100.0, "0xCreator")
    with pytest.raises(ValueError):
        manager.create_pool("", "DAI", 600.0, "0xCreator")

    clock.advance(10)
    pool_id_2 = manager.create_pool("dai", "usdc", 600.0, "0xSecond")
    assert pool_id_2 == "pool_DAI_USDC"
    assert manager.get_pool_info("DAI", "USDC")["timestamp"] == clock.now()


def test_pool_creation_requires_positive_minimum():
    with pytest.raises(ValueError):
        PoolCreationManager(min_initial_liquidity=0)
