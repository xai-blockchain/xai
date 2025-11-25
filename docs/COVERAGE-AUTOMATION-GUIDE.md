# Coverage Automation & Maintenance Guide

Complete guide to using the coverage automation tools for XAI (Python) and PAW (Go) projects to achieve and maintain 98%+ test coverage.

## Table of Contents

1. [Quick Start](#quick-start)
2. [XAI (Python) Tools](#xai-python-tools)
3. [PAW (Go) Tools](#paw-go-tools)
4. [CI/CD Integration](#cicd-integration)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Examples](#examples)

## Quick Start

### XAI Project (Python)

```bash
# Check current coverage
cd /path/to/Crypto
pytest --cov=src --cov-report=term-missing

# Generate test scaffold for a module
python scripts/coverage_tools/generate_test_scaffold.py src/xai/core/blockchain.py

# Find uncovered lines
python scripts/coverage_tools/find_uncovered_lines.py --show-code

# Monitor coverage
python scripts/coverage_tools/coverage_monitor.py --check --threshold 98

# Generate coverage badge
python scripts/coverage_tools/coverage_badge_generator.py --all
```

### PAW Project (Go)

```bash
# Check coverage
cd /path/to/paw
go test -cover ./...

# Generate test scaffold
go run scripts/coverage_tools/go_test_generator.go cmd/main.go

# Compare Python and Go coverage
python scripts/coverage_tools/coverage_diff.py --show-gaps
```

## XAI (Python) Tools

### 1. generate_test_scaffold.py

**Purpose**: Analyze Python modules and generate comprehensive test templates.

**Features**:
- Extracts all functions, methods, and classes
- Generates test stubs with fixtures
- Includes edge case placeholders
- Provides coverage recommendations

**Usage**:

```bash
# Generate test for a single module
python scripts/coverage_tools/generate_test_scaffold.py src/xai/core/blockchain.py

# Custom output location
python scripts/coverage_tools/generate_test_scaffold.py src/xai/core/wallet.py \
  --output tests/test_wallet_custom.py

# Force overwrite existing file
python scripts/coverage_tools/generate_test_scaffold.py src/xai/core/node.py \
  --force
```

**Output Example**:

```python
from xai.core.blockchain import Blockchain

class TestBlockchain:
    """Test suite for Blockchain class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.blockchain = Blockchain()

    def test_initialization(self):
        """Test Blockchain initialization."""
        assert isinstance(self.blockchain.chain, list)
        assert self.blockchain.chain == [] or all(hasattr(block, "hash") for block in self.blockchain.chain)

    def test_add_block_edge_cases(self):
        """Test add_block with edge cases."""
        placeholder_block = Blockchain().create_block([], "GENESIS")
        assert placeholder_block is not None
        result = self.blockchain.add_block(placeholder_block)
        assert result
```

**Next Steps**:
1. Edit generated file to add test implementations
2. Run `pytest tests/test_<module>.py -v`
3. Run `pytest tests/test_<module>.py --cov --cov-report=html`

---

### 2. find_uncovered_lines.py

**Purpose**: Identify and prioritize uncovered lines for testing.

**Features**:
- Parses coverage.json reports
- Shows code context for uncovered lines
- Prioritizes by module importance
- Generates actionable TODO lists

**Usage**:

```bash
# Show all uncovered lines
python scripts/coverage_tools/find_uncovered_lines.py

# Show with code context
python scripts/coverage_tools/find_uncovered_lines.py --show-code

# Focus on specific module
python scripts/coverage_tools/find_uncovered_lines.py --module blockchain

# Only show files with many uncovered lines
python scripts/coverage_tools/find_uncovered_lines.py --min-uncovered 20

# Save to file
python scripts/coverage_tools/find_uncovered_lines.py \
  --show-code \
  --output coverage_gaps.txt

# JSON format for programmatic use
python scripts/coverage_tools/find_uncovered_lines.py \
  --json \
  --output coverage_gaps.json
```

**Example Output**:

```
================================================================================
UNCOVERED LINES REPORT
================================================================================

SUMMARY
----------------================================================================
Total Files Analyzed: 42
Files Below 98% Coverage: 5
Total Uncovered Lines: 127

DETAILED UNCOVERED LINES
================================================================================

File: src/xai/core/blockchain.py
Coverage: 96.45% (203/210)
Uncovered Lines: 7
--------------------------------------------------------------------------------
  Line 125: def validate_block(block: Block) -> bool:
    > def validate_block(block: Block) -> bool:
    < if not isinstance(block, Block):
  Line 145: return check_merkle_root(block)
  ...

ACTION ITEMS (PRIORITIZED)
================================================================================
1. [96.5%] src/xai/core/blockchain.py
   Add 7 tests to reach 100% coverage

2. [94.2%] src/xai/core/wallet.py
   Add 15 tests to reach 100% coverage
```

---

### 3. coverage_monitor.py

**Purpose**: Track coverage over time and prevent regressions.

**Features**:
- Records coverage snapshots
- Detects coverage decreases
- Compares branches
- Generates trend reports
- Creates HTML trend charts

**Usage**:

```bash
# Record current coverage
python scripts/coverage_tools/coverage_monitor.py --record

# Check coverage meets threshold
python scripts/coverage_tools/coverage_monitor.py --check --threshold 98

# Compare with main branch
python scripts/coverage_tools/coverage_monitor.py --compare main --verbose

# View coverage trend
python scripts/coverage_tools/coverage_monitor.py --report

# Generate HTML trend chart
python scripts/coverage_tools/coverage_monitor.py --html coverage_trend.html

# Full workflow
pytest --cov=src --cov-report=json
python scripts/coverage_tools/coverage_monitor.py --record
python scripts/coverage_tools/coverage_monitor.py --check --threshold 98
```

**In CI/CD**:

```yaml
- name: Check coverage
  run: |
    pytest --cov=src --cov-report=json
    python scripts/coverage_tools/coverage_monitor.py --check --threshold 98

- name: Compare with main
  if: github.event_name == 'pull_request'
  run: |
    python scripts/coverage_tools/coverage_monitor.py --compare main
```

---

### 4. edge_case_generator.py

**Purpose**: Generate parameterized tests for edge cases.

**Features**:
- Analyzes function signatures
- Generates boundary condition tests
- Creates property-based tests (Hypothesis)
- Tests edge cases: empty, null, min, max values

**Usage**:

```bash
# Generate edge case tests
python scripts/coverage_tools/edge_case_generator.py src/xai/core/blockchain.py

# Custom output
python scripts/coverage_tools/edge_case_generator.py src/xai/core/wallet.py \
  --output tests/test_wallet_edge_cases.py
```

**Generated Tests**:

```python
class TestBoundaryConditions:
    """Test boundary conditions and special cases."""

    def test_empty_collections(self):
        """Test with empty lists, dicts, sets."""
        # TODO: Test empty []
        # TODO: Test empty {}
        # TODO: Test empty set()
        pass

    def test_special_numeric_values(self):
        """Test with special numeric values."""
        # TODO: Test zero: 0
        # TODO: Test negative: -1
        # TODO: Test infinity: float('inf')
        # TODO: Test NaN: float('nan')
        pass

@given(st.lists(st.integers()))
def test_with_arbitrary_lists(self, value):
    """Test with arbitrary list values using Hypothesis."""
    # TODO: Add property-based test
    pass
```

---

### 5. coverage_badge_generator.py

**Purpose**: Generate coverage badges and update documentation.

**Features**:
- Creates SVG coverage badges
- Updates README automatically
- Supports Markdown and HTML formats
- Color-coded by coverage level

**Usage**:

```bash
# Generate SVG badge
python scripts/coverage_tools/coverage_badge_generator.py \
  --output badges/coverage.svg

# Update README with badge
python scripts/coverage_tools/coverage_badge_generator.py \
  --update-readme

# Do both
python scripts/coverage_tools/coverage_badge_generator.py --all

# Generate Markdown badge for docs
python scripts/coverage_tools/coverage_badge_generator.py --markdown

# Generate HTML badge
python scripts/coverage_tools/coverage_badge_generator.py --html
```

**Badge Colors**:
- Green: 98%+ (excellent)
- Light Blue: 95-98% (good)
- Yellow: 90-95% (fair)
- Orange: 80-90% (poor)
- Red: <80% (critical)

---

## PAW (Go) Tools

### 1. go_test_generator.go

**Purpose**: Analyze Go functions and generate test scaffolds.

**Features**:
- Parses Go source files
- Generates table-driven tests
- Creates benchmark tests
- Generates test fixtures
- Includes edge case test templates

**Build and Usage**:

```bash
# Build the generator
cd /path/to/paw/scripts/coverage_tools
go build -o go_test_generator go_test_generator.go

# Generate tests for a Go file
./go_test_generator cmd/main.go

# Custom output
./go_test_generator cmd/main.go --output cmd/main_test.go
```

**Generated Test Structure**:

```go
// TestFunctionName tests FunctionName with table-driven tests.
func TestFunctionName(t *testing.T) {
    tests := []struct {
        name    string
        args    args
        want    interface{}
        wantErr bool
    }{
        {
            name: "basic case",
            args: args{
                // TODO: Add test values
            },
            want:    nil, // TODO: Add expected value
            wantErr: false,
        },
        {
            name: "empty input",
            // ...
        },
        {
            name: "invalid input",
            // ...
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // TODO: Call function and verify results
        })
    }
}

// BenchmarkFunctionName benchmarks FunctionName.
func BenchmarkFunctionName(b *testing.B) {
    // TODO: Add benchmark setup
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        // TODO: Call function
    }
}
```

---

### 2. coverage_diff.py

**Purpose**: Compare Go and Python coverage metrics.

**Features**:
- Analyzes both Go and Python coverage
- Identifies gaps in both projects
- Generates comparative reports
- Tracks progress across languages

**Usage**:

```bash
# Compare coverage between projects
python scripts/coverage_tools/coverage_diff.py \
  --go-coverage coverage.out \
  --py-coverage ../Crypto/coverage.json

# Show coverage gaps
python scripts/coverage_tools/coverage_diff.py --show-gaps

# Specific threshold
python scripts/coverage_tools/coverage_diff.py --show-gaps --threshold 95

# Generate reports
python scripts/coverage_tools/coverage_diff.py --report

# Save to file
python scripts/coverage_tools/coverage_diff.py --report --output comparison.txt

# Generate HTML comparison
python scripts/coverage_tools/coverage_diff.py --html coverage_comparison.html
```

**Example Output**:

```
================================================================================
COVERAGE COMPARISON REPORT
================================================================================

[GO PROJECT]
Total Coverage: 94.23%
Files: 45/48
Statements: 1823/1935

[PYTHON PROJECT]
Total Coverage: 98.15%
Files: 38/39
Statements: 2156/2198

[DIFFERENCE]
Absolute: -3.92%
Better: Python

================================================================================
MODULES BELOW 95% COVERAGE
================================================================================

Go Modules:
  x/types: 87.50% (gap: 7.50%)
  x/keeper: 92.15% (gap: 2.85%)

Python Modules:
  (All modules above 95%)
```

---

## CI/CD Integration

### GitHub Actions Workflow

The project includes `.github/workflows/coverage-enforcement.yml` that:

1. **Runs on every PR**: Checks coverage meets 98% threshold
2. **Comments on PRs**: Posts coverage report with comparison to main
3. **Generates badges**: Creates and commits coverage badge
4. **Tracks trends**: Records coverage over time
5. **Prevents regressions**: Fails if coverage decreases

**Workflow Jobs**:

```yaml
- coverage-check: Main coverage validation
- coverage-trend: Historical trend analysis
- pr-enforcement: Pull request specific checks
- code-coverage-badge: Badge generation
- security-coverage: Security module audits
```

**Example PR Comment**:

```
## Coverage Report

✅ **Total Coverage: 98.45%**

- **Statements**: 2156/2198
- **Missing**: 42 lines
- **Threshold**: 98%
- **Status**: ✅ PASS

### Uncovered Lines
src/xai/core/blockchain.py:125: def validate_block(...)
src/xai/core/wallet.py:234: def transfer_funds(...)
```

### Local Testing Before PR

```bash
# Simulate CI checks locally
pytest \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=json \
  --cov-fail-under=98

# Check against main
git fetch origin main
python scripts/coverage_tools/coverage_monitor.py --compare main --verbose

# Find what to test next
python scripts/coverage_tools/find_uncovered_lines.py --show-code --min-uncovered 5
```

---

## Best Practices

### 1. Regular Coverage Checks

```bash
# Add to your development workflow
alias cov="pytest --cov=src --cov-report=html && open htmlcov/index.html"

# Check daily
cov
python scripts/coverage_tools/find_uncovered_lines.py --min-uncovered 10
```

### 2. Incremental Test Development

```bash
# 1. Generate scaffold
python scripts/coverage_tools/generate_test_scaffold.py src/xai/core/new_module.py

# 2. Implement tests incrementally
# - Start with basic test cases
# - Run coverage check
# - Add edge case tests
# - Add boundary condition tests

pytest tests/test_new_module.py --cov --cov-report=html
python scripts/coverage_tools/find_uncovered_lines.py --module new_module --show-code
```

### 3. Edge Case Testing

```bash
# Generate edge case tests
python scripts/coverage_tools/edge_case_generator.py src/xai/core/module.py

# Run only edge case tests
pytest tests/test_module_edge_cases.py -v

# Property-based testing with Hypothesis
pytest tests/test_module_edge_cases.py::TestPropertyBased -v
```

### 4. Branch-Specific Checks

```bash
# Before committing
git fetch origin
python scripts/coverage_tools/coverage_monitor.py --compare main

# Only commit if coverage didn't decrease
if [[ $? -eq 0 ]]; then
  git commit -m "feat: add feature with 98%+ coverage"
fi
```

### 5. Security Module Testing

```bash
# Highest priority for security modules
pytest \
  --cov=src/xai/core/security \
  --cov=src/xai/core/blockchain_security \
  --cov-fail-under=99 \
  -v

python scripts/coverage_tools/find_uncovered_lines.py \
  --module security \
  --show-code
```

---

## Troubleshooting

### Issue: Coverage.json not found

**Solution**:
```bash
# Generate coverage.json
pytest --cov=src --cov-report=json

# Or specify custom path
python scripts/coverage_tools/find_uncovered_lines.py \
  --coverage-file path/to/coverage.json
```

### Issue: Coverage report shows 0%

**Solution**:
```bash
# Ensure correct source paths in pytest config
cat pyproject.toml | grep -A5 "tool.coverage"

# Run with verbose output
pytest --cov=src --cov-report=term -vv
```

### Issue: Tests timing out

**Solution**:
```bash
# Run with timeout
pytest -v --timeout=300 --cov=src

# Skip slow tests during development
pytest -v --cov=src -m "not slow"
```

### Issue: Coverage threshold fails

**Solution**:
```bash
# Find uncovered lines
python scripts/coverage_tools/find_uncovered_lines.py \
  --show-code \
  --min-uncovered 1

# Generate edge case tests
python scripts/coverage_tools/edge_case_generator.py src/xai/core/module.py

# Run specific tests
pytest tests/test_module.py::TestClass::test_method -vv
```

### Issue: Git hook blocking commits

**Solution**:
```bash
# Run coverage check locally first
pytest --cov=src --cov-fail-under=98

# Or skip hooks (only for development)
git commit --no-verify -m "message"
```

---

## Examples

### Example 1: Add Tests to Reach 98% Coverage

```bash
# 1. Find current gaps
python scripts/coverage_tools/find_uncovered_lines.py \
  --module wallet \
  --show-code \
  --output wallet_gaps.txt

# 2. Generate test scaffold
python scripts/coverage_tools/generate_test_scaffold.py \
  src/xai/core/wallet.py \
  --output tests/test_wallet.py

# 3. Implement tests based on gaps
# Edit tests/test_wallet.py and add implementations

# 4. Check coverage incrementally
pytest tests/test_wallet.py --cov --cov-report=html

# 5. Add edge cases
python scripts/coverage_tools/edge_case_generator.py \
  src/xai/core/wallet.py \
  --output tests/test_wallet_edge_cases.py

# 6. Final check
pytest tests/test_wallet*.py --cov=src.xai.core.wallet --cov-fail-under=98
```

### Example 2: Review PR Coverage

```bash
# 1. Fetch PR changes
git fetch origin pull/123/head:pr-123
git checkout pr-123

# 2. Run coverage
pytest --cov=src --cov-report=json

# 3. Compare with main
python scripts/coverage_tools/coverage_monitor.py --compare main --verbose

# 4. Find gaps in new code
python scripts/coverage_tools/find_uncovered_lines.py \
  --show-code \
  --output pr_123_gaps.txt

# 5. Request test improvements if needed
```

### Example 3: Cross-Project Coverage Analysis

```bash
# 1. Generate both reports
cd ../Crypto
pytest --cov=src --cov-report=json

cd ../paw
go test -coverprofile=coverage.out ./...

# 2. Compare coverage
python scripts/coverage_tools/coverage_diff.py \
  --go-coverage coverage.out \
  --py-coverage ../Crypto/coverage.json \
  --html comparison.html

# 3. Identify priority gaps
python scripts/coverage_tools/coverage_diff.py \
  --show-gaps \
  --threshold 95

# 4. Generate reports
python scripts/coverage_tools/coverage_diff.py \
  --report \
  --output coverage_analysis.txt
```

---

## Integration with IDEs

### VSCode

Add to `.vscode/settings.json`:

```json
{
  "python.linting.pylintEnabled": true,
  "python.linting.pylintArgs": ["--load-plugins=pylint_django"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests", "--cov=src"],
  "coverage.showCoverage": true,
  "coverage.gutterHighlight": true
}
```

### PyCharm

1. Run → Edit Configurations
2. Select pytest configuration
3. Set Coverage options:
   - ✅ Show coverage data
   - ✅ Highlight uncovered code
   - Threshold: 98%

---

## Maintenance

### Monthly Coverage Review

```bash
# 1. Generate trend report
python scripts/coverage_tools/coverage_monitor.py --report

# 2. Review uncovered modules
python scripts/coverage_tools/find_uncovered_lines.py --min-uncovered 20

# 3. Plan coverage improvements
# - Prioritize critical modules
# - Schedule test implementation
# - Update roadmap

# 4. Generate badges
python scripts/coverage_tools/coverage_badge_generator.py --all
```

### Quarterly Coverage Goals

- Target: 98% + (aim for 99%)
- New modules: 100%
- Refactored code: 100%
- Security modules: 99%+

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Hypothesis Testing](https://hypothesis.readthedocs.io/)
- [Go Testing](https://golang.org/pkg/testing/)
- [Table-Driven Tests](https://github.com/golang/go/wiki/TableDrivenTests)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Examples](#examples) for similar use cases
3. Check tool help: `python <tool>.py --help`
4. Review generated reports for insights

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
