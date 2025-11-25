"""Integration-style tests for the security webhook forwarder."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from xai.core.node import _SecurityWebhookForwarder


def wait_for(condition, timeout=3.0, interval=0.05):
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False


@pytest.mark.integration
def test_forwarder_replays_after_restart(tmp_path: Path):
    queue_file = tmp_path / "security_queue.json"
    key = Fernet.generate_key().decode("utf-8")

    forwarder = _SecurityWebhookForwarder(
        "https://example.com/webhook",
        headers={},
        timeout=1,
        max_retries=1,
        backoff=0.01,
        max_queue=10,
        start_worker=False,
        queue_path=str(queue_file),
        encryption_key=key,
    )
    forwarder.enqueue({"event_type": "api_key_audit", "severity": "WARNING"})
    del forwarder

    with patch("xai.core.node.requests.post", return_value=None) as mock_post:
        restored = _SecurityWebhookForwarder(
            "https://example.com/webhook",
            headers={},
            timeout=1,
            max_retries=3,
            backoff=0.01,
            max_queue=10,
            start_worker=True,
            queue_path=str(queue_file),
            encryption_key=key,
        )

        assert wait_for(lambda: restored.queue.empty())
        restored.queue.join()
        assert mock_post.call_count == 1
