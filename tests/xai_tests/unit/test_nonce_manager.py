from xai.blockchain.nonce_manager import NonceManager


def test_nonce_manager_sequences():
    manager = NonceManager()
    assert manager.check_and_increment_nonce("0xUser", 1) is True
    assert manager.check_and_increment_nonce("0xUser", 3) is False
    assert manager.check_and_increment_nonce("0xUser", 2) is True
    assert manager.check_and_increment_nonce("0xUser", 2) is False
