import json
from pathlib import Path

import pytest

from xai.core.wallets.watch_only_wallet import (
    WatchOnlyWalletStore,
    DuplicateWatchAddressError,
)
from xai.security.hd_wallet import HDWallet


def test_watch_store_add_and_persist(tmp_path: Path):
    store_path = tmp_path / "watch.json"
    store = WatchOnlyWalletStore(store_path)
    address = "XAI" + "A" * 40
    entry = store.add_address(address, label="treasury", tags=["ops", "multi-sig"])
    assert entry.address == address

    # Ensure persistence and re-load
    store_again = WatchOnlyWalletStore(store_path)
    entries = store_again.list_addresses()
    assert len(entries) == 1
    assert entries[0].label == "treasury"
    assert "ops" in entries[0].tags

    with pytest.raises(DuplicateWatchAddressError):
        store_again.add_address(address)


def test_watch_store_xpub_derivation(tmp_path: Path):
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    hd = HDWallet(mnemonic)
    xpub = hd.export_extended_public_key(0)

    store_path = tmp_path / "watch.json"
    store = WatchOnlyWalletStore(store_path)
    added = store.add_from_xpub(xpub, count=2, start_index=0, change=0, label="xpub")
    assert len(added) == 2

    expected_addresses = [
        hd.derive_address(account_index=0, change=0, address_index=i)["address"] for i in range(2)
    ]
    stored = [entry.address for entry in store.list_addresses()]
    assert stored == expected_addresses

    # Ensure duplicates are ignored gracefully
    added_again = store.add_from_xpub(xpub, count=2, start_index=0, change=0)
    assert added_again == []
