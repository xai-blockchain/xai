import time

import pytest

from xai.security.two_factor_auth import TwoFactorAuthManager
from xai.wallet.two_factor_profile import TwoFactorProfile, TwoFactorProfileStore


def test_profile_store_save_load_and_verify(tmp_path, monkeypatch):
    store = TwoFactorProfileStore(base_dir=tmp_path)
    manager = TwoFactorAuthManager()

    setup = manager.setup_2fa("tester", user_email="tester@example.com")
    hashed_codes = manager.hash_backup_codes(setup.backup_codes)

    profile = TwoFactorProfile(
        label="tester",
        secret=setup.secret,
        backup_codes=hashed_codes,
        issuer=manager.issuer_name,
        created_at=time.time(),
        metadata={"user_email": "tester@example.com"},
    )

    store.save(profile)
    loaded = store.load("tester")
    assert loaded.secret == profile.secret
    assert loaded.metadata["user_email"] == "tester@example.com"

    current_code = manager.generate_totp(loaded.secret)
    success, message = store.verify_code("tester", current_code, manager=manager)
    assert success
    assert message == "TOTP verified"

    # Backup code usage
    backup_plain = setup.backup_codes[0]
    success, message = store.verify_code("tester", backup_plain, manager=manager)
    assert success
    assert message == "Backup code consumed"

    # Using same backup again should fail
    success, _ = store.verify_code("tester", backup_plain, manager=manager)
    assert not success


def test_store_delete(tmp_path):
    store = TwoFactorProfileStore(base_dir=tmp_path)
    profile = TwoFactorProfile(label="temp", secret="ABC", backup_codes=[], issuer="XAI")
    store.save(profile)
    assert store.exists("temp")
    store.delete("temp")
    assert not store.exists("temp")
    with pytest.raises(FileNotFoundError):
        store.load("temp")
