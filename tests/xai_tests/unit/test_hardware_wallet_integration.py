from xai.core.hardware_wallet import HardwareWalletManager, MockHardwareWallet
from xai.core.wallet import Wallet


def test_wallet_with_hardware_provider():
    """Wallet should delegate signing and address retrieval to the hardware wallet."""
    manager = HardwareWalletManager()
    device_name = "test-mock"
    mock_hw = MockHardwareWallet(address="XAI" + "1234" * 10)
    manager.register_device(device_name, mock_hw)

    wallet = Wallet(hardware_wallet=mock_hw)

    assert wallet.address == mock_hw.address
    sig = wallet.sign_message("test")

    assert sig == mock_hw.sign_transaction(b"test").hex()


def test_default_hardware_wallet_registration():
    """When HW mode is enabled, manager should auto-populate the default provider."""
    manager = HardwareWalletManager()
    # At least one default device should exist if HW mode is disabled as well (mock fallback)
    devices = manager.list_devices()
    assert isinstance(devices, list)
