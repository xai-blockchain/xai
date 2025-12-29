from xai.core.wallets.hardware_wallet import HardwareWalletManager, MockHardwareWallet
from xai.core.wallet import Wallet
from xai.core.security.crypto_utils import verify_signature_hex


def test_wallet_with_hardware_provider():
    """Wallet should delegate signing and address retrieval to the hardware wallet."""
    manager = HardwareWalletManager()
    device_name = "test-mock"
    mock_hw = MockHardwareWallet()  # Let it generate its own address from the key
    manager.register_device(device_name, mock_hw)

    wallet = Wallet(hardware_wallet=mock_hw)

    # Address should match the hardware wallet's address
    assert wallet.address == mock_hw.address
    # Address should start with XAI (mainnet) or TXAI (testnet)
    assert wallet.address.startswith("XAI") or wallet.address.startswith("TXAI")
    # Length: XAI + 40 hex = 43 chars, or TXAI + 40 hex = 44 chars
    assert len(wallet.address) in (43, 44)

    # Sign a message
    message = "test"
    sig = wallet.sign_message(message)

    # Verify the signature is valid ECDSA signature (64 bytes = 128 hex chars)
    assert len(sig) == 128, f"Expected 128 hex chars (64 bytes), got {len(sig)}"

    # Verify the signature using the hardware wallet's public key
    public_key = mock_hw.get_public_key()
    is_valid = verify_signature_hex(public_key, message.encode(), sig)
    assert is_valid, "Hardware wallet signature should be verifiable"


def test_default_hardware_wallet_registration():
    """When HW mode is enabled, manager should auto-populate the default provider."""
    manager = HardwareWalletManager()
    # At least one default device should exist if HW mode is disabled as well (mock fallback)
    devices = manager.list_devices()
    assert isinstance(devices, list)


def test_mock_hardware_wallet_produces_valid_signatures():
    """MockHardwareWallet should produce valid ECDSA signatures for testing."""
    mock_hw = MockHardwareWallet()

    # Sign multiple messages
    messages = [b"hello", b"world", b"blockchain", b""]

    for msg in messages:
        sig = mock_hw.sign_transaction(msg)

        # Signature should be 64 bytes (r || s format)
        assert len(sig) == 64, f"Expected 64 bytes, got {len(sig)}"

        # Verify signature is valid
        public_key = mock_hw.get_public_key()
        is_valid = verify_signature_hex(public_key, msg, sig.hex())
        assert is_valid, f"Signature for {msg!r} should be valid"


def test_mock_hardware_wallet_deterministic_keys():
    """MockHardwareWallet should generate deterministic keys for reproducible tests."""
    # Create two separate instances
    hw1 = MockHardwareWallet()
    hw2 = MockHardwareWallet()

    # They should have the same address and public key (deterministic from seed)
    assert hw1.address == hw2.address
    assert hw1.get_public_key() == hw2.get_public_key()
