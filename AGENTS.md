# XAI Project Guidelines

**Read `../CLAUDE.md` first** - contains all general instructions.

## Project-Specific

**Node:** `~/.xai/` (not in repo)
**Install:** `pip install -e .` (use venv if dependency conflicts)
**Run:** `python -m xai.core.node` or `./src/xai/START_TESTNET.sh`
**Test:** `pytest` (activate venv first if using one)

**Tools:** black, isort, pylint, flake8, mypy, bandit
**Pre-commit:** `pre-commit run --all-files`
