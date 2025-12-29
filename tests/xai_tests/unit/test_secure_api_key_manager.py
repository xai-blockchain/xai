"""
Unit tests for SecureAPIKeyManager submission/usage flows with in-memory storage.
"""

import os
import tempfile
import time

from xai.core.security.secure_api_key_manager import (
    AIProvider,
    KeyStatus,
    SecureAPIKeyManager,
)


def _make_manager(tmp_dir):
    return SecureAPIKeyManager(blockchain_seed="seed", storage_path=tmp_dir)


def test_submit_api_key_rate_limit_and_format(tmp_path, monkeypatch):
    """Enforces rate limiting and provider-specific format checks."""
    mgr = _make_manager(tmp_path)
    # First submission ok
    long_openai_key = "sk-" + "a" * 60
    res = mgr.submit_api_key("addr", AIProvider.OPENAI, long_openai_key, 10)
    assert res["success"] is True

    # Second immediate submission blocked by rate limit
    res2 = mgr.submit_api_key("addr", AIProvider.OPENAI, long_openai_key, 5)
    assert res2["success"] is False
    assert res2["error"] == "RATE_LIMIT_EXCEEDED"

    # Invalid format rejected
    monkeypatch.setattr(mgr, "_check_rate_limit", lambda addr: True)
    bad = mgr.submit_api_key("addr2", AIProvider.ANTHROPIC, "bad", 1)
    assert bad["success"] is False
    assert bad["error"] == "INVALID_API_KEY_FORMAT"


def test_validation_and_usage_lifecycle(tmp_path, monkeypatch):
    """Lifecycle from submission through validation, retrieval, usage, and destruction."""
    mgr = _make_manager(tmp_path)
    monkeypatch.setattr(mgr, "_check_rate_limit", lambda addr: True)
    # Simplify triple encryption so retrieval decrypt succeeds
    monkeypatch.setattr(
        mgr,
        "_triple_encrypt",
        lambda api_key: f"sig:{mgr.fernet.encrypt(api_key.encode()).decode()}",
    )
    res = mgr.submit_api_key("addr", AIProvider.OPENAI, "sk-" + "b" * 60, 10)
    key_id = res["key_id"]

    # Mark as validated
    validate_res = mgr.validate_key(key_id, is_valid=True)
    assert validate_res["status"] == KeyStatus.ACTIVE.value

    # Retrieve for task
    retrieved = mgr.get_api_key_for_task(AIProvider.OPENAI, required_tokens=3)
    assert retrieved is not None
    ret_key_id, decrypted, meta = retrieved
    assert ret_key_id == key_id
    assert meta["status"] == KeyStatus.IN_USE.value

    # Mark tokens used, keep active
    usage = mgr.mark_tokens_used(key_id, tokens_used=5)
    assert usage["status"] == KeyStatus.ACTIVE.value
    assert usage["tokens_remaining"] == 5

    # Deplete remaining tokens to trigger destroy
    depleted = mgr.mark_tokens_used(key_id, tokens_used=5)
    assert depleted["destroyed"] is True
    assert mgr.stored_keys[key_id]["status"] == KeyStatus.DESTROYED.value
