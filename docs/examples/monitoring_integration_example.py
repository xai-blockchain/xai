"""
XAI Blockchain - Monitoring Integration Example

This example demonstrates how to integrate Prometheus metrics
into your XAI blockchain node.
"""

import time
import random
from src.xai.core.prometheus_metrics import initialize_metrics, get_metrics


class BlockchainNodeExample:
    """Example blockchain node with monitoring integration"""

    def __init__(self):
        # Initialize metrics on port 8000
        self.metrics = initialize_metrics(
            port=8000,
            version="1.0.0",
            network="mainnet",
            node_id="example-node-001"
        )

        self.current_height = 0
        self.peers = []
        self.mempool = []

    def mine_block(self):
        """Simulate mining a block with metrics"""
        print(f"\nMining block {self.current_height + 1}...")
        start_time = time.time()

        # Simulate mining attempts
        attempts = 0
        while True:
            attempts += 1
            self.metrics.record_mining_attempt(success=False)

            # Simulate mining difficulty
            if random.random() < 0.01:  # 1% success rate
                # Block mined successfully!
                self.current_height += 1
                mining_time = time.time() - start_time
                block_size = random.randint(1000, 100000)
                difficulty = random.randint(100000, 1000000)

                # Record block metrics
                self.metrics.record_block(
                    height=self.current_height,
                    size=block_size,
                    difficulty=difficulty,
                    mining_time=mining_time
                )
                self.metrics.record_mining_attempt(success=True)

                print(f"✓ Block {self.current_height} mined!")
                print(f"  Mining time: {mining_time:.2f}s")
                print(f"  Attempts: {attempts}")
                print(f"  Size: {block_size:,} bytes")
                print(f"  Difficulty: {difficulty:,}")
                break

            time.sleep(0.01)

    def process_transaction(self):
        """Simulate processing a transaction with metrics"""
        start_time = time.time()

        # Generate random transaction
        tx_value = random.uniform(0.1, 1000)
        tx_fee = tx_value * 0.001

        # Simulate processing
        time.sleep(random.uniform(0.01, 0.5))

        # Random success/failure
        if random.random() < 0.95:  # 95% success rate
            status = 'confirmed'
            print(f"✓ Transaction confirmed: {tx_value:.4f} XAI (fee: {tx_fee:.6f})")
        else:
            status = 'failed'
            print(f"✗ Transaction failed")

        # Record transaction metrics
        processing_time = time.time() - start_time
        self.metrics.record_transaction(
            status=status,
            value=tx_value,
            fee=tx_fee,
            processing_time=processing_time
        )

    def update_network(self):
        """Simulate network activity with metrics"""
        # Simulate peer connections
        if random.random() < 0.3:  # 30% chance to change peers
            if random.random() < 0.5 and len(self.peers) < 10:
                # Add peer
                peer = f"peer-{random.randint(1000, 9999)}"
                self.peers.append(peer)
                print(f"+ Peer connected: {peer}")
            elif self.peers:
                # Remove peer
                peer = self.peers.pop(random.randint(0, len(self.peers) - 1))
                print(f"- Peer disconnected: {peer}")

        # Update peer count metric
        self.metrics.update_peer_count(len(self.peers))

        # Simulate network messages
        message_types = ['block', 'transaction', 'ping', 'sync']
        for _ in range(random.randint(1, 10)):
            msg_type = random.choice(message_types)
            self.metrics.record_network_message(msg_type)

    def update_mempool(self):
        """Simulate mempool changes with metrics"""
        # Add new transactions to mempool
        new_txs = random.randint(0, 5)
        for _ in range(new_txs):
            self.mempool.append(f"tx-{random.randint(10000, 99999)}")

        # Remove confirmed transactions
        if self.mempool:
            confirmed = random.randint(0, min(3, len(self.mempool)))
            self.mempool = self.mempool[confirmed:]

        # Update mempool size metric
        self.metrics.update_mempool_size(len(self.mempool))

    def simulate_api_request(self):
        """Simulate API requests with metrics"""
        endpoints = ['/api/blocks', '/api/transactions', '/api/peers', '/api/status']
        methods = ['GET', 'POST']

        endpoint = random.choice(endpoints)
        method = random.choice(methods)

        start_time = time.time()

        # Simulate request processing
        time.sleep(random.uniform(0.001, 0.1))

        # Random success/failure
        if random.random() < 0.98:  # 98% success rate
            status = 200
        else:
            status = 500

        duration = time.time() - start_time

        # Record API request metrics
        self.metrics.record_api_request(endpoint, method, status, duration)

    def run(self, duration_seconds=300):
        """
        Run the example blockchain node with monitoring

        Args:
            duration_seconds: How long to run the simulation (default: 5 minutes)
        """
        print("=" * 60)
        print("XAI Blockchain Node - Monitoring Example")
        print("=" * 60)
        print(f"\nMetrics endpoint: http://localhost:8000/metrics")
        print(f"Running for {duration_seconds} seconds...\n")

        start_time = time.time()
        last_block_time = time.time()
        last_system_update = time.time()

        try:
            while time.time() - start_time < duration_seconds:
                # Mine a block every 30-60 seconds
                if time.time() - last_block_time > random.uniform(30, 60):
                    self.mine_block()
                    last_block_time = time.time()

                # Process transactions
                if random.random() < 0.8:  # 80% chance
                    self.process_transaction()

                # Update network metrics
                if random.random() < 0.5:  # 50% chance
                    self.update_network()

                # Update mempool
                self.update_mempool()

                # Simulate API requests
                for _ in range(random.randint(0, 3)):
                    self.simulate_api_request()

                # Update system metrics every 5 seconds
                if time.time() - last_system_update > 5:
                    self.metrics.update_system_metrics()
                    last_system_update = time.time()

                # Sleep between iterations
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nStopping node...")

        print("\n" + "=" * 60)
        print("Simulation complete!")
        print("=" * 60)
        print("\nFinal Stats:")
        print(f"  Blocks mined: {self.current_height}")
        print(f"  Connected peers: {len(self.peers)}")
        print(f"  Mempool size: {len(self.mempool)}")
        print(f"\nMetrics still available at: http://localhost:8000/metrics")
        print("Press Ctrl+C to exit...")

        # Keep metrics server running
        try:
            while True:
                self.metrics.update_system_metrics()
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nShutting down...")


def main():
    """Main entry point"""
    # Create and run example node
    node = BlockchainNodeExample()
    node.run(duration_seconds=300)  # Run for 5 minutes


if __name__ == "__main__":
    main()
