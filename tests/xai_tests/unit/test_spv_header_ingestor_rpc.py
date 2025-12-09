"""
Tests RPC-based header ingestion with monkeypatched responses.
"""

import json
from types import SimpleNamespace

import pytest

from xai.core.spv_header_ingestor import SPVHeaderIngestor


class DummyResponse:
    def __init__(self, result):
        self._result = result
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"result": self._result, "error": None}


def test_ingest_from_rpc(monkeypatch):
    calls = []

    def fake_post(self, url, auth=None, json=None, timeout=None):
        calls.append(json["method"])
        if json["method"] == "getblockhash":
            return DummyResponse("00" * 16 + str(json["params"][0]))
        if json["method"] == "getblockheader":
            height = json["params"][0]
            prev = "00" * 16 + str(int(height[-1]) - 1) if height != "00" * 16 + "0" else "0" * 32
            return DummyResponse(
                {
                    "previousblockhash": prev,
                    "bits": hex(0x1f00ffff),
                }
            )
        raise AssertionError("unexpected method")

    monkeypatch.setattr("requests.Session.post", fake_post)
    ingestor = SPVHeaderIngestor()
    added, rejected = ingestor.ingest_from_rpc("url", "user", "pass", 0, 1)
    assert added == 2
    assert rejected == []
    assert calls.count("getblockhash") == 2
    assert calls.count("getblockheader") == 2
