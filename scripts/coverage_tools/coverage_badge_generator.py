#!/usr/bin/env python3
from __future__ import annotations

"""
Generate SVG coverage badges and update README files.

Creates coverage badges with color coding, updates README files
automatically, and tracks coverage metrics for CI/CD pipelines.

Usage:
    python coverage_badge_generator.py [--output badge.svg]
    python coverage_badge_generator.py --update-readme
    python coverage_badge_generator.py --all

Examples:
    python coverage_badge_generator.py
    python coverage_badge_generator.py --coverage-file coverage.json --output badge.svg
    python coverage_badge_generator.py --update-readme --threshold 98
"""

import json
import sys
from pathlib import Path

import argparse
import re

class CoverageBadgeGenerator:
    """Generate coverage badges and update documentation."""

    # Color scheme: (percentage_threshold, color_hex, label)
    COLOR_SCHEME = [
        (98, '#28a745', 'excellent'),      # Green for 98%+
        (95, '#85c1e2', 'good'),           # Light blue for 95-98%
        (90, '#ffc107', 'fair'),           # Yellow for 90-95%
        (80, '#fd7e14', 'poor'),           # Orange for 80-90%
        (0, '#dc3545', 'critical'),        # Red for <80%
    ]

    def __init__(self, coverage_file: Path = Path("coverage.json")):
        """Initialize badge generator."""
        self.coverage_file = coverage_file
        self.coverage_percentage = 0.0
        self.load_coverage()

    def load_coverage(self) -> None:
        """Load coverage percentage from coverage.json."""
        if not self.coverage_file.exists():
            print(f"Warning: Coverage file not found: {self.coverage_file}", file=sys.stderr)
            return

        try:
            with open(self.coverage_file, 'r') as f:
                data = json.load(f)
                totals = data.get('totals', {})
                self.coverage_percentage = totals.get('percent_covered', 0.0)
        except Exception as e:
            print(f"Error reading coverage: {e}", file=sys.stderr)

    def get_color_for_percentage(self, percentage: float) -> tuple[str, str]:
        """Get color and label for coverage percentage."""
        for threshold, color, label in self.COLOR_SCHEME:
            if percentage >= threshold:
                return color, label
        return self.COLOR_SCHEME[-1][1], self.COLOR_SCHEME[-1][2]

    def generate_svg_badge(self, percentage: float | None = None) -> str:
        """Generate SVG badge for coverage."""
        if percentage is None:
            percentage = self.coverage_percentage

        color, status = self.get_color_for_percentage(percentage)

        # Format percentage
        coverage_text = f"{percentage:.1f}%"

        # SVG template
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="140" height="20">
  <defs>
    <style>
      .badge-text {{ font-family: Arial, sans-serif; font-size: 11px; font-weight: bold; }}
      .badge-label {{ fill: white; }}
      .badge-value {{ fill: white; }}
    </style>
  </defs>
  <rect width="70" height="20" fill="#555"/>
  <rect x="70" width="70" height="20" fill="{color}"/>
  <text class="badge-text badge-label" x="35" y="15" text-anchor="middle">Coverage</text>
  <text class="badge-text badge-value" x="105" y="15" text-anchor="middle">{coverage_text}</text>
</svg>'''

        return svg

    def generate_html_badge(self, percentage: float | None = None) -> str:
        """Generate HTML badge for coverage."""
        if percentage is None:
            percentage = self.coverage_percentage

        color, status = self.get_color_for_percentage(percentage)

        html = f'''<div style="display: inline-block; padding: 5px; margin: 5px; border-radius: 5px; background-color: {color}; color: white; font-weight: bold;">
  Coverage: {percentage:.1f}% ({status})
</div>'''

        return html

    def generate_markdown_badge(self, percentage: float | None = None) -> str:
        """Generate Markdown badge for coverage."""
        if percentage is None:
            percentage = self.coverage_percentage

        # For shields.io
        badge = f"[![Coverage](https://img.shields.io/badge/coverage-{percentage:.1f}%25-brightgreen)]"
        return badge

    def write_svg_badge(self, output_file: Path) -> None:
        """Write SVG badge to file."""
        svg_content = self.generate_svg_badge()
        output_file.write_text(svg_content)
        print(f"SVG badge written to: {output_file}")

    def update_readme(self, readme_file: Path, percentage: float | None = None) -> bool:
        """Update README with coverage badge."""
        if percentage is None:
            percentage = self.coverage_percentage

        if not readme_file.exists():
            print(f"Warning: README not found: {readme_file}", file=sys.stderr)
            return False

        try:
            with open(readme_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if coverage badge exists
            coverage_badge_pattern = r'!\[Coverage\]\([^)]*\)'
            badge_text = f"![Coverage](https://img.shields.io/badge/coverage-{percentage:.1f}%25-brightgreen)"

            if re.search(coverage_badge_pattern, content):
                # Replace existing badge
                content = re.sub(coverage_badge_pattern, badge_text, content)
                print("Updated existing coverage badge in README")
            else:
                # Insert new badge after title
                title_pattern = r'(^#\s+[^\n]+\n)'
                if re.search(title_pattern, content, re.MULTILINE):
                    content = re.sub(
                        title_pattern,
                        r'\1\n' + badge_text + '\n',
                        content,
                        count=1,
                        flags=re.MULTILINE
                    )
                    print("Added coverage badge to README")
                else:
                    # Add at the beginning
                    content = badge_text + '\n\n' + content
                    print("Added coverage badge at the beginning of README")

            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error updating README: {e}", file=sys.stderr)
            return False

    def update_workflow_file(self, workflow_file: Path, threshold: float = 98.0) -> bool:
        if not workflow_file.exists():
            print(f"Warning: Workflow file not found: {workflow_file}", file=sys.stderr)
            return False

        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update coverage threshold in pytest command
            old_pattern = r'--cov-fail-under=\d+(?:\.\d+)?'
            new_pattern = f'--cov-fail-under={threshold}'

            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_pattern, content)
                print(f"Updated coverage threshold to {threshold}% in workflow")
            else:
                print("Could not find coverage threshold in workflow file")

            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error updating workflow: {e}", file=sys.stderr)
            return False

    return """
  - name: Generate Coverage Badge
    if: always()
    run: |
      python scripts/coverage_tools/coverage_badge_generator.py \\
        --coverage-file coverage.xml \\
        --output badges/coverage.svg \\
        --update-readme

  - name: Upload Coverage Badge
    if: always()
    uses: actions/upload-artifact@v3
    with:
      name: coverage-badge
      path: badges/coverage.svg
"""

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate coverage badges and update documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coverage_badge_generator.py
  python coverage_badge_generator.py --output badge.svg
  python coverage_badge_generator.py --update-readme --coverage-file coverage.json
  python coverage_badge_generator.py --all --threshold 98
        """
    )

    parser.add_argument(
        "--coverage-file", "-c",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage.json file"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output SVG badge file path"
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("README.md"),
        help="Path to README.md file"
    )
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="Update README.md with coverage badge"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=98.0,
        help="Coverage threshold percentage for CI/CD"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate badge, update README, and show all outputs"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML badge"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generate Markdown badge"
    )

    args = parser.parse_args()

    generator = CoverageBadgeGenerator(args.coverage_file)

    if args.all:
        # Generate SVG badge
        badge_path = Path("badges/coverage.svg")
        badge_path.parent.mkdir(parents=True, exist_ok=True)
        generator.write_svg_badge(badge_path)

        # Update README
        generator.update_readme(args.readme)

        # Show all formats
        print("\n" + "=" * 80)
        print("COVERAGE BADGE FORMATS")
        print("=" * 80)
        print("\nMarkdown:")
        print(generator.generate_markdown_badge())
        print("\nHTML:")
        print(generator.generate_html_badge())
        print("\nSVG (written to file)")

        return 0

    if args.output:
        generator.write_svg_badge(args.output)

    if args.update_readme:
        generator.update_readme(args.readme)

    if args.html:
        print(generator.generate_html_badge())

    if args.markdown:
        print(generator.generate_markdown_badge())

    if not any([args.output, args.update_readme, args.html, args.markdown]):
        # Default: print SVG
        print(generator.generate_svg_badge())

    return 0

if __name__ == "__main__":
    sys.exit(main())
