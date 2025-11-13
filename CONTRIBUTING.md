# Contributing to AIXN Blockchain

Thank you for your interest in contributing to the AIXN blockchain project! We welcome contributions from the community and are grateful for your support.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Node.js (for Electron wallet)
- Basic understanding of blockchain technology
- Familiarity with cryptographic principles

### First-Time Contributors

If you're new to open source or blockchain development:

1. Read through the [documentation](docs/README.md)
2. Check out issues labeled `good first issue` or `help wanted`
3. Join our community discussions
4. Ask questions - we're here to help!

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/crypto.git
cd crypto

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL-ORG/crypto.git
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# For testing
pip install -r tests/requirements_test.txt

# For Electron wallet
cd electron
npm install
cd ..
```

### 3. Configure Environment

```bash
# Copy example configuration
cp config.example.json config.json

# Edit configuration as needed
# Never commit your actual config.json with sensitive data
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/unit/
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=src tests/
```

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check the [issue tracker](https://github.com/[your-org]/crypto/issues) to avoid duplicates
- Collect relevant information (OS, Python version, error messages, logs)

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) when creating an issue.

### Suggesting Enhancements

Enhancement suggestions are welcome! Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:
- Clear use case and benefit
- Implementation ideas (if any)
- Potential impact on existing features
- Alignment with project goals

### Code Contributions

1. **Find or Create an Issue**: Start with an existing issue or create one to discuss your proposed changes
2. **Get Assigned**: Comment on the issue to get assigned or confirm approach
3. **Create a Branch**: Use a descriptive branch name
4. **Write Code**: Follow our coding standards
5. **Test Thoroughly**: Add tests for new functionality
6. **Submit PR**: Use our pull request template

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line Length**: Maximum 120 characters
- **Imports**: Grouped and sorted (stdlib, third-party, local)
- **Naming**:
  - Classes: `PascalCase`
  - Functions/Variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private: Prefix with `_`

### Code Quality Tools

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/

# Sort imports
isort src/ tests/
```

### Best Practices

- **DRY Principle**: Don't repeat yourself
- **Single Responsibility**: Each function/class should have one purpose
- **Documentation**: Add docstrings to all public functions and classes
- **Error Handling**: Use appropriate exception handling
- **Security**: Never hardcode secrets; validate all inputs
- **Type Hints**: Use type annotations for function parameters and returns

### Example Code Style

```python
from typing import List, Optional
import hashlib


class Block:
    """
    Represents a block in the blockchain.

    Attributes:
        index: The position of the block in the chain
        timestamp: When the block was created
        transactions: List of transactions in the block
        previous_hash: Hash of the previous block
    """

    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: List[dict],
        previous_hash: str
    ) -> None:
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate the SHA-256 hash of the block."""
        block_string = f"{self.index}{self.timestamp}{self.transactions}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for system interaction
├── performance/    # Performance and stress tests
└── security/       # Security and vulnerability tests
```

### Writing Tests

- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names: `test_<what>_<when>_<expected>`
- Use fixtures for common setup
- Mock external dependencies

### Example Test

```python
import pytest
from src.core.blockchain import Blockchain


class TestBlockchain:
    """Test suite for Blockchain class."""

    def test_create_blockchain_initializes_genesis_block(self):
        """Test that creating a blockchain initializes with genesis block."""
        blockchain = Blockchain()
        assert len(blockchain.chain) == 1
        assert blockchain.chain[0].index == 0

    def test_add_block_increases_chain_length(self):
        """Test that adding a block increases the chain length."""
        blockchain = Blockchain()
        initial_length = len(blockchain.chain)
        blockchain.add_block(transactions=[])
        assert len(blockchain.chain) == initial_length + 1
```

## Pull Request Process

### Before Submitting

- [ ] Branch from `main` (or relevant feature branch)
- [ ] Update documentation for any changed functionality
- [ ] Add tests for new features
- [ ] Ensure all tests pass locally
- [ ] Run code quality tools (black, flake8, mypy)
- [ ] Update CHANGELOG.md if applicable
- [ ] Rebase on latest `main` to avoid merge conflicts

### PR Guidelines

1. **Title**: Clear, concise description of changes
2. **Description**: Use the PR template, explain what and why
3. **Scope**: Keep PRs focused on a single concern
4. **Size**: Prefer smaller PRs (<500 lines when possible)
5. **Reviews**: Address all review comments
6. **CI/CD**: Ensure all automated checks pass

### PR Review Process

1. Automated checks must pass (tests, linting, security scans)
2. At least one maintainer review required
3. Address all comments and requested changes
4. Maintainer approves and merges

### After Merge

- Delete your feature branch
- Close related issues (if applicable)
- Monitor for any issues in production

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semi-colons, etc.)
- **refactor**: Code refactoring without changing functionality
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates
- **ci**: CI/CD configuration changes
- **build**: Build system or external dependency changes

### Examples

```
feat(wallet): add multi-signature support

Implement multi-signature wallet functionality allowing multiple
signers to approve transactions before execution.

Closes #123
```

```
fix(blockchain): resolve race condition in block validation

Fixed a race condition that occurred when multiple nodes attempted
to validate the same block simultaneously.

Fixes #456
```

## Documentation

### When to Update Documentation

- Adding new features
- Changing existing behavior
- Fixing bugs that affect usage
- Improving configuration options
- Adding or updating APIs

### Documentation Standards

- Keep README.md up to date
- Document all public APIs
- Include code examples where helpful
- Update relevant guides in `/docs`
- Use clear, concise language
- Include diagrams for complex concepts

## Community

### Communication Channels

- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bug reports and feature requests
- **Discord**: [Join our server](#) for real-time chat
- **Twitter**: [@AIXN](#) for announcements

### Getting Help

- Check existing documentation and issues first
- Ask questions in GitHub Discussions
- Be respectful and patient
- Provide context and details when asking for help

### Recognition

We value all contributions! Contributors will be:
- Listed in our CONTRIBUTORS.md file
- Mentioned in release notes (for significant contributions)
- Eligible for community rewards and recognition

## Development Workflow

### Feature Development

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feat/my-feature

# Make changes, commit regularly
git add .
git commit -m "feat(scope): description"

# Push to your fork
git push origin feat/my-feature

# Create pull request on GitHub
```

### Staying Updated

```bash
# Sync with upstream regularly
git checkout main
git pull upstream main
git push origin main

# Rebase feature branch
git checkout feat/my-feature
git rebase main
```

## License

By contributing to AIXN, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE) file).

## Questions?

If you have questions about contributing, please:
1. Check this guide and other documentation
2. Search existing issues and discussions
3. Ask in GitHub Discussions
4. Contact the maintainers

Thank you for contributing to AIXN! Your efforts help build a better blockchain ecosystem.

---

**Last Updated**: January 2025
