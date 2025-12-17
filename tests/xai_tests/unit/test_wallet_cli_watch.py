import argparse
import json
from pathlib import Path

from xai.wallet import cli as wallet_cli
from xai.security.hd_wallet import HDWallet


def _make_add_args(**overrides):
    defaults = {
        "address": None,
        "xpub": None,
        "derive_count": 1,
        "start_index": 0,
        "change": 0,
        "label": None,
        "notes": None,
        "tags": None,
        "store": None,
        "json": True,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_list_args(**overrides):
    defaults = {"tag": None, "store": None, "json": True}
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_remove_args(**overrides):
    defaults = {"address": None, "store": None, "json": True}
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_watch_add_and_list_manual(tmp_path, capsys):
    store_path = tmp_path / "watch.json"
    args = _make_add_args(
        address="XAI" + "B" * 40,
        label="manual",
        tags=["monitor"],
        store=str(store_path),
    )
    result = wallet_cli._watch_add(args)
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["label"] == "manual"

    list_args = _make_list_args(store=str(store_path))
    result = wallet_cli._watch_list(list_args)
    assert result == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing[0]["address"] == "XAI" + "B" * 40

    remove_args = _make_remove_args(address="XAI" + "B" * 40, store=str(store_path))
    result = wallet_cli._watch_remove(remove_args)
    assert result == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["address"] == "XAI" + "B" * 40


def test_watch_add_from_xpub(tmp_path, capsys):
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    hd = HDWallet(mnemonic)
    xpub = hd.export_extended_public_key(0)
    store_path = tmp_path / "watch.json"

    args = _make_add_args(
        address=None,
        xpub=xpub,
        derive_count=2,
        start_index=0,
        change=0,
        label="xpub-watch",
        store=str(store_path),
    )
    result = wallet_cli._watch_add(args)
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 2
    assert payload[0]["label"] == "xpub-watch"

    expected = [
        hd.derive_address(account_index=0, change=0, address_index=i)["address"] for i in range(2)
    ]
    assert [entry["address"] for entry in payload] == expected
