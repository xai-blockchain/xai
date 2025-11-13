"""
XAI Blockchain Configuration Manager

Centralized configuration management system supporting:
- Environment-based configs (dev/staging/prod)
- Config file loading (YAML/JSON)
- Command-line override support
- Environment variable support (XAI_*)
- Config validation
- Type checking
"""

import os
import json
import yaml
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from dotenv import load_dotenv # Import load_dotenv


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "config"


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTNET = "testnet"


class NetworkType(Enum):
    """Network types"""
    TESTNET = "testnet"
    MAINNET = "mainnet"


@dataclass
class NetworkConfig:
    """Network configuration settings"""
    port: int = 8545
    host: str = "0.0.0.0"
    rpc_port: int = 8546
    max_peers: int = 50
    peer_timeout: int = 30
    sync_interval: int = 60
    p2p_enabled: bool = True

    def validate(self):
        """Validate network configuration"""
        if not (1024 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}. Must be between 1024-65535")
        if not (1024 <= self.rpc_port <= 65535):
            raise ValueError(f"Invalid RPC port: {self.rpc_port}. Must be between 1024-65535")
        if self.max_peers < 1:
            raise ValueError(f"Invalid max_peers: {self.max_peers}. Must be >= 1")
        if self.peer_timeout < 1:
            raise ValueError(f"Invalid peer_timeout: {self.peer_timeout}. Must be >= 1")


@dataclass
class BlockchainConfig:
    """Blockchain configuration settings"""
    difficulty: int = 4
    block_time_target: int = 120  # seconds
    initial_block_reward: float = 12.0
    halving_interval: int = 262800  # blocks
    max_supply: float = 121000000.0
    max_block_size: int = 1048576  # 1MB
    min_transaction_fee: float = 0.0001
    transaction_fee_percent: float = 0.24

    def validate(self):
        """Validate blockchain configuration"""
        if self.difficulty < 1 or self.difficulty > 32:
            raise ValueError(f"Invalid difficulty: {self.difficulty}. Must be between 1-32")
        if self.block_time_target < 1:
            raise ValueError(f"Invalid block_time_target: {self.block_time_target}. Must be >= 1")
        if self.initial_block_reward <= 0:
            raise ValueError(f"Invalid initial_block_reward: {self.initial_block_reward}. Must be > 0")
        if self.halving_interval <= 0:
            raise ValueError(f"Invalid halving_interval: {self.halving_interval}. Must be > 0")
        if self.max_supply <= 0:
            raise ValueError(f"Invalid max_supply: {self.max_supply}. Must be > 0")
        if self.max_block_size < 1024:
            raise ValueError(f"Invalid max_block_size: {self.max_block_size}. Must be >= 1024")


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    ban_threshold: int = 10
    ban_duration: int = 3600  # seconds
    enable_ip_whitelist: bool = False
    ip_whitelist: list = field(default_factory=list)
    enable_ip_blacklist: bool = True
    ip_blacklist: list = field(default_factory=list)
    max_transaction_size: int = 102400  # 100KB
    max_mempool_size: int = 10000

    def validate(self):
        """Validate security configuration"""
        if self.rate_limit_requests < 1:
            raise ValueError(f"Invalid rate_limit_requests: {self.rate_limit_requests}. Must be >= 1")
        if self.rate_limit_window < 1:
            raise ValueError(f"Invalid rate_limit_window: {self.rate_limit_window}. Must be >= 1")
        if self.ban_threshold < 1:
            raise ValueError(f"Invalid ban_threshold: {self.ban_threshold}. Must be >= 1")
        if self.max_mempool_size < 1:
            raise ValueError(f"Invalid max_mempool_size: {self.max_mempool_size}. Must be >= 1")


@dataclass
class StorageConfig:
    """Storage configuration settings"""
    data_dir: str = "data"
    blockchain_file: str = "blockchain.json"
    wallet_dir: str = "wallets"
    backup_enabled: bool = True
    backup_frequency: int = 3600  # seconds
    backup_retention: int = 7  # days
    max_backup_count: int = 10
    enable_compression: bool = True

    def validate(self):
        """Validate storage configuration"""
        if not self.data_dir:
            raise ValueError("data_dir cannot be empty")
        if not self.blockchain_file:
            raise ValueError("blockchain_file cannot be empty")
        if self.backup_frequency < 60:
            raise ValueError(f"Invalid backup_frequency: {self.backup_frequency}. Must be >= 60")
        if self.backup_retention < 1:
            raise ValueError(f"Invalid backup_retention: {self.backup_retention}. Must be >= 1")


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True
    log_file: str = "logs/node.log"
    max_log_size: int = 10485760  # 10MB
    log_retention: int = 7  # days
    enable_console_logging: bool = True
    enable_anonymous_logging: bool = True

    def validate(self):
        """Validate logging configuration"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
        if self.max_log_size < 1024:
            raise ValueError(f"Invalid max_log_size: {self.max_log_size}. Must be >= 1024")


@dataclass
class GenesisConfig:
    """Genesis block configuration"""
    genesis_file: str = "genesis_new.json"
    genesis_timestamp: float = 1704067200.0
    network_id: int = 0x5841
    address_prefix: str = "AIXN"

    def validate(self):
        """Validate genesis configuration"""
        if not self.genesis_file:
            raise ValueError("genesis_file cannot be empty")
        if self.genesis_timestamp <= 0:
            raise ValueError(f"Invalid genesis_timestamp: {self.genesis_timestamp}. Must be > 0")
        if not self.address_prefix:
            raise ValueError("address_prefix cannot be empty")


class ConfigManager:
    """
    Configuration Manager for XAI Blockchain

    Handles loading, validation, and access to configuration settings
    from multiple sources with proper precedence:
    1. Command-line arguments (highest priority)
    2. Environment variables (XAI_*)
    3. Environment-specific config files
    4. Default config file
    5. Built-in defaults (lowest priority)
    """

    def __init__(self,
                 environment: Optional[str] = None,
                 config_dir: Optional[str] = None,
                 cli_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize Configuration Manager

        Args:
            environment: Environment name (development/staging/production/testnet)
            config_dir: Directory containing config files
            cli_overrides: Command-line argument overrides
        """
        # Load .env file first to make its variables available for subsequent steps
        load_dotenv() # <-- Added this line

        self.environment = self._determine_environment(environment)
        self.config_dir = Path(config_dir).resolve() if config_dir else DEFAULT_CONFIG_DIR
        self.cli_overrides = cli_overrides or {}

        # Configuration sections
        self.network: NetworkConfig = None
        self.blockchain: BlockchainConfig = None
        self.security: SecurityConfig = None
        self.storage: StorageConfig = None
        self.logging: LoggingConfig = None
        self.genesis: GenesisConfig = None

        # Raw config data
        self._raw_config: Dict[str, Any] = {}

        # Load configuration
        self._load_configuration()

    def _determine_environment(self, environment: Optional[str]) -> Environment:
        """
        Determine the environment to use

        Priority:
        1. Passed environment parameter
        2. XAI_ENVIRONMENT environment variable
        3. XAI_NETWORK environment variable (for backwards compatibility)
        4. Default to DEVELOPMENT
        """
        if environment:
            env_str = environment.lower()
        else:
            env_str = os.getenv("XAI_ENVIRONMENT",
                               os.getenv("XAI_NETWORK", "development")).lower()

        # Map to Environment enum
        env_mapping = {
            "dev": Environment.DEVELOPMENT,
            "development": Environment.DEVELOPMENT,
            "staging": Environment.STAGING,
            "stage": Environment.STAGING,
            "prod": Environment.PRODUCTION,
            "production": Environment.PRODUCTION,
            "testnet": Environment.TESTNET,
            "test": Environment.TESTNET,
        }

        return env_mapping.get(env_str, Environment.DEVELOPMENT)

    def _load_configuration(self):
        """Load configuration from all sources with proper precedence"""
        # 1. Load default configuration
        default_config = self._load_config_file("default")

        # 2. Load environment-specific configuration
        env_config = self._load_config_file(self.environment.value)

        # 3. Merge configurations (env overrides default)
        merged_config = self._merge_configs(default_config, env_config)

        # 4. Apply environment variable overrides
        merged_config = self._apply_env_variables(merged_config)

        # 5. Apply CLI overrides
        merged_config = self._apply_cli_overrides(merged_config)

        # Store raw config
        self._raw_config = merged_config

        # 6. Parse into typed configuration objects
        self._parse_configuration(merged_config)

        # 7. Validate all configurations
        self._validate_configuration()

    def _load_config_file(self, filename: str) -> Dict[str, Any]:
        """
        Load configuration from YAML or JSON file

        Args:
            filename: Config filename (without extension)

        Returns:
            Configuration dictionary
        """
        # Try YAML first
        yaml_path = self.config_dir / f"{filename}.yaml"
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}

        # Try JSON
        json_path = self.config_dir / f"{filename}.json"
        if json_path.exists():
            with open(json_path, 'r') as f:
                return json.load(f)

        # File not found - return empty dict
        return {}

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides (XAI_*)

        Environment variables format:
        XAI_SECTION_KEY=value

        Example:
        XAI_NETWORK_PORT=8545
        XAI_BLOCKCHAIN_DIFFICULTY=4
        """
        result = config.copy()

        # Scan all environment variables starting with XAI_
        for key, value in os.environ.items():
            if not key.startswith("XAI_"):
                continue

            # Skip special environment variables
            if key in ["XAI_ENVIRONMENT", "XAI_NETWORK", "XAI_HOST", "XAI_PORT"]:
                continue

            # Parse the key (XAI_SECTION_SUBSECTION_KEY)
            parts = key[4:].lower().split("_")

            if len(parts) < 2:
                continue

            section = parts[0]
            config_key = "_".join(parts[1:])

            # Apply to config
            if section in result:
                if not isinstance(result[section], dict):
                    result[section] = {}

                # Try to parse value as appropriate type
                parsed_value = self._parse_env_value(value)
                result[section][config_key] = parsed_value

        return result

    def _parse_env_value(self, value: str) -> Union[str, int, float, bool]:
        """
        Parse environment variable value to appropriate type

        Args:
            value: String value from environment variable

        Returns:
            Parsed value
        """
        # Boolean
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String
        return value

    def _apply_cli_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply command-line argument overrides

        Args:
            config: Current configuration

        Returns:
            Configuration with CLI overrides applied
        """
        result = config.copy()

        for key, value in self.cli_overrides.items():
            # Parse key path (e.g., "network.port")
            parts = key.split(".")

            if len(parts) == 1:
                result[key] = value
            elif len(parts) == 2:
                section, config_key = parts
                if section not in result:
                    result[section] = {}
                result[section][config_key] = value

        return result

    def _parse_configuration(self, config: Dict[str, Any]):
        """
        Parse configuration into typed objects

        Args:
            config: Raw configuration dictionary
        """
        # Network configuration
        network_config = config.get("network", {})
        self.network = NetworkConfig(**network_config)

        # Blockchain configuration
        blockchain_config = config.get("blockchain", {})
        self.blockchain = BlockchainConfig(**blockchain_config)

        # Security configuration
        security_config = config.get("security", {})
        self.security = SecurityConfig(**security_config)

        # Storage configuration
        storage_config = config.get("storage", {})
        self.storage = StorageConfig(**storage_config)

        # Logging configuration
        logging_config = config.get("logging", {})
        self.logging = LoggingConfig(**logging_config)

        # Genesis configuration
        genesis_config = config.get("genesis", {})
        self.genesis = GenesisConfig(**genesis_config)

    def _validate_configuration(self):
        """Validate all configuration sections"""
        self.network.validate()
        self.blockchain.validate()
        self.security.validate()
        self.storage.validate()
        self.logging.validate()
        self.genesis.validate()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key

        Args:
            key: Configuration key (e.g., "network.port")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        parts = key.split(".")
        value = self._raw_config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Get entire configuration section

        Args:
            section: Section name

        Returns:
            Section configuration dictionary
        """
        return self._raw_config.get(section)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration to dictionary

        Returns:
            Complete configuration dictionary
        """
        return {
            "environment": self.environment.value,
            "network": asdict(self.network),
            "blockchain": asdict(self.blockchain),
            "security": asdict(self.security),
            "storage": asdict(self.storage),
            "logging": asdict(self.logging),
            "genesis": asdict(self.genesis),
        }

    def get_public_config(self) -> Dict[str, Any]:
        """
        Get public (non-sensitive) configuration for API exposure

        Returns:
            Public configuration dictionary
        """
        return {
            "environment": self.environment.value,
            "network": {
                "port": self.network.port,
                "max_peers": self.network.max_peers,
                "p2p_enabled": self.network.p2p_enabled,
            },
            "blockchain": {
                "difficulty": self.blockchain.difficulty,
                "block_time_target": self.blockchain.block_time_target,
                "initial_block_reward": self.blockchain.initial_block_reward,
                "halving_interval": self.blockchain.halving_interval,
                "max_supply": self.blockchain.max_supply,
                "transaction_fee_percent": self.blockchain.transaction_fee_percent,
            },
            "genesis": {
                "network_id": self.genesis.network_id,
                "address_prefix": self.genesis.address_prefix,
            }
        }

    def reload(self):
        """Reload configuration from files"""
        self._load_configuration()

    def __repr__(self) -> str:
        return f"ConfigManager(environment={self.environment.value})"


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(
    environment: Optional[str] = None,
    config_dir: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    force_reload: bool = False
) -> ConfigManager:
    """
    Get or create ConfigManager singleton instance

    Args:
        environment: Environment name
        config_dir: Config directory path
        cli_overrides: CLI argument overrides
        force_reload: Force reload configuration

    Returns:
        ConfigManager instance
    """
    global _config_manager

    if _config_manager is None or force_reload:
        _config_manager = ConfigManager(
            environment=environment,
            config_dir=config_dir,
            cli_overrides=cli_overrides
        )

    return _config_manager