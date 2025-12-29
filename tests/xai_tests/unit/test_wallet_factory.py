"""
Unit tests for WalletFactory collision resistance and wallet lifecycle helpers.
"""

from pathlib import Path

from xai.core.wallets.wallet_factory import CollisionResistance, WalletFactory


def test_collision_resistance_uniqueness_and_stats():
    """CollisionResistance tracks collisions and stats."""
    cr = CollisionResistance()
    res1 = cr.check_address_uniqueness("addr1")
    res2 = cr.check_address_uniqueness("addr1")

    assert res1["unique"] is True
    assert res2["unique"] is False
    stats = cr.get_stats()
    assert stats["collision_attempts"] == 1
    assert stats["total_generation_attempts"] == 2


def test_wallet_factory_create_and_list(tmp_path, monkeypatch):
    """WalletFactory creates wallets and lists available files."""
    wf = WalletFactory(data_dir=str(tmp_path))
    wf.create_new_wallet("alice", password="pw")
    wf.create_new_wallet("bob", password="pw")

    available = wf.list_available_wallets()
    assert set(available.keys()) == {"alice", "bob"}
    stats = wf.get_stats()
    assert stats["wallet_files_count"] == 2
