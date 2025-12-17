from xai.core.wallet import Wallet
from xai.security.hd_wallet import HDWallet

MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)


def test_wallet_from_mnemonic_matches_hd_wallet_derivation():
    wallet = Wallet.from_mnemonic(
        MNEMONIC,
        passphrase="xai",
        account_index=0,
        change=0,
        address_index=5,
    )

    hd_wallet = HDWallet(mnemonic=MNEMONIC, passphrase="xai")
    derived = hd_wallet.derive_address(account_index=0, change=0, address_index=5)

    # Wallet now returns checksummed addresses; compare case-insensitively
    assert wallet.address.lower() == derived["address"].lower()
    assert wallet.public_key == derived["public_key"]

    metadata = wallet.get_derivation_metadata()
    assert metadata is not None
    assert metadata["derivation_path"] == derived["path"]
    assert metadata["account_index"] == 0
    assert metadata["address_index"] == 5
    assert metadata["change"] == 0
    assert metadata["coin_type"] == HDWallet.XAI_COIN_TYPE


def test_wallet_accounts_use_hardened_paths_and_unique_addresses():
    primary = Wallet.from_mnemonic(MNEMONIC, account_index=0, address_index=0)
    treasury = Wallet.from_mnemonic(MNEMONIC, account_index=1, address_index=0)

    assert primary.address != treasury.address

    primary_meta = primary.get_derivation_metadata()
    treasury_meta = treasury.get_derivation_metadata()

    assert primary_meta is not None
    assert treasury_meta is not None

    # Account component should use hardened derivation (path m/44'/coin'/account')
    assert primary_meta["derivation_path"].split("/")[3].endswith("'")
    assert treasury_meta["derivation_path"].split("/")[3].endswith("'")


def test_wallet_hd_metadata_persists_across_disk_roundtrip(tmp_path):
    wallet = Wallet.from_mnemonic(MNEMONIC, account_index=2, change=1, address_index=3)
    metadata = wallet.get_derivation_metadata()
    assert metadata is not None

    wallet_file = tmp_path / "hd_wallet.json"
    wallet.save_to_file(str(wallet_file))

    reloaded = Wallet.load_from_file(str(wallet_file))
    reloaded_metadata = reloaded.get_derivation_metadata()

    assert reloaded_metadata == metadata


def test_wallet_supports_hardened_address_derivation():
    wallet = Wallet.from_mnemonic(MNEMONIC, address_index=7, hardened_address=True)
    metadata = wallet.get_derivation_metadata()
    assert metadata is not None
    assert metadata["derivation_path"].endswith("'")
