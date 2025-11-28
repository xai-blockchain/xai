import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.coverage_tools.find_uncovered_lines import (
    FileReport,
    analyze_coverage_json,
    generate_json_report,
    generate_text_report,
    get_line_context,
    prioritize_files,
)


def test_analyze_coverage_json_returns_expected_report():
    """Coverage analysis should detect uncovered lines and compute rates."""
    coverage_data = {
        "files": {
            "src\\xai\\core\\example.py": {
                "summary": {"executed_lines": 4, "num_statements": 10},
                "lines": [1, 0, 1, 0, 1, 1, 0, 1, 0, 0],
            }
        }
    }

    reports = analyze_coverage_json(coverage_data)

    assert len(reports) == 1
    report = reports[0]
    assert report.file_path == "src/xai/core/example.py"
    assert report.coverage_percentage == 40.0
    assert report.uncovered_lines == [2, 4, 7, 9, 10]
    assert report.uncovered_count == 5


def test_prioritize_files_by_coverage_and_uncovered_count():
    """Files with lower coverage and more uncovered lines rank higher."""
    reports = [
        FileReport(file_path="a.py", total_lines=10, covered_lines=9, uncovered_lines=[10], coverage_percentage=90.0, uncovered_count=1),
        FileReport(file_path="core/b.py", total_lines=10, covered_lines=5, uncovered_lines=[1, 2, 3, 4, 5], coverage_percentage=50.0, uncovered_count=5),
    ]

    ordered = prioritize_files(reports)

    assert ordered[0].file_path == "core/b.py"
    assert ordered[1].file_path == "a.py"


def test_generate_text_report_contains_summary_entries():
    """Text report should include summary header and detailed file info."""
    reports = [
        FileReport(file_path="src/xai/core/example.py", total_lines=20, covered_lines=10, uncovered_lines=[5, 6], coverage_percentage=50.0, uncovered_count=2)
    ]

    output = generate_text_report(reports, min_uncovered=1, show_code=False)

    assert "UNCOVERED LINES REPORT" in output
    assert "File: src/xai/core/example.py" in output
    assert "Coverage: 50.00%" in output
    assert "Uncovered Lines: 2" in output


def test_generate_json_report_converts_reports_to_dict():
    """JSON report should summarize the same data provided."""
    reports = [
        FileReport(file_path="src/xai/core/example.py", total_lines=20, covered_lines=20, uncovered_lines=[], coverage_percentage=100.0, uncovered_count=0)
    ]

    json_output = generate_json_report(reports)

    assert json_output["summary"]["total_files"] == 1
    assert json_output["summary"]["files_below_98"] == 0
    assert json_output["files"][0]["file_path"] == "src/xai/core/example.py"


def test_get_line_context_returns_surrounding_lines(tmp_path: Path):
    """Line context should capture surrounding lines around the requested row."""
    sample = tmp_path / "sample.py"
    sample.write_text("first\nsecond\nthird\nfourth\nfifth\n")

    before, code, after = get_line_context(sample, 3, context_size=1)

    assert before == ["second"]
    assert code == "third"
    assert after == ["fourth"]
