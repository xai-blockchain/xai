#!/usr/bin/env python3
from __future__ import annotations

"""
Monitor test coverage over time and across branches.

Tracks coverage metrics, alerts on decreases, generates trend reports,
compares branches, and can block PRs if coverage drops below threshold.

Usage:
    python coverage_monitor.py --check
    python coverage_monitor.py --record
    python coverage_monitor.py --compare main
    python coverage_monitor.py --report

Examples:
    python coverage_monitor.py --check --threshold 98
    python coverage_monitor.py --record --branch feature/new-wallet
    python coverage_monitor.py --compare main --verbose
    python coverage_monitor.py --report --output coverage_trend.html
"""

import json
import sys
import subprocess
from pathlib import Path

from dataclasses import dataclass, asdict
from datetime import datetime
import argparse

@dataclass
class CoverageSnapshot:
    """Single coverage measurement."""
    timestamp: str
    branch: str
    commit: str
    total_coverage: float
    line_coverage: float
    branch_coverage: float
    statements: int
    executed: int
    missing: int

@dataclass
class CoverageTrend:
    """Coverage trend analysis."""
    branch: str
    snapshots: list[CoverageSnapshot]
    avg_coverage: float
    trend: str  # 'up', 'down', 'stable'
    change_percentage: float
    change_color: str  # 'green', 'red', 'yellow'

class CoverageMonitor:
    """Monitor and track test coverage."""

    def __init__(self, data_file: Path = Path(".coverage_history.json")):
        """Initialize coverage monitor."""
        self.data_file = data_file
        self.snapshots: list[CoverageSnapshot] = []
        self.load_history()

    def load_history(self) -> None:
        """Load coverage history from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.snapshots = [CoverageSnapshot(**s) for s in data]
            except Exception as e:
                print(f"Warning: Could not load history: {e}", file=sys.stderr)

    def save_history(self) -> None:
        """Save coverage history to file."""
        with open(self.data_file, 'w') as f:
            json.dump([asdict(s) for s in self.snapshots], f, indent=2)

    def get_current_coverage(self, coverage_file: Path = Path("coverage.json")) -> CoverageSnapshot | None:
        """Extract coverage metrics from coverage.json."""
        if not coverage_file.exists():
            print(f"Error: Coverage file not found: {coverage_file}", file=sys.stderr)
            return None

        try:
            with open(coverage_file, 'r') as f:
                data = json.load(f)

            summary = data.get('totals', {})
            branch = self.get_current_branch()
            commit = self.get_current_commit()

            return CoverageSnapshot(
                timestamp=datetime.now().isoformat(),
                branch=branch,
                commit=commit,
                total_coverage=summary.get('percent_covered', 0),
                line_coverage=summary.get('percent_covered', 0),
                branch_coverage=summary.get('percent_covered_with_branch', 0),
                statements=summary.get('num_statements', 0),
                executed=summary.get('executed_lines', 0),
                missing=summary.get('num_statements', 0) - summary.get('executed_lines', 0),
            )
        except Exception as e:
            print(f"Error reading coverage: {e}", file=sys.stderr)
            return None

    def get_current_branch(self) -> str:
        try:
            result = subprocess.run(
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def get_current_commit(self) -> str:
        try:
            result = subprocess.run(
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def record_snapshot(self, coverage_file: Path = Path("coverage.json")) -> bool:
        """Record current coverage snapshot."""
        snapshot = self.get_current_coverage(coverage_file)
        if not snapshot:
            return False

        self.snapshots.append(snapshot)
        self.save_history()
        print(f"Recorded coverage: {snapshot.total_coverage:.2f}% on {snapshot.branch}")
        return True

    def check_coverage(self, threshold: float = 98.0, fail_on_decrease: bool = True) -> int:
        """Check if coverage meets threshold and hasn't decreased."""
        current = self.get_current_coverage()
        if not current:
            print("Error: Could not get current coverage", file=sys.stderr)
            return 1

        # Check threshold
        if current.total_coverage < threshold:
            print(f"FAIL: Coverage {current.total_coverage:.2f}% is below threshold {threshold:.2f}%")
            return 1

        # Check for decrease
        branch_snapshots = [s for s in self.snapshots if s.branch == current.branch]
        if branch_snapshots and fail_on_decrease:
            previous = branch_snapshots[-1]
            if current.total_coverage < previous.total_coverage:
                diff = previous.total_coverage - current.total_coverage
                print(f"FAIL: Coverage decreased by {diff:.2f}% (from {previous.total_coverage:.2f}% to {current.total_coverage:.2f}%)")
                return 1

        print(f"PASS: Coverage {current.total_coverage:.2f}% meets threshold {threshold:.2f}%")
        return 0

    def compare_branches(self, base_branch: str = "main", verbose: bool = False) -> Dict:
        """Compare coverage between branches."""
        base_snapshots = [s for s in self.snapshots if s.branch == base_branch]
        current_branch = self.get_current_branch()
        current_snapshots = [s for s in self.snapshots if s.branch == current_branch]

        if not base_snapshots or not current_snapshots:
            print(f"Not enough data to compare branches", file=sys.stderr)
            return {}

        base_coverage = base_snapshots[-1].total_coverage
        current_coverage = current_snapshots[-1].total_coverage
        difference = current_coverage - base_coverage

        result = {
            'base_branch': base_branch,
            'base_coverage': round(base_coverage, 2),
            'current_branch': current_branch,
            'current_coverage': round(current_coverage, 2),
            'difference': round(difference, 2),
            'status': 'IMPROVED' if difference > 0 else 'DECREASED' if difference < 0 else 'SAME',
        }

        if verbose:
            print(f"\nCOVERAGE COMPARISON")
            print(f"Base branch ({base_branch}): {base_coverage:.2f}%")
            print(f"Current branch ({current_branch}): {current_coverage:.2f}%")
            print(f"Difference: {difference:+.2f}%")
            print(f"Status: {result['status']}")

        return result

    def generate_report(self) -> str:
        """Generate coverage trend report."""
        if not self.snapshots:
            return "No coverage history available"

        # Group by branch
        branch_history: dict[str, list[CoverageSnapshot]] = {}
        for snap in self.snapshots:
            if snap.branch not in branch_history:
                branch_history[snap.branch] = []
            branch_history[snap.branch].append(snap)

        report = []
        report.append("=" * 80)
        report.append("COVERAGE TREND REPORT")
        report.append("=" * 80)

        for branch, snaps in sorted(branch_history.items()):
            snaps.sort(key=lambda x: x.timestamp)

            coverage_values = [s.total_coverage for s in snaps]
            avg = sum(coverage_values) / len(coverage_values)
            min_val = min(coverage_values)
            max_val = max(coverage_values)

            trend = "STABLE"
            if len(snaps) > 1:
                if snaps[-1].total_coverage > snaps[0].total_coverage:
                    trend = "IMPROVING"
                elif snaps[-1].total_coverage < snaps[0].total_coverage:
                    trend = "DECLINING"

            report.append(f"\nBranch: {branch}")
            report.append(f"  Latest: {snaps[-1].total_coverage:.2f}%")
            report.append(f"  Average: {avg:.2f}%")
            report.append(f"  Range: {min_val:.2f}% - {max_val:.2f}%")
            report.append(f"  Trend: {trend}")
            report.append(f"  Snapshots: {len(snaps)}")

        return "\n".join(report)

    def generate_html_report(self, output_file: Path) -> None:
        """Generate HTML coverage trend report."""
        # Group by branch
        branch_history: dict[str, list[CoverageSnapshot]] = {}
        for snap in self.snapshots:
            if snap.branch not in branch_history:
                branch_history[snap.branch] = []
            branch_history[snap.branch].append(snap)

        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Coverage Trend Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .branch-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .metric { display: inline-block; margin-right: 30px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .metric-label { color: #666; font-size: 12px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f5f5f5; }
        .good { color: green; }
        .bad { color: red; }
        .warning { color: orange; }
    </style>
</head>
<body>
    <h1>Coverage Trend Report</h1>
    <p>Generated: """ + datetime.now().isoformat() + """</p>
"""

        for branch, snaps in sorted(branch_history.items()):
            snaps.sort(key=lambda x: x.timestamp)
            coverage_values = [s.total_coverage for s in snaps]
            avg = sum(coverage_values) / len(coverage_values)
            latest = snaps[-1].total_coverage

            html += f"""
    <div class="branch-section">
        <h2>{branch}</h2>
        <div class="metric">
            <div class="metric-value {'good' if latest >= 98 else 'warning' if latest >= 95 else 'bad'}">{latest:.2f}%</div>
            <div class="metric-label">Latest Coverage</div>
        </div>
        <div class="metric">
            <div class="metric-value">{avg:.2f}%</div>
            <div class="metric-label">Average Coverage</div>
        </div>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Commit</th>
                <th>Coverage</th>
                <th>Statements</th>
                <th>Executed</th>
                <th>Missing</th>
            </tr>
"""

            for snap in reversed(snaps[-10:]):  # Last 10
                html += f"""
            <tr>
                <td>{snap.timestamp}</td>
                <td>{snap.commit}</td>
                <td class="{'good' if snap.total_coverage >= 98 else 'warning' if snap.total_coverage >= 95 else 'bad'}">{snap.total_coverage:.2f}%</td>
                <td>{snap.statements}</td>
                <td>{snap.executed}</td>
                <td>{snap.missing}</td>
            </tr>
"""

            html += """
        </table>
    </div>
"""

        html += """
</body>
</html>
"""

        output_file.write_text(html)
        print(f"HTML report written to: {output_file}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor test coverage over time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coverage_monitor.py --check --threshold 98
  python coverage_monitor.py --record
  python coverage_monitor.py --compare main --verbose
  python coverage_monitor.py --report
  python coverage_monitor.py --html coverage_report.html
        """
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if coverage meets threshold"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=98.0,
        help="Coverage threshold percentage (default: 98.0)"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record current coverage snapshot"
    )
    parser.add_argument(
        "--compare",
        metavar="BRANCH",
        help="Compare with another branch"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate text trend report"
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Generate HTML trend report to file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage-file", "-c",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage.json"
    )

    args = parser.parse_args()

    monitor = CoverageMonitor()

    if args.check:
        return monitor.check_coverage(threshold=args.threshold)

    if args.record:
        if monitor.record_snapshot(args.coverage_file):
            return 0
        else:
            return 1

    if args.compare:
        result = monitor.compare_branches(args.compare, verbose=args.verbose)
        if result.get('difference', 0) < 0:
            return 1
        return 0

    if args.report:
        print(monitor.generate_report())
        return 0

    if args.html:
        monitor.generate_html_report(args.html)
        return 0

    # Default: show report
    print(monitor.generate_report())
    return 0

if __name__ == "__main__":
    sys.exit(main())
