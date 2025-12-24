"""
Route registration helpers for NodeAPIRoutes.

Each module exposes a register_*_routes function that takes a NodeAPIRoutes
instance and wires the relevant endpoints. Importing these modules keeps the
main node_api module smaller and easier to audit.
"""

from xai.core.api_routes.admin_emergency_routes import register_admin_emergency_routes
from xai.core.api_routes.admin_keys_routes import register_admin_keys_routes
from xai.core.api_routes.admin_monitoring_routes import register_admin_monitoring_routes
from xai.core.api_routes.admin_profiling_routes import register_admin_profiling_routes
from xai.core.api_routes.algo import register_algo_routes
from xai.core.api_routes.blockchain import register_blockchain_routes
from xai.core.api_routes.contracts import register_contract_routes
from xai.core.api_routes.core import register_core_routes
from xai.core.api_routes.crypto_deposits import register_crypto_deposit_routes
from xai.core.api_routes.exchange_orders_routes import register_exchange_orders_routes
from xai.core.api_routes.exchange_payment_routes import register_exchange_payment_routes
from xai.core.api_routes.exchange_wallet_routes import register_exchange_wallet_routes
from xai.core.api_routes.faucet import register_faucet_routes
from xai.core.api_routes.gamification import register_gamification_routes
from xai.core.api_routes.light_client import register_light_client_routes
from xai.core.api_routes.mining import register_mining_routes
from xai.core.api_routes.mining_bonus import register_mining_bonus_routes
from xai.core.api_routes.notifications import register_notification_routes
from xai.core.api_routes.payment_qr_routes import register_payment_qr_routes
from xai.core.api_routes.payment_request_routes import register_payment_request_routes
from xai.core.api_routes.peer import register_peer_routes
from xai.core.api_routes.recovery import register_recovery_routes
from xai.core.api_routes.sync import register_sync_routes
from xai.core.api_routes.transactions import register_transaction_routes
from xai.core.api_routes.wallet import register_wallet_routes


def register_payment_routes(routes):
    """Register all payment-related routes (legacy compatibility wrapper)."""
    register_payment_qr_routes(routes)
    register_payment_request_routes(routes)


def register_exchange_routes(routes):
    """Register all exchange-related routes (legacy compatibility wrapper)."""
    register_exchange_orders_routes(routes)
    register_exchange_wallet_routes(routes)
    register_exchange_payment_routes(routes)


def register_admin_routes(routes):
    """Register all admin-related routes (legacy compatibility wrapper)."""
    register_admin_keys_routes(routes)
    register_admin_emergency_routes(routes)
    register_admin_monitoring_routes(routes)
    register_admin_profiling_routes(routes)


__all__ = [
    "register_core_routes",
    "register_blockchain_routes",
    "register_transaction_routes",
    "register_contract_routes",
    "register_wallet_routes",
    "register_faucet_routes",
    "register_mining_routes",
    "register_peer_routes",
    "register_algo_routes",
    "register_recovery_routes",
    "register_gamification_routes",
    "register_mining_bonus_routes",
    "register_exchange_routes",
    "register_admin_routes",
    "register_crypto_deposit_routes",
    "register_payment_routes",
    "register_notification_routes",
    "register_sync_routes",
    "register_light_client_routes",
    # New modular route functions
    "register_payment_qr_routes",
    "register_payment_request_routes",
    "register_exchange_orders_routes",
    "register_exchange_wallet_routes",
    "register_exchange_payment_routes",
    "register_admin_keys_routes",
    "register_admin_emergency_routes",
    "register_admin_monitoring_routes",
    "register_admin_profiling_routes",
]
