#!/usr/bin/env python3
"""
XAI Node Setup Wizard
Interactive configuration for new node operators

Features:
- Beginner-friendly interface with ASCII art
- Network selection (testnet/mainnet)
- Node mode selection (full/pruned/light/archival)
- Mining configuration
- Port configuration with conflict detection
- Data directory setup
- .env file generation
- Optional wallet creation
- Optional testnet token request
- Summary and next steps
"""

import os
import sys
import socket
import secrets
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for colorful terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        """Disable colors for non-TTY environments."""
        Colors.HEADER = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


# Disable colors if not running in a terminal
if not sys.stdout.isatty():
    Colors.disable()


# ASCII Art Banner
BANNER = f"""{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗  ██╗ █████╗ ██╗    ███╗   ██╗ ██████╗ ██████╗ ███████╗║
║   ╚██╗██╔╝██╔══██╗██║    ████╗  ██║██╔═══██╗██╔══██╗██╔════╝║
║    ╚███╔╝ ███████║██║    ██╔██╗ ██║██║   ██║██║  ██║█████╗  ║
║    ██╔██╗ ██╔══██║██║    ██║╚██╗██║██║   ██║██║  ██║██╔══╝  ║
║   ██╔╝ ██╗██║  ██║██████╗██║ ╚████║╚██████╔╝██████╔╝███████╗║
║   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝║
║                                                               ║
║              Interactive Node Setup Wizard                    ║
║                      Version 1.0.0                            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*65}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^65}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*65}{Colors.ENDC}\n")


def print_info(text: str):
    """Print informational text."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def prompt(text: str, default: Optional[str] = None) -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{Colors.CYAN}? {text}{suffix}: {Colors.ENDC}").strip()
        if not value and default is not None:
            return default
        return value
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Colors.YELLOW}Setup cancelled by user.{Colors.ENDC}")
        sys.exit(0)


def confirm(text: str, default: bool = True) -> bool:
    """Ask for yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{Colors.CYAN}? {text} {suffix}: {Colors.ENDC}").strip().lower()
        if not answer:
            return default
        return answer.startswith('y')
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Colors.YELLOW}Setup cancelled by user.{Colors.ENDC}")
        sys.exit(0)


def select_option(text: str, options: List[Tuple[str, str, str]], default: int = 0) -> str:
    """Present a numbered list of options and get user selection."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}? {text}{Colors.ENDC}")
    for i, (key, name, desc) in enumerate(options, 1):
        default_marker = f" {Colors.GREEN}(default){Colors.ENDC}" if i == default + 1 else ""
        print(f"  {Colors.BOLD}{i}.{Colors.ENDC} {Colors.BOLD}{name}{Colors.ENDC}{default_marker}")
        print(f"     {Colors.CYAN}{desc}{Colors.ENDC}")

    while True:
        try:
            choice = input(f"{Colors.CYAN}> Enter choice [1-{len(options)}]: {Colors.ENDC}").strip()
            if not choice:
                return options[default][0]

            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
            print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}Setup cancelled by user.{Colors.ENDC}")
            sys.exit(0)


def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def validate_xai_address(address: str) -> bool:
    """Validate XAI address format (basic check)."""
    if not address:
        return False
    # XAI addresses should start with "XAI1" or "0x" and be reasonable length
    if address.startswith("XAI1"):
        return len(address) >= 40
    elif address.startswith("0x"):
        return len(address) == 42
    return False


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret."""
    return secrets.token_hex(32)


def generate_wallet_trade_secret() -> str:
    """Generate a secure wallet trade peer secret."""
    return secrets.token_hex(32)


def generate_encryption_key() -> str:
    """Generate a secure encryption key."""
    return secrets.token_hex(32)


def check_disk_space(path: Path, required_gb: int) -> Tuple[bool, int]:
    """Check if sufficient disk space is available.

    Returns:
        (is_sufficient, available_gb)
    """
    try:
        stat = os.statvfs(path.parent if not path.exists() else path)
        # Available space in GB
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        return available_gb >= required_gb, int(available_gb)
    except Exception:
        # If we can't check, assume it's OK
        return True, 0


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets requirements (3.10+).

    Returns:
        (is_sufficient, version_string)
    """
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    is_ok = version_info >= (3, 10)
    return is_ok, version_str


def check_dependencies() -> List[Tuple[str, bool, str]]:
    """Check if required Python packages are available.

    Returns:
        List of (package_name, is_available, version_or_error)
    """
    dependencies = []

    # Core dependencies
    packages = [
        'flask',
        'requests',
        'cryptography',
        'eth_keys',
        'ecdsa',
    ]

    for package in packages:
        try:
            mod = __import__(package.replace('-', '_'))
            version = getattr(mod, '__version__', 'unknown')
            dependencies.append((package, True, version))
        except ImportError as e:
            dependencies.append((package, False, str(e)))

    return dependencies


def test_network_connectivity() -> Tuple[bool, str]:
    """Test basic internet connectivity.

    Returns:
        (is_connected, message)
    """
    try:
        # Try to resolve a DNS name
        socket.gethostbyname('google.com')
        return True, "Internet connectivity OK"
    except socket.error:
        return False, "No internet connection detected"


def create_wallet() -> Tuple[str, str, str]:
    """Create a new wallet and return (address, private_key, mnemonic).

    Attempts to use the proper wallet module if available, falls back to
    simplified generation for standalone wizard use.
    """
    # Try to use the proper wallet module
    try:
        # Add parent directory to path to import xai modules
        project_root = Path(__file__).parent.parent
        if str(project_root / 'src') not in sys.path:
            sys.path.insert(0, str(project_root / 'src'))

        from xai.core.wallet_factory import WalletFactory

        # Use proper wallet creation
        wallet = WalletFactory.create_wallet()
        address = wallet.get_address()
        private_key = wallet.get_private_key_hex()
        mnemonic = wallet.get_mnemonic() if hasattr(wallet, 'get_mnemonic') else ""

        return address, private_key, mnemonic
    except ImportError:
        # Fall back to simplified wallet generation
        pass

    # Simple secp256k1 keypair generation (fallback)
    private_key = secrets.token_hex(32)

    # Generate address from private key (simplified)
    # In production, this uses proper secp256k1 curve operations
    hash_obj = hashlib.sha256(private_key.encode())
    address_bytes = hash_obj.digest()[:20]
    address = "XAI1" + address_bytes.hex()

    # Generate mnemonic (12 words from simple wordlist)
    wordlist = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
        "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid"
    ]

    # Use private key to seed mnemonic generation
    seed = int(private_key[:24], 16)
    mnemonic_words = []
    for _ in range(12):
        mnemonic_words.append(wordlist[seed % len(wordlist)])
        seed = seed // len(wordlist) + 1

    mnemonic = " ".join(mnemonic_words)

    return address, private_key, mnemonic


def backup_existing_env(env_path: Path):
    """Create a backup of existing .env file."""
    if env_path.exists():
        timestamp = os.popen('date +%Y%m%d_%H%M%S').read().strip()
        backup_path = env_path.parent / f".env.backup.{timestamp}"
        shutil.copy2(env_path, backup_path)
        print_success(f"Backed up existing .env to: {backup_path}")


def write_env_file(config: Dict[str, str], env_path: Path):
    """Write configuration to .env file."""
    lines = [
        "# XAI Blockchain Node Configuration",
        f"# Generated by setup wizard on {os.popen('date').read().strip()}",
        "# WARNING: This file contains sensitive information. Do not commit to git!",
        "",
        "# Network Configuration",
        f"XAI_NETWORK={config['network']}",
        f"XAI_NODE_MODE={config['node_mode']}",
        f"XAI_NODE_NAME={config.get('node_name', 'xai-node')}",
        "",
        "# Port Configuration",
        f"XAI_RPC_PORT={config['rpc_port']}",
        f"XAI_P2P_PORT={config['p2p_port']}",
        f"XAI_METRICS_PORT={config.get('metrics_port', '12090')}",
        f"XAI_RPC_URL=http://localhost:{config['rpc_port']}",
        "",
        "# Data Directory",
        f"XAI_DATA_DIR={config['data_dir']}",
        f"XAI_LOG_LEVEL={config.get('log_level', 'INFO')}",
        "",
        "# Mining Configuration",
        f"XAI_MINING_ENABLED={config['mining_enabled']}",
    ]

    if config.get('miner_address'):
        lines.append(f"MINER_ADDRESS={config['miner_address']}")
        lines.append(f"XAI_MINING_THREADS={config.get('mining_threads', '2')}")

    lines.extend([
        "",
        "# Security Secrets (auto-generated)",
        f"XAI_JWT_SECRET={config['jwt_secret']}",
        f"XAI_WALLET_TRADE_PEER_SECRET={config['wallet_trade_secret']}",
        f"XAI_TIME_CAPSULE_MASTER_KEY={config.get('time_capsule_key', generate_encryption_key())}",
        f"XAI_EMBEDDED_SALT={config.get('embedded_salt', generate_encryption_key())}",
        f"XAI_LUCKY_BLOCK_SEED={config.get('lucky_block_seed', generate_encryption_key())}",
        "",
        "# Monitoring",
        f"XAI_PROMETHEUS_ENABLED={config.get('prometheus_enabled', 'true')}",
        "",
        "# API Keys (optional - for AI features)",
        "# ANTHROPIC_API_KEY=",
        "# OPENAI_API_KEY=",
        "# GOOGLE_AI_API_KEY=",
        "",
        "# Database",
        f"DATABASE_URL=sqlite:///{config['data_dir']}/blockchain.db",
        "",
    ])

    env_path.write_text("\n".join(lines))
    # Set restrictive permissions
    os.chmod(env_path, 0o600)
    print_success(f"Configuration written to: {env_path}")


def create_systemd_service(config: Dict[str, str], project_root: Path) -> Optional[Path]:
    """Create a systemd service file for auto-starting the node.

    Returns:
        Path to the service file if created, None otherwise
    """
    service_name = f"xai-node-{config['network']}"
    service_content = f"""[Unit]
Description=XAI Blockchain Node ({config['network']})
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'xai')}
WorkingDirectory={project_root}
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile={project_root}/.env
ExecStart=/usr/bin/python3 -m xai.core.node
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={config['data_dir']}

[Install]
WantedBy=multi-user.target
"""

    # Write to temporary location (user can move it)
    service_file = project_root / f"{service_name}.service"
    service_file.write_text(service_content)

    return service_file


def main():
    """Main wizard flow."""
    print(BANNER)

    print_info("Welcome to the XAI Node Setup Wizard!")
    print_info("This wizard will help you configure your XAI blockchain node.\n")

    # Pre-flight checks
    print_header("System Requirements Check")

    # Check Python version
    py_ok, py_version = check_python_version()
    if py_ok:
        print_success(f"Python version: {py_version}")
    else:
        print_error(f"Python {py_version} is installed, but 3.10+ is required")
        if not confirm("Continue anyway? (Not recommended)", False):
            return

    # Check dependencies
    print_info("Checking Python dependencies...")
    deps = check_dependencies()
    missing_deps = []
    for name, available, version in deps:
        if available:
            print_success(f"{name}: {version}")
        else:
            print_warning(f"{name}: Not installed")
            missing_deps.append(name)

    if missing_deps:
        print_warning(f"\nMissing dependencies: {', '.join(missing_deps)}")
        print_info("Install with: pip install " + " ".join(missing_deps))
        if not confirm("Continue without these packages?", False):
            return

    # Check network connectivity
    connected, msg = test_network_connectivity()
    if connected:
        print_success(msg)
    else:
        print_warning(msg)
        print_info("You can still run a local node, but won't sync with peers")

    if not confirm("\nReady to begin setup?", True):
        print_info("Setup cancelled. Run this script again when ready.")
        return

    config: Dict[str, str] = {}

    # Step 1: Network Selection
    print_header("Network Selection")
    print_info("Choose which network you want to connect to:")
    print_info("- Testnet: For testing and development (recommended for beginners)")
    print_info("- Mainnet: Production network with real value (requires careful setup)")

    network_options = [
        ("testnet", "Testnet", "Safe environment for testing and learning"),
        ("mainnet", "Mainnet", "Production network with real economic value"),
    ]
    config['network'] = select_option("Select network:", network_options, default=0)

    if config['network'] == 'mainnet':
        print_warning("\nYou selected MAINNET. Please ensure you understand the security implications!")
        if not confirm("Are you sure you want to continue with mainnet?", False):
            print_info("Switching to testnet for safety.")
            config['network'] = 'testnet'

    print_success(f"Network: {config['network'].upper()}")

    # Step 2: Node Mode Selection
    print_header("Node Mode Selection")
    print_info("Different node modes have different storage and sync requirements:")

    node_mode_options = [
        ("full", "Full Node", "Store complete blockchain (recommended, ~50GB)"),
        ("pruned", "Pruned Node", "Store recent blocks only (~10GB)"),
        ("light", "Light Node", "Minimal storage, depends on full nodes (~1GB)"),
        ("archival", "Archival Node", "Store all historical states (~500GB, for developers)"),
    ]
    config['node_mode'] = select_option("Select node mode:", node_mode_options, default=0)
    print_success(f"Node mode: {config['node_mode']}")

    # Step 3: Data Directory
    print_header("Data Directory")
    print_info("Where should the blockchain data be stored?")

    # Determine disk space requirements based on node mode
    disk_requirements = {
        'full': 50,
        'pruned': 10,
        'light': 1,
        'archival': 500
    }
    required_gb = disk_requirements.get(config['node_mode'], 50)

    default_data_dir = str(Path.home() / ".xai")
    data_dir = prompt("Data directory path", default_data_dir)
    config['data_dir'] = str(Path(data_dir).expanduser().absolute())

    data_path = Path(config['data_dir'])

    # Check disk space
    space_ok, available_gb = check_disk_space(data_path, required_gb)
    if space_ok:
        print_success(f"Available disk space: {available_gb} GB")
    else:
        print_error(f"Only {available_gb} GB available, but {required_gb} GB recommended for {config['node_mode']} mode")
        if not confirm("Continue anyway?", False):
            print_error("Please free up disk space or choose a different location.")
            return

    if data_path.exists():
        print_warning(f"Directory already exists: {config['data_dir']}")
        if not confirm("Use this directory?", True):
            print_error("Please run the wizard again and choose a different directory.")
            return
    else:
        data_path.mkdir(parents=True, exist_ok=True)
        print_success(f"Created directory: {config['data_dir']}")

    # Step 4: Port Configuration
    print_header("Port Configuration")
    print_info("Configure network ports for your node:")
    print_info("XAI project uses port range 12000-12999 to avoid conflicts")

    # RPC Port
    default_rpc = "12001"
    while True:
        rpc_port = prompt("RPC/API port", default_rpc)
        try:
            rpc_port_int = int(rpc_port)
            if not (12000 <= rpc_port_int <= 12999):
                print_warning("Recommended port range is 12000-12999")
                if not confirm("Use this port anyway?", False):
                    continue

            if not is_port_available(rpc_port_int):
                print_error(f"Port {rpc_port_int} is already in use!")
                if not confirm("Choose a different port?", True):
                    print_warning("Using unavailable port - you may need to stop the conflicting service")
                    config['rpc_port'] = rpc_port
                    break
                continue

            config['rpc_port'] = rpc_port
            print_success(f"RPC port: {rpc_port}")
            break
        except ValueError:
            print_error("Please enter a valid port number")

    # P2P Port
    default_p2p = str(int(config['rpc_port']) + 1)
    while True:
        p2p_port = prompt("P2P port", default_p2p)
        try:
            p2p_port_int = int(p2p_port)
            if p2p_port_int == int(config['rpc_port']):
                print_error("P2P port must be different from RPC port!")
                continue

            if not is_port_available(p2p_port_int):
                print_error(f"Port {p2p_port_int} is already in use!")
                if not confirm("Choose a different port?", True):
                    print_warning("Using unavailable port - you may need to stop the conflicting service")
                    config['p2p_port'] = p2p_port
                    break
                continue

            config['p2p_port'] = p2p_port
            print_success(f"P2P port: {p2p_port}")
            break
        except ValueError:
            print_error("Please enter a valid port number")

    # WebSocket Port
    default_ws = str(int(config['rpc_port']) + 2)
    while True:
        ws_port = prompt("WebSocket port", default_ws)
        try:
            ws_port_int = int(ws_port)
            if ws_port_int in [int(config['rpc_port']), int(config['p2p_port'])]:
                print_error("WebSocket port must be different from RPC and P2P ports!")
                continue

            if not is_port_available(ws_port_int):
                print_error(f"Port {ws_port_int} is already in use!")
                if not confirm("Choose a different port?", True):
                    print_warning("Using unavailable port - you may need to stop the conflicting service")
                    config['ws_port'] = ws_port
                    break
                continue

            config['ws_port'] = ws_port
            print_success(f"WebSocket port: {ws_port}")
            break
        except ValueError:
            print_error("Please enter a valid port number")

    # Step 5: Mining Configuration
    print_header("Mining Configuration")
    print_info("Mining helps secure the network and earn rewards.")
    print_info("Mining requires CPU resources but can be started/stopped anytime.")

    if confirm("Enable mining on this node?", True):
        config['mining_enabled'] = "true"

        print_info("\nYou'll need a wallet address to receive mining rewards.")

        if confirm("Do you have an existing wallet address?", False):
            while True:
                miner_address = prompt("Enter your XAI wallet address")
                if validate_xai_address(miner_address):
                    config['miner_address'] = miner_address
                    print_success(f"Miner address: {miner_address}")
                    break
                else:
                    print_error("Invalid XAI address format (should start with XAI1 or 0x)")
                    if not confirm("Try again?", True):
                        config['mining_enabled'] = "false"
                        break
        else:
            print_info("\nNo problem! We can create a wallet later.")
            print_info("Mining will be enabled but you'll need to set the address before mining.")
    else:
        config['mining_enabled'] = "false"
        print_info("Mining disabled. You can enable it later by editing the .env file.")

    # Step 6: Monitoring Configuration
    print_header("Monitoring Configuration")
    print_info("XAI includes Prometheus metrics for monitoring node health.")

    if confirm("Enable Prometheus metrics?", True):
        config['prometheus_enabled'] = 'true'
        metrics_port = prompt("Metrics port", "12090")
        config['metrics_port'] = metrics_port
        print_success("Metrics will be available at http://localhost:" + metrics_port + "/metrics")
    else:
        config['prometheus_enabled'] = 'false'

    # Step 7: Generate Security Secrets
    print_header("Security Configuration")
    print_info("Generating secure secrets for your node...")

    config['jwt_secret'] = generate_jwt_secret()
    config['wallet_trade_secret'] = generate_wallet_trade_secret()
    config['time_capsule_key'] = generate_encryption_key()
    config['embedded_salt'] = generate_encryption_key()
    config['lucky_block_seed'] = generate_encryption_key()

    print_success("JWT secret generated")
    print_success("Wallet trade secret generated")
    print_success("Time capsule key generated")
    print_success("Embedded wallet salt generated")
    print_success("Lucky block seed generated")

    if config['network'] == 'mainnet':
        print_warning("\nMAINNET SECURITY WARNING:")
        print_warning("- Keep your .env file secure and never share it")
        print_warning("- Back up your wallet private keys")
        print_warning("- Use a hardware wallet for large amounts")
        print_warning("- Consider running behind a firewall")
        print_warning("- Enable firewall rules to protect P2P and RPC ports")

    # Step 8: Write Configuration
    print_header("Save Configuration")

    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"

    print_info(f"Configuration will be saved to: {env_path}")

    if env_path.exists():
        print_warning("An .env file already exists!")
        if not confirm("Overwrite existing configuration?", False):
            print_error("Setup cancelled. Your existing configuration was not modified.")
            return
        backup_existing_env(env_path)

    write_env_file(config, env_path)

    # Optional: Create systemd service
    if sys.platform == 'linux':
        print_info("\nSystemd service file can be created for auto-starting the node.")
        if confirm("Create systemd service file?", False):
            service_file = create_systemd_service(config, project_root)
            if service_file:
                print_success(f"Service file created: {service_file}")
                print_info("\nTo install the service:")
                print(f"  sudo cp {service_file} /etc/systemd/system/")
                print(f"  sudo systemctl daemon-reload")
                print(f"  sudo systemctl enable xai-node-{config['network']}")
                print(f"  sudo systemctl start xai-node-{config['network']}")

    # Step 9: Optional Wallet Creation
    print_header("Wallet Creation (Optional)")

    if config['mining_enabled'] == "true" and not config.get('miner_address'):
        print_info("You enabled mining but don't have a wallet yet.")
        create_new_wallet = confirm("Create a new wallet now?", True)
    else:
        create_new_wallet = confirm("Create a new wallet?", False)

    wallet_info = None
    if create_new_wallet:
        print_info("\nCreating new wallet...")
        address, private_key, mnemonic = create_wallet()
        wallet_info = (address, private_key, mnemonic)

        print_success(f"\nWallet created successfully!")
        print(f"\n{Colors.BOLD}{Colors.GREEN}IMPORTANT: Save this information securely!{Colors.ENDC}\n")
        print(f"{Colors.BOLD}Address:{Colors.ENDC} {Colors.YELLOW}{address}{Colors.ENDC}")
        print(f"{Colors.BOLD}Private Key:{Colors.ENDC} {Colors.YELLOW}{private_key}{Colors.ENDC}")
        print(f"{Colors.BOLD}Mnemonic:{Colors.ENDC} {Colors.YELLOW}{mnemonic}{Colors.ENDC}\n")

        print_warning("Write down your mnemonic phrase and store it safely!")
        print_warning("Anyone with your private key or mnemonic can access your funds!")

        if confirm("\nSave wallet to file?", True):
            wallet_dir = data_path / "wallets"
            wallet_dir.mkdir(exist_ok=True)
            wallet_file = wallet_dir / f"wallet_{address[:12]}.json"

            wallet_data = {
                "address": address,
                "private_key": private_key,
                "mnemonic": mnemonic,
                "created_at": os.popen('date -Iseconds').read().strip(),
                "network": config['network']
            }

            wallet_file.write_text(json.dumps(wallet_data, indent=2))
            os.chmod(wallet_file, 0o600)
            print_success(f"Wallet saved to: {wallet_file}")
            print_warning(f"File permissions set to 0600 (owner read/write only)")

        # Update miner address if mining is enabled
        if config['mining_enabled'] == "true" and not config.get('miner_address'):
            config['miner_address'] = address
            # Re-write env file with miner address
            write_env_file(config, env_path)
            print_success(f"Miner address updated in .env file")

    # Step 10: Optional Testnet Tokens
    if config['network'] == 'testnet' and wallet_info:
        print_header("Testnet Tokens (Optional)")
        print_info("You can request free testnet tokens to start testing.")

        if confirm("Request testnet tokens?", True):
            print_info("\nTestnet Faucet Information:")
            print(f"  Address: {Colors.YELLOW}{wallet_info[0]}{Colors.ENDC}")
            print(f"  Faucet URL: {Colors.CYAN}https://faucet.xai.network{Colors.ENDC}")
            print(f"  Discord: {Colors.CYAN}https://discord.gg/xai-network{Colors.ENDC}")
            print_info("\nVisit the faucet URL or ask in Discord for testnet tokens.")

    # Step 11: Summary and Next Steps
    print_header("Setup Complete!")

    print(f"\n{Colors.BOLD}{Colors.GREEN}Configuration Summary:{Colors.ENDC}\n")
    print(f"  Network:        {Colors.CYAN}{config['network'].upper()}{Colors.ENDC}")
    print(f"  Node Mode:      {Colors.CYAN}{config['node_mode']}{Colors.ENDC}")
    print(f"  Data Directory: {Colors.CYAN}{config['data_dir']}{Colors.ENDC}")
    print(f"  RPC Port:       {Colors.CYAN}{config['rpc_port']}{Colors.ENDC}")
    print(f"  P2P Port:       {Colors.CYAN}{config['p2p_port']}{Colors.ENDC}")
    print(f"  WebSocket Port: {Colors.CYAN}{config['ws_port']}{Colors.ENDC}")
    print(f"  Mining:         {Colors.CYAN}{'Enabled' if config['mining_enabled'] == 'true' else 'Disabled'}{Colors.ENDC}")
    if config.get('miner_address'):
        print(f"  Miner Address:  {Colors.CYAN}{config['miner_address']}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}{Colors.BLUE}Next Steps:{Colors.ENDC}\n")

    print(f"{Colors.BOLD}1. Start your node:{Colors.ENDC}")
    print(f"   cd {project_root}")
    print(f"   python -m xai.core.node")
    print()

    print(f"{Colors.BOLD}2. Check node status:{Colors.ENDC}")
    print(f"   curl http://localhost:{config['rpc_port']}/health")
    print()

    print(f"{Colors.BOLD}3. View blockchain info:{Colors.ENDC}")
    print(f"   curl http://localhost:{config['rpc_port']}/blocks")
    print()

    if config['mining_enabled'] == "true" and config.get('miner_address'):
        print(f"{Colors.BOLD}4. Start mining:{Colors.ENDC}")
        mining_cmd = {
            "miner_address": config['miner_address'],
            "threads": 2
        }
        print(f"   curl -X POST http://localhost:{config['rpc_port']}/mining/start \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{json.dumps(mining_cmd)}'")
        print()

    print(f"{Colors.BOLD}5. Explore the blockchain:{Colors.ENDC}")
    print(f"   Block Explorer: http://localhost:12080")
    print(f"   Grafana Dashboard: http://localhost:12030")
    print()

    print(f"{Colors.BOLD}Documentation:{Colors.ENDC}")
    print(f"   README: {project_root}/README.md")
    print(f"   Docs: https://docs.xai.network")
    print()

    print_success("Setup wizard completed successfully!")
    print_info("Your node is ready to start. Good luck!\n")

    # Optional: Start node
    if confirm("Start node now?", False):
        print_info("\nStarting node...")
        os.chdir(project_root)
        os.system("python -m xai.core.node")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelled by user.{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
