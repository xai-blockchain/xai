from dataclasses import dataclass

import pytest

from xai.core.security import blacklist_updater


@dataclass
class DummyResponse:
    """Simple stand-in for an HTTP response used by tests."""

    content: bytes = b""
    text: str = ""
    json_data: dict | None = None

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""
        return None

    def json(self) -> dict:
        """Return pre-populated JSON data."""
        return self.json_data or {}


def test_ofac_blacklist_parses_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the OFAC parser extracts digital-currency entries."""
    monkeypatch.setattr(blacklist_updater, "BLACKLIST_USE_MOCK", False)

    sample_xml = """
    <sdnList>
      <sdnEntry>
        <ID>
          <idType>Digital Currency Address</idType>
          <idNumber>OFAC1234</idNumber>
        </ID>
      </sdnEntry>
      <sdnEntry>
        <ID>
          <idType>Other</idType>
          <idNumber>IGNOREME</idNumber>
        </ID>
      </sdnEntry>
    </sdnList>
    """

    response = DummyResponse(content=sample_xml.encode("utf-8"))
    monkeypatch.setattr(
        blacklist_updater.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    addresses = blacklist_updater.OFACBlacklist().fetch_addresses()

    assert "OFAC1234" in addresses
    assert "IGNOREME" not in addresses


def test_community_blacklist_respects_vote_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only include entries that hit the configured vote threshold."""
    monkeypatch.setattr(blacklist_updater, "BLACKLIST_USE_MOCK", False)
    monkeypatch.setattr(blacklist_updater, "COMMUNITY_VOTE_THRESHOLD", 5)

    payload = {
        "blacklisted_addresses": [
            {"address": "COMMUNITY_A", "votes": 7},
            {"address": "COMMUNITY_B", "votes": 3},
            {"address": "COMMUNITY_C", "votes": 5},
        ]
    }

    response = DummyResponse(json_data=payload)
    monkeypatch.setattr(
        blacklist_updater.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    addresses = blacklist_updater.CommunityBlacklist().fetch_addresses()

    assert addresses == {"COMMUNITY_A", "COMMUNITY_C"}


def test_ransomware_blacklist_parses_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip comments and capture the second comma-delimited column."""
    monkeypatch.setattr(blacklist_updater, "BLACKLIST_USE_MOCK", False)

    raw_text = "# header\n1, RANSOMWARE_1\n2,RANSOMWARE_2  \n# footer"
    response = DummyResponse(text=raw_text)
    monkeypatch.setattr(
        blacklist_updater.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    addresses = blacklist_updater.RansomwareTrackerBlacklist().fetch_addresses()

    assert addresses == {"RANSOMWARE_1", "RANSOMWARE_2"}


def test_blacklist_manager_aggregates_all_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """The manager should capture all mock addresses and expose the hash."""
    monkeypatch.setattr(blacklist_updater, "BLACKLIST_USE_MOCK", True)
    manager = blacklist_updater.BlacklistManager()

    summary = manager.update_all_sources()

    assert summary["total_addresses"] == len(manager.get_blacklist())
    assert summary["new_addresses"] == summary["total_addresses"]
    assert summary["sources"]
    assert manager.get_blacklist_hash()
