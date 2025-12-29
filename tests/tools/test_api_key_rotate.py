import time
from pathlib import Path

import pytest

from scripts.tools import api_key_rotate as cli
from xai.core.api.api_auth import APIKeyStore


def test_api_key_store_rotate_logs(tmp_path):
    store = APIKeyStore(str(tmp_path / "keys.json"))
    _, key_id = store.issue_key(label="svc", scope="user")
    new_plain, new_id = store.rotate_key(key_id, label="svc", scope="admin")
    assert new_plain != ""
    events = store.get_events()
    assert any(e.get("action") == "rotate" and e.get("key_id") == new_id for e in events)


def test_cli_rate_limit(monkeypatch, tmp_path):
    cli.RATE_STATE_PATH = tmp_path / "rate.json"
    now = time.time()
    cli.enforce_rate_limit(now)
    for _ in range(cli.RATE_LIMIT - 1):
        cli.enforce_rate_limit(now)
    with pytest.raises(SystemExit):
        cli.enforce_rate_limit(now)
