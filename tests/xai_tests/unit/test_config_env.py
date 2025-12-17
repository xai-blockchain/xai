import importlib
import os
import sys

import pytest


def _reload_config(monkeypatch, env: dict[str, str]):
    for key in list(os.environ.keys()):
        if key.startswith("XAI_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if "xai.core.config" in sys.modules:
        del sys.modules["xai.core.config"]
    import xai.core.config as config

    importlib.reload(config)
    return config


def test_mainnet_requires_secrets(monkeypatch):
    with pytest.raises(Exception):
        _reload_config(
            monkeypatch,
            {
                "XAI_NETWORK": "mainnet",
                # leave secrets unset to force ConfigurationError
            },
        )


def test_testnet_generates_secrets_and_parses_versions(monkeypatch):
    config = _reload_config(
        monkeypatch,
        {
            "XAI_NETWORK": "testnet",
            "XAI_API_VERSIONS": "v1,v2",
            "XAI_API_DEFAULT_VERSION": "v5",  # invalid, should fallback to last supported
        },
    )
    # Secrets auto-generated but non-empty
    assert config.WALLET_TRADE_PEER_SECRET
    assert config.TIME_CAPSULE_MASTER_KEY
    # Default version falls back to last supported when invalid
    assert config.API_DEFAULT_VERSION == "v2"
