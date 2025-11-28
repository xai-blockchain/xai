# Coverage Automation Tools

Comprehensive suite of tools for achieving and maintaining 98%+ test coverage across XAI (Python) and PAW (Go) projects.

## Tools Overview

### Python Tools (XAI)

| Tool | Purpose | Status |
|------|---------|--------|
| `generate_test_scaffold.py` | Generate test file templates from Python modules | ✅ Ready |
| `find_uncovered_lines.py` | Identify and prioritize uncovered lines with context | ✅ Ready |
| `coverage_monitor.py` | Track coverage over time, detect regressions | ✅ Ready |
| `edge_case_generator.py` | Generate edge case and boundary condition tests | ✅ Ready |
| `coverage_badge_generator.py` | Create SVG badges and update documentation | ✅ Ready |

### Go Tools (PAW)

| Tool | Purpose | Status |
|------|---------|--------|
| `go_test_generator.go` | Generate table-driven test scaffolds for Go functions | ✅ Ready |
| `coverage_diff.py` | Compare Go and Python coverage metrics | ✅ Ready |

### CI/CD Integration

| Component | Purpose | Location | Status |
|-----------|---------|----------|--------|

## Quick Start

### Python (XAI)

```bash
cd /path/to/Crypto/scripts/coverage_tools

# Generate test scaffold for a module
python generate_test_scaffold.py ../../src/xai/core/blockchain.py

# Find uncovered lines
python find_uncovered_lines.py --show-code

# Monitor coverage
python coverage_monitor.py --check --threshold 98

# Generate badge
python coverage_badge_generator.py --all
```

### Go (PAW)

```bash
cd /path/to/paw/scripts/coverage_tools

# Build test generator
go build -o go_test_generator go_test_generator.go

# Generate tests
./go_test_generator ../../cmd/main.go

# Compare coverage
python coverage_diff.py --show-gaps
```

## Key Features

### ✅ Multi-Language Support
- Python test scaffolding and coverage analysis
- Go table-driven test generation
- Cross-language coverage comparison

### ✅ Comprehensive Coverage Analysis
- Uncovered line identification with code context
- Module-level coverage breakdown
- Priority-based recommendations

### ✅ Regression Prevention
- Coverage trend tracking over time
- Branch comparison (PR vs main)
- Automatic PR blocking if coverage decreases

### ✅ Automation Ready
- JSON output formats
- Markdown and HTML reporting

### ✅ Developer Friendly
- Simple CLI interfaces
- Clear error messages
- Detailed documentation

## Tool Descriptions

### 1. generate_test_scaffold.py

**Generates test file templates from Python source code**

Features:
- Analyzes functions, methods, and classes
- Creates test stubs with fixtures
- Includes edge case placeholders
- Provides coverage recommendations

```bash
python generate_test_scaffold.py <module_path> [--output <test_file>] [--force]
```

Example:
```bash
python generate_test_scaffold.py ../../src/xai/core/wallet.py \
  --output ../../tests/test_wallet.py
```

---

### 2. find_uncovered_lines.py

**Analyzes coverage.json and identifies uncovered lines**

Features:
- Parses coverage reports
- Shows code context
- Prioritizes by importance
- Generates TODO lists

```bash
python find_uncovered_lines.py [--coverage-file <file>] [--module <name>] [--show-code] [--output <file>]
```

Example:
```bash
python find_uncovered_lines.py \
  --coverage-file ../../coverage.json \
  --module blockchain \
  --show-code \
  --output blockchain_gaps.txt
```

---

### 3. coverage_monitor.py

**Tracks coverage over time and prevents regressions**

Features:
- Records coverage snapshots
- Detects decreases
- Compares branches
- Generates trend reports

```bash
python coverage_monitor.py [--record] [--check] [--compare <branch>] [--report] [--html <file>]
```

Example:
```bash
# Record current coverage
pytest --cov=src --cov-report=json
python coverage_monitor.py --record

# Check threshold
python coverage_monitor.py --check --threshold 98

# Compare with main
python coverage_monitor.py --compare main --verbose

# Generate trend chart
python coverage_monitor.py --html trend.html
```

---

### 4. edge_case_generator.py

**Generates edge case and boundary condition tests**

Features:
- Analyzes function signatures
- Creates parameterized tests
- Property-based test templates (Hypothesis)
- Boundary condition test stubs

```bash
python edge_case_generator.py <module_path> [--output <file>]
```

Example:
```bash
python edge_case_generator.py ../../src/xai/core/blockchain.py \
  --output ../../tests/test_blockchain_edge_cases.py
```

---

### 5. coverage_badge_generator.py

**Generates coverage badges and updates documentation**

Features:
- Creates SVG badges
- Updates README.md
- Color-coded by threshold
- Markdown and HTML formats

```bash
python coverage_badge_generator.py [--output <file>] [--update-readme] [--all]
```

Example:
```bash
# Generate everything
python coverage_badge_generator.py --all --threshold 98

# Just update README
python coverage_badge_generator.py --update-readme

# Just generate SVG
python coverage_badge_generator.py --output ../../badges/coverage.svg
```

---

### 6. go_test_generator.go

**Generates test scaffolds for Go functions**

Features:
- Table-driven test templates
- Benchmark test generation
- Test fixture stubs
- Edge case test placeholders

```bash
# Build first
go build -o go_test_generator go_test_generator.go

# Generate tests
./go_test_generator <go_file> [--output <test_file>]
```

Example:
```bash
go build -o go_test_generator go_test_generator.go
./go_test_generator ../../cmd/main.go --output ../../cmd/main_test.go
```

---

### 7. coverage_diff.py

**Compares Go and Python coverage metrics**

Features:
- Analyzes both languages
- Identifies coverage gaps
- Comparative reporting
- Progress tracking

```bash
python coverage_diff.py [--go-coverage <file>] [--py-coverage <file>] [--show-gaps] [--report] [--html <file>]
```

Example:
```bash
# Compare projects
python coverage_diff.py \
  --go-coverage ../../coverage.out \
  --py-coverage ../../Crypto/coverage.json \
  --show-gaps --threshold 95

# Generate HTML report
python coverage_diff.py \
  --html coverage_comparison.html
```

---

## CI/CD Integration



**Jobs:**
- `coverage-check`: Main coverage validation (98% threshold)
- `coverage-trend`: Historical trend analysis
- `pr-enforcement`: PR-specific enforcement
- `code-coverage-badge`: Badge generation
- `security-coverage`: Security module audits

**Features:**
- Runs on push, PR, and schedule
- Comments coverage on PRs
- Uploads reports as artifacts
- Generates badges
- Prevents coverage regressions

---

## Best Practices

### Daily Development

```bash
# Before committing
pytest --cov=src --cov-report=term-missing

# Find what to test
python scripts/coverage_tools/find_uncovered_lines.py --min-uncovered 5

# Add tests
# ... write tests ...

# Verify
python scripts/coverage_tools/coverage_monitor.py --check --threshold 98
```

### Creating New Modules

```bash
# 1. Create implementation
# ... write code ...

# 2. Generate test scaffold
python scripts/coverage_tools/generate_test_scaffold.py \
  src/xai/core/new_module.py

# 3. Implement tests
# ... write tests in scaffold ...

# 4. Generate edge cases
python scripts/coverage_tools/edge_case_generator.py \
  src/xai/core/new_module.py

# 5. Implement edge case tests
# ... write edge case tests ...

# 6. Verify 100% coverage
pytest tests/test_new_module.py --cov=src.xai.core.new_module --cov-fail-under=100
```

### Pull Request Review

```bash
# Fetch PR

# Check coverage
pytest --cov=src --cov-report=json
python scripts/coverage_tools/coverage_monitor.py --compare main --verbose

# Find gaps
python scripts/coverage_tools/find_uncovered_lines.py --show-code

# Accept or request improvements
```

---

## Dependencies

### Python Tools
- Python 3.10+
- pytest
- coverage
- hypothesis (for edge case generation)

Install:
```bash
pip install -e ".[dev]"
```

### Go Tools
- Go 1.21+

Build:
```bash
cd scripts/coverage_tools
go build -o go_test_generator go_test_generator.go
```

---

## Configuration

### pytest.ini / pyproject.toml

```ini
[tool.pytest.ini_options]
addopts = [
    "--cov=src",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-report=json",
    "--cov-fail-under=98",
]
```


The workflow uses environment variables:
```yaml
env:
  PYTHON_VERSION: '3.11'
  COVERAGE_THRESHOLD: 98
```


---

## Troubleshooting

### Coverage file not found
```bash
# Generate coverage.json first
pytest --cov=src --cov-report=json
```

### Tool shows 0% coverage
```bash
# Check source paths in pytest config
pytest --cov=src --cov-report=term -vv
```

### Python version mismatch
```bash
python3.11 scripts/coverage_tools/generate_test_scaffold.py <file>
```

### Go test generation fails
```bash
# Ensure Go module is properly initialized
go mod tidy
```

---

## File Structure

```
scripts/coverage_tools/
├── README.md                          # This file
├── generate_test_scaffold.py          # Python test generation
├── find_uncovered_lines.py            # Coverage analysis
├── coverage_monitor.py                # Coverage tracking
├── edge_case_generator.py             # Edge case tests
├── coverage_badge_generator.py        # Badge generation
├── go_test_generator.go               # Go test generation
├── coverage_diff.py                   # Cross-language comparison
└── __init__.py                        # Package marker


docs/
└── COVERAGE-AUTOMATION-GUIDE.md       # Comprehensive guide
```

---

## Contributing

To improve these tools:

1. Test changes locally
2. Update documentation
3. Add examples for new features
4. Ensure backward compatibility

---

## Support

For help:
1. Check tool `--help`
2. Review `COVERAGE-AUTOMATION-GUIDE.md`
3. Check Examples in tool documentation
4. Review generated reports

---

## License

Same as project (MIT)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-18
**Maintainer**: Coverage Automation Team
