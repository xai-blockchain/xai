import os
import importlib
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
