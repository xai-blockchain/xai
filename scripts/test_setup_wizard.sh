#!/usr/bin/env bash
#
# Test script for XAI Setup Wizard
# Verifies all features and functions work correctly
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WIZARD_PY="$SCRIPT_DIR/setup_wizard.py"
WIZARD_SH="$SCRIPT_DIR/setup_wizard.sh"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

print_test() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

# Test 1: Python syntax check
print_test "Python syntax validation"
if python3 -m py_compile "$WIZARD_PY" 2>/dev/null; then
    pass "Python syntax is valid"
else
    fail "Python syntax errors found"
fi

# Test 2: Bash syntax check
print_test "Bash syntax validation"
if bash -n "$WIZARD_SH" 2>/dev/null; then
    pass "Bash syntax is valid"
else
    fail "Bash syntax errors found"
fi

# Test 3: Python imports
print_test "Python imports"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/..')
try:
    import os, sys, socket, secrets, hashlib, json, shutil, subprocess, platform, getpass
    from pathlib import Path
    from typing import Optional, Dict, List, Tuple
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
" 2>/dev/null; then
    pass "All required imports available"
else
    fail "Missing required imports"
fi

# Test 4: Check functions exist
print_test "Function definitions"
if grep -q "def detect_os()" "$WIZARD_PY" && \
   grep -q "def check_python_version()" "$WIZARD_PY" && \
   grep -q "def check_git_installed()" "$WIZARD_PY" && \
   grep -q "def check_pip_installed()" "$WIZARD_PY" && \
   grep -q "def print_progress(" "$WIZARD_PY" && \
   grep -q "def print_step(" "$WIZARD_PY" && \
   grep -q "def create_wallet()" "$WIZARD_PY"; then
    pass "All required functions defined"
else
    fail "Missing function definitions"
fi

# Test 5: OS detection
print_test "OS detection functionality"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
os_type, os_name, os_version = detect_os()
assert os_type in ['linux', 'darwin', 'windows'], f'Invalid OS type: {os_type}'
assert len(os_name) > 0, 'OS name is empty'
print('OK')
" 2>/dev/null; then
    pass "OS detection works"
else
    fail "OS detection failed"
fi

# Test 6: Python version check
print_test "Python version checking"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
is_ok, version = check_python_version()
assert isinstance(is_ok, bool), 'Invalid return type'
assert len(version) > 0, 'Version string is empty'
print('OK')
" 2>/dev/null; then
    pass "Python version check works"
else
    fail "Python version check failed"
fi

# Test 7: Git check
print_test "Git installation check"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
is_ok, version = check_git_installed()
assert isinstance(is_ok, bool), 'Invalid return type'
print('OK')
" 2>/dev/null; then
    pass "Git check works"
else
    fail "Git check failed"
fi

# Test 8: Pip check
print_test "Pip installation check"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
is_ok, version = check_pip_installed()
assert isinstance(is_ok, bool), 'Invalid return type'
print('OK')
" 2>/dev/null; then
    pass "Pip check works"
else
    fail "Pip check failed"
fi

# Test 9: Port availability check
print_test "Port availability checking"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
# Test with a likely available port
available = is_port_available(54321)
assert isinstance(available, bool), 'Invalid return type'
print('OK')
" 2>/dev/null; then
    pass "Port checking works"
else
    fail "Port checking failed"
fi

# Test 10: Secret generation
print_test "Secret generation"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
jwt_secret = generate_jwt_secret()
wallet_secret = generate_wallet_trade_secret()
enc_key = generate_encryption_key()
assert len(jwt_secret) == 64, f'JWT secret wrong length: {len(jwt_secret)}'
assert len(wallet_secret) == 64, f'Wallet secret wrong length: {len(wallet_secret)}'
assert len(enc_key) == 64, f'Encryption key wrong length: {len(enc_key)}'
assert jwt_secret != wallet_secret, 'Secrets should be different'
print('OK')
" 2>/dev/null; then
    pass "Secret generation works"
else
    fail "Secret generation failed"
fi

# Test 11: Address validation
print_test "Address validation"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
# Valid addresses
assert validate_xai_address('XAI1' + 'a'*40) == True, 'Should accept valid XAI1 address'
assert validate_xai_address('0x' + 'a'*40) == True, 'Should accept valid 0x address'
# Invalid addresses
assert validate_xai_address('XAI1abc') == False, 'Should reject short XAI1 address'
assert validate_xai_address('0xabc') == False, 'Should reject short 0x address'
assert validate_xai_address('invalid') == False, 'Should reject invalid format'
print('OK')
" 2>/dev/null; then
    pass "Address validation works"
else
    fail "Address validation failed"
fi

# Test 12: Disk space check
print_test "Disk space checking"
if python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
is_ok, available = check_disk_space(Path('/tmp'), 1)
assert isinstance(is_ok, bool), 'Invalid return type for is_ok'
assert isinstance(available, int), 'Invalid return type for available'
print('OK')
" 2>/dev/null; then
    pass "Disk space check works"
else
    fail "Disk space check failed"
fi

# Test 13: Network connectivity test
print_test "Network connectivity test"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
connected, msg = test_network_connectivity()
assert isinstance(connected, bool), 'Invalid return type for connected'
assert isinstance(msg, str), 'Invalid return type for message'
assert len(msg) > 0, 'Message should not be empty'
print('OK')
" 2>/dev/null; then
    pass "Network connectivity test works"
else
    fail "Network connectivity test failed"
fi

# Test 14: Color class
print_test "Color class"
if python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
exec(open('$WIZARD_PY').read())
assert hasattr(Colors, 'GREEN'), 'Missing GREEN color'
assert hasattr(Colors, 'RED'), 'Missing RED color'
assert hasattr(Colors, 'YELLOW'), 'Missing YELLOW color'
assert hasattr(Colors, 'CYAN'), 'Missing CYAN color'
assert hasattr(Colors, 'disable'), 'Missing disable method'
Colors.disable()
assert Colors.GREEN == '', 'Colors not disabled properly'
print('OK')
" 2>/dev/null; then
    pass "Color class works"
else
    fail "Color class failed"
fi

# Test 15: Executable permissions
print_test "Executable permissions"
if [ -x "$WIZARD_PY" ] && [ -x "$WIZARD_SH" ]; then
    pass "Scripts have executable permissions"
else
    fail "Scripts missing executable permissions"
fi

# Summary
echo ""
echo "================================"
echo "Test Summary"
echo "================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "================================"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
