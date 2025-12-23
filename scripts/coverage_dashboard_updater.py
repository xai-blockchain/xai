#!/usr/bin/env python3
from __future__ import annotations

"""
Coverage Dashboard Updater for XAI Blockchain
Generates real-time coverage progress tracking dashboard
"""

import json
import os
from datetime import datetime
from pathlib import Path

import sys

class CoverageDashboard:
    """Generates coverage progress dashboard from coverage.json data"""

    TARGET_COVERAGE = 98.0
    PRIORITY_THRESHOLDS = {
        'critical': 30,      # Below 30% coverage
        'high': 50,          # 30-50% coverage
        'medium': 75,        # 50-75% coverage
        'low': TARGET_COVERAGE  # 75-98% coverage
    }

    def __init__(self, coverage_file: str = 'coverage.json'):
        self.coverage_file = coverage_file
        self.data = {}
        self.modules = {}
        self.load_coverage_data()

    def load_coverage_data(self):
        """Load coverage data from JSON file"""
        if not os.path.exists(self.coverage_file):
            raise FileNotFoundError(f"Coverage file not found: {self.coverage_file}")

        with open(self.coverage_file, 'r') as f:
            self.data = json.load(f)

        # Parse module-level coverage
        files = self.data.get('files', {})
        for file_path, file_data in files.items():
            if 'xai' in file_path and file_data.get('summary'):
                summary = file_data['summary']
                coverage = summary.get('percent_covered', 0)
                lines = summary.get('num_statements', 0)
                covered = summary.get('covered_lines', 0)

                # Extract module path
                parts = file_path.replace('\\', '/').split('/')
                if 'xai' in parts:
                    idx = parts.index('xai')
                    module_path = '/'.join(parts[idx:])
                    self.modules[module_path] = {
                        'coverage': coverage,
                        'lines': lines,
                        'covered': covered,
                        'missing': lines - covered,
                        'branches': summary.get('num_branches', 0),
                        'covered_branches': summary.get('covered_branches', 0),
                    }

    def get_overall_stats(self) -> Dict:
        """Get overall coverage statistics"""
        totals = self.data.get('totals', {})
        coverage = totals.get('percent_covered', 0)
        target = self.TARGET_COVERAGE

        return {
            'current': coverage,
            'target': target,
            'remaining': target - coverage,
            'total_lines': totals.get('num_statements', 0),
            'covered_lines': totals.get('covered_lines', 0),
            'uncovered_lines': totals.get('missing_lines', 0),
        }

    def get_priority_modules(self) -> list[tuple[str, Dict, str]]:
        """Get modules sorted by priority (critical -> low)"""
        prioritized = []

        for module, stats in self.modules.items():
            coverage = stats['coverage']

            # Determine priority
            if coverage < self.PRIORITY_THRESHOLDS['critical']:
                priority = 'CRITICAL'
                score = 0
            elif coverage < self.PRIORITY_THRESHOLDS['high']:
                priority = 'HIGH'
                score = 1
            elif coverage < self.PRIORITY_THRESHOLDS['medium']:
                priority = 'MEDIUM'
                score = 2
            else:
                priority = 'LOW'
                score = 3

            prioritized.append((score, module, stats, priority))

        # Sort by priority score (ascending) then by coverage (ascending)
        prioritized.sort(key=lambda x: (x[0], x[2]['coverage']))

        return [(m, s, p) for _, m, s, p in prioritized]

    def estimate_tests_needed(self, module: str, stats: Dict) -> int:
        """Estimate number of tests needed to reach target"""
        current_coverage = stats['coverage']
        missing_lines = stats['missing']

        # Estimate: ~0.5 tests per line of code (baseline)
        # Adjust based on current coverage (harder to improve at high coverage)
        if current_coverage < 50:
            tests_per_line = 0.3
        elif current_coverage < 75:
            tests_per_line = 0.5
        else:
            tests_per_line = 1.0

        return max(1, int(missing_lines * tests_per_line))

    def estimate_completion_date(self) -> tuple[float, str]:
        """Estimate days to reach 98% coverage"""
        overall = self.get_overall_stats()
        current = overall['current']
        target = overall['target']
        remaining = overall['remaining']

        # Historical velocity: estimate ~0.5% per day
        velocity_per_day = 0.5
        days_to_completion = remaining / velocity_per_day if velocity_per_day > 0 else float('inf')

        return days_to_completion, f"{int(days_to_completion)} days"

    def generate_progress_bar(self, current: float, target: float = 100) -> str:
        """Generate ASCII progress bar"""
        percentage = (current / target * 100) if target > 0 else 0
        filled = int(percentage / 5)  # 20 chars = 100%
        empty = 20 - filled
        bar = '█' * filled + '░' * empty
        return f"[{bar}] {percentage:.1f}%"

    def generate_status_indicator(self, coverage: float) -> str:
        """Generate status indicator emoji/symbol"""
        if coverage >= self.TARGET_COVERAGE:
            return '✅'
        elif coverage >= 75:
            return '⚠️'
        elif coverage >= 50:
            return '🔶'
        else:
            return '❌'

    def generate_markdown(self) -> str:
        """Generate markdown dashboard"""
        overall = self.get_overall_stats()
        prioritized = self.get_priority_modules()
        days_to_completion, completion_str = self.estimate_completion_date()

        lines = []

        # Header
        lines.append("# XAI Blockchain - Coverage Progress Dashboard\n")
        lines.append(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        lines.append("---\n")

        # Overall Progress
        lines.append("## Overall Progress\n")
        lines.append(f"**Target Coverage:** {overall['target']}%+")
        lines.append(f"**Current Coverage:** `{overall['current']:.2f}%`")
        lines.append(f"**Remaining to Target:** `{overall['remaining']:.2f}%`\n")
        lines.append(f"**Progress:** {self.generate_progress_bar(overall['current'], overall['target'])}\n")

        lines.append("### Coverage Statistics")
        lines.append(f"- Total Lines of Code: **{overall['total_lines']:,}**")
        lines.append(f"- Covered Lines: **{overall['covered_lines']:,}**")
        lines.append(f"- Uncovered Lines: **{overall['uncovered_lines']:,}**")
        lines.append("")

        # Estimated Completion
        lines.append("### Estimated Completion")
        lines.append(f"- **Estimated Days:** ~{completion_str}")
        lines.append(f"- **Completion Date:** {datetime.now().date()}")
        lines.append(f"- **Assumed Velocity:** ~0.5% coverage per day")
        lines.append("")

        # Priority Summary
        critical_count = sum(1 for _, _, p in prioritized if p == 'CRITICAL')
        high_count = sum(1 for _, _, p in prioritized if p == 'HIGH')
        medium_count = sum(1 for _, _, p in prioritized if p == 'MEDIUM')
        low_count = sum(1 for _, _, p in prioritized if p == 'LOW')

        lines.append("### Priority Summary")
        lines.append(f"- **CRITICAL** (< 30%): {critical_count} modules")
        lines.append(f"- **HIGH** (30-50%): {high_count} modules")
        lines.append(f"- **MEDIUM** (50-75%): {medium_count} modules")
        lines.append(f"- **LOW** (75-98%): {low_count} modules")
        lines.append("")

        # Module-by-Module Status
        lines.append("---\n")
        lines.append("## Module-by-Module Status\n")

        # Break modules into priority groups
        for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            modules_in_priority = [(m, s, p) for m, s, p in prioritized if p == priority]

            if not modules_in_priority:
                continue

            lines.append(f"### {priority} Priority ({len(modules_in_priority)} modules)\n")

            # Create table header
            lines.append("| Module | Coverage | Status | Lines | Tests Needed | Action |")
            lines.append("|--------|----------|--------|-------|--------------|--------|")

            for module, stats, _ in modules_in_priority[:10]:  # Show top 10 per priority
                coverage = stats['coverage']
                status = self.generate_status_indicator(coverage)
                lines_needed = stats['missing']
                tests_needed = self.estimate_tests_needed(module, stats)

                # Shorten module name for table
                short_name = module.split('/')[-1]
                category = '/'.join(module.split('/')[-2:])

                action = "Write tests" if coverage < self.TARGET_COVERAGE else "Maintain"

                lines.append(f"| {category} | {coverage:.2f}% | {status} | {lines_needed} | {tests_needed} | {action} |")

            if len(modules_in_priority) > 10:
                lines.append(f"| ... and {len(modules_in_priority) - 10} more modules | | | | | |")

            lines.append("")

        # Recent Improvements Section
        lines.append("---\n")
        lines.append("## Recent Improvements\n")
        lines.append("### Today's Progress")
        lines.append("- Baseline established: 8.68% → Target: 98%")
        lines.append("- Core blockchain modules identified for priority coverage")
        lines.append("- Test estimation model created")
        lines.append("")

        lines.append("### Coverage Trend")
        lines.append(f"```")
        lines.append(f"Current: {overall['current']:.2f}%")
        lines.append(f"Target:  {overall['target']:.2f}%")
        lines.append(f"```")
        lines.append("")

        # Next Actions
        lines.append("---\n")
        lines.append("## Next Actions (Prioritized)\n")

        next_actions = []
        for module, stats, priority in prioritized[:5]:
            tests = self.estimate_tests_needed(module, stats)
            next_actions.append((priority, module, tests, stats['coverage']))

        for i, (priority, module, tests, coverage) in enumerate(next_actions, 1):
            lines.append(f"### {i}. {module.split('/')[-1]}")
            lines.append(f"- **Priority:** {priority}")
            lines.append(f"- **Current Coverage:** {coverage:.2f}%")
            lines.append(f"- **Estimated Tests Needed:** {tests}")
            lines.append(f"- **Effort:** {'Low' if tests < 10 else 'Medium' if tests < 25 else 'High'}")
            lines.append("")

        # Footer
        lines.append("---\n")
        lines.append("## Legend\n")
        lines.append("- **✅** Meets or exceeds 98% target")
        lines.append("- **⚠️** 75-98% coverage range (good)")
        lines.append("- **🔶** 50-75% coverage range (needs work)")
        lines.append("- **❌** Below 50% coverage (critical)")
        lines.append("")
        lines.append("*This dashboard is automatically generated. Update frequency: on-demand*")

        return '\n'.join(lines)

    def save_dashboard(self, output_file: str = 'COVERAGE_PROGRESS_DASHBOARD.md'):
        """Save generated dashboard to file"""
        markdown = self.generate_markdown()

        with open(output_file, 'w') as f:
            f.write(markdown)

        print(f"Dashboard saved to: {output_file}")
        return output_file

def main():
    """Main entry point"""
    try:
        # Check if coverage.json exists
        coverage_file = 'coverage.json'
        if not os.path.exists(coverage_file):
            print(f"Error: {coverage_file} not found")
            sys.exit(1)

        # Generate dashboard
        dashboard = CoverageDashboard(coverage_file)

        # Print summary to console
        overall = dashboard.get_overall_stats()
        print("\nXAI Blockchain Coverage Progress Dashboard")
        print("=" * 50)
        print(f"Current Coverage: {overall['current']:.2f}%")
        print(f"Target Coverage:  {overall['target']:.2f}%")
        print(f"Remaining:        {overall['remaining']:.2f}%")
        print(f"Total Lines:      {overall['total_lines']:,}")
        print("=" * 50)

        # Save dashboard
        output_file = dashboard.save_dashboard('COVERAGE_PROGRESS_DASHBOARD.md')
        print(f"\nDashboard generated successfully!")
        print(f"View the dashboard at: {os.path.abspath(output_file)}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
