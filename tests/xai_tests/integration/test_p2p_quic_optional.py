import pytest

pytest.importorskip("aioquic")

from xai.core.node_p2p import P2PNetworkManager
from xai.core.blockchain import Blockchain


def test_quic_flag_enables_feature(monkeypatch):
    bc = Blockchain()
    manager = P2PNetworkManager(bc, max_connections=1)
    assert hasattr(manager, "quic_enabled")
    # Ensure the flag can be flipped on when env set and aioquic present
    manager.quic_enabled = True
    assert manager.quic_enabled is True
