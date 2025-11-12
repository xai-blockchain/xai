"""
Tests for Configuration Manager

Run with: python -m pytest tests/test_config_manager.py -v
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import (
    ConfigManager,
    get_config_manager,
    Environment,
    NetworkConfig,
    BlockchainConfig,
    SecurityConfig,
    StorageConfig,
    LoggingConfig,
    GenesisConfig
)


def test_default_configuration():
    """Test loading default configuration"""
    config = get_config_manager(force_reload=True)

    assert config.environment in [Environment.DEVELOPMENT, Environment.TESTNET,
                                  Environment.PRODUCTION, Environment.STAGING]
    assert config.network is not None
    assert config.blockchain is not None
    assert config.security is not None
    assert config.storage is not None
    assert config.logging is not None
    assert config.genesis is not None


def test_environment_specific_config():
    """Test environment-specific configuration"""
    # Production
    prod_config = get_config_manager(environment="production", force_reload=True)
    assert prod_config.environment == Environment.PRODUCTION
    assert prod_config.blockchain.difficulty == 4  # Production difficulty

    # Development
    dev_config = get_config_manager(environment="development", force_reload=True)
    assert dev_config.environment == Environment.DEVELOPMENT
    assert dev_config.blockchain.difficulty == 2  # Development difficulty


def test_cli_overrides():
    """Test command-line argument overrides"""
    cli_overrides = {
        "network.port": 9999,
        "blockchain.difficulty": 8
    }

    config = get_config_manager(
        environment="production",
        cli_overrides=cli_overrides,
        force_reload=True
    )

    assert config.network.port == 9999
    assert config.blockchain.difficulty == 8


def test_environment_variables():
    """Test environment variable overrides"""
    # Set test environment variables
    os.environ["XAI_NETWORK_PORT"] = "7777"
    os.environ["XAI_BLOCKCHAIN_DIFFICULTY"] = "6"

    config = get_config_manager(environment="production", force_reload=True)

    assert config.network.port == 7777
    assert config.blockchain.difficulty == 6

    # Clean up
    del os.environ["XAI_NETWORK_PORT"]
    del os.environ["XAI_BLOCKCHAIN_DIFFICULTY"]


def test_configuration_validation():
    """Test configuration validation"""
    # Valid configuration should work
    valid_config = NetworkConfig(port=8545, host="0.0.0.0")
    valid_config.validate()  # Should not raise

    # Invalid port should fail
    try:
        invalid_config = NetworkConfig(port=999)  # Port too low
        invalid_config.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "port" in str(e).lower()


def test_get_method():
    """Test get() method for accessing config values"""
    config = get_config_manager(force_reload=True)

    # Test dot notation
    port = config.get("network.port")
    assert port is not None

    difficulty = config.get("blockchain.difficulty")
    assert difficulty is not None

    # Test with default
    nonexistent = config.get("nonexistent.key", "default_value")
    assert nonexistent == "default_value"


def test_get_section():
    """Test get_section() method"""
    config = get_config_manager(force_reload=True)

    network_section = config.get_section("network")
    assert network_section is not None
    assert "port" in network_section
    assert "host" in network_section


def test_public_config():
    """Test public configuration export"""
    config = get_config_manager(environment="production", force_reload=True)

    public_config = config.get_public_config()

    # Should include non-sensitive values
    assert "environment" in public_config
    assert "network" in public_config
    assert "blockchain" in public_config

    # Check network info
    assert "port" in public_config["network"]
    assert "max_peers" in public_config["network"]

    # Should not include sensitive values like IP whitelists
    assert "ip_whitelist" not in str(public_config)


def test_to_dict():
    """Test configuration export to dictionary"""
    config = get_config_manager(force_reload=True)

    config_dict = config.to_dict()

    assert "environment" in config_dict
    assert "network" in config_dict
    assert "blockchain" in config_dict
    assert "security" in config_dict
    assert "storage" in config_dict
    assert "logging" in config_dict
    assert "genesis" in config_dict


def test_network_config_validation():
    """Test NetworkConfig validation"""
    # Valid config
    config = NetworkConfig(port=8545, rpc_port=8546, max_peers=50)
    config.validate()

    # Invalid port
    try:
        config = NetworkConfig(port=100000)  # Too high
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Invalid max_peers
    try:
        config = NetworkConfig(max_peers=0)
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_blockchain_config_validation():
    """Test BlockchainConfig validation"""
    # Valid config
    config = BlockchainConfig(
        difficulty=4,
        initial_block_reward=12.0,
        max_supply=121000000.0
    )
    config.validate()

    # Invalid difficulty
    try:
        config = BlockchainConfig(difficulty=100)  # Too high
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Invalid block reward
    try:
        config = BlockchainConfig(initial_block_reward=-1)
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_security_config_validation():
    """Test SecurityConfig validation"""
    # Valid config
    config = SecurityConfig(
        rate_limit_enabled=True,
        rate_limit_requests=100,
        ban_threshold=10
    )
    config.validate()

    # Invalid rate limit
    try:
        config = SecurityConfig(rate_limit_requests=0)
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_storage_config_validation():
    """Test StorageConfig validation"""
    # Valid config
    config = StorageConfig(
        data_dir="data",
        blockchain_file="blockchain.json"
    )
    config.validate()

    # Invalid backup frequency
    try:
        config = StorageConfig(backup_frequency=10)  # Too low
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_logging_config_validation():
    """Test LoggingConfig validation"""
    # Valid config
    config = LoggingConfig(level="INFO")
    config.validate()

    # Invalid log level
    try:
        config = LoggingConfig(level="INVALID")
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_genesis_config_validation():
    """Test GenesisConfig validation"""
    # Valid config
    config = GenesisConfig(
        genesis_file="genesis.json",
        address_prefix="AIXN"
    )
    config.validate()

    # Invalid timestamp
    try:
        config = GenesisConfig(genesis_timestamp=-1)
        config.validate()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_config_precedence():
    """Test configuration precedence order"""
    # Create temporary config files
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)

        # Create default config
        default_config = {
            "network": {"port": 8545},
            "blockchain": {"difficulty": 4}
        }
        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        # Create production config (overrides default)
        prod_config = {
            "network": {"port": 9545}  # Override port
        }
        with open(config_dir / "production.yaml", 'w') as f:
            yaml.dump(prod_config, f)

        # Set environment variable (overrides file)
        os.environ["XAI_BLOCKCHAIN_DIFFICULTY"] = "6"

        # CLI override (highest priority)
        cli_overrides = {"network.port": 7777}

        # Load config
        config = ConfigManager(
            environment="production",
            config_dir=str(config_dir),
            cli_overrides=cli_overrides
        )

        # Verify precedence:
        # 1. CLI override takes precedence for port
        assert config.network.port == 7777

        # 2. Environment variable takes precedence for difficulty
        assert config.blockchain.difficulty == 6

        # Clean up
        del os.environ["XAI_BLOCKCHAIN_DIFFICULTY"]


def test_reload():
    """Test configuration reload"""
    config = get_config_manager(force_reload=True)
    initial_port = config.network.port

    # Modify environment and reload
    os.environ["XAI_NETWORK_PORT"] = "9999"
    config.reload()

    assert config.network.port == 9999

    # Clean up
    del os.environ["XAI_NETWORK_PORT"]


def test_environment_determination():
    """Test environment determination logic"""
    # Test explicit environment
    config = ConfigManager(environment="production")
    assert config.environment == Environment.PRODUCTION

    # Test environment variable
    os.environ["XAI_ENVIRONMENT"] = "staging"
    config = ConfigManager()
    assert config.environment == Environment.STAGING
    del os.environ["XAI_ENVIRONMENT"]

    # Test backwards compatibility with XAI_NETWORK
    os.environ["XAI_NETWORK"] = "testnet"
    config = ConfigManager()
    assert config.environment == Environment.TESTNET
    del os.environ["XAI_NETWORK"]


if __name__ == "__main__":
    # Run tests
    print("Running configuration manager tests...")

    test_functions = [
        test_default_configuration,
        test_environment_specific_config,
        test_cli_overrides,
        test_environment_variables,
        test_configuration_validation,
        test_get_method,
        test_get_section,
        test_public_config,
        test_to_dict,
        test_network_config_validation,
        test_blockchain_config_validation,
        test_security_config_validation,
        test_storage_config_validation,
        test_logging_config_validation,
        test_genesis_config_validation,
        test_config_precedence,
        test_reload,
        test_environment_determination
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"[PASS] {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)
