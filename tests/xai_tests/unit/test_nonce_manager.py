from xai.blockchain.nonce_manager import NonceManager


def test_nonce_manager_sequences():
    manager = NonceManager()
    assert manager.check_and_increment_nonce("0xUser", 1) is True
    assert manager.check_and_increment_nonce("0xUser", 3) is False
    assert manager.check_and_increment_nonce("0xUser", 2) is True
    assert manager.check_and_increment_nonce("0xUser", 2) is False


def test_nonce_manager_rejects_zero_or_negative():
    manager = NonceManager()
    assert manager.check_and_increment_nonce("0xUnderflow", 0) is False
    assert manager.check_and_increment_nonce("0xUnderflow", -1) is False
    assert manager.check_and_increment_nonce("0xUnderflow", 1) is True


def test_nonce_manager_handles_large_nonce_overflow():
    manager = NonceManager()
    high = 2**63
    manager.last_nonces["0xHigh"] = high - 1
    assert manager.check_and_increment_nonce("0xHigh", high) is True
    assert manager.last_nonces["0xHigh"] == high
    assert manager.check_and_increment_nonce("0xHigh", high + 1) is True
