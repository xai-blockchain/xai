# Contributing to XAI

Thanks for helping improve the project.

## Code of Conduct

By participating, you agree to follow `CODE_OF_CONDUCT.md`.

## Development Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest

# Optional: P2P checks
make ci-p2p
```

## Submitting Changes

1. Create a branch from `main`.
2. Keep changes focused and update docs as needed.
3. Run tests.
4. Open a pull request with a clear description.

## Reporting Issues

Use the issue tracker for bugs and feature requests. Include reproduction steps and logs where possible.

## Security Issues

Report security issues privately. See `SECURITY.md`.

## DCO Sign-off

Please sign off commits:

```bash
git commit -s -m "type: short description"
```

## License

By contributing, you agree that your contributions are licensed under the Apache 2.0 license.
