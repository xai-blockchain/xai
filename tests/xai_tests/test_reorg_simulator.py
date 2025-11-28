from unittest.mock import Mock

from xai.core.reorg_simulator import ReorgSimulator


def test_reorg_simulator_collects_snapshots():
    blockchain = Mock()
    blockchain.compute_state_snapshot.side_effect = [
        {"height": 5, "tip": "a", "utxo_digest": "d1"},
        {"height": 6, "tip": "b", "utxo_digest": "d2"},
    ]
    blockchain.replace_chain.return_value = True

    simulator = ReorgSimulator(blockchain)
    replaced, pre, post = simulator.simulate_reorg(["block"])

    assert replaced is True
    assert pre["height"] == 5
    assert post["height"] == 6
    assert pre["utxo_digest"] != post["utxo_digest"]


def test_reorg_simulator_requires_blockchain_interface():
    bad = object()
    try:
        ReorgSimulator(bad)
    except TypeError:
        return
    assert False, "ReorgSimulator should require replace_chain/compute_state_snapshot"
