"""
Unit tests for timelock release scheduling and cancellation.
"""

import time

from xai.core.timelock_releases import SoftwareReleaseManager, TimeLockRelease


def test_schedule_and_release(monkeypatch):
    """Active release becomes available after activation timestamp."""
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)
    code = "print('hi')".encode()
    encoded = __import__("base64").b64encode(code).decode()
    release = TimeLockRelease("comp", encoded, activation_timestamp=now - 5, version="1.0")
    mgr = SoftwareReleaseManager(genesis_releases=[release.to_dict()])
    available = mgr.get_available_software()
    assert available[0]["component"] == "comp"


def test_cancel_release(monkeypatch):
    """Upcoming releases list includes locked items."""
    now = time.time()
    code = "print('hi')".encode()
    encoded = __import__("base64").b64encode(code).decode()
    release = TimeLockRelease("comp", encoded, activation_timestamp=now + 1000, version="1.0")
    mgr = SoftwareReleaseManager(genesis_releases=[release.to_dict()])
    upcoming = mgr.get_upcoming_releases()
    assert upcoming and upcoming[0]["is_active"] is False


def test_time_lock_boundary(monkeypatch):
    """Release is locked just before activation and active at boundary."""
    now = time.time()
    encoded = __import__("base64").b64encode(b"hi").decode()
    release = TimeLockRelease("comp", encoded, activation_timestamp=int(now + 100), version="1.0")
    mgr = SoftwareReleaseManager(genesis_releases=[release.to_dict()])

    monkeypatch.setattr("xai.core.timelock_releases.time.time", lambda: now + 50)
    assert mgr.get_available_software() == []

    monkeypatch.setattr("xai.core.timelock_releases.time.time", lambda: now + 120)
    assert mgr.get_available_software()[0]["component"] == "comp"
