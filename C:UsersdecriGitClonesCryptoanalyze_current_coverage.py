#!/usr/bin/env python3
"""Analyze current test coverage from .coverage file"""

import sys
import json
from pathlib import Path

try:
    # Try to import coverage library
    import coverage

    # Load the coverage data
    cov = coverage.Coverage(data_file='.coverage')
    cov.load()

    # Get the data
    data = cov.get_data()

    # Generate JSON report
    cov.json_report(outfile='coverage.json')

    # Now read and parse the JSON
    with open('coverage.json', 'r') as f:
        cov_data = json.load(f)

    # Extract overall stats
    totals = cov_data.get('totals', {})

    overall_percent = totals.get('percent_covered', 0)
    covered_lines = totals.get('covered_lines', 0)
    total_lines = totals.get('num_statements', 0)
    missing_lines = totals.get('missing_lines', 0)

    target = 80.0
    gap = target - overall_percent

    # Calculate statements needed for 80%
    if overall_percent < target:
        # Need to cover X more lines to reach 80%
        # (covered + X) / total = 0.80
        # covered + X = 0.80 * total
        # X = 0.80 * total - covered
        statements_needed = int((target / 100.0) * total_lines - covered_lines)
    else:
        statements_needed = 0

    # Get files data and sort by coverage percentage
    files_data = []
    for file_path, file_info in cov_data.get('files', {}).items():
        summary = file_info.get('summary', {})
        files_data.append({
            'path': file_path,
            'percent': summary.get('percent_covered', 0),
            'covered': summary.get('covered_lines', 0),
            'total': summary.get('num_statements', 0),
            'missing': summary.get('missing_lines', 0)
        })

    # Sort by coverage percentage (lowest first)
    files_data.sort(key=lambda x: x['percent'])

    # Write the report
    report_lines = []
    report_lines.append(f"Current Overall Coverage: {overall_percent:.2f}%")
    report_lines.append(f"Target: {target:.2f}%")
    report_lines.append(f"Gap: {gap:+.2f}%")
    report_lines.append(f"Covered Statements: {covered_lines} / {total_lines}")
    report_lines.append(f"Statements Needed for 80%: {statements_needed}")
    report_lines.append("")
    report_lines.append("Top 20 Lowest Coverage Modules:")

    for i, file_data in enumerate(files_data[:20], 1):
        file_name = Path(file_data['path']).name
        report_lines.append(
            f"{i}. {file_name} - {file_data['percent']:.2f}% "
            f"({file_data['missing']} statements missing)"
        )

    report = "\n".join(report_lines)

    # Write to file
    with open('OVERALL_COVERAGE_STATUS.txt', 'w') as f:
        f.write(report)

    # Print to stdout
    print(report)
    print()

    # Summary
    if overall_percent >= target:
        status = "ACHIEVED"
    else:
        status = "IN PROGRESS"

    print(f"\nSummary: Current overall coverage: {overall_percent:.2f}%. Gap to 80%: {gap:+.2f}%. Status: {status}")

except ImportError:
    print("ERROR: coverage module not found. Please install: pip install coverage")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
