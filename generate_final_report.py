#!/usr/bin/env python3
"""
Generate Final Test and Coverage Report
"""
import subprocess
import json
import sys
from pathlib import Path

def run_tests():
    """Run full test suite"""
    print("=" * 80)
    print("RUNNING FULL TEST SUITE")
    print("=" * 80)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/xai_tests/",
         "-v", "--tb=short", "--maxfail=20"],
        capture_output=True,
        text=True,
        timeout=600
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0

def run_coverage():
    """Run coverage analysis"""
    print("\n" + "=" * 80)
    print("RUNNING COVERAGE ANALYSIS")
    print("=" * 80)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/",
         "--cov=src/xai",
         "--cov-report=term",
         "--cov-report=json:final_coverage.json",
         "--cov-report=html:final_htmlcov",
         "-q"],
        capture_output=True,
        text=True,
        timeout=900
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0

def analyze_coverage():
    """Analyze coverage.json file"""
    try:
        with open("final_coverage.json", "r") as f:
            data = json.load(f)

        total = data.get("totals", {})

        print("\n" + "=" * 80)
        print("COVERAGE SUMMARY")
        print("=" * 80)
        print(f"Total Statements: {total.get('num_statements', 0)}")
        print(f"Covered Statements: {total.get('covered_lines', 0)}")
        print(f"Missing Statements: {total.get('missing_lines', 0)}")
        print(f"Coverage Percentage: {total.get('percent_covered', 0):.2f}%")
        print(f"Branch Coverage: {total.get('percent_branches_covered', 0):.2f}%")

        return total.get('percent_covered', 0)
    except FileNotFoundError:
        # Try the old coverage.json
        try:
            with open("coverage.json", "r") as f:
                data = json.load(f)

            total = data.get("totals", {})
            coverage_pct = total.get('percent_covered', 0)

            print("\n" + "=" * 80)
            print("COVERAGE SUMMARY (from previous run)")
            print("=" * 80)
            print(f"Coverage Percentage: {coverage_pct:.2f}%")

            return coverage_pct
        except:
            print("No coverage data found")
            return 0

def main():
    """Main execution"""
    print("XAI BLOCKCHAIN - FINAL TEST AND COVERAGE REPORT")
    print("=" * 80)

    # Run tests
    tests_passed = run_tests()

    # Run coverage
    coverage_success = run_coverage()

    # Analyze coverage
    coverage_pct = analyze_coverage()

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Tests Passed: {'YES' if tests_passed else 'NO'}")
    print(f"Coverage Generated: {'YES' if coverage_success else 'NO'}")
    print(f"Coverage Achieved: {coverage_pct:.2f}%")
    print(f"Target Met (98%+): {'YES ✓' if coverage_pct >= 98 else 'NO - ' + str(round(98 - coverage_pct, 2)) + '% remaining'}")
    print("=" * 80)

    # Save summary to file
    with open("FINAL_TEST_COVERAGE_REPORT.txt", "w") as f:
        f.write("XAI BLOCKCHAIN - FINAL TEST AND COVERAGE REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Tests Passed: {'YES' if tests_passed else 'NO'}\n")
        f.write(f"Coverage Generated: {'YES' if coverage_success else 'NO'}\n")
        f.write(f"Coverage Achieved: {coverage_pct:.2f}%\n")
        f.write(f"Target Met (98%+): {'YES ✓' if coverage_pct >= 98 else 'NO - ' + str(round(98 - coverage_pct, 2)) + '% remaining'}\n")

    print("\nReport saved to: FINAL_TEST_COVERAGE_REPORT.txt")

if __name__ == "__main__":
    main()
