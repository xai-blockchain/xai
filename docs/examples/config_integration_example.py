"""
XAI Blockchain - Configuration Integration Example

This script demonstrates how to integrate the new configuration management
system with the existing blockchain code.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import get_config_manager, ConfigManager


def example_basic_usage():
    """Basic configuration manager usage"""
    print("=" * 70)
    print("Example 1: Basic Usage")
    print("=" * 70)

    # Get config manager (uses default environment)
    config = get_config_manager()

    print(f"Environment: {config.environment.value}")
    print(f"Network Port: {config.network.port}")
    print(f"Blockchain Difficulty: {config.blockchain.difficulty}")
    print(f"Log Level: {config.logging.level}")
    print()


def example_environment_specific():
    """Load environment-specific configuration"""
    print("=" * 70)
    print("Example 2: Environment-Specific Configuration")
    print("=" * 70)

    # Production
    prod_config = get_config_manager(environment="production", force_reload=True)
    print(f"Production Port: {prod_config.network.port}")
    print(f"Production Difficulty: {prod_config.blockchain.difficulty}")
    print(f"Production Faucet: {prod_config.get('features.faucet_enabled', False)}")
    print()

    # Testnet
    testnet_config = get_config_manager(environment="testnet", force_reload=True)
    print(f"Testnet Port: {testnet_config.network.port}")
    print(f"Testnet Difficulty: {testnet_config.blockchain.difficulty}")
    print(f"Testnet Faucet: {testnet_config.get('features.faucet_enabled', False)}")
    print()


def example_cli_overrides():
    """Use command-line overrides"""
    print("=" * 70)
    print("Example 3: Command-Line Overrides")
    print("=" * 70)

    # Simulate CLI arguments
    cli_overrides = {
        "network.port": 9999,
        "blockchain.difficulty": 8,
        "logging.level": "DEBUG"
    }

    config = get_config_manager(
        environment="production",
        cli_overrides=cli_overrides,
        force_reload=True
    )

    print(f"Port (overridden): {config.network.port}")
    print(f"Difficulty (overridden): {config.blockchain.difficulty}")
    print(f"Log Level (overridden): {config.logging.level}")
    print()


def example_environment_variables():
    """Demonstrate environment variable support"""
    print("=" * 70)
    print("Example 4: Environment Variables")
    print("=" * 70)

    # Set environment variables
    os.environ["XAI_NETWORK_PORT"] = "7777"
    os.environ["XAI_BLOCKCHAIN_DIFFICULTY"] = "10"
    os.environ["XAI_LOGGING_LEVEL"] = "WARNING"

    config = get_config_manager(environment="production", force_reload=True)

    print(f"Port (from env var): {config.network.port}")
    print(f"Difficulty (from env var): {config.blockchain.difficulty}")
    print(f"Log Level (from env var): {config.logging.level}")
    print()

    # Clean up
    del os.environ["XAI_NETWORK_PORT"]
    del os.environ["XAI_BLOCKCHAIN_DIFFICULTY"]
    del os.environ["XAI_LOGGING_LEVEL"]


def example_blockchain_integration():
    """Show how to integrate with blockchain code"""
    print("=" * 70)
    print("Example 5: Blockchain Integration")
    print("=" * 70)

    config = get_config_manager(environment="production", force_reload=True)

    # Example: Initialize blockchain with config
    print("Blockchain initialization with config:")
    print(f"  Difficulty: {config.blockchain.difficulty}")
    print(f"  Block Reward: {config.blockchain.initial_block_reward}")
    print(f"  Max Supply: {config.blockchain.max_supply:,.0f}")
    print(f"  Halving Interval: {config.blockchain.halving_interval:,}")
    print()

    # Example: Network settings
    print("Network configuration:")
    print(f"  Host: {config.network.host}")
    print(f"  Port: {config.network.port}")
    print(f"  Max Peers: {config.network.max_peers}")
    print(f"  P2P Enabled: {config.network.p2p_enabled}")
    print()


def example_node_integration():
    """Show how to integrate with node code"""
    print("=" * 70)
    print("Example 6: Node Integration")
    print("=" * 70)

    config = get_config_manager(environment="testnet", force_reload=True)

    # Simulate node initialization
    print("Node initialization with config:")
    print(f"  Environment: {config.environment.value}")
    print(f"  Network: {config.genesis.address_prefix}")
    print(f"  Data Directory: {config.storage.data_dir}")
    print(f"  Blockchain File: {config.storage.blockchain_file}")
    print(f"  Genesis File: {config.genesis.genesis_file}")
    print()

    # Security settings
    print("Security configuration:")
    print(f"  Rate Limiting: {config.security.rate_limit_enabled}")
    print(f"  Max Requests: {config.security.rate_limit_requests}/{config.security.rate_limit_window}s")
    print(f"  Ban Threshold: {config.security.ban_threshold}")
    print(f"  Max Mempool: {config.security.max_mempool_size}")
    print()


def example_public_config():
    """Get public configuration for API exposure"""
    print("=" * 70)
    print("Example 7: Public Configuration (for /config endpoint)")
    print("=" * 70)

    config = get_config_manager(environment="production", force_reload=True)

    # Get public config (non-sensitive values only)
    public_config = config.get_public_config()

    print("Public configuration (safe to expose via API):")
    import json
    print(json.dumps(public_config, indent=2))
    print()


def example_validation():
    """Demonstrate configuration validation"""
    print("=" * 70)
    print("Example 8: Configuration Validation")
    print("=" * 70)

    # This will work
    try:
        valid_overrides = {
            "network.port": 8545,
            "blockchain.difficulty": 4
        }
        config = get_config_manager(
            environment="production",
            cli_overrides=valid_overrides,
            force_reload=True
        )
        print("Valid configuration loaded successfully")
    except Exception as e:
        print(f"Error: {e}")

    # This will fail validation
    try:
        invalid_overrides = {
            "network.port": 99999,  # Invalid port
            "blockchain.difficulty": -1  # Invalid difficulty
        }
        config = get_config_manager(
            environment="production",
            cli_overrides=invalid_overrides,
            force_reload=True
        )
    except Exception as e:
        print(f"Validation error (expected): {e}")

    print()


def example_config_sections():
    """Access different configuration sections"""
    print("=" * 70)
    print("Example 9: Accessing Configuration Sections")
    print("=" * 70)

    config = get_config_manager(environment="production", force_reload=True)

    # Access typed configuration objects
    print("Network Config:")
    print(f"  Port: {config.network.port}")
    print(f"  Host: {config.network.host}")
    print()

    print("Blockchain Config:")
    print(f"  Difficulty: {config.blockchain.difficulty}")
    print(f"  Block Time: {config.blockchain.block_time_target}s")
    print()

    print("Storage Config:")
    print(f"  Data Dir: {config.storage.data_dir}")
    print(f"  Backups: {config.storage.backup_enabled}")
    print()

    print("Logging Config:")
    print(f"  Level: {config.logging.level}")
    print(f"  File: {config.logging.log_file}")
    print()


def example_full_integration():
    """Complete integration example"""
    print("=" * 70)
    print("Example 10: Complete Integration Pattern")
    print("=" * 70)

    # This is how you would integrate into blockchain.py
    print("""
# In blockchain.py:

from config_manager import get_config_manager

class Blockchain:
    def __init__(self, config_manager=None):
        # Get or use provided config
        self.config = config_manager or get_config_manager()

        # Use config values instead of hardcoded values
        self.difficulty = self.config.blockchain.difficulty
        self.initial_block_reward = self.config.blockchain.initial_block_reward
        self.halving_interval = self.config.blockchain.halving_interval
        self.max_supply = self.config.blockchain.max_supply
        self.transaction_fee_percent = self.config.blockchain.transaction_fee_percent

        # ... rest of initialization

# In node.py:

from config_manager import get_config_manager

class BlockchainNode:
    def __init__(self, config_manager=None):
        # Get or use provided config
        self.config = config_manager or get_config_manager()

        # Use config for network settings
        self.host = self.config.network.host
        self.port = self.config.network.port
        self.max_peers = self.config.network.max_peers

        # Initialize blockchain with same config
        self.blockchain = Blockchain(config_manager=self.config)

        # Use config for storage
        self.data_dir = self.config.storage.data_dir
        self.blockchain_file = self.config.storage.blockchain_file

        # ... rest of initialization

# Running the node:

if __name__ == "__main__":
    # Load config from environment and CLI
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--environment', default='production')
    parser.add_argument('--port', type=int)
    parser.add_argument('--difficulty', type=int)
    args = parser.parse_args()

    # Build CLI overrides
    cli_overrides = {}
    if args.port:
        cli_overrides['network.port'] = args.port
    if args.difficulty:
        cli_overrides['blockchain.difficulty'] = args.difficulty

    # Initialize config
    config = get_config_manager(
        environment=args.environment,
        cli_overrides=cli_overrides
    )

    # Create and run node
    node = BlockchainNode(config_manager=config)
    node.run()
    """)


def main():
    """Run all examples"""
    examples = [
        example_basic_usage,
        example_environment_specific,
        example_cli_overrides,
        example_environment_variables,
        example_blockchain_integration,
        example_node_integration,
        example_public_config,
        example_validation,
        example_config_sections,
        example_full_integration
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 70)
    print("Examples Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
