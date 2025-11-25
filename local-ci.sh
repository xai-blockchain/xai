#!/bin/bash
# Local CI/CD Pipeline - Bash Script
# Replicates GitHub Actions workflows locally for FREE
# Run this before pushing to GitHub to save CI minutes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

FAILED_CHECKS=()
PASSED_CHECKS=()

# Parse arguments
QUICK=false
SKIP_TESTS=false
SECURITY_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick) QUICK=true; shift ;;
        --skip-tests) SKIP_TESTS=true; shift ;;
        --security-only) SECURITY_ONLY=true; shift ;;
        *) shift ;;
    esac
done

print_header() {
    echo -e "\n${CYAN}========================================"
    echo -e " $1"
    echo -e "========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    PASSED_CHECKS+=("$1")
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    FAILED_CHECKS+=("$1")
}

echo -e "${MAGENTA}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║         LOCAL CI/CD PIPELINE - FREE ALTERNATIVE          ║
║              Replicates GitHub Actions                   ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Activate virtual environment
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}No virtual environment found. Creating one...${NC}"
    python -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
else
    if [ -d ".venv" ]; then source .venv/bin/activate
    elif [ -d "venv" ]; then source venv/bin/activate
    fi
fi

# ============================================================================
# 1. LINTING - Code Quality Checks
# ============================================================================
if [ "$SECURITY_ONLY" != true ]; then
    print_header "LINTING - Code Quality Checks"

    echo -e "${YELLOW}Installing linting tools...${NC}"
    pip install -q black isort flake8 pylint mypy 2>/dev/null || true

    # Black - Code formatting
    echo -e "\n${YELLOW}Running Black (code formatter)...${NC}"
    if black --check --diff src/ tests/ scripts/ 2>/dev/null; then
        print_success "Black formatting check"
    else
        print_failure "Black formatting check"
        black --check src/ tests/ scripts/ || true
    fi

    # isort - Import sorting
    echo -e "${YELLOW}Running isort (import sorting)...${NC}"
    if isort --check-only --diff src/ tests/ scripts/ 2>/dev/null; then
        print_success "isort import sorting"
    else
        print_failure "isort import sorting"
        isort --check-only src/ tests/ || true
    fi

    # Flake8 - Style guide enforcement
    echo -e "${YELLOW}Running Flake8 (style guide)...${NC}"
    if flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503 2>/dev/null; then
        print_success "Flake8 style guide"
    else
        print_failure "Flake8 style guide"
        flake8 src/ tests/ --max-line-length=100 || true
    fi

    if [ "$QUICK" != true ]; then
        # Pylint - Code analysis
        echo -e "${YELLOW}Running Pylint (code analysis)...${NC}"
        if pylint src/ --exit-zero --output-format=colorized >/dev/null 2>&1; then
            print_success "Pylint code analysis"
        else
            print_failure "Pylint code analysis"
        fi

        # MyPy - Type checking
        echo -e "${YELLOW}Running MyPy (type checking)...${NC}"
        if mypy src/ --ignore-missing-imports --no-strict-optional 2>/dev/null; then
            print_success "MyPy type checking"
        else
            print_failure "MyPy type checking"
        fi
    fi
fi

# ============================================================================
# 2. SECURITY SCANNING
# ============================================================================
print_header "SECURITY SCANNING"

echo -e "${YELLOW}Installing security tools...${NC}"
pip install -q bandit safety semgrep pip-audit 2>/dev/null || true

# Bandit - Security linter
echo -e "\n${YELLOW}Running Bandit (security linter)...${NC}"
bandit -r src/ -f json -o bandit-report.json 2>/dev/null || true
if bandit -r src/ -f txt --quiet; then
    print_success "Bandit security scan"
else
    print_failure "Bandit security scan"
fi

# Safety - Dependency vulnerability scanner
echo -e "${YELLOW}Running Safety (dependency vulnerabilities)...${NC}"
safety check --json --output safety-report.json 2>/dev/null || true
if safety check; then
    print_success "Safety dependency scan"
else
    print_failure "Safety dependency scan"
fi

# pip-audit - Dependency auditing
echo -e "${YELLOW}Running pip-audit (dependency auditing)...${NC}"
pip-audit --format json --output pip-audit-report.json 2>/dev/null || true
if pip-audit; then
    print_success "pip-audit dependency audit"
else
    print_failure "pip-audit dependency audit"
fi

if [ "$QUICK" != true ]; then
    # Semgrep - SAST scanning
    echo -e "${YELLOW}Running Semgrep (SAST analysis)...${NC}"
    semgrep --config=auto src/ --json --output=semgrep-report.json 2>/dev/null || true
    if semgrep --config=auto src/ --quiet; then
        print_success "Semgrep SAST scan"
    else
        print_failure "Semgrep SAST scan"
    fi
fi

# ============================================================================
# 3. TESTING
# ============================================================================
if [ "$SKIP_TESTS" != true ] && [ "$SECURITY_ONLY" != true ]; then
    print_header "TESTING"

    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -q pytest pytest-cov pytest-xdist pytest-timeout pytest-benchmark hypothesis 2>/dev/null || true
    [ -f "src/xai/requirements.txt" ] && pip install -q -r src/xai/requirements.txt 2>/dev/null || true
    [ -f "tests/xai_tests/requirements_test.txt" ] && pip install -q -r tests/xai_tests/requirements_test.txt 2>/dev/null || true

    # Unit Tests
    echo -e "\n${YELLOW}Running Unit Tests...${NC}"
    if pytest tests/xai_tests/unit/ -v --cov=src/xai/core --cov-report=xml --cov-report=html --cov-report=term-missing -n auto; then
        print_success "Unit tests"
    else
        print_failure "Unit tests"
    fi

    if [ "$QUICK" != true ]; then
        # Integration Tests
        echo -e "${YELLOW}Running Integration Tests...${NC}"
        if pytest tests/xai_tests/integration/ -v --cov=src/xai --cov-report=term-missing --timeout=300; then
            print_success "Integration tests"
        else
            print_failure "Integration tests"
        fi

        # Security Tests
        echo -e "${YELLOW}Running Security Tests...${NC}"
        if pytest tests/xai_tests/security/ -v --cov=src/xai --cov-report=term-missing; then
            print_success "Security tests"
        else
            print_failure "Security tests"
        fi

        # Performance Tests
        echo -e "${YELLOW}Running Performance Tests...${NC}"
        if pytest tests/xai_tests/performance/ -v --benchmark-only --benchmark-json=benchmark.json; then
            print_success "Performance tests"
        else
            print_failure "Performance tests"
        fi
    fi
fi

# ============================================================================
# SUMMARY
# ============================================================================
print_header "CI PIPELINE SUMMARY"

echo -e "\n${GREEN}Passed Checks (${#PASSED_CHECKS[@]}):${NC}"
for check in "${PASSED_CHECKS[@]}"; do
    echo -e "  ${GREEN}✓ $check${NC}"
done

if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "\n${RED}Failed Checks (${#FAILED_CHECKS[@]}):${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  ${RED}✗ $check${NC}"
    done
    echo -e "\n${YELLOW}⚠ Fix failed checks before pushing to GitHub!${NC}"
    exit 1
else
    echo -e "\n${GREEN}✓ All checks passed! Safe to push to GitHub.${NC}"
    echo -e "${CYAN}💰 You just saved GitHub Actions minutes!${NC}"
    exit 0
fi
