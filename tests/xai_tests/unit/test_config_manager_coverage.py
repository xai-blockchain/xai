"""
Comprehensive test coverage for ConfigManager module

Tests for:
- NetworkConfig initialization and validation
- BlockchainConfig initialization and validation
- SecurityConfig initialization and validation
- StorageConfig initialization and validation
- LoggingConfig initialization and validation
- GenesisConfig initialization and validation
- ConfigManager environment detection
- Configuration file loading (YAML/JSON)
- Environment variable handling
- CLI override handling
- Config merging and validation
- Singleton pattern
"""

import pytest
import os
import json
import yaml
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

from xai.config_manager import (
    NetworkConfig,
    BlockchainConfig,
    SecurityConfig,
    StorageConfig,
    LoggingConfig,
    GenesisConfig,
    ConfigManager,
    Environment,
    NetworkType,
    get_config_manager,
    _config_manager,
)


class TestNetworkConfig:
    """Test NetworkConfig class"""

    def test_default_initialization(self):
        """Test NetworkConfig initializes with defaults"""
        config = NetworkConfig()
        assert config.port == 8545
        assert config.host == "127.0.0.1"
        assert config.rpc_port == 8546
        assert config.max_peers == 50
        assert config.peer_timeout == 30
        assert config.sync_interval == 60
        assert config.p2p_enabled is True

    def test_custom_initialization(self):
        """Test NetworkConfig with custom values"""
        config = NetworkConfig(
            port=9000,
            host="192.168.1.100",
            rpc_port=9001,
            max_peers=100,
            peer_timeout=60,
            sync_interval=120,
            p2p_enabled=False,
        )
        assert config.port == 9000
        assert config.host == "192.168.1.100"
        assert config.rpc_port == 9001
        assert config.max_peers == 100
        assert config.peer_timeout == 60
        assert config.sync_interval == 120
        assert config.p2p_enabled is False

    def test_host_security_warning(self):
        """Test security warning for binding to all interfaces"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = NetworkConfig(host="0.0.0.0")
            assert len(w) == 1
            assert issubclass(w[0].category, Warning)
            assert "0.0.0.0" in str(w[0].message)
            assert "production" in str(w[0].message).lower()

    def test_validate_valid_config(self):
        """Test validation passes for valid config"""
        config = NetworkConfig()
        config.validate()  # Should not raise

    def test_validate_port_too_low(self):
        """Test validation fails for port below 1024"""
        config = NetworkConfig(port=1023)
        with pytest.raises(ValueError, match="Invalid port.*1023.*Must be between 1024-65535"):
            config.validate()

    def test_validate_port_too_high(self):
        """Test validation fails for port above 65535"""
        config = NetworkConfig(port=65536)
        with pytest.raises(ValueError, match="Invalid port.*65536.*Must be between 1024-65535"):
            config.validate()

    def test_validate_rpc_port_too_low(self):
        """Test validation fails for RPC port below 1024"""
        config = NetworkConfig(rpc_port=1023)
        with pytest.raises(ValueError, match="Invalid RPC port.*1023.*Must be between 1024-65535"):
            config.validate()

    def test_validate_rpc_port_too_high(self):
        """Test validation fails for RPC port above 65535"""
        config = NetworkConfig(rpc_port=65536)
        with pytest.raises(ValueError, match="Invalid RPC port.*65536.*Must be between 1024-65535"):
            config.validate()

    def test_validate_same_ports(self):
        """Test validation fails when port and RPC port are same"""
        config = NetworkConfig(port=8545, rpc_port=8545)
        with pytest.raises(ValueError, match="Port and RPC port must be different.*8545"):
            config.validate()

    def test_validate_max_peers_too_low(self):
        """Test validation fails for max_peers < 1"""
        config = NetworkConfig(max_peers=0)
        with pytest.raises(ValueError, match="Invalid max_peers.*0.*Must be >= 1"):
            config.validate()

    def test_validate_max_peers_too_high(self):
        """Test validation fails for max_peers > 10000"""
        config = NetworkConfig(max_peers=10001)
        with pytest.raises(ValueError, match="Invalid max_peers.*10001.*Must be <= 10000"):
            config.validate()

    def test_validate_peer_timeout_too_low(self):
        """Test validation fails for peer_timeout < 1"""
        config = NetworkConfig(peer_timeout=0)
        with pytest.raises(ValueError, match="Invalid peer_timeout.*0.*Must be >= 1"):
            config.validate()

    def test_validate_sync_interval_too_low(self):
        """Test validation fails for sync_interval < 1"""
        config = NetworkConfig(sync_interval=0)
        with pytest.raises(ValueError, match="Invalid sync_interval.*0.*Must be >= 1"):
            config.validate()


class TestBlockchainConfig:
    """Test BlockchainConfig class"""

    def test_default_initialization(self):
        """Test BlockchainConfig initializes with defaults"""
        config = BlockchainConfig()
        assert config.difficulty == 4
        assert config.block_time_target == 120
        assert config.initial_block_reward == 12.0
        assert config.halving_interval == 262800
        assert config.max_supply == 121000000.0
        assert config.max_block_size == 1048576
        assert config.min_transaction_fee == 0.0001
        assert config.transaction_fee_percent == 0.24

    def test_validate_difficulty_too_low(self):
        """Test validation fails for difficulty < 1"""
        config = BlockchainConfig(difficulty=0)
        with pytest.raises(ValueError, match="Invalid difficulty.*0.*Must be between 1-32"):
            config.validate()

    def test_validate_difficulty_too_high(self):
        """Test validation fails for difficulty > 32"""
        config = BlockchainConfig(difficulty=33)
        with pytest.raises(ValueError, match="Invalid difficulty.*33.*Must be between 1-32"):
            config.validate()

    def test_validate_block_time_target_too_low(self):
        """Test validation fails for block_time_target < 1"""
        config = BlockchainConfig(block_time_target=0)
        with pytest.raises(ValueError, match="Invalid block_time_target.*0.*Must be >= 1"):
            config.validate()

    def test_validate_initial_block_reward_zero(self):
        """Test validation fails for zero initial_block_reward"""
        config = BlockchainConfig(initial_block_reward=0)
        with pytest.raises(ValueError, match="Invalid initial_block_reward.*0.*Must be > 0"):
            config.validate()

    def test_validate_initial_block_reward_negative(self):
        """Test validation fails for negative initial_block_reward"""
        config = BlockchainConfig(initial_block_reward=-1)
        with pytest.raises(ValueError, match="Invalid initial_block_reward.*-1.*Must be > 0"):
            config.validate()

    def test_validate_halving_interval_zero(self):
        """Test validation fails for zero halving_interval"""
        config = BlockchainConfig(halving_interval=0)
        with pytest.raises(ValueError, match="Invalid halving_interval.*0.*Must be > 0"):
            config.validate()

    def test_validate_halving_interval_negative(self):
        """Test validation fails for negative halving_interval"""
        config = BlockchainConfig(halving_interval=-1)
        with pytest.raises(ValueError, match="Invalid halving_interval.*-1.*Must be > 0"):
            config.validate()

    def test_validate_max_supply_zero(self):
        """Test validation fails for zero max_supply"""
        config = BlockchainConfig(max_supply=0)
        with pytest.raises(ValueError, match="Invalid max_supply.*0.*Must be > 0"):
            config.validate()

    def test_validate_max_supply_negative(self):
        """Test validation fails for negative max_supply"""
        config = BlockchainConfig(max_supply=-1)
        with pytest.raises(ValueError, match="Invalid max_supply.*-1.*Must be > 0"):
            config.validate()

    def test_validate_max_block_size_too_small(self):
        """Test validation fails for max_block_size < 1024"""
        config = BlockchainConfig(max_block_size=1023)
        with pytest.raises(ValueError, match="Invalid max_block_size.*1023.*Must be >= 1024"):
            config.validate()

    def test_validate_max_block_size_too_large(self):
        """Test validation fails for max_block_size > 10MB"""
        config = BlockchainConfig(max_block_size=10485761)
        with pytest.raises(ValueError, match="Invalid max_block_size.*10485761.*Must be <= 10MB"):
            config.validate()

    def test_validate_min_transaction_fee_negative(self):
        """Test validation fails for negative min_transaction_fee"""
        config = BlockchainConfig(min_transaction_fee=-0.1)
        with pytest.raises(ValueError, match="Invalid min_transaction_fee.*-0.1.*Must be >= 0"):
            config.validate()

    def test_validate_transaction_fee_percent_negative(self):
        """Test validation fails for negative transaction_fee_percent"""
        config = BlockchainConfig(transaction_fee_percent=-1)
        with pytest.raises(ValueError, match="Invalid transaction_fee_percent.*-1.*Must be 0-100"):
            config.validate()

    def test_validate_transaction_fee_percent_too_high(self):
        """Test validation fails for transaction_fee_percent > 100"""
        config = BlockchainConfig(transaction_fee_percent=101)
        with pytest.raises(ValueError, match="Invalid transaction_fee_percent.*101.*Must be 0-100"):
            config.validate()


class TestSecurityConfig:
    """Test SecurityConfig class"""

    def test_default_initialization(self):
        """Test SecurityConfig initializes with defaults"""
        config = SecurityConfig()
        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60
        assert config.ban_threshold == 10
        assert config.ban_duration == 3600
        assert config.enable_ip_whitelist is False
        assert config.ip_whitelist == []
        assert config.enable_ip_blacklist is True
        assert config.ip_blacklist == []
        assert config.max_transaction_size == 102400
        assert config.max_mempool_size == 10000

    def test_validate_rate_limit_requests_too_low(self):
        """Test validation fails for rate_limit_requests < 1"""
        config = SecurityConfig(rate_limit_requests=0)
        with pytest.raises(ValueError, match="Invalid rate_limit_requests.*0.*Must be >= 1"):
            config.validate()

    def test_validate_rate_limit_window_too_low(self):
        """Test validation fails for rate_limit_window < 1"""
        config = SecurityConfig(rate_limit_window=0)
        with pytest.raises(ValueError, match="Invalid rate_limit_window.*0.*Must be >= 1"):
            config.validate()

    def test_validate_ban_threshold_too_low(self):
        """Test validation fails for ban_threshold < 1"""
        config = SecurityConfig(ban_threshold=0)
        with pytest.raises(ValueError, match="Invalid ban_threshold.*0.*Must be >= 1"):
            config.validate()

    def test_validate_max_mempool_size_too_low(self):
        """Test validation fails for max_mempool_size < 1"""
        config = SecurityConfig(max_mempool_size=0)
        with pytest.raises(ValueError, match="Invalid max_mempool_size.*0.*Must be >= 1"):
            config.validate()


class TestStorageConfig:
    """Test StorageConfig class"""

    def test_default_initialization(self):
        """Test StorageConfig initializes with defaults"""
        config = StorageConfig()
        assert config.data_dir == "data"
        assert config.blockchain_file == "blockchain.json"
        assert config.wallet_dir == "wallets"
        assert config.backup_enabled is True
        assert config.backup_frequency == 3600
        assert config.backup_retention == 7
        assert config.max_backup_count == 10
        assert config.enable_compression is True

    def test_validate_empty_data_dir(self):
        """Test validation fails for empty data_dir"""
        config = StorageConfig(data_dir="")
        with pytest.raises(ValueError, match="data_dir cannot be empty"):
            config.validate()

    def test_validate_empty_blockchain_file(self):
        """Test validation fails for empty blockchain_file"""
        config = StorageConfig(blockchain_file="")
        with pytest.raises(ValueError, match="blockchain_file cannot be empty"):
            config.validate()

    def test_validate_backup_frequency_too_low(self):
        """Test validation fails for backup_frequency < 60"""
        config = StorageConfig(backup_frequency=59)
        with pytest.raises(ValueError, match="Invalid backup_frequency.*59.*Must be >= 60"):
            config.validate()

    def test_validate_backup_retention_too_low(self):
        """Test validation fails for backup_retention < 1"""
        config = StorageConfig(backup_retention=0)
        with pytest.raises(ValueError, match="Invalid backup_retention.*0.*Must be >= 1"):
            config.validate()


class TestLoggingConfig:
    """Test LoggingConfig class"""

    def test_default_initialization(self):
        """Test LoggingConfig initializes with defaults"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
        assert config.enable_file_logging is True
        assert config.log_file == "logs/node.log"
        assert config.max_log_size == 10485760
        assert config.log_retention == 7
        assert config.enable_console_logging is True
        assert config.enable_anonymous_logging is True

    def test_validate_invalid_log_level(self):
        """Test validation fails for invalid log level"""
        config = LoggingConfig(level="INVALID")
        with pytest.raises(ValueError, match="Invalid log level.*INVALID"):
            config.validate()

    def test_validate_case_insensitive_log_level(self):
        """Test validation accepts case-insensitive log levels"""
        for level in ["debug", "info", "warning", "error", "critical"]:
            config = LoggingConfig(level=level)
            config.validate()  # Should not raise

    def test_validate_max_log_size_too_small(self):
        """Test validation fails for max_log_size < 1024"""
        config = LoggingConfig(max_log_size=1023)
        with pytest.raises(ValueError, match="Invalid max_log_size.*1023.*Must be >= 1024"):
            config.validate()


class TestGenesisConfig:
    """Test GenesisConfig class"""

    def test_default_initialization(self):
        """Test GenesisConfig initializes with defaults"""
        config = GenesisConfig()
        assert config.genesis_file == "genesis_new.json"
        assert config.genesis_timestamp == 1704067200.0
        assert config.network_id == 0x5841
        assert config.address_prefix == "XAI"

    def test_validate_empty_genesis_file(self):
        """Test validation fails for empty genesis_file"""
        config = GenesisConfig(genesis_file="")
        with pytest.raises(ValueError, match="genesis_file cannot be empty"):
            config.validate()

    def test_validate_genesis_timestamp_zero(self):
        """Test validation fails for zero genesis_timestamp"""
        config = GenesisConfig(genesis_timestamp=0)
        with pytest.raises(ValueError, match="Invalid genesis_timestamp.*0.*Must be > 0"):
            config.validate()

    def test_validate_genesis_timestamp_negative(self):
        """Test validation fails for negative genesis_timestamp"""
        config = GenesisConfig(genesis_timestamp=-1)
        with pytest.raises(ValueError, match="Invalid genesis_timestamp.*-1.*Must be > 0"):
            config.validate()

    def test_validate_empty_address_prefix(self):
        """Test validation fails for empty address_prefix"""
        config = GenesisConfig(address_prefix="")
        with pytest.raises(ValueError, match="address_prefix cannot be empty"):
            config.validate()


class TestEnvironmentDetection:
    """Test ConfigManager environment detection"""

    def test_determine_environment_from_parameter(self):
        """Test environment determination from parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(environment="production", config_dir=tmpdir)
            assert manager.environment == Environment.PRODUCTION

    def test_determine_environment_development_aliases(self):
        """Test development environment aliases"""
        for alias in ["dev", "development"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(environment=alias, config_dir=tmpdir)
                assert manager.environment == Environment.DEVELOPMENT

    def test_determine_environment_staging_aliases(self):
        """Test staging environment aliases"""
        for alias in ["stage", "staging"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(environment=alias, config_dir=tmpdir)
                assert manager.environment == Environment.STAGING

    def test_determine_environment_production_aliases(self):
        """Test production environment aliases"""
        for alias in ["prod", "production"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(environment=alias, config_dir=tmpdir)
                assert manager.environment == Environment.PRODUCTION

    def test_determine_environment_testnet_aliases(self):
        """Test testnet environment aliases"""
        for alias in ["test", "testnet"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(environment=alias, config_dir=tmpdir)
                assert manager.environment == Environment.TESTNET

    def test_determine_environment_from_env_var(self):
        """Test environment determination from XAI_ENVIRONMENT env var"""
        with patch.dict(os.environ, {"XAI_ENVIRONMENT": "staging"}):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.environment == Environment.STAGING

    def test_determine_environment_from_legacy_env_var(self):
        """Test environment determination from XAI_NETWORK env var (legacy)"""
        with patch.dict(os.environ, {"XAI_NETWORK": "testnet"}, clear=False):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.environment == Environment.TESTNET

    def test_determine_environment_default(self):
        """Test environment defaults to DEVELOPMENT"""
        with patch.dict(os.environ, {}, clear=True):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.environment == Environment.DEVELOPMENT

    def test_determine_environment_invalid_fallback(self):
        """Test invalid environment falls back to DEVELOPMENT"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(environment="invalid", config_dir=tmpdir)
            assert manager.environment == Environment.DEVELOPMENT


class TestConfigFileLoading:
    """Test configuration file loading"""

    def test_load_yaml_config(self):
        """Test loading YAML configuration file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"
            config_data = {
                "network": {"port": 9000},
                "blockchain": {"difficulty": 5},
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 9000
            assert manager.blockchain.difficulty == 5

    def test_load_json_config(self):
        """Test loading JSON configuration file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.json"
            config_data = {
                "network": {"port": 9001},
                "blockchain": {"difficulty": 6},
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 9001
            assert manager.blockchain.difficulty == 6

    def test_yaml_takes_precedence_over_json(self):
        """Test YAML file takes precedence over JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "default.yaml"
            json_path = Path(tmpdir) / "default.json"

            yaml_data = {"network": {"port": 9000}}
            json_data = {"network": {"port": 9001}}

            with open(yaml_path, "w") as f:
                yaml.dump(yaml_data, f)
            with open(json_path, "w") as f:
                json.dump(json_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 9000

    def test_missing_config_file_returns_defaults(self):
        """Test missing config file returns default values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 8545  # Default value


class TestConfigMerging:
    """Test configuration merging"""

    def test_environment_config_overrides_default(self):
        """Test environment-specific config overrides default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            production_path = Path(tmpdir) / "production.yaml"

            default_data = {"network": {"port": 8545}}
            production_data = {"network": {"port": 9000}}

            with open(default_path, "w") as f:
                yaml.dump(default_data, f)
            with open(production_path, "w") as f:
                yaml.dump(production_data, f)

            manager = ConfigManager(environment="production", config_dir=tmpdir)
            assert manager.network.port == 9000

    def test_deep_merge_nested_configs(self):
        """Test deep merging of nested configuration dictionaries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            production_path = Path(tmpdir) / "production.yaml"

            default_data = {
                "network": {"port": 8545, "host": "127.0.0.1"},
                "blockchain": {"difficulty": 4},
            }
            production_data = {
                "network": {"port": 9000},  # Override only port
            }

            with open(default_path, "w") as f:
                yaml.dump(default_data, f)
            with open(production_path, "w") as f:
                yaml.dump(production_data, f)

            manager = ConfigManager(environment="production", config_dir=tmpdir)
            assert manager.network.port == 9000
            assert manager.network.host == "127.0.0.1"  # Should preserve default
            assert manager.blockchain.difficulty == 4  # Should preserve default


class TestEnvironmentVariables:
    """Test environment variable handling"""

    def test_apply_env_variables_network_port(self):
        """Test environment variable override for network port"""
        with patch.dict(os.environ, {"XAI_NETWORK_PORT": "9999"}):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.network.port == 9999

    def test_apply_env_variables_blockchain_difficulty(self):
        """Test environment variable override for blockchain difficulty"""
        with patch.dict(os.environ, {"XAI_BLOCKCHAIN_DIFFICULTY": "8"}):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.blockchain.difficulty == 8

    def test_parse_env_value_boolean_true(self):
        """Test parsing boolean true values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            for value in ["true", "True", "TRUE", "yes", "Yes", "1", "on"]:
                assert manager._parse_env_value(value) is True

    def test_parse_env_value_boolean_false(self):
        """Test parsing boolean false values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            for value in ["false", "False", "FALSE", "no", "No", "0", "off"]:
                assert manager._parse_env_value(value) is False

    def test_parse_env_value_integer(self):
        """Test parsing integer values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager._parse_env_value("42") == 42
            assert manager._parse_env_value("-100") == -100

    def test_parse_env_value_float(self):
        """Test parsing float values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager._parse_env_value("3.14") == 3.14
            assert manager._parse_env_value("-2.5") == -2.5

    def test_parse_env_value_string(self):
        """Test parsing string values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager._parse_env_value("hello") == "hello"
            assert manager._parse_env_value("test_value") == "test_value"

    def test_skip_special_env_variables(self):
        """Test that special XAI_ env vars are skipped"""
        with patch.dict(
            os.environ,
            {
                "XAI_ENVIRONMENT": "production",
                "XAI_NETWORK": "mainnet",
                "XAI_HOST": "192.168.1.1",
                "XAI_PORT": "8080",
            },
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                # These should not affect the network config
                assert manager.environment == Environment.PRODUCTION


class TestCLIOverrides:
    """Test CLI override handling"""

    def test_cli_override_single_level(self):
        """Test CLI override for single-level key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_overrides = {"environment": "testnet"}
            manager = ConfigManager(config_dir=tmpdir, cli_overrides=cli_overrides)
            assert manager._raw_config.get("environment") == "testnet"

    def test_cli_override_nested_key(self):
        """Test CLI override for nested key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_overrides = {"network.port": 7777}
            manager = ConfigManager(config_dir=tmpdir, cli_overrides=cli_overrides)
            assert manager.network.port == 7777

    def test_cli_override_multiple_keys(self):
        """Test CLI override for multiple keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_overrides = {
                "network.port": 7777,
                "blockchain.difficulty": 10,
            }
            manager = ConfigManager(config_dir=tmpdir, cli_overrides=cli_overrides)
            assert manager.network.port == 7777
            assert manager.blockchain.difficulty == 10

    def test_cli_override_creates_section(self):
        """Test CLI override creates missing section"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_overrides = {"newsection.key": "value"}
            manager = ConfigManager(config_dir=tmpdir, cli_overrides=cli_overrides)
            assert manager._raw_config.get("newsection", {}).get("key") == "value"


class TestConfigManagerMethods:
    """Test ConfigManager utility methods"""

    def test_get_method_simple_key(self):
        """Test get method with simple key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 9000}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.get("network.port") == 9000

    def test_get_method_nested_key(self):
        """Test get method with nested key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"section": {"subsection": {"key": "value"}}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.get("section.subsection.key") == "value"

    def test_get_method_missing_key_returns_default(self):
        """Test get method returns default for missing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager.get("nonexistent.key", "default_value") == "default_value"

    def test_get_method_missing_key_returns_none(self):
        """Test get method returns None for missing key without default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager.get("nonexistent.key") is None

    def test_get_section_method(self):
        """Test get_section method"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 9000, "host": "localhost"}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            section = manager.get_section("network")
            assert section["port"] == 9000
            assert section["host"] == "localhost"

    def test_get_section_missing_returns_none(self):
        """Test get_section returns None for missing section"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager.get_section("nonexistent") is None

    def test_to_dict_method(self):
        """Test to_dict method exports complete config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            config_dict = manager.to_dict()

            assert "environment" in config_dict
            assert "network" in config_dict
            assert "blockchain" in config_dict
            assert "security" in config_dict
            assert "storage" in config_dict
            assert "logging" in config_dict
            assert "genesis" in config_dict

    def test_get_public_config_method(self):
        """Test get_public_config method filters sensitive data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            public_config = manager.get_public_config()

            assert "environment" in public_config
            assert "network" in public_config
            assert "blockchain" in public_config
            assert "genesis" in public_config

            # Check network only includes public fields
            assert "port" in public_config["network"]
            assert "max_peers" in public_config["network"]
            assert "p2p_enabled" in public_config["network"]
            # Host should not be exposed
            assert "host" not in public_config["network"]

    def test_reload_method(self):
        """Test reload method reloads configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 8545}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 8545

            # Update config file
            config_data["network"]["port"] = 9999
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager.reload()
            assert manager.network.port == 9999

    def test_repr_method(self):
        """Test __repr__ method"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(environment="production", config_dir=tmpdir)
            repr_str = repr(manager)
            assert "ConfigManager" in repr_str
            assert "production" in repr_str


class TestSingletonPattern:
    """Test ConfigManager singleton pattern"""

    def test_get_config_manager_singleton(self):
        """Test get_config_manager returns singleton instance"""
        import xai.config_manager as cm

        # Reset singleton
        cm._config_manager = None

        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = get_config_manager(config_dir=tmpdir)
            manager2 = get_config_manager(config_dir=tmpdir)
            assert manager1 is manager2

    def test_get_config_manager_force_reload(self):
        """Test get_config_manager with force_reload creates new instance"""
        import xai.config_manager as cm

        # Reset singleton
        cm._config_manager = None

        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = get_config_manager(config_dir=tmpdir)
            manager2 = get_config_manager(config_dir=tmpdir, force_reload=True)
            assert manager1 is not manager2

    def test_get_config_manager_with_parameters(self):
        """Test get_config_manager accepts all parameters"""
        import xai.config_manager as cm

        # Reset singleton
        cm._config_manager = None

        with tempfile.TemporaryDirectory() as tmpdir:
            cli_overrides = {"network.port": 7777}
            manager = get_config_manager(
                environment="staging",
                config_dir=tmpdir,
                cli_overrides=cli_overrides,
                force_reload=True,
            )
            assert manager.environment == Environment.STAGING
            assert manager.network.port == 7777


class TestComplexScenarios:
    """Test complex configuration scenarios"""

    def test_full_override_precedence(self):
        """Test complete override precedence chain"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create default config
            default_path = Path(tmpdir) / "default.yaml"
            default_data = {"network": {"port": 8545}}
            with open(default_path, "w") as f:
                yaml.dump(default_data, f)

            # 2. Create production config
            production_path = Path(tmpdir) / "production.yaml"
            production_data = {"network": {"port": 9000}}
            with open(production_path, "w") as f:
                yaml.dump(production_data, f)

            # 3. Set environment variable (should override both files)
            with patch.dict(os.environ, {"XAI_NETWORK_PORT": "9999"}):
                # 4. Set CLI override (should override everything)
                cli_overrides = {"network.port": 7777}
                manager = ConfigManager(
                    environment="production",
                    config_dir=tmpdir,
                    cli_overrides=cli_overrides,
                )
                # CLI override should win
                assert manager.network.port == 7777

    def test_partial_config_sections(self):
        """Test handling partial configuration sections"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            # Only provide network config, other sections should use defaults
            config_data = {"network": {"port": 9000}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager.network.port == 9000
            assert manager.blockchain.difficulty == 4  # Should use default

    def test_empty_yaml_file(self):
        """Test handling empty YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            with open(default_path, "w") as f:
                f.write("")  # Empty file

            manager = ConfigManager(config_dir=tmpdir)
            # Should use all defaults
            assert manager.network.port == 8545
            assert manager.blockchain.difficulty == 4

    def test_malformed_section_in_env_var(self):
        """Test handling malformed environment variable sections"""
        with patch.dict(os.environ, {"XAI_INVALID": "value"}):
            with tempfile.TemporaryDirectory() as tmpdir:
                # Should not crash, should ignore invalid env var
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.network.port == 8545


class TestEnumTypes:
    """Test enum types"""

    def test_environment_enum_values(self):
        """Test Environment enum values"""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTNET.value == "testnet"

    def test_network_type_enum_values(self):
        """Test NetworkType enum values"""
        assert NetworkType.TESTNET.value == "testnet"
        assert NetworkType.MAINNET.value == "mainnet"


class TestEdgeCasesAndAdditionalCoverage:
    """Additional tests for edge cases and uncovered code paths"""

    def test_network_config_with_xai_host_env(self):
        """Test NetworkConfig uses XAI_HOST environment variable"""
        with patch.dict(os.environ, {"XAI_HOST": "10.0.0.1"}):
            config = NetworkConfig()
            assert config.host == "10.0.0.1"

    def test_network_config_validation_edge_cases_min_valid(self):
        """Test network config validation with minimum valid values"""
        config = NetworkConfig(port=1024, rpc_port=1025, max_peers=1, peer_timeout=1, sync_interval=1)
        config.validate()  # Should not raise

    def test_network_config_validation_edge_cases_max_valid(self):
        """Test network config validation with maximum valid values"""
        config = NetworkConfig(port=65535, rpc_port=65534, max_peers=10000)
        config.validate()  # Should not raise

    def test_blockchain_config_validation_edge_cases_min_valid(self):
        """Test blockchain config validation with minimum valid values"""
        config = BlockchainConfig(
            difficulty=1,
            block_time_target=1,
            initial_block_reward=0.01,
            halving_interval=1,
            max_supply=1.0,
            max_block_size=1024,
            min_transaction_fee=0,
            transaction_fee_percent=0,
        )
        config.validate()  # Should not raise

    def test_blockchain_config_validation_edge_cases_max_valid(self):
        """Test blockchain config validation with maximum valid values"""
        config = BlockchainConfig(
            difficulty=32,
            max_block_size=10485760,  # 10MB
            transaction_fee_percent=100,
        )
        config.validate()  # Should not raise

    def test_security_config_with_custom_lists(self):
        """Test SecurityConfig with custom whitelist and blacklist"""
        config = SecurityConfig(
            enable_ip_whitelist=True,
            ip_whitelist=["192.168.1.1", "10.0.0.1"],
            enable_ip_blacklist=True,
            ip_blacklist=["1.2.3.4"],
        )
        assert len(config.ip_whitelist) == 2
        assert len(config.ip_blacklist) == 1
        config.validate()  # Should not raise

    def test_storage_config_validation_edge_cases_min_valid(self):
        """Test storage config validation with minimum valid values"""
        config = StorageConfig(backup_frequency=60, backup_retention=1)
        config.validate()  # Should not raise

    def test_logging_config_all_uppercase_levels(self):
        """Test logging config with all uppercase log levels"""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            config.validate()  # Should not raise

    def test_logging_config_validation_edge_cases_min_valid(self):
        """Test logging config validation with minimum valid values"""
        config = LoggingConfig(max_log_size=1024)
        config.validate()  # Should not raise

    def test_config_manager_load_dotenv_integration(self):
        """Test that ConfigManager integrates load_dotenv"""
        with patch("xai.config_manager.load_dotenv") as mock_dotenv:
            with tempfile.TemporaryDirectory() as tmpdir:
                ConfigManager(config_dir=tmpdir)
                mock_dotenv.assert_called_once()

    def test_config_manager_parse_configuration_all_sections(self):
        """Test that all config sections are parsed correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"
            config_data = {
                "network": {"port": 9000, "host": "192.168.1.1"},
                "blockchain": {"difficulty": 5, "block_time_target": 150},
                "security": {"rate_limit_requests": 200, "ban_threshold": 20},
                "storage": {"data_dir": "custom_data", "backup_enabled": False},
                "logging": {"level": "DEBUG", "enable_file_logging": False},
                "genesis": {"genesis_file": "custom_genesis.json", "network_id": 12345},
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)

            assert manager.network.port == 9000
            assert manager.network.host == "192.168.1.1"
            assert manager.blockchain.difficulty == 5
            assert manager.blockchain.block_time_target == 150
            assert manager.security.rate_limit_requests == 200
            assert manager.security.ban_threshold == 20
            assert manager.storage.data_dir == "custom_data"
            assert manager.storage.backup_enabled is False
            assert manager.logging.level == "DEBUG"
            assert manager.logging.enable_file_logging is False
            assert manager.genesis.genesis_file == "custom_genesis.json"
            assert manager.genesis.network_id == 12345

    def test_apply_env_variables_non_dict_section(self):
        """Test applying env variables when section is not a dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            # Create a config with non-dict section
            config = {"network": "not_a_dict"}

            with patch.dict(os.environ, {"XAI_NETWORK_PORT": "9999"}):
                result = manager._apply_env_variables(config)
                # Should convert to dict and add value
                assert isinstance(result["network"], dict)
                assert result["network"]["port"] == 9999

    def test_apply_env_variables_multi_level_keys(self):
        """Test applying env variables with multiple underscore levels"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            config = {"network": {}}

            with patch.dict(os.environ, {"XAI_NETWORK_MAX_PEERS": "200"}):
                result = manager._apply_env_variables(config)
                assert result["network"]["max_peers"] == 200

    def test_get_method_with_non_dict_intermediate(self):
        """Test get method when intermediate value is not a dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": "not_a_dict"}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            # Should return default since path is not valid
            value = manager.get("network.port", "default")
            assert value == "default"

    def test_cli_override_more_than_two_levels(self):
        """Test that CLI overrides with more than 2 levels are ignored"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            config = {}
            manager.cli_overrides = {"section.subsection.key": "value"}

            result = manager._apply_cli_overrides(config)
            # Should not be applied (only 1 or 2 levels supported)
            assert "section" not in result or "subsection" not in result.get("section", {})

    def test_merge_configs_non_dict_override(self):
        """Test merge configs when override value is not a dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            base = {"network": {"port": 8545, "host": "127.0.0.1"}}
            override = {"network": "simple_value"}

            result = manager._merge_configs(base, override)
            # Override should replace entire section
            assert result["network"] == "simple_value"

    def test_parse_env_value_edge_cases(self):
        """Test parsing environment values with edge cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            # Test mixed case boolean values
            assert manager._parse_env_value("YES") is True
            assert manager._parse_env_value("NO") is False
            assert manager._parse_env_value("ON") is True
            assert manager._parse_env_value("OFF") is False

            # Test zero (should be False, not integer)
            assert manager._parse_env_value("0") is False

            # Test string that looks like float but with text
            assert manager._parse_env_value("3.14abc") == "3.14abc"

    def test_environment_config_missing_file(self):
        """Test that missing environment-specific config doesn't fail"""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 8545}}
            with open(default_path, "w") as f:
                yaml.dump(config_data, f)

            # Request staging environment but don't create staging.yaml
            manager = ConfigManager(environment="staging", config_dir=tmpdir)
            assert manager.network.port == 8545  # Should use default

    def test_to_dict_includes_all_fields(self):
        """Test to_dict exports all config dataclass fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            config_dict = manager.to_dict()

            # Check all network fields are present
            assert "port" in config_dict["network"]
            assert "host" in config_dict["network"]
            assert "rpc_port" in config_dict["network"]
            assert "max_peers" in config_dict["network"]
            assert "peer_timeout" in config_dict["network"]
            assert "sync_interval" in config_dict["network"]
            assert "p2p_enabled" in config_dict["network"]

    def test_get_public_config_structure(self):
        """Test get_public_config has correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            public_config = manager.get_public_config()

            # Verify blockchain public fields
            assert "difficulty" in public_config["blockchain"]
            assert "block_time_target" in public_config["blockchain"]
            assert "initial_block_reward" in public_config["blockchain"]
            assert "halving_interval" in public_config["blockchain"]
            assert "max_supply" in public_config["blockchain"]
            assert "transaction_fee_percent" in public_config["blockchain"]

            # Verify genesis public fields
            assert "network_id" in public_config["genesis"]
            assert "address_prefix" in public_config["genesis"]

    def test_config_manager_with_empty_cli_overrides(self):
        """Test ConfigManager handles empty CLI overrides dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir, cli_overrides={})
            assert manager.cli_overrides == {}

    def test_config_manager_raw_config_populated(self):
        """Test that _raw_config is properly populated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 9000}}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            assert manager._raw_config is not None
            assert "network" in manager._raw_config

    def test_default_config_dir_constant(self):
        """Test DEFAULT_CONFIG_DIR is set correctly"""
        from xai.config_manager import DEFAULT_CONFIG_DIR

        assert DEFAULT_CONFIG_DIR is not None
        assert isinstance(DEFAULT_CONFIG_DIR, Path)
        assert "config" in str(DEFAULT_CONFIG_DIR)

    def test_validation_called_during_init(self):
        """Test that validation is called during initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"
            # Create invalid config
            config_data = {"network": {"port": 100}}  # Invalid port
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            with pytest.raises(ValueError, match="Invalid port"):
                ConfigManager(config_dir=tmpdir)

    def test_multiple_env_variables_combined(self):
        """Test multiple environment variables applied together"""
        env_vars = {
            "XAI_NETWORK_PORT": "9999",
            "XAI_BLOCKCHAIN_DIFFICULTY": "10",
            "XAI_SECURITY_BAN_THRESHOLD": "50",
        }

        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigManager(config_dir=tmpdir)
                assert manager.network.port == 9999
                assert manager.blockchain.difficulty == 10
                assert manager.security.ban_threshold == 50

    def test_config_precedence_all_sources(self):
        """Test configuration precedence from all sources"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create default config
            default_path = Path(tmpdir) / "default.yaml"
            default_data = {
                "network": {"port": 8545, "rpc_port": 8546, "max_peers": 50, "peer_timeout": 30}
            }
            with open(default_path, "w") as f:
                yaml.dump(default_data, f)

            # Create environment-specific config
            prod_path = Path(tmpdir) / "production.yaml"
            prod_data = {"network": {"port": 9000, "rpc_port": 9001}}
            with open(prod_path, "w") as f:
                yaml.dump(prod_data, f)

            # Apply env var and CLI override
            with patch.dict(os.environ, {"XAI_NETWORK_MAX_PEERS": "100"}):
                cli_overrides = {"network.peer_timeout": 60}
                manager = ConfigManager(
                    environment="production", config_dir=tmpdir, cli_overrides=cli_overrides
                )

                # Check precedence
                assert manager.network.port == 9000  # From production.yaml
                assert manager.network.rpc_port == 9001  # From production.yaml
                assert manager.network.max_peers == 100  # From env var
                assert manager.network.peer_timeout == 60  # From CLI override

    def test_reload_preserves_config_dir_and_environment(self):
        """Test that reload preserves config directory and environment"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "production.yaml"
            config_data = {"network": {"port": 8545}}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(environment="production", config_dir=tmpdir)
            original_env = manager.environment
            original_dir = manager.config_dir

            manager.reload()

            assert manager.environment == original_env
            assert manager.config_dir == original_dir

    def test_get_section_returns_copy(self):
        """Test that get_section returns the actual section from raw config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"
            config_data = {"network": {"port": 9000, "host": "localhost"}}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            manager = ConfigManager(config_dir=tmpdir)
            section = manager.get_section("network")

            # Verify it's the actual data
            assert section is not None
            assert section["port"] == 9000
            assert section["host"] == "localhost"
