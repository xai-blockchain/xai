from xai.core.security.crypto_utils import is_canonical_signature, verify_signature_hex
from xai.core.wallets.hardware_wallet import MockHardwareWallet


def test_mock_hardware_wallet_signatures_are_canonical():
    wallet = MockHardwareWallet()
    payload = b"hardware-wallet-canonical"

    signature = wallet.sign_transaction(payload)
    assert len(signature) == 64

    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    assert is_canonical_signature(r, s) is True

    assert verify_signature_hex(wallet.get_public_key(), payload, signature.hex()) is True
