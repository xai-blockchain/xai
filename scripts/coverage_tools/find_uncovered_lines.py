#!/usr/bin/env python3
"""
Find uncovered lines in Python code from coverage.json reports.

Analyzes coverage.json and identifies uncovered lines with context,
prioritized by module importance. Generates actionable TODO list.

Usage:
    python find_uncovered_lines.py [--coverage-file coverage.json]
    python find_uncovered_lines.py --min-uncovered 10 --output report.txt

Examples:
    python find_uncovered_lines.py
    python find_uncovered_lines.py --module src/xai/core/blockchain.py
    python find_uncovered_lines.py --min-uncovered 5 --show-code
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import argparse


@dataclass
class UncoveredLine:
    """Information about an uncovered line."""
    line_number: int
    code: Optional[str]
    file_path: str
    context_before: List[str]
    context_after: List[str]


@dataclass
class FileReport:
    """Coverage report for a file."""
    file_path: str
    total_lines: int
    covered_lines: int
    uncovered_lines: List[int]
    coverage_percentage: float
    uncovered_count: int


def read_coverage_json(coverage_file: Path) -> Dict:
    """Read coverage.json file."""
    if not coverage_file.exists():
        print(f"Error: Coverage file not found: {coverage_file}", file=sys.stderr)
        sys.exit(1)

    with open(coverage_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_line_context(file_path: Path, line_number: int, context_size: int = 2) -> Tuple[List[str], str, List[str]]:
    """Get code context around a line."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start = max(0, line_number - context_size - 1)
        end = min(len(lines), line_number + context_size)

        context_before = [lines[i].rstrip() for i in range(start, line_number - 1)]
        code = lines[line_number - 1].rstrip() if line_number <= len(lines) else "# Line not found"
        context_after = [lines[i].rstrip() for i in range(line_number, min(end, line_number + context_size))]

        return context_before, code, context_after
    except Exception as e:
        return [], f"# Error reading file: {e}", []


def analyze_coverage_json(coverage_data: Dict, base_path: Optional[Path] = None) -> List[FileReport]:
    """Analyze coverage.json and generate file reports."""
    reports = []
    files = coverage_data.get('files', {})

    for file_path_str, file_data in files.items():
        # Convert Windows paths
        file_path_str = file_path_str.replace('\\', '/')

        summary = file_data.get('summary', {})
        executed_lines = summary.get('executed_lines', 0)
        num_statements = summary.get('num_statements', 0)

        if num_statements == 0:
            continue

        coverage_percentage = (executed_lines / num_statements) * 100

        # Get uncovered lines
        lines = file_data.get('lines', [])
        uncovered = [i + 1 for i, line in enumerate(lines) if line == 0]

        report = FileReport(
            file_path=file_path_str,
            total_lines=num_statements,
            covered_lines=executed_lines,
            uncovered_lines=uncovered,
            coverage_percentage=coverage_percentage,
            uncovered_count=len(uncovered)
        )
        reports.append(report)

    # Sort by coverage percentage (ascending) then by uncovered count (descending)
    reports.sort(key=lambda r: (r.coverage_percentage, -r.uncovered_count))
    return reports


def prioritize_files(reports: List[FileReport]) -> List[FileReport]:
    """Prioritize files by importance for testing."""
    # Scoring logic: files with lower coverage and more uncovered lines are higher priority
    priority_scores = []

    for report in reports:
        # Files with <95% coverage are high priority
        coverage_score = (100 - report.coverage_percentage) * 2
        # More uncovered lines = higher priority
        uncovered_score = report.uncovered_count
        # Core module files (containing keywords) get boost
        module_boost = 0
        critical_keywords = ['core', 'security', 'validator', 'blockchain', 'transaction', 'consensus']
        for keyword in critical_keywords:
            if keyword in report.file_path:
                module_boost = 5
                break

        total_score = coverage_score + uncovered_score + module_boost
        priority_scores.append((total_score, report))

    # Sort by score descending
    priority_scores.sort(key=lambda x: -x[0])
    return [report for _, report in priority_scores]


def generate_text_report(reports: List[FileReport], min_uncovered: int = 0, show_code: bool = False) -> str:
    """Generate text report of uncovered lines."""
    output = []
    output.append("=" * 80)
    output.append("UNCOVERED LINES REPORT")
    output.append("=" * 80)

    # Summary
    total_files = len(reports)
    files_below_98 = sum(1 for r in reports if r.coverage_percentage < 98)
    total_uncovered = sum(r.uncovered_count for r in reports)

    output.append(f"\nSUMMARY")
    output.append("-" * 80)
    output.append(f"Total Files Analyzed: {total_files}")
    output.append(f"Files Below 98% Coverage: {files_below_98}")
    output.append(f"Total Uncovered Lines: {total_uncovered}")

    # Detailed reports
    output.append(f"\n{'=' * 80}")
    output.append("DETAILED UNCOVERED LINES")
    output.append("=" * 80)

    for report in reports:
        if report.uncovered_count < min_uncovered:
            continue

        output.append(f"\nFile: {report.file_path}")
        output.append(f"Coverage: {report.coverage_percentage:.2f}% ({report.covered_lines}/{report.total_lines})")
        output.append(f"Uncovered Lines: {report.uncovered_count}")
        output.append("-" * 80)

        if show_code:
            for line_num in report.uncovered_lines[:20]:  # Show first 20
                try:
                    file_path = Path(report.file_path)
                    if not file_path.is_absolute():
                        file_path = Path.cwd() / file_path

                    context_before, code, context_after = get_line_context(file_path, line_num)

                    output.append(f"  Line {line_num}: {code[:100]}")
                    if context_before:
                        for ctx in context_before[-1:]:
                            output.append(f"    > {ctx[:100]}")
                    if context_after:
                        for ctx in context_after[:1]:
                            output.append(f"    < {ctx[:100]}")
                except Exception as e:
                    output.append(f"  Line {line_num}: [Error reading: {e}]")

            if report.uncovered_count > 20:
                output.append(f"  ... and {report.uncovered_count - 20} more uncovered lines")
        else:
            # Just list line numbers
            lines_str = ", ".join(str(l) for l in report.uncovered_lines[:50])
            if report.uncovered_count > 50:
                lines_str += f", ... (+{report.uncovered_count - 50} more)"
            output.append(f"  Uncovered: {lines_str}")

    # TODO list
    output.append(f"\n{'=' * 80}")
    output.append("ACTION ITEMS (PRIORITIZED)")
    output.append("=" * 80)

    for i, report in enumerate(prioritize_files(reports), 1):
        if report.uncovered_count > 0:
            output.append(f"{i}. [{report.coverage_percentage:.1f}%] {report.file_path}")
            output.append(f"   Add {report.uncovered_count} tests to reach 100% coverage")

    return "\n".join(output)


def generate_json_report(reports: List[FileReport]) -> Dict:
    """Generate JSON report of uncovered lines."""
    return {
        'timestamp': str(Path.cwd()),
        'summary': {
            'total_files': len(reports),
            'files_below_98': sum(1 for r in reports if r.coverage_percentage < 98),
            'total_uncovered_lines': sum(r.uncovered_count for r in reports),
        },
        'files': [
            {
                'file_path': r.file_path,
                'coverage_percentage': round(r.coverage_percentage, 2),
                'covered_lines': r.covered_lines,
                'total_lines': r.total_lines,
                'uncovered_count': r.uncovered_count,
                'uncovered_lines': r.uncovered_lines[:100],  # First 100
            }
            for r in reports
        ]
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Find uncovered lines in coverage reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_uncovered_lines.py
  python find_uncovered_lines.py --coverage-file coverage.json --show-code
  python find_uncovered_lines.py --module core --min-uncovered 10
  python find_uncovered_lines.py --output report.txt --json
        """
    )

    parser.add_argument(
        "--coverage-file", "-c",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage.json file (default: coverage.json)"
    )
    parser.add_argument(
        "--module", "-m",
        help="Filter to specific module (substring match)"
    )
    parser.add_argument(
        "--min-uncovered",
        type=int,
        default=0,
        help="Only show files with at least this many uncovered lines"
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Show code context for uncovered lines"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Write report to file"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )

    args = parser.parse_args()

    # Read coverage data
    print(f"Reading coverage from: {args.coverage_file}")
    coverage_data = read_coverage_json(args.coverage_file)

    # Analyze
    print("Analyzing coverage data...")
    reports = analyze_coverage_json(coverage_data)

    # Filter by module if specified
    if args.module:
        reports = [r for r in reports if args.module.lower() in r.file_path.lower()]
        print(f"Filtered to {len(reports)} files matching '{args.module}'")

    # Generate report
    if args.json:
        report_content = json.dumps(generate_json_report(reports), indent=2)
    else:
        report_content = generate_text_report(reports, min_uncovered=args.min_uncovered, show_code=args.show_code)

    # Output
    if args.output:
        args.output.write_text(report_content)
        print(f"Report written to: {args.output}")
    else:
        print(report_content)


if __name__ == "__main__":
    main()
