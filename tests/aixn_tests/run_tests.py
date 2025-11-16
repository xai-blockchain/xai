#!/usr/bin/env python3
"""
XAI Blockchain Test Runner

Comprehensive test runner with multiple test suites and reporting options
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime


class TestRunner:
    """XAI Blockchain test runner"""

    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.test_dir)

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("Running ALL XAI Blockchain Tests")
        print("=" * 70 + "\n")

        return self._run_pytest([])

    def run_unit_tests(self):
        """Run only unit tests"""
        print("\n" + "=" * 70)
        print("Running UNIT Tests")
        print("=" * 70 + "\n")

        return self._run_pytest(["-m", "unit", "unit/"])

    def run_integration_tests(self):
        """Run only integration tests"""
        print("\n" + "=" * 70)
        print("Running INTEGRATION Tests")
        print("=" * 70 + "\n")

        return self._run_pytest(["-m", "integration", "integration/"])

    def run_security_tests(self):
        """Run only security tests"""
        print("\n" + "=" * 70)
        print("Running SECURITY Tests")
        print("=" * 70 + "\n")

        return self._run_pytest(["-m", "security", "security/"])

    def run_performance_tests(self):
        """Run only performance tests"""
        print("\n" + "=" * 70)
        print("Running PERFORMANCE Tests")
        print("=" * 70 + "\n")

        return self._run_pytest(["-m", "slow", "performance/"])

    def run_fast_tests(self):
        """Run fast tests only (exclude slow tests)"""
        print("\n" + "=" * 70)
        print("Running FAST Tests (excluding slow tests)")
        print("=" * 70 + "\n")

        return self._run_pytest(["-m", "not slow"])

    def run_with_coverage(self):
        """Run all tests with coverage report"""
        print("\n" + "=" * 70)
        print("Running Tests with COVERAGE")
        print("=" * 70 + "\n")

        return self._run_pytest(["--cov=../core", "--cov-report=html", "--cov-report=term"])

    def run_specific_test(self, test_path):
        """Run a specific test file or function"""
        print("\n" + "=" * 70)
        print(f"Running Specific Test: {test_path}")
        print("=" * 70 + "\n")

        return self._run_pytest([test_path])

    def _run_pytest(self, args):
        """Execute pytest with given arguments"""
        cmd = [sys.executable, "-m", "pytest"] + args

        # Add working directory
        cmd.append("--rootdir=" + self.test_dir)

        try:
            result = subprocess.run(cmd, cwd=self.test_dir, capture_output=False)
            return result.returncode
        except Exception as e:
            print(f"Error running tests: {e}")
            return 1

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 70)
        print("Generating Test Report")
        print("=" * 70 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.test_dir, f"test_report_{timestamp}.html")

        return self._run_pytest(["--html=" + report_file, "--self-contained-html"])

    def list_tests(self):
        """List all available tests"""
        print("\n" + "=" * 70)
        print("Available Tests")
        print("=" * 70 + "\n")

        return self._run_pytest(["--collect-only", "-q"])

    def run_by_keyword(self, keyword):
        """Run tests matching keyword"""
        print("\n" + "=" * 70)
        print(f"Running Tests Matching: {keyword}")
        print("=" * 70 + "\n")

        return self._run_pytest(["-k", keyword])


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="XAI Blockchain Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all              Run all tests
  %(prog)s --unit             Run unit tests only
  %(prog)s --integration      Run integration tests only
  %(prog)s --security         Run security tests only
  %(prog)s --performance      Run performance tests only
  %(prog)s --fast             Run fast tests only (exclude slow)
  %(prog)s --coverage         Run tests with coverage report
  %(prog)s --list             List all available tests
  %(prog)s --keyword balance  Run tests matching 'balance'
  %(prog)s --test unit/test_wallet.py  Run specific test file
        """,
    )

    parser.add_argument("--all", action="store_true", help="Run all tests")

    parser.add_argument("--unit", action="store_true", help="Run unit tests only")

    parser.add_argument("--integration", action="store_true", help="Run integration tests only")

    parser.add_argument("--security", action="store_true", help="Run security tests only")

    parser.add_argument("--performance", action="store_true", help="Run performance tests only")

    parser.add_argument(
        "--fast", action="store_true", help="Run fast tests only (exclude slow tests)"
    )

    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")

    parser.add_argument("--report", action="store_true", help="Generate HTML test report")

    parser.add_argument("--list", action="store_true", help="List all available tests")

    parser.add_argument("--keyword", "-k", type=str, help="Run tests matching keyword")

    parser.add_argument("--test", "-t", type=str, help="Run specific test file or function")

    args = parser.parse_args()

    runner = TestRunner()
    exit_code = 0

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    # Run tests based on arguments
    if args.all:
        exit_code = runner.run_all_tests()
    elif args.unit:
        exit_code = runner.run_unit_tests()
    elif args.integration:
        exit_code = runner.run_integration_tests()
    elif args.security:
        exit_code = runner.run_security_tests()
    elif args.performance:
        exit_code = runner.run_performance_tests()
    elif args.fast:
        exit_code = runner.run_fast_tests()
    elif args.coverage:
        exit_code = runner.run_with_coverage()
    elif args.report:
        exit_code = runner.generate_report()
    elif args.list:
        exit_code = runner.list_tests()
    elif args.keyword:
        exit_code = runner.run_by_keyword(args.keyword)
    elif args.test:
        exit_code = runner.run_specific_test(args.test)
    else:
        parser.print_help()

    # Print summary
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("Tests PASSED")
    else:
        print("Tests FAILED")
    print("=" * 70 + "\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
