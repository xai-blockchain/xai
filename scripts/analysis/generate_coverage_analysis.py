#!/usr/bin/env python3
import json
from collections import defaultdict

def generate_coverage_gaps_analysis():
    with open("coverage.json", "r") as f:
        cov_data = json.load(f)

    # Get overall coverage
    totals = cov_data.get("totals", {})
    overall_coverage = totals.get("percent_covered", 0)

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

        # Get uncovered lines
        executed_lines = set(filedata.get("executed_lines", []))
        missing_lines = filedata.get("missing_lines", [])

        module_coverage.append({
            'name': module_name,
            'percent': percent,
            'statements': statements,
            'covered': covered,
            'missing': missing,
            'missing_lines': missing_lines,
            'full_path': filepath
        })

    # Sort by coverage percentage
    module_coverage.sort(key=lambda x: (x['percent'], x['name']))

    # Create markdown report
    report = []
    report.append("# Test Coverage Analysis and Gap Report\n")
    report.append(f"**Last Updated:** {import_time()}\n\n")

    # Overall Summary
    report.append("## 1. Overall Coverage Status\n")
    report.append(f"- **Current Overall Coverage:** {overall_coverage:.2f}%\n")
    report.append(f"- **Target Coverage:** 80.0%\n")
    report.append(f"- **Coverage Gap:** {80 - overall_coverage:.2f}%\n")
    report.append(f"- **Total Statements:** {totals.get('num_statements', 0):,}\n")
    report.append(f"- **Covered Statements:** {totals.get('covered_lines', 0):,}\n")
    report.append(f"- **Missing Statements:** {totals.get('missing_lines', 0):,}\n\n")

    # Coverage Distribution
    report.append("## 2. Coverage Distribution\n\n")
    critical = [m for m in module_coverage if m['percent'] < 50]
    medium = [m for m in module_coverage if 50 <= m['percent'] < 80]
    high = [m for m in module_coverage if m['percent'] >= 80]

    report.append(f"| Coverage Range | Count | % of Total |\n")
    report.append(f"|---|---|---|\n")
    report.append(f"| 0-50% (Critical) | {len(critical)} | {len(critical)/len(module_coverage)*100:.1f}% |\n")
    report.append(f"| 50-80% (Medium) | {len(medium)} | {len(medium)/len(module_coverage)*100:.1f}% |\n")
    report.append(f"| 80-100% (Good) | {len(high)} | {len(high)/len(module_coverage)*100:.1f}% |\n\n")

    # Critical Priority Modules (< 50%)
    report.append("## 3. Critical Priority Modules (< 50% Coverage)\n\n")
    report.append("These modules have the lowest coverage and should be prioritized:\n\n")

    critical_sorted = sorted(critical, key=lambda x: x['statements'], reverse=True)[:20]

    for mod in critical_sorted:
        report.append(f"### {mod['name']}\n")
        report.append(f"- **Coverage:** {mod['percent']:.2f}%\n")
        report.append(f"- **Statements:** {mod['statements']} total | {mod['covered']} covered | {mod['missing']} missing\n")
        report.append(f"- **Priority:** HIGH (Core module with {mod['statements']} statements)\n")
        if mod['missing_lines']:
            ranges = _get_line_ranges(mod['missing_lines'][:20])
            report.append(f"- **Uncovered Lines (sample):** {ranges}\n")
        report.append("\n")

    # Medium Priority Modules (50-80%)
    report.append("## 4. Medium Priority Modules (50-80% Coverage)\n\n")
    report.append("These modules need targeted testing to reach 80%:\n\n")

    for mod in medium:
        gap_to_80 = 80 - mod['percent']
        estimated_tests = max(2, int((mod['statements'] * gap_to_80) / 100))

        report.append(f"### {mod['name']}\n")
        report.append(f"- **Coverage:** {mod['percent']:.2f}%\n")
        report.append(f"- **Gap to 80%:** {gap_to_80:.2f}%\n")
        report.append(f"- **Statements:** {mod['statements']} total | {mod['covered']} covered | {mod['missing']} missing\n")
        report.append(f"- **Estimated Tests Needed:** {estimated_tests}\n")
        if mod['missing_lines']:
            ranges = _get_line_ranges(mod['missing_lines'][:10])
            report.append(f"- **Uncovered Lines (sample):** {ranges}\n")
        report.append("\n")

    # Specific High-Impact Modules
    report.append("## 5. High-Impact Modules from Task\n\n")
    report.append("These are critical modules mentioned in the task:\n\n")

    mentioned = ['node_api.py', 'node.py', 'blockchain_security.py', 'wallet.py']
    for mention in mentioned:
        found = [m for m in module_coverage if mention in m['name']]
        if found:
            mod = found[0]
            gap = 80 - mod['percent']
            priority = "CRITICAL" if mod['percent'] < 50 else "HIGH" if mod['percent'] < 70 else "MEDIUM"

            report.append(f"### {mod['name']}\n")
            report.append(f"- **Coverage:** {mod['percent']:.2f}% ({priority} Priority)\n")
            report.append(f"- **Gap to 80%:** {gap:.2f}%\n")
            report.append(f"- **Statements:** {mod['statements']} | Covered: {mod['covered']} | Missing: {mod['missing']}\n")

            if gap > 0:
                estimated_tests = max(3, int((mod['statements'] * gap) / 100))
                report.append(f"- **Estimated Tests to Reach 80%:** {estimated_tests}\n")
                if mod['missing_lines']:
                    ranges = _get_line_ranges(mod['missing_lines'][:15])
                    report.append(f"- **Uncovered Lines (sample):** {ranges}\n")
            report.append("\n")

    # Prioritized Action Plan
    report.append("## 6. Prioritized Action Plan to Reach 80%\n\n")

    # Calculate impact
    impact_modules = []

    # High impact = many statements + low coverage
    for mod in module_coverage:
        if mod['percent'] >= 80:
            continue
        impact_score = mod['statements'] * (80 - mod['percent']) / 100
        impact_modules.append((mod, impact_score))

    impact_modules.sort(key=lambda x: x[1], reverse=True)

    report.append("### Phase 1: High-Impact Modules (Greatest Coverage Gain)\n\n")
    for idx, (mod, impact) in enumerate(impact_modules[:10], 1):
        gap = 80 - mod['percent']
        est_tests = max(2, int((mod['statements'] * gap) / 100))
        report.append(f"{idx}. **{mod['name']}** - Impact: +{impact:.1f} statements\n")
        report.append(f"   - Current: {mod['percent']:.1f}% | Gap: {gap:.1f}% | Est. Tests: {est_tests}\n")

    report.append("\n### Phase 2: Medium-Impact Modules\n\n")
    for idx, (mod, impact) in enumerate(impact_modules[10:20], 11):
        gap = 80 - mod['percent']
        est_tests = max(2, int((mod['statements'] * gap) / 100))
        report.append(f"{idx}. **{mod['name']}** - Impact: +{impact:.1f} statements\n")
        report.append(f"   - Current: {mod['percent']:.1f}% | Gap: {gap:.1f}% | Est. Tests: {est_tests}\n")

    # Summary Statistics
    report.append("\n## 7. Summary Statistics\n\n")

    total_gap_statements = sum((80 - m['percent']) * m['statements'] / 100
                               for m in module_coverage if m['percent'] < 80)
    total_tests_needed = max(50, int(total_gap_statements / 20))  # Rough estimate

    report.append(f"- **Total modules below 80%:** {len(module_coverage) - len(high)}\n")
    report.append(f"- **Estimated statements to cover:** {int(total_gap_statements):,}\n")
    report.append(f"- **Estimated new tests needed:** {total_tests_needed}\n")
    report.append(f"- **Potential coverage improvement:** From {overall_coverage:.1f}% to 80%+\n\n")

    # Recommendations
    report.append("## 8. Testing Recommendations\n\n")
    report.append("1. **Focus on Critical Modules First**: Start with modules at 0-50% coverage\n")
    report.append("2. **Target High-Impact Modules**: Prioritize modules with many statements\n")
    report.append("3. **Use Coverage-Driven Development**: Write tests that explicitly target missing lines\n")
    report.append("4. **Leverage pytest-cov**: Use `--cov-report=html` for visual coverage inspection\n")
    report.append("5. **Implement Incrementally**: Add tests in phases to track progress\n")
    report.append("6. **Focus on Module Categories**: Group related modules and test together\n\n")

    # Write report
    with open("COVERAGE_GAPS_ANALYSIS.md", "w") as f:
        f.write("\n".join(report))

    print("Report generated: COVERAGE_GAPS_ANALYSIS.md")
    print(f"\nOverall Coverage: {overall_coverage:.2f}%")
    print(f"Modules below 80%: {len(module_coverage) - len(high)}")
    print(f"Modules below 50%: {len(critical)}")

def _get_line_ranges(lines):
    """Convert list of line numbers to range strings"""
    if not lines:
        return "None"

    ranges = []
    start = lines[0]
    end = lines[0]

    for line in lines[1:]:
        if line == end + 1:
            end = line
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = line
            end = line

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges[:5]) + ("..." if len(ranges) > 5 else "")

def import_time():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    generate_coverage_gaps_analysis()
