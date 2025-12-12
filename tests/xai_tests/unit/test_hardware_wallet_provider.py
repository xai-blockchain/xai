import os
import sys
import importlib
import builtins
import pytest


def reload_hw_module(env: dict):
    for key, value in env.items():
        os.environ[key] = value
    import xai.core.hardware_wallet as hw  # noqa: WPS433
    importlib.reload(hw)
    return hw


def test_mock_wallet_disabled_without_explicit_opt_in():
    hw = reload_hw_module(
        {
            "XAI_HARDWARE_WALLET_ENABLED": "1",
            "XAI_HARDWARE_WALLET_PROVIDER": "mock",
            "XAI_ALLOW_MOCK_HARDWARE_WALLET": "0",
        }
    )
    with pytest.raises(ValueError):
        hw.get_default_hardware_wallet()


def test_mock_wallet_allowed_when_opted_in():
    hw = reload_hw_module(
        {
            "XAI_HARDWARE_WALLET_ENABLED": "1",
            "XAI_HARDWARE_WALLET_PROVIDER": "mock",
            "XAI_ALLOW_MOCK_HARDWARE_WALLET": "1",
        }
    )
    wallet = hw.get_default_hardware_wallet()
    assert wallet is not None
    assert wallet.get_address()


def test_hardware_wallet_disabled_returns_none():
    hw = reload_hw_module(
        {
            "XAI_HARDWARE_WALLET_ENABLED": "0",
            "XAI_ALLOW_MOCK_HARDWARE_WALLET": "0",
        }
    )
    assert hw.get_default_hardware_wallet() is None


def test_ledger_provider_missing_dependency(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("ledgerblue"):
            raise ImportError("ledgerblue missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("xai.core.hardware_wallet_ledger", None)

    hw = reload_hw_module(
        {
            "XAI_HARDWARE_WALLET_ENABLED": "1",
            "XAI_HARDWARE_WALLET_PROVIDER": "ledger",
            "XAI_ALLOW_MOCK_HARDWARE_WALLET": "0",
        }
    )

    with pytest.raises(ImportError) as exc:
        hw.get_default_hardware_wallet()
    assert "ledgerblue" in str(exc.value)


def test_trezor_provider_missing_dependency(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("trezorlib"):
            raise ImportError("trezorlib missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("xai.core.hardware_wallet_trezor", None)

    hw = reload_hw_module(
        {
            "XAI_HARDWARE_WALLET_ENABLED": "1",
            "XAI_HARDWARE_WALLET_PROVIDER": "trezor",
            "XAI_ALLOW_MOCK_HARDWARE_WALLET": "0",
        }
    )

    with pytest.raises(ImportError) as exc:
        hw.get_default_hardware_wallet()
    assert "trezorlib" in str(exc.value)
