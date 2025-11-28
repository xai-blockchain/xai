# Contributing to XAI

Thank you for your interest in contributing to XAI! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

- Check existing issues to avoid duplicates
- Use the bug report template
- Include steps to reproduce
- Provide system information (OS, Python version, etc.)

### Suggesting Features

- Check existing issues and discussions
- Clearly describe the feature and its use case
- Consider implementation complexity

### Submitting Code

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Run tests locally**
   ```bash
   source .venv/bin/activate
   pytest
   pre-commit run --all-files
   ```
5. **Commit with clear messages**
   ```bash
   git commit -m "feat: add new feature description"
   ```
6. **Push and create a Pull Request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/xai.git
cd xai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `isort` for import sorting

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, no code change
- `refactor:` - Code change that neither fixes a bug nor adds a feature
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Testing

- Write tests for new features
- Maintain or improve code coverage
- All tests must pass before merge

### Security

- Never commit secrets or private keys
- Run `bandit` security scanner
- Follow blockchain security best practices
- Report vulnerabilities privately (see SECURITY.md)

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all checks pass
4. Request review from maintainers
5. Address review feedback
6. Squash commits if requested

## Questions?

- Open a GitHub Discussion
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).
