import pytest

from xai.core.security.security_middleware import TOTPManager


@pytest.fixture(name="manager")
def fixture_manager() -> TOTPManager:
    pytest.importorskip("pyotp")
    return TOTPManager()


def test_backup_codes_persist_hashed(manager: TOTPManager):
    manager.generate_secret("user-1")
    codes = manager.get_backup_codes("user-1", count=3)
    assert len(codes) == 3

    record = manager.user_backup_codes["user-1"]
    assert "salt" in record
    assert len(record["hashes"]) == 3

    for code in codes:
        hashed = manager._hash_backup_code(code, record["salt"])  # pylint: disable=protected-access
        assert hashed in record["hashes"] or hashed in record["used"]


def test_backup_codes_single_use_verification(manager: TOTPManager):
    manager.generate_secret("user-2")
    codes = manager.get_backup_codes("user-2", count=2)

    assert manager.verify_backup_code("user-2", codes[0]) is True
    # Code cannot be reused
    assert manager.verify_backup_code("user-2", codes[0]) is False
    # Wrong code rejected
    assert manager.verify_backup_code("user-2", "deadbeef") is False
