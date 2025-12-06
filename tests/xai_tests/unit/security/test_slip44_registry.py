import pytest

from xai.security.hd_wallet import HDWallet
from xai.security.slip44_registry import Slip44Registry, Slip44RegistrationError


TEST_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)


def test_registry_contains_registered_xai_coin_type():
    registry = Slip44Registry()
    entry = registry.get_entry("XAI")

    assert entry.coin_type == HDWallet.XAI_COIN_TYPE
    assert entry.name == "Xai Blockchain"
    assert "XAI" in entry.symbol
    assert entry.reference.endswith("XAI-SLIP44-22593")


def test_registry_validates_coin_type_mismatch():
    registry = Slip44Registry()

    with pytest.raises(Slip44RegistrationError):
        registry.validate_coin_type("XAI", 9999)


def test_hd_wallet_coin_type_matches_registry_assignment():
    assert HDWallet.XAI_COIN_TYPE == 22593


def test_hd_wallet_uses_registered_coin_type_in_paths():
    wallet = HDWallet(mnemonic=TEST_MNEMONIC, passphrase="XAI")
    account_info = wallet.derive_account(0)
    receiving = wallet.derive_receiving_address(account_index=0, index=0)

    expected_path_prefix = f"m/44'/{HDWallet.XAI_COIN_TYPE}'/0'"

    assert account_info["path"] == expected_path_prefix
    assert receiving["path"].startswith(f"{expected_path_prefix}/0/0")
