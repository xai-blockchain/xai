#!/usr/bin/env python3
from __future__ import annotations

"""
Comprehensive Security Monitoring Script for XAI Blockchain

This script performs automated security scanning, vulnerability detection,
dependency auditing, and generates comprehensive security reports.

Usage:
    python scripts/security_monitor.py [--mode MODE] [--output OUTPUT] [--config CONFIG]

Modes:
    - quick: Fast security scan (Bandit only)
    - standard: Full security scan (Bandit, Safety, pip-audit)
    - comprehensive: Complete analysis (all tools + Semgrep + CodeQL)
    - continuous: Monitor for changes and re-scan
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import argparse
import time
from dataclasses import dataclass, asdict
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('security_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ScanResult:
    """Security scan result data class"""
    tool: str
    timestamp: str
    status: str
    summary: Dict
    details: Dict
    vulnerabilities: list[Dict]
    warnings: list[str]
    errors: list[str]
    duration: float

class SecurityMonitor:
    """Main security monitoring orchestrator"""

    def __init__(self, config_path: str | None = None):
        """Initialize security monitor with configuration"""
        self.config_path = config_path or '.security/config.yml'
        self.config = self._load_config()
        self.results: dict[str, ScanResult] = {}
        self.start_time = datetime.now()
        self.repo_root = Path.cwd()
        self.reports_dir = self.repo_root / 'security_reports'
        self.reports_dir.mkdir(exist_ok=True)

    def _load_config(self) -> Dict:
        """Load security configuration from YAML file"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")

        return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default security configuration"""
        return {
            'scan_targets': {
                'source': 'src/',
                'tests': 'tests/',
                'scripts': 'scripts/'
            },
            'severity_thresholds': {
                'critical': 0,
                'high': 5,
                'medium': 20,
                'low': 100
            },
            'exclusions': {
                'files': ['*.pyc', '*.pyo']
            },
            'tools': {
                'bandit': {'enabled': True, 'level': '-ll'},
                'safety': {'enabled': True},
                'pip_audit': {'enabled': True},
                'semgrep': {'enabled': True},
                'trivy': {'enabled': False},
                'owasp_check': {'enabled': False}
            },
            'alerts': {
                'email': False,
                'slack': False,
            }
        }

    def run_bandit_scan(self) -> ScanResult:
        """Run Bandit security scanner"""
        logger.info("Running Bandit security scan...")
        start = time.time()

        try:
            result = subprocess.run(
                ['bandit', '-r', 'src/', '-f', 'json', '-ll'],
                capture_output=True,
                text=True,
                timeout=300
            )

            output = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = output.get('results', [])

            summary = {
                'total_issues': len(vulnerabilities),
                'metrics': output.get('metrics', {}),
                'skipped_tests': output.get('metrics', {}).get('_totals', {})
            }

            warnings = []
            errors = []

            if result.returncode != 0 and result.stderr:
                errors.append(result.stderr)

            return ScanResult(
                tool='bandit',
                timestamp=datetime.now().isoformat(),
                status='completed' if result.returncode == 0 else 'issues_found',
                summary=summary,
                details=output,
                vulnerabilities=vulnerabilities,
                warnings=warnings,
                errors=errors,
                duration=time.time() - start
            )

        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
            return ScanResult(
                tool='bandit',
                timestamp=datetime.now().isoformat(),
                status='timeout',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=['Bandit scan timed out after 300 seconds'],
                duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return ScanResult(
                tool='bandit',
                timestamp=datetime.now().isoformat(),
                status='error',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=[str(e)],
                duration=time.time() - start
            )

    def run_safety_scan(self) -> ScanResult:
        """Run Safety dependency vulnerability scanner"""
        logger.info("Running Safety dependency scan...")
        start = time.time()

        try:
            result = subprocess.run(
                ['safety', 'check', '--json', '--file', 'requirements.txt'],
                capture_output=True,
                text=True,
                timeout=300
            )

            output = json.loads(result.stdout) if result.stdout else []
            vulnerabilities = output if isinstance(output, list) else []

            summary = {
                'total_vulnerabilities': len(vulnerabilities),
                'scanned_packages': sum(1 for _ in vulnerabilities)
            }

            return ScanResult(
                tool='safety',
                timestamp=datetime.now().isoformat(),
                status='completed',
                summary=summary,
                details={'raw_output': result.stdout},
                vulnerabilities=vulnerabilities,
                warnings=[],
                errors=[],
                duration=time.time() - start
            )

        except FileNotFoundError:
            logger.warning("Safety not installed or requirements.txt not found")
            return ScanResult(
                tool='safety',
                timestamp=datetime.now().isoformat(),
                status='skipped',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=['Safety not installed or requirements.txt not found'],
                errors=[],
                duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
            return ScanResult(
                tool='safety',
                timestamp=datetime.now().isoformat(),
                status='error',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=[str(e)],
                duration=time.time() - start
            )

    def run_pip_audit_scan(self) -> ScanResult:
        """Run pip-audit dependency scanner"""
        logger.info("Running pip-audit scan...")
        start = time.time()

        try:
            result = subprocess.run(
                ['pip-audit', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=300
            )

            output = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = output.get('vulnerabilities', [])

            summary = {
                'total_vulnerabilities': len(vulnerabilities),
                'scanned_packages': output.get('scanned_packages', {})
            }

            return ScanResult(
                tool='pip-audit',
                timestamp=datetime.now().isoformat(),
                status='completed' if result.returncode == 0 else 'issues_found',
                summary=summary,
                details=output,
                vulnerabilities=vulnerabilities,
                warnings=[],
                errors=[],
                duration=time.time() - start
            )

        except FileNotFoundError:
            logger.warning("pip-audit not installed")
            return ScanResult(
                tool='pip-audit',
                timestamp=datetime.now().isoformat(),
                status='skipped',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=['pip-audit not installed'],
                errors=[],
                duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"pip-audit scan failed: {e}")
            return ScanResult(
                tool='pip-audit',
                timestamp=datetime.now().isoformat(),
                status='error',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=[str(e)],
                duration=time.time() - start
            )

    def run_semgrep_scan(self) -> ScanResult:
        """Run Semgrep SAST scanner"""
        logger.info("Running Semgrep static analysis...")
        start = time.time()

        try:
            result = subprocess.run(
                ['semgrep', '--config', 'auto', '--json', 'src/'],
                capture_output=True,
                text=True,
                timeout=600
            )

            output = json.loads(result.stdout) if result.stdout else {}
            results = output.get('results', [])

            summary = {
                'total_findings': len(results),
                'errors': output.get('errors', [])
            }

            warnings = []
            if output.get('errors'):
                warnings.extend([str(e) for e in output.get('errors', [])])

            return ScanResult(
                tool='semgrep',
                timestamp=datetime.now().isoformat(),
                status='completed',
                summary=summary,
                details=output,
                vulnerabilities=results,
                warnings=warnings,
                errors=[],
                duration=time.time() - start
            )

        except FileNotFoundError:
            logger.warning("Semgrep not installed")
            return ScanResult(
                tool='semgrep',
                timestamp=datetime.now().isoformat(),
                status='skipped',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=['Semgrep not installed'],
                errors=[],
                duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
            return ScanResult(
                tool='semgrep',
                timestamp=datetime.now().isoformat(),
                status='error',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=[str(e)],
                duration=time.time() - start
            )

    def run_trivy_scan(self) -> ScanResult:
        """Run Trivy container security scanner"""
        logger.info("Running Trivy security scan...")
        start = time.time()

        try:
            result = subprocess.run(
                ['trivy', 'fs', '--format', 'json', '.'],
                capture_output=True,
                text=True,
                timeout=600
            )

            output = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = output.get('Results', [])

            summary = {
                'total_vulnerabilities': len(vulnerabilities),
                'schema_version': output.get('SchemaVersion', '')
            }

            return ScanResult(
                tool='trivy',
                timestamp=datetime.now().isoformat(),
                status='completed',
                summary=summary,
                details=output,
                vulnerabilities=vulnerabilities,
                warnings=[],
                errors=[],
                duration=time.time() - start
            )

        except FileNotFoundError:
            logger.info("Trivy not installed, skipping container scan")
            return ScanResult(
                tool='trivy',
                timestamp=datetime.now().isoformat(),
                status='skipped',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=['Trivy not installed'],
                errors=[],
                duration=time.time() - start
            )
        except Exception as e:
            logger.warning(f"Trivy scan failed: {e}")
            return ScanResult(
                tool='trivy',
                timestamp=datetime.now().isoformat(),
                status='error',
                summary={},
                details={},
                vulnerabilities=[],
                warnings=[],
                errors=[str(e)],
                duration=time.time() - start
            )

    def run_quick_scan(self):
        """Run quick security scan (Bandit only)"""
        logger.info("Starting QUICK security scan...")
        self.results['bandit'] = self.run_bandit_scan()
        self._generate_reports()

    def run_standard_scan(self):
        """Run standard security scan"""
        logger.info("Starting STANDARD security scan...")
        self.results['bandit'] = self.run_bandit_scan()
        self.results['safety'] = self.run_safety_scan()
        self.results['pip_audit'] = self.run_pip_audit_scan()
        self._generate_reports()

    def run_comprehensive_scan(self):
        """Run comprehensive security scan"""
        logger.info("Starting COMPREHENSIVE security scan...")
        self.results['bandit'] = self.run_bandit_scan()
        self.results['safety'] = self.run_safety_scan()
        self.results['pip_audit'] = self.run_pip_audit_scan()
        self.results['semgrep'] = self.run_semgrep_scan()
        self.results['trivy'] = self.run_trivy_scan()
        self._generate_reports()

    def _generate_reports(self):
        """Generate security reports"""
        logger.info("Generating security reports...")

        # JSON report
        self._generate_json_report()

        # Markdown report
        self._generate_markdown_report()

        # Dashboard update
        self._generate_dashboard()

        logger.info(f"Reports saved to {self.reports_dir}")

    def _generate_json_report(self):
        """Generate JSON security report"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'scan_duration': (datetime.now() - self.start_time).total_seconds(),
            'results': {}
        }

        for tool, result in self.results.items():
            report_data['results'][tool] = asdict(result)

        report_path = self.reports_dir / f'security_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"JSON report saved: {report_path}")

    def _generate_markdown_report(self):
        """Generate markdown security report"""
        report_lines = [
            "# Security Scan Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"Scan Duration: {(datetime.now() - self.start_time).total_seconds():.2f} seconds\n"
        ]

        # Summary
        total_vulns = sum(
            len(result.vulnerabilities)
            for result in self.results.values()
        )
        report_lines.extend([
            "## Summary",
            f"- Total Vulnerabilities Found: {total_vulns}",
            f"- Tools Run: {len(self.results)}\n"
        ])

        # Tool Results
        report_lines.append("## Tool Results\n")

        for tool, result in self.results.items():
            report_lines.extend([
                f"### {tool.upper()}",
                f"- Status: {result.status}",
                f"- Duration: {result.duration:.2f}s",
                f"- Vulnerabilities: {len(result.vulnerabilities)}",
                f"- Warnings: {len(result.warnings)}",
                f"- Errors: {len(result.errors)}\n"
            ])

            if result.vulnerabilities:
                report_lines.append(f"#### Vulnerabilities ({len(result.vulnerabilities)})")
                for vuln in result.vulnerabilities[:10]:  # Show first 10
                    if isinstance(vuln, dict):
                        report_lines.append(f"- {vuln.get('issue_text', str(vuln))}")
                if len(result.vulnerabilities) > 10:
                    report_lines.append(f"- ... and {len(result.vulnerabilities) - 10} more")
                report_lines.append("")

        report_path = self.reports_dir / f'security_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        logger.info(f"Markdown report saved: {report_path}")

    def _generate_dashboard(self):
        """Generate security dashboard"""
        # This updates SECURITY-DASHBOARD.md with current status
        dashboard_path = Path('SECURITY-DASHBOARD.md')

        lines = [
            "# Security Dashboard",
            f"\nLast Updated: {datetime.now().isoformat()}\n",
            "## Current Status\n"
        ]

        # Calculate security score
        total_vulns = sum(len(r.vulnerabilities) for r in self.results.values())
        max_score = 100
        vuln_score = max(0, max_score - (total_vulns * 2))

        lines.extend([
            f"**Security Score: {vuln_score}/100**\n",
            "## Active Scans\n"
        ])

        for tool, result in self.results.items():
            status_emoji = "✅" if result.status == 'completed' else "⚠️"
            lines.append(f"{status_emoji} **{tool.upper()}**: {result.status} ({result.duration:.2f}s)")

        lines.extend([
            "\n## Vulnerabilities by Severity\n",
            "| Severity | Count | Threshold | Status |",
            "|----------|-------|-----------|--------|"
        ])

        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        thresholds = self.config.get('severity_thresholds', {})

        for severity in severity_counts:
            count = severity_counts[severity]
            threshold = thresholds.get(severity, 100)
            status = "✅ OK" if count <= threshold else "❌ FAILED"
            lines.append(f"| {severity.capitalize()} | {count} | {threshold} | {status} |")

        with open(dashboard_path, 'w') as f:
            f.write('\n'.join(lines))
        logger.info(f"Dashboard updated: {dashboard_path}")

    def get_summary(self) -> Dict:
        """Get scan summary"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_vulnerabilities': sum(
                len(result.vulnerabilities)
                for result in self.results.values()
            ),
            'tools_run': len(self.results),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'tools_status': {
                tool: result.status
                for tool, result in self.results.items()
            }
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='XAI Blockchain Security Monitoring System'
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'standard', 'comprehensive'],
        default='standard',
        help='Scan mode (default: standard)'
    )
    parser.add_argument(
        '--output',
        help='Output directory for reports',
        default='security_reports'
    )
    parser.add_argument(
        '--config',
        help='Configuration file path',
        default='.security/config.yml'
    )

    args = parser.parse_args()

    # Initialize monitor
    monitor = SecurityMonitor(config_path=args.config)

    # Run appropriate scan
    try:
        if args.mode == 'quick':
            monitor.run_quick_scan()
        elif args.mode == 'standard':
            monitor.run_standard_scan()
        else:
            monitor.run_comprehensive_scan()

        # Print summary
        summary = monitor.get_summary()
        logger.info(f"Scan Summary: {json.dumps(summary, indent=2)}")
        print(json.dumps(summary, indent=2))

    except KeyboardInterrupt:
        logger.warning("Scan interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
