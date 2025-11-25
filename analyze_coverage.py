#!/usr/bin/env python3
"""Analyze coverage and create priority matrix for test creation."""
import json
from pathlib import Path

# Load coverage data
with open('coverage.json', 'r') as f:
    data = json.load(f)

# Analyze by priority
core_modules = {}
security_modules = {}
api_modules = {}
blockchain_modules = {}

for filepath, filedata in data['files'].items():
    filename = filepath.split('\\')[-1]
    summary = filedata['summary']
    coverage_pct = summary.get('percent_covered', 0)
    missing = summary.get('missing_lines', 0)
    total_statements = summary.get('num_statements', 0)

    module_info = {
        'path': filepath,
        'coverage': coverage_pct,
        'missing_lines': missing,
        'total_statements': total_statements,
        'num_branches': summary.get('num_branches', 0),
        'missing_branches': summary.get('missing_branches', 0)
    }

    if 'src\\xai\\core\\' in filepath:
        core_modules[filename] = module_info
    if 'src\\xai\\security\\' in filepath:
        security_modules[filename] = module_info
    if 'src\\xai\\core\\api_' in filepath:
        api_modules[filename] = module_info
    if 'src\\xai\\blockchain\\' in filepath:
        blockchain_modules[filename] = module_info

print('=' * 100)
print('COMPREHENSIVE COVERAGE ANALYSIS FOR 98% TARGET')
print('=' * 100)
print(f'Overall Coverage: {data["totals"]["percent_covered"]:.2f}%')
print(f'Target Coverage: 98.00%')
print(f'Gap to Close: {98.0 - data["totals"]["percent_covered"]:.2f}%')
print(f'Total Files: {len(data["files"])}')
print(f'Total Statements: {data["totals"]["num_statements"]:,}')
print(f'Covered Statements: {data["totals"]["covered_lines"]:,}')
print(f'Missing Statements: {data["totals"]["missing_lines"]:,}')
print(f'Statements Needed for 98%: {int(data["totals"]["num_statements"] * 0.98 - data["totals"]["covered_lines"]):,}')
print('=' * 100)
print()

# Priority modules
priority_files = [
    'blockchain.py', 'wallet.py', 'transaction_validator.py',
    'security_validation.py', 'utxo_manager.py', 'node.py',
    'node_api.py', 'blockchain_security.py', 'advanced_consensus.py',
    'gamification.py', 'config_manager.py', 'trading.py'
]

print('PRIORITY 1: CORE MODULES (Target: 98%+)')
print('-' * 100)
print(f'{'Module':<45} {'Current':<12} {'Target':<12} {'Missing':<10} {'Total':<10}')
print('-' * 100)

for pfile in priority_files:
    if pfile in core_modules:
        mod = core_modules[pfile]
        print(f'{pfile:<45} {mod["coverage"]:>6.2f}%      98.00%      {mod["missing_lines"]:>6}     {mod["total_statements"]:>6}')

print()
print('PRIORITY 2: SECURITY MODULES (Target: 100%)')
print('-' * 100)
print(f'{'Module':<45} {'Current':<12} {'Target':<12} {'Missing':<10} {'Total':<10}')
print('-' * 100)

# Show top 10 security modules by statements
security_sorted = sorted(security_modules.items(), key=lambda x: x[1]['total_statements'], reverse=True)[:10]
for filename, mod in security_sorted:
    print(f'{filename:<45} {mod["coverage"]:>6.2f}%     100.00%      {mod["missing_lines"]:>6}     {mod["total_statements"]:>6}')

print()
print('MODULES WITH 0% COVERAGE (Critical Gap)')
print('-' * 100)
zero_coverage = []
for filepath, filedata in data['files'].items():
    filename = filepath.split('\\')[-1]
    if filedata['summary']['percent_covered'] == 0 and filedata['summary']['num_statements'] > 0:
        zero_coverage.append((filename, filedata['summary']['num_statements'], filepath))

zero_coverage.sort(key=lambda x: x[1], reverse=True)
print(f'Total modules with 0% coverage: {len(zero_coverage)}')
print(f'{'Module':<50} {'Statements':<15} {'Impact'}')
print('-' * 100)
for filename, statements, filepath in zero_coverage[:20]:
    impact = 'HIGH' if statements > 100 else 'MEDIUM' if statements > 50 else 'LOW'
    print(f'{filename:<50} {statements:>10}        {impact}')

print()
print('=' * 100)
print('RECOMMENDED TEST CREATION STRATEGY')
print('=' * 100)
print('''
PHASE 1: Critical Core Modules (Estimated: 2000+ test functions needed)
- blockchain.py: ~150 test functions
- wallet.py: ~120 test functions
- transaction_validator.py: ~80 test functions
- security_validation.py: ~100 test functions
- node_api.py: ~300 test functions
- utxo_manager.py: ~60 test functions

PHASE 2: Security & Validation (Estimated: 1500+ test functions needed)
- All security/* modules: ~500 test functions
- blockchain_security.py: ~150 test functions
- All blockchain/* modules: ~1000 test functions

PHASE 3: API & Network (Estimated: 1000+ test functions needed)
- All api_*.py modules: ~600 test functions
- All network/* modules: ~400 test functions

PHASE 4: Advanced Features (Estimated: 1500+ test functions needed)
- Governance modules: ~600 test functions
- Mining modules: ~400 test functions
- AI integration: ~500 test functions

TOTAL ESTIMATED: 6000+ test functions needed for 98% coverage
REALISTIC TIMEFRAME: Multiple weeks of full-time development
''')

print('=' * 100)
print('IMMEDIATE ACTION ITEMS')
print('=' * 100)
print('''
1. Start with blockchain.py - highest impact, 62% coverage → 98%
2. Add transaction_validator.py tests - security critical, 51% → 100%
3. Add security_validation.py tests - security critical, 44% → 100%
4. Add wallet.py comprehensive tests - core functionality, 28% → 98%
5. Add node_api.py tests - API coverage, 3% → 98%
''')
