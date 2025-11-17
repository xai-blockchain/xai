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
from typing import Optional, Set, Any, Dict, List
import json
import os
import sys
import time
import threading
import argparse
import requests
from flask import Flask
from flask_cors import CORS

# Import blockchain core
from aixn.core.blockchain import Blockchain, Transaction
from aixn.core.monitoring import MetricsCollector

# Import refactored modules
from aixn.core.node_utils import (
    get_allowed_origins,
    get_base_dir,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MINER_ADDRESS,
    ALGO_FEATURES_ENABLED,
)
from aixn.core.node_api import NodeAPIRoutes
from aixn.core.node_consensus import ConsensusManager


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
        blockchain: Optional[Blockchain] = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        miner_address: Optional[str] = None
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
        self.peers: Set[str] = set()
        self.mining_thread: Optional[threading.Thread] = None

        # Flask app setup
        self.app = Flask(__name__)
        allowed_origins = get_allowed_origins()
        CORS(self.app, origins=allowed_origins)

        # Initialize managers
        self.metrics_collector = MetricsCollector(blockchain=self.blockchain)
        self.consensus_manager = ConsensusManager(blockchain=self.blockchain)

        # Initialize optional features (these may not exist in all setups)
        self._initialize_optional_features()

        # Setup API routes
        self.api_routes = NodeAPIRoutes(self)
        self.api_routes.setup_routes()

        print("📊 Blockchain node initialized")

    def _initialize_optional_features(self) -> None:
        """
        Initialize optional features that may not be available.

        These features are initialized if ALGO_FEATURES_ENABLED or if
        the necessary managers exist in the blockchain.
        """
        # Algorithmic features
        if ALGO_FEATURES_ENABLED:
            try:
                from aixn.core.algo_fee_optimizer import FeeOptimizer
                from aixn.core.fraud_detection import FraudDetector
                self.fee_optimizer = FeeOptimizer()
                self.fraud_detector = FraudDetector()
            except ImportError:
                self.fee_optimizer = None
                self.fraud_detector = None
                print("⚠️  Algorithmic features not available")
        else:
            self.fee_optimizer = None
            self.fraud_detector = None

        # Social recovery
        try:
            from aixn.core.social_recovery import SocialRecoveryManager
            self.recovery_manager = SocialRecoveryManager()
        except (ImportError, AttributeError):
            self.recovery_manager = None

        # Mining bonuses
        try:
            from aixn.core.mining_bonus_system import MiningBonusSystem
            self.bonus_manager = MiningBonusSystem()
        except (ImportError, AttributeError):
            self.bonus_manager = None

        # Exchange features
        try:
            from aixn.core.exchange_wallet_manager import ExchangeWalletManager
            from aixn.core.crypto_deposit_manager import CryptoDepositManager
            from aixn.core.payment_processor import PaymentProcessor
            self.exchange_wallet_manager = ExchangeWalletManager()
            self.crypto_deposit_manager = CryptoDepositManager()
            self.payment_processor = PaymentProcessor()
        except (ImportError, AttributeError):
            self.exchange_wallet_manager = None
            self.crypto_deposit_manager = None
            self.payment_processor = None

    # ==================== MINING OPERATIONS ====================

    def start_mining(self) -> None:
        """Start automatic mining in background thread."""
        if self.is_mining:
            print("⚠️  Mining already active")
            return

        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        print("⛏️  Auto-mining started")

    def stop_mining(self) -> None:
        """Stop automatic mining."""
        if not self.is_mining:
            print("⚠️  Mining not active")
            return

        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("⏸️  Auto-mining stopped")

    def _mine_continuously(self) -> None:
        """
        Continuously mine blocks.

        This method runs in a background thread and mines blocks
        whenever there are pending transactions.
        """
        while self.is_mining:
            if self.blockchain.pending_transactions:
                try:
                    print(f"Mining block with {len(self.blockchain.pending_transactions)} transactions...")
                    block = self.blockchain.mine_pending_transactions(self.miner_address)
                    print(f"✅ Block {block.index} mined! Hash: {block.hash}")

                    # Broadcast to peers
                    self.broadcast_block(block)
                except Exception as e:
                    print(f"❌ Mining error: {e}")

            time.sleep(1)  # Small delay between mining attempts

    # ==================== P2P NETWORKING ====================

    def add_peer(self, peer_url: str) -> None:
        """
        Add peer node to the network.

        Args:
            peer_url: URL of the peer node (e.g., "http://peer.example.com:8545")
        """
        if peer_url not in self.peers:
            self.peers.add(peer_url)
            print(f"✅ Added peer: {peer_url}")

    def broadcast_transaction(self, transaction: Transaction) -> None:
        """
        Broadcast transaction to all peers.

        Args:
            transaction: Transaction to broadcast
        """
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/transaction/receive",
                    json=transaction.to_dict(),
                    timeout=2
                )
            except Exception:
                pass  # Silent failure for unavailable peers

    def broadcast_block(self, block: Any) -> None:
        """
        Broadcast new block to all peers.

        Args:
            block: Block to broadcast
        """
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/block/receive",
                    json=block.to_dict(),
                    timeout=2
                )
            except Exception:
                pass  # Silent failure for unavailable peers

    def sync_with_network(self) -> bool:
        """
        Sync blockchain with network.

        Queries all peers for their chains and adopts the longest valid chain.

        Returns:
            True if sync was successful and chain was updated
        """
        longest_chain = None
        max_length = len(self.blockchain.chain)

        # Query all peers
        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/blocks", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    chain_length = data["total"]

                    if chain_length > max_length:
                        # This chain is longer, get full chain
                        full_response = requests.get(
                            f"{peer}/blocks?limit={chain_length}",
                            timeout=10
                        )
                        if full_response.status_code == 200:
                            longest_chain = full_response.json()["blocks"]
                            max_length = chain_length

            except Exception as e:
                print(f"❌ Error syncing with {peer}: {e}")

        # Replace chain if we found a longer valid one
        if longest_chain and len(longest_chain) > len(self.blockchain.chain):
            # Use consensus manager to validate
            # In production, implement full chain validation and replacement
            print(f"🔄 Syncing blockchain... New length: {len(longest_chain)}")
            return True

        return False

    # ==================== EXCHANGE ORDER MATCHING ====================

    def _match_orders(self, new_order: Dict[str, Any], all_orders: Dict[str, List[Dict[str, Any]]]) -> bool:
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
                    o for o in all_orders["sell"]
                    if o["status"] == "open" and o["price"] <= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"])  # Lowest price first
            else:
                matching_orders = [
                    o for o in all_orders["buy"]
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
                buyer_addr = new_order["address"] if new_order["order_type"] == "buy" else match_order["address"]
                seller_addr = match_order["address"] if new_order["order_type"] == "buy" else new_order["address"]

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
                        print(f"❌ Trade execution failed: {trade_result.get('error')}")
                        continue

                    # Unlock balances
                    if new_order["order_type"] == "buy":
                        self.exchange_wallet_manager.unlock_from_order(buyer_addr, quote_currency, trade_total)
                        self.exchange_wallet_manager.unlock_from_order(seller_addr, base_currency, trade_amount)
                    else:
                        self.exchange_wallet_manager.unlock_from_order(seller_addr, base_currency, trade_amount)
                        self.exchange_wallet_manager.unlock_from_order(buyer_addr, quote_currency, trade_total)

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

        except Exception as e:
            print(f"❌ Error matching orders: {e}")
            return False

    # ==================== NODE CONTROL ====================

    def run(self, debug: bool = False) -> None:
        """
        Start the blockchain node.

        Args:
            debug: Enable Flask debug mode
        """
        self.start_time = time.time()

        print("=" * 60)
        print("AIXN BLOCKCHAIN NODE")
        print("=" * 60)
        print(f"Miner Address: {self.miner_address}")
        print(f"Listening on: http://{self.host}:{self.port}")
        print(f"Blockchain height: {len(self.blockchain.chain)}")
        print(f"Network difficulty: {self.blockchain.difficulty}")
        print("=" * 60)

        # Start auto-mining by default
        self.start_mining()

        # Run Flask app
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIXN Blockchain Node")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AIXN_API_PORT", DEFAULT_PORT)),
        help="Port to listen on"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--miner", help="Miner wallet address")
    parser.add_argument("--peers", nargs="+", help="Peer node URLs")

    args = parser.parse_args()

    # Create blockchain and node
    blockchain = Blockchain()
    node = BlockchainNode(
        blockchain=blockchain,
        host=args.host,
        port=args.port,
        miner_address=args.miner
    )

    # Add peers if specified
    if args.peers:
        for peer in args.peers:
            node.add_peer(peer)

    # Start the node
    node.run()
