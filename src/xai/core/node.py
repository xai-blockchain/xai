"""
AXN Blockchain Node - Core Orchestration
Coordinates blockchain operations, mining, P2P networking, and API services.

This refactored version delegates most functionality to specialized modules:
- node_utils.py: Utility functions and constants
- node_api.py: All Flask route handlers
- node_consensus.py: Consensus and validation logic
- node_mining.py: Mining operations
- node_p2p.py: Peer-to-peer networking
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import threading
import time
import weakref
from typing import Any, Callable

import requests
from flask import Flask, jsonify, make_response, request

logger = logging.getLogger(__name__)

from xai.core.transactions.account_abstraction import AccountAbstractionManager

# Import blockchain core
from xai.core.blockchain import Blockchain, Transaction
from xai.core.api.cors_policy import CORSPolicyManager
from xai.core.security.security_webhook_forwarder import create_security_webhook_sink
from xai.core.config import Config
from xai.core.wallets.crypto_deposit_monitor import (
    CryptoDepositMonitor,
    create_deposit_source,
)
from xai.core.security.flask_secret_manager import get_flask_secret_key
from xai.core.api.monitoring import MetricsCollector
from xai.core.node_api import NodeAPIRoutes
from xai.core.consensus.node_consensus import ConsensusManager
from xai.core.p2p.node_identity import load_or_create_identity
from xai.core.p2p.node_p2p import P2PNetworkManager

# Import refactored modules
from xai.core.chain.node_utils import (
    ALGO_FEATURES_ENABLED,
    DEFAULT_HOST,
    DEFAULT_MINER_ADDRESS,
    DEFAULT_PORT,
    get_allowed_origins,
    get_base_dir,
)
from xai.core.p2p.partial_sync import PartialSyncCoordinator
from xai.core.security.process_sandbox import maybe_enable_process_sandbox
from xai.core.security.request_validator_middleware import setup_request_validation
from xai.core.api.response_compression import setup_compression
from xai.core.security.security_middleware import SecurityConfig, setup_security_middleware
from xai.core.security.security_validation import SecurityEventRouter, SecurityValidator
from xai.core.transaction import Transaction
from xai.core.security.api_rate_limiting import init_rate_limiting
from xai.core.wallet import WalletManager
from xai.core.wallets.withdrawal_processor import WithdrawalProcessor
from xai.network.peer_manager import PeerManager


# CORSPolicyManager and SecurityWebhookForwarder have been extracted to:
# - cors_policy.py
# - security_webhook_forwarder.py

from xai.core.chain.blockchain_interface import BlockchainDataProvider


class BlockchainNode:
    """
    Main blockchain node implementation.

    Orchestrates all node operations including:
    - Blockchain management
    - Mining operations
    - P2P networking
    - API services
    - Consensus mechanisms
    """

    def __init__(
        self,
        blockchain: Blockchain | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        miner_address: str | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize blockchain node.

        Args:
            blockchain: The blockchain instance to manage (creates new if None)
            host: Host address to bind to
            port: Port number to listen on
            miner_address: Address to receive mining rewards
        """
        # Core configuration
        self.blockchain = blockchain if blockchain is not None else Blockchain()
        self.host = host
        self.port = port
        self.miner_address = miner_address or DEFAULT_MINER_ADDRESS

        # Node state
        self.start_time: float = 0.0
        self.is_mining: bool = False
        self.peers: set[str] = set()
        self.mining_thread: threading.Thread | None = None
        self.mined_blocks_counter = 0
        self.last_mining_time = time.time()
        self.withdrawal_processor: WithdrawalProcessor | None = None
        self._withdrawal_worker_thread: threading.Thread | None = None
        self._withdrawal_worker_stop: threading.Event | None = None
        self._withdrawal_worker_interval: int = 30
        self._withdrawal_stats_lock = threading.Lock()
        self._last_withdrawal_stats: dict[str, Any] | None = None
        self.crypto_deposit_monitor: CryptoDepositMonitor | None = None

        # Flask app setup
        self.app = Flask(__name__)
        # Use persistent secret key manager to prevent session invalidation on restart
        self.app.secret_key = get_flask_secret_key(data_dir=os.path.expanduser("~/.xai"))

        # Enable response compression (gzip) for API payloads > threshold
        self.compression_enabled = setup_compression(self.app)

        # Load or create node identity (used for P2P message signing)
        try:
            data_dir = getattr(self.blockchain.storage, "data_dir", os.path.join(os.getcwd(), "data"))
            self.identity = load_or_create_identity(data_dir)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            logger.warning(
                "Failed to initialize node identity: %s",
                type(exc).__name__,
                extra={"event": "node.identity_init_failed"}
            )
            self.identity = {"private_key": "", "public_key": ""}

        # Setup CORS with production-grade policy manager (Task 67)
        self.cors_manager = CORSPolicyManager(self.app)

        # Enforce global request validation limits before any route handlers execute.
        self.request_validator = setup_request_validation(
            self.app,
            max_json_size=getattr(Config, "API_MAX_JSON_BYTES", 1_000_000),
            max_form_size=getattr(Config, "API_MAX_JSON_BYTES", 1_000_000) * 10,
        )

        # Initialize managers
        self.metrics_collector = MetricsCollector(
            blockchain=self.blockchain,
            update_interval=2,
        )
        self._register_security_sinks()
        self.consensus_manager = ConsensusManager(blockchain=self.blockchain)
        self.validator = SecurityValidator()
        self.partial_sync_coordinator = PartialSyncCoordinator(self.blockchain, p2p_manager=None)  # p2p injected later

        # Peer-to-peer networking
        self.peer_manager = PeerManager(
            max_connections_per_ip=getattr(Config, "P2P_MAX_CONNECTIONS_PER_IP", 50),
            trusted_peer_pubkeys=getattr(Config, "TRUSTED_PEER_PUBKEYS", []),
            trusted_cert_fingerprints=getattr(Config, "TRUSTED_PEER_CERT_FINGERPRINTS", []),
            trusted_peer_pubkeys_file=getattr(Config, "TRUSTED_PEER_PUBKEYS_FILE", None) or None,
            trusted_cert_fps_file=getattr(Config, "TRUSTED_PEER_CERT_FPS_FILE", None) or None,
            nonce_ttl_seconds=getattr(Config, "PEER_NONCE_TTL_SECONDS", 300),
            require_client_cert=getattr(Config, "PEER_REQUIRE_CLIENT_CERT", False),
            ca_bundle_path=getattr(Config, "PEER_CA_BUNDLE", None) or None,
            dns_seeds=getattr(Config, "P2P_DNS_SEEDS", None),
            bootstrap_nodes=getattr(Config, "P2P_BOOTSTRAP_NODES", None),
        )
        self.p2p_manager = P2PNetworkManager(
            blockchain=self.blockchain,
            peer_manager=self.peer_manager,
            consensus_manager=self.consensus_manager,
            host=self.host,
            port=kwargs.get("p2p_port", 8765),
            api_port=self.port,  # Pass HTTP API port for handshake
        )
        # Provide P2P to partial sync after creation
        self.partial_sync_coordinator.p2p_manager = self.p2p_manager
        # Provide identity to P2P manager
        setattr(self.p2p_manager, "node_identity", self.identity)

        # Mining heartbeat (allow empty blocks on idle testnet)
        heartbeat_env = os.getenv("XAI_ALLOW_EMPTY_MINING", "0").lower()
        self.allow_empty_mining = heartbeat_env in {"1", "true", "yes", "on"}
        try:
            self.mining_heartbeat_seconds = max(1, int(os.getenv("XAI_MINING_HEARTBEAT_SECONDS", "10")))
        except ValueError:
            self.mining_heartbeat_seconds = 10

        # Setup security middleware
        security_config = SecurityConfig()
        # Align security middleware CORS with CORSPolicyManager
        security_config.CORS_ORIGINS = self.cors_manager.allowed_origins
        self.security_middleware = setup_security_middleware(
            self.app,
            config=security_config,
            enable_cors=True
        )
        logger.info("Security middleware initialized", extra={"event": "node.security_middleware_init"})

        # Initialize API rate limiting (DDoS protection)
        init_rate_limiting(self.app)
        logger.info("API rate limiting initialized", extra={"event": "node.rate_limiting_init"})

        # Initialize optional features (these may not exist in all setups)
        self._initialize_optional_features()
        self._initialize_embedded_wallets()

        # Setup API routes
        self.api_routes = NodeAPIRoutes(self)
        self.api_routes.setup_routes()

        @self.app.before_request
        def before_request():
            request.start_time = time.time()

        @self.app.after_request
        def after_request(response):
            if hasattr(request, 'start_time'):
                latency = time.time() - request.start_time
                self.metrics_collector.get_metric("xai_api_endpoint_latency_seconds").observe(
                    latency, labels={"endpoint": request.path}
                )
            return response

        logger.info("Blockchain node initialized", extra={"event": "node.init_complete"})

    def _register_security_sinks(self) -> None:
        SecurityEventRouter.register_sink(self._create_security_event_sink())

        webhook_url = getattr(Config, "SECURITY_WEBHOOK_URL", "")
        if webhook_url:
            SecurityEventRouter.register_sink(
                self._create_security_webhook_sink(
                    webhook_url,
                    getattr(Config, "SECURITY_WEBHOOK_TOKEN", ""),
                    int(getattr(Config, "SECURITY_WEBHOOK_TIMEOUT", 5) or 5),
                )
            )

    def _create_security_event_sink(self):
        """Create a weakref-backed sink so global security events feed metrics."""
        node_ref = weakref.ref(self)

        def _sink(event_type: str, details: dict[str, Any], severity: str) -> None:
            node = node_ref()
            if not node:
                return
            collector = getattr(node, "metrics_collector", None)
            if collector:
                collector.record_security_event(event_type, severity, details)

        return _sink

    @staticmethod
    def _create_security_webhook_sink(
        url: str,
        token: str = "",
        timeout: int = 5,
        max_retries: int = 3,
        backoff: float = 1.5,
    ) -> Callable[[str, dict[str, Any], str], None] | None:
        """Create a security webhook sink using the extracted module.

        Args:
            url: Webhook endpoint URL
            token: Bearer token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            backoff: Exponential backoff multiplier

        Returns:
            Sink function or None if URL is empty
        """
        queue_path = getattr(Config, "SECURITY_WEBHOOK_QUEUE_PATH", "") or None
        encryption_key = getattr(Config, "SECURITY_WEBHOOK_QUEUE_KEY", "") or None
        return create_security_webhook_sink(
            url=url,
            token=token,
            timeout=timeout,
            max_retries=max_retries,
            backoff=backoff,
            queue_path=queue_path,
            encryption_key=encryption_key,
        )

    def _initialize_optional_features(self) -> None:
        """
        Initialize optional features that may not be available.

        These features are initialized if ALGO_FEATURES_ENABLED or if
        the necessary managers exist in the blockchain.
        """
        # Ensure optional attributes exist even if the imports fail so other
        # parts of the node can safely introspect their availability.
        self.fee_optimizer = None
        self.fraud_detector = None
        self.recovery_manager = None
        self.exchange_wallet_manager = None
        self.withdrawal_processor = None
        self.crypto_deposit_manager = None
        self.crypto_deposit_monitor = None
        self.payment_processor = None

        # Algorithmic features
        if ALGO_FEATURES_ENABLED:
            try:
                from xai.core.transactions.algo_fee_optimizer import FeeOptimizer
                from xai.core.security.fraud_detection import FraudDetector

                self.fee_optimizer = FeeOptimizer()
                self.fraud_detector = FraudDetector()
                logger.info("Algorithmic features enabled", extra={"event": "node.algo_features_enabled"})
            except ImportError as exc:
                logger.debug("Algorithmic features unavailable: %s", type(exc).__name__)

        # Social recovery
        try:
            from xai.core.wallets.social_recovery import SocialRecoveryManager

            self.recovery_manager = SocialRecoveryManager()
        except (ImportError, AttributeError) as exc:
            logger.debug("Social recovery disabled: %s", type(exc).__name__)

        # Mining bonuses
        try:
            from xai.core.mining.mining_bonus_system import MiningBonusSystem

            self.bonus_manager = MiningBonusSystem()
        except (ImportError, AttributeError):
            self.bonus_manager = None

        # Exchange features
        try:
            from xai.core.wallets.exchange_wallet import ExchangeWalletManager

            self.exchange_wallet_manager = ExchangeWalletManager()
            self.blockchain.trade_manager.attach_exchange_manager(self.exchange_wallet_manager)

            processor_cfg = getattr(Config, "WITHDRAWAL_PROCESSOR", {}) or {}
            try:
                self.withdrawal_processor = WithdrawalProcessor(
                    self.exchange_wallet_manager,
                    data_dir=processor_cfg.get(
                        "DATA_DIR", os.path.join(get_base_dir(), "withdrawals")
                    ),
                    lock_amount_threshold=processor_cfg.get("LOCK_AMOUNT_THRESHOLD", 5_000.0),
                    lock_duration_seconds=processor_cfg.get("LOCK_DURATION_SECONDS", 3600),
                    max_withdrawal_per_tx=processor_cfg.get("MAX_PER_TX", 250_000.0),
                    max_daily_volume=processor_cfg.get("MAX_DAILY_VOLUME", 1_000_000.0),
                    manual_review_threshold=processor_cfg.get("MANUAL_REVIEW_THRESHOLD", 0.65),
                    blocked_destinations=set(processor_cfg.get("BLOCKED_DESTINATIONS", [])),
                )
                interval = int(processor_cfg.get("INTERVAL_SECONDS", 45) or 45)
                self._start_withdrawal_worker(interval)
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                self.withdrawal_processor = None
                logger.error(
                    "Failed to initialize withdrawal processor: %s",
                    type(exc).__name__,
                    extra={"event": "withdrawal.processor_init_failed"},
                )
        except (ImportError, AttributeError) as exc:
            self.exchange_wallet_manager = None
            logger.debug("Exchange wallet manager disabled: %s", type(exc).__name__)

        if self.exchange_wallet_manager:
            try:
                from xai.core.wallets.crypto_deposit_manager import CryptoDepositManager

                self.crypto_deposit_manager = CryptoDepositManager(
                    exchange_wallet_manager=self.exchange_wallet_manager
                )
            except (ImportError, AttributeError):
                self.crypto_deposit_manager = None

            self._configure_crypto_deposit_monitor(getattr(Config, "CRYPTO_DEPOSIT_MONITOR", {}))

            try:
                from xai.core.transactions.payment_processor import PaymentProcessor

                self.payment_processor = PaymentProcessor()
            except (ImportError, AttributeError):
                self.payment_processor = None

    def _initialize_embedded_wallets(self) -> None:
        """Initialize wallet and account abstraction managers for embedded wallets."""

        self.wallet_manager = None
        self.account_abstraction = None

        try:
            wallet_dir = getattr(Config, "WALLET_DIR", None)
            if wallet_dir:
                self.wallet_manager = WalletManager(data_dir=wallet_dir)
            else:
                self.wallet_manager = WalletManager()

            storage_dir = getattr(Config, "EMBEDDED_WALLET_DIR", None)
            self.account_abstraction = AccountAbstractionManager(
                wallet_manager=self.wallet_manager,
                storage_path=storage_dir,
            )
            logger.info("Embedded wallet manager initialized", extra={"event": "node.wallet_manager_init"})
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            self.wallet_manager = None
            self.account_abstraction = None
            logger.debug("Embedded wallets disabled: %s", type(exc).__name__)

    def _configure_crypto_deposit_monitor(self, monitor_cfg: dict[str, Any]) -> None:
        """Initialize crypto deposit monitoring if enabled."""
        if not monitor_cfg or not monitor_cfg.get("ENABLED"):
            return
        if not self.crypto_deposit_manager:
            logger.warning(
                "Crypto deposit monitor requested but deposit manager unavailable",
                extra={"event": "deposit.monitor_disabled_no_manager"},
            )
            return

        monitor = CryptoDepositMonitor(
            self.crypto_deposit_manager,
            poll_interval=int(monitor_cfg.get("POLL_INTERVAL", 30) or 30),
            jitter_seconds=int(monitor_cfg.get("JITTER_SECONDS", 5) or 5),
            metrics_collector=self.metrics_collector,
        )

        sources_cfg = monitor_cfg.get("SOURCES") or {}
        for currency, cfg in sources_cfg.items():
            try:
                source = create_deposit_source(currency, cfg, self.crypto_deposit_manager)
            except ValueError as exc:
                logger.warning(
                    "Skipping crypto deposit source for %s: %s",
                    currency,
                    exc,
                    extra={"event": "deposit.monitor_source_skipped", "currency": currency},
                )
                continue
            monitor.register_source(currency, source)

        if monitor.sources:
            monitor.start()
            self.crypto_deposit_monitor = monitor
        else:
            logger.warning(
                "Crypto deposit monitor enabled but no valid sources configured",
                extra={"event": "deposit.monitor_no_valid_sources"},
            )

    def _start_withdrawal_worker(self, interval_seconds: int) -> None:
        """Start automated withdrawal queue processing."""
        if not self.withdrawal_processor:
            return
        if self._withdrawal_worker_thread and self._withdrawal_worker_thread.is_alive():
            return

        self._withdrawal_worker_interval = max(10, int(interval_seconds))
        self._withdrawal_worker_stop = threading.Event()
        self._withdrawal_worker_thread = threading.Thread(
            target=self._withdrawal_worker_loop,
            name="withdrawal-processor",
            daemon=True,
        )
        self._withdrawal_worker_thread.start()
        logger.info(
            "Withdrawal processor thread started (interval=%ss)",
            self._withdrawal_worker_interval,
            extra={"event": "withdrawal.processor_started"},
        )

    def _withdrawal_worker_loop(self) -> None:
        """Loop that periodically processes pending exchange withdrawals."""
        while self.withdrawal_processor and self._withdrawal_worker_stop:
            if self._withdrawal_worker_stop.is_set():
                break
            try:
                stats = self.withdrawal_processor.process_queue()
                queue_depth = (
                    self.exchange_wallet_manager.get_pending_count()
                    if self.exchange_wallet_manager
                    else 0
                )
                snapshot = dict(stats)
                snapshot["queue_depth"] = queue_depth
                snapshot["timestamp"] = time.time()
                with self._withdrawal_stats_lock:
                    self._last_withdrawal_stats = snapshot
                self._record_withdrawal_processor_metrics(stats, queue_depth)
                if any(stats.get(key, 0) for key in ("completed", "flagged", "failed")):
                    logger.info(
                        "Withdrawal processor run summary "
                        "(checked=%d, completed=%d, flagged=%d, failed=%d, deferred=%d)",
                        stats.get("checked", 0),
                        stats.get("completed", 0),
                        stats.get("flagged", 0),
                        stats.get("failed", 0),
                        stats.get("deferred", 0),
                        extra={
                            "event": "withdrawal.processor_cycle",
                            "details": {**stats, "queue_depth": queue_depth},
                        },
                    )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Withdrawal processor cycle failed: %s",
                    type(exc).__name__,
                    extra={"event": "withdrawal.processor_error"},
                )
            finally:
                if self._withdrawal_worker_stop.wait(self._withdrawal_worker_interval):
                    break

    def _stop_withdrawal_worker(self) -> None:
        """Stop withdrawal worker thread gracefully."""
        if not self._withdrawal_worker_thread or not self._withdrawal_worker_stop:
            return
        self._withdrawal_worker_stop.set()
        self._withdrawal_worker_thread.join(timeout=5)
        logger.info("Withdrawal processor stopped", extra={"event": "withdrawal.processor_stopped"})
        self._withdrawal_worker_thread = None
        self._withdrawal_worker_stop = None

    def _stop_crypto_deposit_monitor(self) -> None:
        monitor = getattr(self, "crypto_deposit_monitor", None)
        if monitor:
            monitor.stop()
            self.crypto_deposit_monitor = None

    def _record_withdrawal_processor_metrics(self, stats: dict[str, Any], queue_depth: int) -> None:
        collector = getattr(self, "metrics_collector", None)
        if collector:
            collector.record_withdrawal_processor_stats(stats, queue_depth)

    def get_withdrawal_processor_stats(self) -> dict[str, Any] | None:
        """Return the latest withdrawal processor snapshot if available."""
        with self._withdrawal_stats_lock:
            if not self._last_withdrawal_stats:
                return None
            return dict(self._last_withdrawal_stats)

    # ==================== FAUCET OPERATIONS ====================

    def queue_faucet_transaction(self, recipient: str, amount: float) -> Transaction:
        """
        Create a faucet transaction and enqueue it for inclusion in the next block.

        Args:
            recipient: Address that should receive the testnet funds.
            amount: Amount of XAI to credit.

        Returns:
            The created Transaction instance.
        """
        faucet_tx = Transaction(
            sender="COINBASE",
            recipient=recipient,
            amount=amount,
            tx_type="faucet",
            outputs=[{"address": recipient, "amount": amount}],
        )
        faucet_tx.metadata = {
            "type": "faucet",
            "requested_at": time.time(),
        }
        faucet_tx.txid = faucet_tx.calculate_hash()
        self.blockchain.pending_transactions.append(faucet_tx)
        return faucet_tx

    # ==================== MINING OPERATIONS ====================

    def start_mining(self) -> None:
        """Start automatic mining in background thread."""
        if self.is_mining:
            logger.warning("Mining already active", extra={"event": "mining.already_active"})
            return

        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        logger.info("Auto-mining started", extra={"event": "mining.started"})

    def stop_mining(self) -> None:
        """Stop automatic mining."""
        if not self.is_mining:
            logger.warning("Mining not active", extra={"event": "mining.not_active"})
            return

        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        logger.info("Auto-mining stopped", extra={"event": "mining.stopped"})

    def _mine_continuously(self) -> None:
        """
        Continuously mine blocks.

        This method runs in a background thread and mines blocks
        whenever there are pending transactions.
        """
        while self.is_mining:
            should_mine = bool(self.blockchain.pending_transactions)
            if self.allow_empty_mining and not should_mine:
                # Emit a heartbeat block after a small idle window so the chain advances
                if time.time() - self.last_mining_time >= self.mining_heartbeat_seconds:
                    hb_tx = Transaction(
                        sender="COINBASE",
                        recipient=self.miner_address,
                        amount=0,
                        tx_type="heartbeat",
                        outputs=[{"address": self.miner_address, "amount": 0}],
                    )
                    hb_tx.txid = hb_tx.calculate_hash()
                    self.blockchain.pending_transactions.append(hb_tx)
                    should_mine = True

            if should_mine:
                try:
                    logger.debug(
                        "Mining block with %d transactions",
                        len(self.blockchain.pending_transactions),
                        extra={"event": "mining.block_start"}
                    )
                    block = self.blockchain.mine_pending_transactions(self.miner_address, self.identity)
                    logger.info(
                        "Block %d mined, hash=%s",
                        block.index,
                        block.hash[:16] + "..." if block.hash else "<none>",
                        extra={"event": "mining.block_mined", "block_index": block.index}
                    )

                    self.mined_blocks_counter += 1
                    time_since_last_block = time.time() - self.last_mining_time
                    if time_since_last_block > 0:
                        mining_rate = self.mined_blocks_counter / time_since_last_block
                        self.metrics_collector.get_metric("xai_mining_rate_blocks_per_second").set(mining_rate)
                    self.last_mining_time = time.time()

                    if self.mined_blocks_counter > 100:
                        self.mined_blocks_counter = 0
                        self.last_mining_time = time.time()

                    # Broadcast to peers
                    self.broadcast_block(block)
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.error(
                        "Mining error: %s",
                        type(e).__name__,
                        extra={"event": "mining.error"}
                    )

            time.sleep(1)  # Small delay between mining attempts

    # ==================== P2P NETWORKING ====================

    def add_peer(self, peer_url: str) -> None:
        """
        Add peer node to the network.

        Args:
            peer_url: URL of the peer node (e.g., "http://peer.example.com:8545")
        """
        self.p2p_manager.add_peer(peer_url)

    def broadcast_transaction(self, transaction: Transaction) -> None:
        """
        Broadcast transaction to all peers.

        Args:
            transaction: Transaction to broadcast
        """
        self.p2p_manager.broadcast_transaction(transaction)

    def broadcast_block(self, block: Any) -> None:
        """
        Broadcast new block to all peers.

        Args:
            block: Block to broadcast
        """
        self.p2p_manager.broadcast_block(block)

    def sync_with_network(self) -> bool:
        """
        Sync blockchain with network.

        Queries all peers for their chains and adopts the longest valid chain.

        Returns:
            True if sync was successful and chain was updated
        """
        return self.p2p_manager.sync_with_network()

    # ==================== EXCHANGE ORDER MATCHING ====================

    def _match_orders(
        self, new_order: dict[str, Any], all_orders: dict[str, list[dict[str, Any]]]
    ) -> bool:
        """
        Internal method to match buy/sell orders and execute balance transfers.

        This method is called by the exchange API to match orders immediately
        upon placement.

        Args:
            new_order: The newly placed order
            all_orders: Dictionary containing all buy and sell orders

        Returns:
            True if any trades were matched
        """
        try:
            matched_trades = []

            # Determine which orders to match against
            if new_order["order_type"] == "buy":
                matching_orders = [
                    o
                    for o in all_orders["sell"]
                    if o["status"] == "open" and o["price"] <= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"])  # Lowest price first
            else:
                matching_orders = [
                    o
                    for o in all_orders["buy"]
                    if o["status"] == "open" and o["price"] >= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"], reverse=True)  # Highest price first

            # Match orders
            for match_order in matching_orders:
                if new_order["remaining"] <= 0:
                    break

                # Calculate trade details
                trade_amount = min(new_order["remaining"], match_order["remaining"])
                trade_price = match_order["price"]
                trade_total = trade_price * trade_amount

                # Determine buyer and seller
                buyer_addr = (
                    new_order["address"]
                    if new_order["order_type"] == "buy"
                    else match_order["address"]
                )
                seller_addr = (
                    match_order["address"]
                    if new_order["order_type"] == "buy"
                    else new_order["address"]
                )

                base_currency = new_order.get("base_currency", "AXN")
                quote_currency = new_order.get("quote_currency", "USD")

                # Execute trade if exchange wallet manager available
                if self.exchange_wallet_manager:
                    trade_result = self.exchange_wallet_manager.execute_trade(
                        buyer_address=buyer_addr,
                        seller_address=seller_addr,
                        base_currency=base_currency,
                        quote_currency=quote_currency,
                        base_amount=trade_amount,
                        quote_amount=trade_total,
                    )

                    if not trade_result["success"]:
                        logger.error(
                            "Trade execution failed: %s",
                            trade_result.get("error", "unknown"),
                            extra={"event": "exchange.trade_failed"}
                        )
                        continue

                    # Unlock balances
                    if new_order["order_type"] == "buy":
                        self.exchange_wallet_manager.unlock_from_order(
                            buyer_addr, quote_currency, trade_total
                        )
                        self.exchange_wallet_manager.unlock_from_order(
                            seller_addr, base_currency, trade_amount
                        )
                    else:
                        self.exchange_wallet_manager.unlock_from_order(
                            seller_addr, base_currency, trade_amount
                        )
                        self.exchange_wallet_manager.unlock_from_order(
                            buyer_addr, quote_currency, trade_total
                        )

                # Create trade record
                trade = {
                    "id": f"trade_{int(time.time() * 1000)}",
                    "pair": f"{base_currency}/{quote_currency}",
                    "buyer": buyer_addr,
                    "seller": seller_addr,
                    "price": trade_price,
                    "amount": trade_amount,
                    "total": trade_total,
                    "timestamp": time.time(),
                }
                matched_trades.append(trade)

                # Update order remainings
                new_order["remaining"] -= trade_amount
                match_order["remaining"] -= trade_amount

                # Update order statuses
                if new_order["remaining"] <= 0:
                    new_order["status"] = "filled"
                if match_order["remaining"] <= 0:
                    match_order["status"] = "filled"

            # Save trades
            if matched_trades:
                trades_dir = os.path.join(get_base_dir(), "exchange_data")
                trades_file = os.path.join(trades_dir, "trades.json")

                if os.path.exists(trades_file):
                    with open(trades_file, "r") as f:
                        all_trades = json.load(f)
                else:
                    all_trades = []

                all_trades.extend(matched_trades)

                with open(trades_file, "w") as f:
                    json.dump(all_trades, f, indent=2)

                # Update orders file
                orders_file = os.path.join(trades_dir, "orders.json")
                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

            return len(matched_trades) > 0

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                "Error matching orders: %s",
                type(e).__name__,
                extra={"event": "exchange.order_match_error"}
            )
            return False

    # ==================== NODE CONTROL ====================

    def run(self, debug: bool = False) -> None:
        """
        Start the blockchain node.

        Args:
            debug: Enable Flask debug mode
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_services(debug=debug))

    async def start_services(self, debug: bool = False) -> None:
        """
        Start all node services.
        """
        self.start_time = time.time()

        logger.info(
            "XAI Blockchain Node starting: miner=%s, api=%s:%d, p2p=%s:%d, height=%d, difficulty=%d",
            self.miner_address[:16] + "..." if self.miner_address else "<none>",
            self.host,
            self.port,
            self.p2p_manager.host,
            self.p2p_manager.port,
            len(self.blockchain.chain),
            self.blockchain.difficulty,
            extra={"event": "node.start"}
        )

        # Start Prometheus metrics server
        from xai.core.api.node_metrics_server import start_metrics_server_if_enabled
        metrics_port = int(os.getenv("XAI_METRICS_PORT", "8000"))
        start_metrics_server_if_enabled(port=metrics_port, enabled=True)

        # Start P2P manager
        await self.p2p_manager.start()

        # Attempt partial sync bootstrap when chain is empty (or forced via env)
        force_partial = os.getenv("XAI_FORCE_PARTIAL_SYNC", "").lower() in {"1", "true", "yes"}
        if getattr(Config, "PARTIAL_SYNC_ENABLED", True) and getattr(Config, "P2P_PARTIAL_SYNC_ENABLED", True):
            if self.p2p_manager.sync_with_network(force_partial=force_partial):
                logger.info("Partial/pre-sync completed via P2P manager", extra={"event": "node.partial_sync_applied"})
            else:
                logger.info("Partial/pre-sync skipped or unavailable", extra={"event": "node.partial_sync_skipped"})
        elif getattr(Config, "PARTIAL_SYNC_ENABLED", True) and (len(self.blockchain.chain) == 0 or force_partial):
            if self.partial_sync_coordinator.bootstrap_if_empty(force=force_partial):
                logger.info("Partial sync applied checkpoint successfully", extra={"event": "node.partial_sync_applied"})
            else:
                logger.info("Partial sync skipped or unavailable", extra={"event": "node.partial_sync_skipped"})

        # Start auto-mining by default
        self.start_mining()

        # Run Flask app in a separate thread
        flask_thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": self.host, "port": self.port, "debug": debug, "threaded": True},
            daemon=True,
        )
        flask_thread.start()

        try:
            while True:
                await asyncio.sleep(3600)  # Keep the event loop running
        except asyncio.CancelledError:
            logger.info("Node event loop cancelled, shutting down", extra={"event": "node.cancelled"})
        finally:
            await self.stop_services()

    async def stop_services(self) -> None:
        """
        Stop all node services.
        """
        self.stop_mining()
        self._stop_withdrawal_worker()
        self._stop_crypto_deposit_monitor()
        await self.p2p_manager.stop()

async def main_async() -> None:
    """Command-line entry point for running a blockchain node."""

    parser = argparse.ArgumentParser(description="XAI Blockchain Node")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("XAI_API_PORT", DEFAULT_PORT)),
        help="Port to listen on",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--p2p-port", type=int, default=8765, help="P2P port to listen on")
    parser.add_argument("--miner", help="Miner wallet address")
    parser.add_argument("--data-dir", default=os.getenv("XAI_DATA_DIR", "data"), help="Directory to persist blockchain state")
    parser.add_argument("--peers", nargs="+", help="Peer node URLs")

    args = parser.parse_args()

    blockchain = Blockchain(data_dir=args.data_dir)
    node = BlockchainNode(
        blockchain=blockchain,
        host=args.host,
        port=args.port,
        p2p_port=args.p2p_port,
        miner_address=args.miner,
    )

    if args.peers:
        for peer in args.peers:
            node.add_peer(peer)

    await node.start_services()

def main() -> None:
    """Command-line entry point for running a blockchain node."""
    try:
        maybe_enable_process_sandbox(logger)
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Shutting down node...", extra={"event": "node.shutdown"})

# Backwards compatibility alias
Node = BlockchainNode

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    main()
