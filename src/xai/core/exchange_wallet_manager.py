"""Compatibility wrapper for the exchange wallet manager."""

from xai.core.exchange_wallet import ExchangeWalletManager as _ExchangeWalletManager


class ExchangeWalletManager(_ExchangeWalletManager):
    """Thin wrapper maintained for backward compatibility."""

    pass


__all__ = ["ExchangeWalletManager"]
