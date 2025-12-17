import pytest

from xai.security.hd_wallet import HDWallet
from xai.wallet.mnemonic_qr_backup import MnemonicQRBackupGenerator

MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)


def _derive_first_address(mnemonic: str, passphrase: str) -> str:
    wallet = HDWallet(mnemonic=mnemonic, passphrase=passphrase)
    return wallet.derive_address(account_index=0, change=0, address_index=0)["address"]


def test_passphrase_changes_seed_and_addresses():
    addr_none = _derive_first_address(MNEMONIC, "")
    addr_pass = _derive_first_address(MNEMONIC, "xai-pass")
    assert addr_none != addr_pass


def test_whitespace_in_passphrase_is_significant():
    addr_plain = _derive_first_address(MNEMONIC, "xai")
    addr_spaced = _derive_first_address(MNEMONIC, " xai ")
    assert addr_plain != addr_spaced


def test_long_passphrase_is_supported():
    long_passphrase = "xai-" + ("secure-" * 30)
    addr = _derive_first_address(MNEMONIC, long_passphrase)
    assert addr.startswith("XAI") or addr.startswith("TXAI")


def test_mnemonic_qr_backup_requires_matching_passphrase():
    generator = MnemonicQRBackupGenerator()
    bundle = generator.generate_bundle(MNEMONIC, passphrase="secret-pass")
    with pytest.raises(ValueError):
        generator.recover_mnemonic(bundle.payload, passphrase="wrong-pass")
    recovered = generator.recover_mnemonic(bundle.payload, passphrase="secret-pass")
    assert recovered == " ".join(MNEMONIC.split())
