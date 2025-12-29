"""
XAI Blockchain - Monitoring & Logging Integration Example

This file demonstrates how to integrate the new monitoring and structured logging
systems into the existing XAI blockchain codebase.

Usage:
1. Import the systems
2. Initialize them in your node/blockchain
3. Use throughout the codebase to track metrics and log events
"""

import time

from xai.core.api.monitoring import AlertLevel, MetricsCollector
from xai.core.api.structured_logger import LogContext, PerformanceTimer, StructuredLogger


def example_blockchain_integration():
    """
    Example: Integrating monitoring into the blockchain class
    """

    # Initialize systems
    logger = StructuredLogger("XAI_Blockchain", log_level="INFO")
    metrics = MetricsCollector()

    print("=" * 70)
    print("XAI Blockchain - Monitoring Integration Example")
    print("=" * 70)

    # Example 1: Node startup
    logger.info("Node starting", network="mainnet", port=5000, version="2.0.0")

    # Example 2: Block mining with metrics and logging
    def mine_block(block_index, miner_address, tx_count):
        """Simulate block mining with full monitoring"""

        # Use correlation ID for tracking related logs
        with LogContext() as ctx:
            logger.info(
                f"Starting to mine block #{block_index}",
                block_index=block_index,
                miner=miner_address,
                pending_tx=tx_count,
            )

            # Track mining time
            start_time = time.time()

            # Simulate mining work
            time.sleep(0.5)

            mining_time = time.time() - start_time

            # Log block mined
            logger.block_mined(
                block_index=block_index,
                block_hash="0x1234567890abcdef",
                miner=miner_address,
                tx_count=tx_count,
                reward=50.0,
                mining_time=mining_time,
            )

            # Record metrics
            metrics.record_block_mined(block_index, mining_time)

            for _ in range(tx_count):
                metrics.record_transaction_processed(processing_time=0.01)

            logger.info(
                f"Block #{block_index} successfully mined",
                mining_time_seconds=mining_time,
                hash_rate=1000 / mining_time,
            )

    # Example 3: Transaction processing
    def process_transaction(txid, sender, recipient, amount, fee):
        """Process transaction with monitoring"""

        with LogContext() as ctx:
            # Log transaction
            logger.transaction_submitted(
                txid=txid, sender=sender, recipient=recipient, amount=amount, fee=fee
            )

            # Time validation
            with PerformanceTimer(logger, "transaction_validation"):
                # Simulate validation
                time.sleep(0.01)

                # Record metric
                metrics.record_transaction_processed(processing_time=0.01)

            logger.info("Transaction validated successfully", txid=txid[:16] + "...")

    # Example 4: Network events
    def handle_peer_connection(peer_url, peer_count):
        """Handle peer connection with monitoring"""

        logger.network_event(
            "peer_connected",
            peer_count=peer_count,
            peer_url=peer_url[:20] + "...",  # Truncate for privacy
        )

        metrics.record_peer_connected(peer_count)
        metrics.record_p2p_message("received")

    # Example 5: Security events
    def handle_security_event(event_type, severity, details):
        """Log security events"""

        logger.security_event(event_type, severity=severity, **details)

    # Example 6: API request handling
    def handle_api_request(endpoint, method):
        """Handle API request with monitoring"""

        start_time = time.time()
        status_code = 200
        error = False

        try:
            # Simulate request processing
            with LogContext() as ctx:
                logger.info(f"API request: {method} {endpoint}", method=method, endpoint=endpoint)

                # Simulate work
                time.sleep(0.05)

                logger.info(
                    f"API request completed: {method} {endpoint}",
                    status_code=status_code,
                    duration_ms=(time.time() - start_time) * 1000,
                )

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            error = True
            status_code = 500
            logger.error(
                f"API request failed: {method} {endpoint}", error=str(e), status_code=status_code
            )

        finally:
            duration = time.time() - start_time
            metrics.record_api_request(endpoint, duration, error)
            logger.api_request(endpoint, method, status_code, duration * 1000)

    # Example 7: Alert configuration
    def setup_alerts():
        """Configure monitoring alerts"""

        # High memory usage alert
        metrics.add_alert_rule(
            "high_memory_usage",
            lambda: metrics.get_metric("xai_node_memory_usage_percent").value > 85,
            "Memory usage above 85%",
            AlertLevel.WARNING,
        )

        # Large mempool alert
        metrics.add_alert_rule(
            "large_mempool",
            lambda: metrics.get_metric("xai_pending_transactions").value > 5000,
            "Mempool has more than 5000 pending transactions",
            AlertLevel.WARNING,
        )

        # No peers alert
        metrics.add_alert_rule(
            "no_peers",
            lambda: metrics.get_metric("xai_peers_connected").value == 0,
            "Node has no connected peers",
            AlertLevel.CRITICAL,
        )

        logger.info("Alert rules configured", rules_count=3)

    # Run examples
    print("\n1. Mining blocks...")
    for i in range(3):
        mine_block(block_index=i + 1, miner_address="XAI1234567890abcdef", tx_count=5)
        time.sleep(0.2)

    print("\n2. Processing transactions...")
    for i in range(3):
        process_transaction(
            txid=f"0xabcdef{i}",
            sender="XAI1111111111",
            recipient="XAI2222222222",
            amount=100.0,
            fee=0.01,
        )

    print("\n3. Handling peer connections...")
    handle_peer_connection("http://peer1.xai.network", 1)
    handle_peer_connection("http://peer2.xai.network", 2)

    print("\n4. Security event...")
    handle_security_event(
        "rate_limit_exceeded", "WARN", {"endpoint": "/send", "requests_per_minute": 120}
    )

    print("\n5. API requests...")
    handle_api_request("/blocks", "GET")
    handle_api_request("/send", "POST")

    print("\n6. Setting up alerts...")
    setup_alerts()

    # Wait for metrics to update
    print("\n7. Waiting for metrics update...")
    time.sleep(3)

    # Display health status
    print("\n" + "=" * 70)
    print("Health Status:")
    print("=" * 70)
    import json

    health = metrics.get_health_status()
    print(json.dumps(health, indent=2))

    # Display Prometheus metrics (sample)
    print("\n" + "=" * 70)
    print("Prometheus Metrics (sample):")
    print("=" * 70)
    prom_metrics = metrics.export_prometheus()
    lines = prom_metrics.split("\n")
    print("\n".join(lines[:50]))  # First 50 lines
    print("... (more metrics available)")

    # Display logger stats
    print("\n" + "=" * 70)
    print("Logger Statistics:")
    print("=" * 70)
    logger_stats = logger.get_stats()
    print(json.dumps(logger_stats, indent=2))

    # Cleanup
    print("\n" + "=" * 70)
    print("Shutting down monitoring...")
    metrics.shutdown()
    print("Done!")


def example_node_integration():
    """
    Example: How to integrate into the BlockchainNode class

    Add these lines to node.py:
    """
    integration_code = '''
# At the top of node.py
from xai.core.api.monitoring import MetricsCollector, AlertLevel
from xai.core.api.structured_logger import StructuredLogger, LogContext, PerformanceTimer

class BlockchainNode:
    def __init__(self, host=None, port=None, miner_address=None):
        # ... existing code ...

        # Initialize monitoring and logging
        self.logger = StructuredLogger('XAI_Node', log_level='INFO')
        self.metrics = MetricsCollector(blockchain=self.blockchain)

        # Setup monitoring endpoints
        self.setup_monitoring_routes()

        # Configure alerts
        self._setup_alerts()

    def setup_monitoring_routes(self):
        """Add monitoring endpoints to Flask app"""

        @self.app.route('/metrics', methods=['GET'])
        def prometheus_metrics():
            """Prometheus metrics endpoint"""
            return self.metrics.export_prometheus(), 200, {'Content-Type': 'text/plain'}

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify(self.metrics.get_health_status())

        @self.app.route('/monitoring/stats', methods=['GET'])
        def monitoring_stats():
            """Get monitoring statistics"""
            return jsonify({
                'metrics': self.metrics.get_stats(),
                'logger': self.logger.get_stats()
            })

        @self.app.route('/monitoring/alerts', methods=['GET'])
        def get_alerts():
            """Get active alerts"""
            return jsonify({
                'alerts': self.metrics.get_active_alerts()
            })

    def _setup_alerts(self):
        """Configure monitoring alerts"""

        # Memory usage alert
        self.metrics.add_alert_rule(
            'high_memory',
            lambda: self.metrics.get_metric('xai_node_memory_usage_percent').value > 85,
            'Node memory usage above 85%',
            AlertLevel.WARNING
        )

        # Mempool size alert
        self.metrics.add_alert_rule(
            'large_mempool',
            lambda: self.metrics.get_metric('xai_pending_transactions').value > 5000,
            'Mempool size exceeds 5000 transactions',
            AlertLevel.WARNING
        )

        # No peers alert
        self.metrics.add_alert_rule(
            'isolated_node',
            lambda: self.metrics.get_metric('xai_peers_connected').value == 0,
            'Node has no connected peers',
            AlertLevel.CRITICAL
        )

    def mine_block(self):
        """Enhanced mining with monitoring"""
        with LogContext() as ctx:
            start_time = time.time()

            self.logger.info("Starting block mining",
                           pending_tx=len(self.blockchain.pending_transactions))

            try:
                # Mine block
                block = self.blockchain.mine_pending_transactions(self.miner_address)

                mining_time = time.time() - start_time

                # Log and record metrics
                self.logger.block_mined(
                    block_index=block.index,
                    block_hash=block.hash,
                    miner=self.miner_address,
                    tx_count=len(block.transactions),
                    reward=self.blockchain.block_reward,
                    mining_time=mining_time
                )

                self.metrics.record_block_mined(block.index, mining_time)

                return block

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.logger.error("Block mining failed", error=str(e))
                raise

    def add_peer(self, peer_url):
        """Enhanced peer connection with monitoring"""
        with LogContext() as ctx:
            try:
                # Add peer
                self.peers.add(peer_url)

                # Log and record metrics
                self.logger.network_event('peer_connected',
                                        peer_count=len(self.peers))
                self.metrics.record_peer_connected(len(self.peers))

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.logger.error("Failed to add peer",
                                peer_url=peer_url[:20] + '...',
                                error=str(e))
'''

    print("=" * 70)
    print("Integration Code for node.py:")
    print("=" * 70)
    print(integration_code)


if __name__ == "__main__":
    # Run examples
    example_blockchain_integration()

    print("\n\n")
    example_node_integration()

    print("\n" + "=" * 70)
    print("Integration Complete!")
    print("=" * 70)
    print("\nMonitoring endpoints available:")
    print("  - GET  /metrics          - Prometheus metrics")
    print("  - GET  /health           - Health check")
    print("  - GET  /monitoring/stats - Monitoring statistics")
    print("  - GET  /monitoring/alerts - Active alerts")
    print("\nLog files created in logs/ directory:")
    print("  - xai_blockchain.json.log - Structured JSON logs")
    print("  - xai_blockchain.log      - Human-readable logs")
