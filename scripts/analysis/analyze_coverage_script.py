#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def analyze_coverage():
    with open("coverage.json", "r") as f:
        cov_data = json.load(f)

    # Print overall summary
    print("=== OVERALL COVERAGE ===")
    totals = cov_data.get("totals", {})
    print(f"Percent covered: {totals.get('percent_covered', 'N/A')}%")
    print(f"Total statements: {totals.get('num_statements', 0)}")
    print(f"Covered statements: {totals.get('covered_lines', 0)}")
    print(f"Missing statements: {totals.get('missing_lines', 0)}")
    print()

    # Analyze modules
    files = cov_data.get("files", {})
    module_coverage = []

    for filepath, filedata in files.items():
        if 'src/xai' not in filepath and 'src\\xai' not in filepath:
            continue

        summary = filedata.get("summary", {})
        percent = summary.get("percent_covered", 0)
        statements = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", 0)
        missing = summary.get("missing_lines", 0)

        # Extract module name
        if 'src\\xai' in filepath:
            module_name = filepath.split('src\\xai\\')[-1]
        else:
            module_name = filepath.split('src/xai/')[-1]

        module_coverage.append({
            'name': module_name,
            'percent': percent,
            'statements': statements,
            'covered': covered,
            'missing': missing,
            'full_path': filepath
        })

    # Sort by coverage percentage
    module_coverage.sort(key=lambda x: x['percent'])

    # Print critical modules
    print("=== MODULES WITH <50% COVERAGE (CRITICAL) ===")
    critical = [m for m in module_coverage if m['percent'] < 50]
    print(f"Total modules below 50%: {len(critical)}\n")
    for mod in critical:
        print(f"{mod['name']}: {mod['percent']}%")
        print(f"  Statements: {mod['statements']} | Covered: {mod['covered']} | Missing: {mod['missing']}")
        print()

    print("=== MODULES WITH 50-80% COVERAGE ===")
    medium = [m for m in module_coverage if 50 <= m['percent'] < 80]
    print(f"Total modules in 50-80%: {len(medium)}\n")
    for mod in medium[:30]:
        print(f"{mod['name']}: {mod['percent']}%")
        print(f"  Statements: {mod['statements']} | Covered: {mod['covered']} | Missing: {mod['missing']}")
        print()

    # Check specific modules mentioned in task
    print("=== SPECIFIC MODULES MENTIONED IN TASK ===")
    mentioned = ['node_api.py', 'node.py', 'blockchain_security.py', 'wallet.py']
    for mention in mentioned:
        found = [m for m in module_coverage if mention in m['name']]
        if found:
            mod = found[0]
            print(f"{mod['name']}: {mod['percent']}%")
            print(f"  Statements: {mod['statements']} | Covered: {mod['covered']} | Missing: {mod['missing']}")
        else:
            print(f"{mention}: NOT FOUND")
        print()

    # Return data for file generation
    return {
        'total_coverage': totals.get('percent_covered', 0),
        'critical': critical,
        'medium': medium,
        'all_modules': module_coverage
    }

if __name__ == "__main__":
    analyze_coverage()
