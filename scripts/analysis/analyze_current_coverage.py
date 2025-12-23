#!/usr/bin/env python3
"""
Analyze current coverage from coverage.json file.
"""

import json
import os
from pathlib import Path

def analyze_coverage():
    """Analyze the coverage.json file and generate report."""

    # Try to find the most recent coverage file
    coverage_files = [
        '.coverage.json',
        'new_coverage.json',
        'coverage.json'
    ]

    coverage_data = None
    for file in coverage_files:
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    coverage_data = json.load(f)
                print(f"Loaded coverage from: {file}")
                break
            except Exception as e:
                print(f"Error loading {file}: {e}")
                continue

    if coverage_data is None:
        print("No coverage file found!")
        return

    # Extract totals
    totals = coverage_data.get('totals', {})
    overall_coverage = totals.get('percent_covered', 0)
    covered_lines = totals.get('covered_lines', 0)
    total_statements = totals.get('num_statements', 0)
    missing_lines = totals.get('missing_lines', 0)

    # Calculate statistics
    target_coverage = 80.0
    coverage_gap = target_coverage - overall_coverage

    # Estimate statements needed to reach 80%
    if coverage_gap > 0:
        # We need: (total_needed * 0.80) = current_covered + additional_covered
        # To reach 80%, we need to cover: total_statements * 0.80
        statements_needed_for_80 = int(total_statements * 0.80)
        additional_statements = statements_needed_for_80 - covered_lines
    else:
        additional_statements = 0

    print("\n" + "="*70)
    print("CURRENT COVERAGE STATUS")
    print("="*70)
    print(f"\nOverall Coverage:      {overall_coverage:.2f}%")
    print(f"Covered Statements:    {covered_lines:,} / {total_statements:,}")
    print(f"Missing Statements:    {missing_lines:,}")
    print(f"\nTarget Coverage:       {target_coverage:.2f}%")
    print(f"Coverage Gap:          {coverage_gap:+.2f}%")

    if coverage_gap > 0:
        print(f"\nTo reach 80% coverage:")
        print(f"  Additional statements to cover: {additional_statements:,}")
        print(f"  Total required coverage:        {statements_needed_for_80:,}")
    else:
        print(f"\nTarget already achieved! Exceeding by {abs(coverage_gap):.2f}%")

    # Analyze by file
    files = coverage_data.get('files', {})
    file_coverage = []

    for file_path, file_data in files.items():
        summary = file_data.get('summary', {})
        pct = summary.get('percent_covered', 0)
        covered = summary.get('covered_lines', 0)
        total = summary.get('num_statements', 0)
        file_coverage.append({
            'path': file_path,
            'coverage': pct,
            'covered': covered,
            'total': total
        })

    # Sort by coverage (lowest first)
    file_coverage.sort(key=lambda x: x['coverage'])

    print("\n" + "="*70)
    print("TOP 20 MODULES WITH LOWEST COVERAGE")
    print("="*70)
    print(f"{'File':<50} {'Coverage':<12} {'Covered/Total':<15}")
    print("-"*70)

    for i, item in enumerate(file_coverage[:20]):
        file_name = Path(item['path']).name
        coverage_str = f"{item['coverage']:.2f}%"
        covered_str = f"{item['covered']}/{item['total']}"
        print(f"{file_name:<50} {coverage_str:<12} {covered_str:<15}")

    print("\n" + "="*70)
    print("COVERAGE DISTRIBUTION")
    print("="*70)

    # Count files by coverage ranges
    ranges = [
        (0, 20, "0-20%"),
        (20, 40, "20-40%"),
        (40, 60, "40-60%"),
        (60, 80, "60-80%"),
        (80, 100, "80-100%"),
        (100, 101, "100%")
    ]

    for low, high, label in ranges:
        count = sum(1 for item in file_coverage if low <= item['coverage'] < high)
        pct = (count / len(file_coverage) * 100) if file_coverage else 0
        print(f"{label:<15}: {count:>4} files ({pct:>5.1f}%)")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nTotal files analyzed:  {len(file_coverage)}")
    print(f"Average coverage:      {sum(item['coverage'] for item in file_coverage) / len(file_coverage):.2f}%")

    if coverage_gap > 0:
        print(f"\nEstimated priority areas to improve coverage:")
        priority_files = [f for f in file_coverage if f['coverage'] < 50]
        if priority_files:
            for item in priority_files[:5]:
                print(f"  - {Path(item['path']).name:<40} {item['coverage']:.2f}%")
        else:
            print("  (Most files already above 50% coverage)")

    return coverage_data, overall_coverage, covered_lines, total_statements, additional_statements


if __name__ == '__main__':
    analyze_coverage()
