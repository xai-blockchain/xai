# XAI Blockchain Project Guidelines

**Read the parent guidelines first:** `../CLAUDE.md` and `../AGENTS.md` contain general agent instructions that apply to all projects.

This file contains XAI-specific conventions and instructions.

---

## Project Overview

XAI is a Python-based blockchain focused on AI integration, governance, trading, and cryptocurrency functionality. It includes AI assistants, atomic swaps, and a complete node implementation.

## Project Structure

```
xai/
├── src/xai/              # Main source code
│   ├── core/             # Core blockchain logic
│   │   ├── blockchain.py # Blockchain implementation
│   │   ├── node.py       # Node implementation
│   │   ├── wallet.py     # Wallet functionality
│   │   ├── trading.py    # Trading engine
│   │   └── ai/           # AI components
│   ├── ai/               # AI assistants
│   ├── blockchain/       # Blockchain utilities
│   └── cli/              # Command-line interface
├── sdk/python/           # Python SDK
├── tests/                # Test suites
├── scripts/              # Utility scripts
├── config/               # Configuration files
├── docker/               # Docker configurations
├── docs/                 # Documentation
├── deploy/               # Deployment scripts
└── k8s/                  # Kubernetes manifests
```

## Node Data Directory

**The node data directory is `~/.xai/` (in user's home directory), NOT in the repo.**

This directory contains:
- Blockchain data files
- Wallet files and keys
- Node configuration
- Mining data

**Do NOT:**
- Put blockchain data in the repo
- Commit private keys or wallet files
- Commit `.env` files with secrets

**Data directories excluded from git:**
- `blockchain_data/`
- `mining_data/`
- `recovery_data/`
- `wallets_testnet/`
- `data/`

## Virtual Environment

**Always use a virtual environment for Python development.**

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .
# or
pip install -r requirements.txt
```

**Note:** The `.venv/` directory is excluded from git.

## Building / Installing

```bash
# Activate virtual environment first
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install with all dependencies
pip install -e ".[dev]"
```

## Testing

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src/xai

# Run specific test file
pytest tests/test_blockchain.py

# Run with verbose output
pytest -v
```

**Pre-commit hooks are configured.** Run `pre-commit install` to enable them.

## Running the Node

```bash
# Activate virtual environment
source .venv/bin/activate

# Start testnet node
python -m xai.core.node
# or use the scripts
./src/xai/START_TESTNET.sh
```

## Code Quality Tools

The project uses:
- **black** - Code formatting
- **isort** - Import sorting
- **pylint** - Linting
- **flake8** - Style checking
- **mypy** - Type checking
- **bandit** - Security scanning

Run all checks:
```bash
pre-commit run --all-files
```

## Git Workflow

- Commit frequently after completing each task
- Push to GitHub after each commit (SSH is configured - no auth prompts)
- Use clear commit messages
- GitHub Actions are DISABLED (local testing only via pre-commit hooks)

**SSH Authentication:** Remote is `git@github.com:decristofaroj/xai.git`. Push works without prompts.

## Environment Variables

Create a `.env` file (excluded from git) for local configuration:
```
XAI_NODE_PORT=8545
XAI_RPC_URL=http://localhost:8545
XAI_NETWORK=testnet
```

## Configuration Files

- `config/default.yaml` - Default configuration
- `config/testnet.yaml` - Testnet configuration
- `config/production.yaml` - Production configuration (template)

## Common Issues

**"ModuleNotFoundError: No module named 'xai'"**
- Activate virtual environment: `source .venv/bin/activate`
- Install package: `pip install -e .`

**Virtual environment issues**
- Delete and recreate: `rm -rf .venv && python3 -m venv .venv`

**Import errors after moving files**
- Run `pip install -e .` again to update package paths
