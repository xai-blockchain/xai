import pytest

from xai.security.hd_wallet import HDWallet

MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)


def test_create_account_tracks_indices():
    wallet = HDWallet(mnemonic=MNEMONIC, passphrase="xai")

    first = wallet.create_account()
    second = wallet.create_account(account_name="Treasury")

    assert first["index"] == 0
    assert second["index"] == 1
    assert second["name"] == "Treasury"

    accounts = wallet.list_accounts()
    assert len(accounts) == 2
    assert accounts[0]["index"] == 0
    assert accounts[1]["index"] == 1


def test_select_account_and_next_derivation_advances_indexes():
    wallet = HDWallet(mnemonic=MNEMONIC, passphrase="xai")
    wallet.create_account()
    wallet.create_account()

    wallet.select_account(1)

    addr1 = wallet.derive_next_receiving()
    addr2 = wallet.derive_next_receiving()

    assert addr1["path"] != addr2["path"]

    metadata = wallet.get_selected_account()
    assert metadata["index"] == 1
    assert metadata["receiving_index"] == 2


def test_next_change_address_tracks_separate_counter():
    wallet = HDWallet(mnemonic=MNEMONIC, passphrase="xai")
    wallet.create_account()

    change1 = wallet.derive_next_change()
    change2 = wallet.derive_next_change()

    assert change1["path"] != change2["path"]
    assert wallet.get_selected_account()["change_index"] == 2
