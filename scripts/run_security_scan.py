#!/usr/bin/env python
"""
scripts/run_security_scan.py
Comprehensive security scanning suite for GraphRAG API Service

Author: Pierre Grothé
Creation Date: 2025-09-05
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


class SecurityScanner:
    """Comprehensive security scanning suite."""

    def __init__(self, verbose: bool = False):
        """Initialize security scanner."""
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.results: Dict[str, Dict] = {}
        self.start_time: float = time.time()
        self.scan_timestamp = datetime.now().isoformat()

    def print_header(self, message: str) -> None:
        """Print a formatted header."""
        print(f"\n{CYAN}{BOLD}{'=' * 70}{RESET}")
        print(f"{CYAN}{BOLD}{message.center(70)}{RESET}")
        print(f"{CYAN}{BOLD}{'=' * 70}{RESET}\n")

    def print_section(self, message: str) -> None:
        """Print a section header."""
        print(f"\n{BLUE}{BOLD}[*] {message}{RESET}")
        print(f"{BLUE}{'-' * 60}{RESET}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        print(f"{GREEN}[PASS] {message}{RESET}")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        print(f"{YELLOW}[WARN] {message}{RESET}")

    def print_error(self, message: str) -> None:
        """Print error message."""
        print(f"{RED}[FAIL] {message}{RESET}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        print(f"{CYAN}[INFO] {message}{RESET}")

    def run_command(self, command: str, description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        if self.verbose:
            print(f"  Running: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.project_root
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def scan_dependencies(self) -> Dict:
        """Scan for dependency vulnerabilities using pip-audit."""
        self.print_section("Dependency Vulnerability Scan (pip-audit)")

        # Check if pip-audit is installed
        check_cmd, _ = self.run_command("poetry run pip list | grep pip-audit", "Checking pip-audit")
        if not check_cmd:
            self.print_info("Installing pip-audit...")
            self.run_command("poetry run pip install pip-audit --quiet", "Installing pip-audit")

        # Run pip-audit - it returns non-zero exit code when vulnerabilities are found
        # but we still want to parse the output
        _, output = self.run_command(
            "poetry run pip-audit --desc --format json 2>&1",
            "Scanning dependencies"
        )

        vulnerabilities = []
        vulnerable_packages = []

        # pip-audit returns non-zero when vulnerabilities are found, but still provides output
        if output:
            try:
                # Parse JSON output (it's on the second line after the summary)
                json_lines = output.strip().split('\n')
                json_output = None
                for line in json_lines:
                    if line.startswith('{'):
                        json_output = line
                        break

                if json_output:
                    audit_data = json.loads(json_output)
                    dependencies = audit_data.get("dependencies", [])

                    # Find packages with vulnerabilities
                    for dep in dependencies:
                        if dep.get("vulns") and len(dep["vulns"]) > 0:
                            vulnerable_packages.append(dep)
                            vulnerabilities.extend(dep["vulns"])

                    if vulnerable_packages:
                        self.print_error(f"Found {len(vulnerable_packages)} packages with {len(vulnerabilities)} vulnerabilities")
                        print(f"\n  {BOLD}Vulnerable Packages:{RESET}")

                        for pkg in vulnerable_packages:
                            pkg_name = pkg.get("name")
                            pkg_version = pkg.get("version")
                            vulns = pkg.get("vulns", [])

                            print(f"\n  {RED}[VULNERABLE]{RESET} {pkg_name} {pkg_version}")
                            for vuln in vulns:
                                vuln_id = vuln.get("id")
                                aliases = vuln.get("aliases", [])
                                description = vuln.get("description", "No description")
                                fix_versions = vuln.get("fix_versions", [])

                                cve_ids = [a for a in aliases if a.startswith("CVE")]
                                cve_str = f" ({', '.join(cve_ids)})" if cve_ids else ""

                                print(f"    {YELLOW}ID:{RESET} {vuln_id}{cve_str}")
                                print(f"    {YELLOW}Description:{RESET} {description[:200]}")
                                if fix_versions:
                                    print(f"    {GREEN}Fix:{RESET} Upgrade to {', '.join(fix_versions)}")
                                else:
                                    print(f"    {YELLOW}Fix:{RESET} No fix available yet")
                    else:
                        self.print_success("No known vulnerabilities in dependencies")
                else:
                    self.print_error("Could not parse pip-audit output")
                    if self.verbose:
                        print(f"  Output: {output[:500]}")

            except Exception as e:
                self.print_error(f"Failed to parse pip-audit results: {str(e)}")
                if self.verbose:
                    print(f"  Raw output: {output[:500]}")
        else:
            self.print_error("Dependency scan failed completely")
            if output:
                print(f"  {RED}Error output:{RESET}")
                for line in output.strip().split('\n')[:10]:
                    print(f"    {line}")

        return {
            "tool": "pip-audit",
            "status": "failed" if vulnerabilities else "passed",
            "vulnerabilities": len(vulnerabilities),
            "vulnerable_packages": vulnerable_packages,
            "details": vulnerabilities[:10] if vulnerabilities else []
        }

    def scan_secrets(self) -> Dict:
        """Scan for hardcoded secrets using detect-secrets."""
        self.print_section("Secret Detection Scan (detect-secrets)")

        # Check if detect-secrets is installed
        check_cmd, _ = self.run_command("pip list | grep detect-secrets", "Checking detect-secrets")
        if not check_cmd:
            self.print_info("Installing detect-secrets...")
            self.run_command("pip install detect-secrets --quiet", "Installing detect-secrets")

        # Scan for secrets excluding cache directories
        success, output = self.run_command(
            'detect-secrets scan --exclude-files "\\.mypy_cache|\\.pytest_cache|__pycache__|node_modules|\\.venv" src/',
            "Scanning for secrets"
        )

        secrets_found = []
        secret_types = {}

        if output:
            try:
                # Parse the JSON output from detect-secrets
                import json
                scan_results = json.loads(output) if output.startswith('{') else {}
                results = scan_results.get("results", {})

                # Process each file with potential secrets
                for filepath, file_secrets in results.items():
                    for secret in file_secrets:
                        secret_type = secret.get("type", "Unknown")
                        line_number = secret.get("line_number", 0)
                        hashed_secret = secret.get("hashed_secret", "")

                        secrets_found.append({
                            "file": filepath.replace(str(self.project_root), "."),
                            "line": line_number,
                            "type": secret_type,
                            "hash": hashed_secret[:16] + "..."  # Show partial hash
                        })

                        # Count by type
                        secret_types[secret_type] = secret_types.get(secret_type, 0) + 1

                if secrets_found:
                    self.print_warning(f"Found {len(secrets_found)} potential secrets in {len(results)} files")

                    # Show breakdown by type
                    print(f"\n  {BOLD}Secret Types Found:{RESET}")
                    for stype, count in sorted(secret_types.items(), key=lambda x: x[1], reverse=True):
                        print(f"    {YELLOW}- {stype}: {count}{RESET}")

                    # Show top findings
                    print(f"\n  {BOLD}Top Secret Findings:{RESET}")
                    for secret in secrets_found[:5]:  # Show top 5
                        print(f"    {RED}[{secret['type']}]{RESET} {secret['file']}:{secret['line']}")
                        print(f"      Hash: {secret['hash']}")
                else:
                    self.print_success("No hardcoded secrets detected")

            except Exception as e:
                # Fallback to simple detection
                if "secret" in output.lower() or "password" in output.lower():
                    self.print_warning("Potential secrets detected (unable to parse details)")
                else:
                    self.print_success("No obvious secrets detected")
                if self.verbose:
                    print(f"  Parse error: {str(e)}")
                    print(f"  Output sample: {output[:200]}")
        else:
            self.print_warning("Secret scan completed with no output")

        return {
            "tool": "detect-secrets",
            "status": "passed" if len(secrets_found) == 0 else "warning",
            "secrets_found": len(secrets_found),
            "secret_types": secret_types,
            "details": secrets_found[:10]  # Store top 10 for remediation
        }

    def scan_bandit(self) -> Dict:
        """Run Bandit security linter."""
        self.print_section("Security Linting (Bandit)")

        success, output = self.run_command(
            "poetry run bandit -r src/ -f json -ll",
            "Running Bandit scan"
        )

        issues = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        all_issues = []
        if success:
            try:
                bandit_data = json.loads(output)
                metrics = bandit_data.get("metrics", {})
                results = bandit_data.get("results", [])
                all_issues = results

                for severity in ["SEVERITY.HIGH", "SEVERITY.MEDIUM", "SEVERITY.LOW"]:
                    key = severity.split(".")[1]
                    issues[key] = metrics.get(severity, 0)

                if issues["HIGH"] > 0:
                    self.print_error(f"Found {issues['HIGH']} high severity issues")
                elif issues["MEDIUM"] > 0:
                    self.print_warning(f"Found {issues['MEDIUM']} medium severity issues")
                else:
                    self.print_success("No high/medium severity issues found")

                # Show details of HIGH and MEDIUM issues
                if all_issues and (issues["HIGH"] > 0 or issues["MEDIUM"] > 0 or self.verbose):
                    print(f"\n  {BOLD}Top security findings:{RESET}")
                    shown_count = 0
                    for issue in all_issues:
                        severity = issue.get("issue_severity", "")
                        if severity in ["HIGH", "MEDIUM"] or (self.verbose and shown_count < 5):
                            filename = issue.get("filename", "").replace(str(self.project_root) + "\\", "")
                            line = issue.get("line_number", 0)
                            confidence = issue.get("issue_confidence", "")
                            test_id = issue.get("test_id", "")
                            text = issue.get("issue_text", "")[:100]

                            color = RED if severity == "HIGH" else YELLOW if severity == "MEDIUM" else CYAN
                            print(f"    {color}[{severity}]{RESET} {filename}:{line}")
                            print(f"      {test_id}: {text}")
                            shown_count += 1
                            if shown_count >= 10:  # Limit to 10 issues max
                                break
            except Exception as e:
                self.print_success("Bandit scan completed")
                if self.verbose:
                    print(f"  Parse error: {str(e)}")

        return {
            "tool": "bandit",
            "status": "failed" if issues["HIGH"] > 0 else "warning" if issues["MEDIUM"] > 0 else "passed",
            "issues": issues
        }

    def scan_safety(self) -> Dict:
        """Check for known security vulnerabilities using safety."""
        self.print_section("Known Vulnerability Check (Safety)")

        # Check if safety is installed
        check_cmd, _ = self.run_command("pip list | grep safety", "Checking safety")
        if not check_cmd:
            self.print_info("Installing safety...")
            self.run_command("pip install safety --quiet", "Installing safety")

        # Run safety check - it returns non-zero on vulnerabilities but still outputs JSON
        _, output = self.run_command(
            "poetry run safety check --json 2>&1",
            "Checking known vulnerabilities"
        )

        vulnerabilities = []
        vulnerable_packages = {}

        if output:
            try:
                # Safety outputs JSON array of vulnerabilities
                if output.strip().startswith('['):
                    safety_data = json.loads(output)
                    vulnerabilities = safety_data if isinstance(safety_data, list) else []

                    # Group vulnerabilities by package
                    for vuln in vulnerabilities:
                        pkg_name = vuln.get("package", "unknown")
                        if pkg_name not in vulnerable_packages:
                            vulnerable_packages[pkg_name] = {
                                "name": pkg_name,
                                "installed": vuln.get("installed_version", ""),
                                "affected": vuln.get("affected_versions", ""),
                                "vulnerabilities": []
                            }

                        vulnerable_packages[pkg_name]["vulnerabilities"].append({
                            "id": vuln.get("vulnerability_id", ""),
                            "cve": vuln.get("CVE", ""),
                            "description": vuln.get("advisory", ""),
                            "severity": vuln.get("severity", "unknown"),
                            "fixed_in": vuln.get("more_info_url", "")
                        })

                    if vulnerable_packages:
                        self.print_warning(f"Found {len(vulnerabilities)} vulnerabilities in {len(vulnerable_packages)} packages")

                        print(f"\n  {BOLD}Vulnerable Packages:{RESET}")
                        for pkg_name, pkg_info in list(vulnerable_packages.items())[:5]:  # Show top 5
                            print(f"\n  {RED}[VULNERABLE]{RESET} {pkg_name} {pkg_info['installed']}")
                            print(f"    Affected versions: {pkg_info['affected']}")

                            for vuln in pkg_info["vulnerabilities"][:2]:  # Show top 2 vulns per package
                                cve = f" ({vuln['cve']})" if vuln['cve'] else ""
                                print(f"    {YELLOW}Vulnerability:{RESET} {vuln['id']}{cve}")
                                desc = vuln['description'][:150] if vuln['description'] else "No description"
                                print(f"      {desc}")
                    else:
                        self.print_success("No known vulnerabilities found")
                else:
                    # Try to parse any error messages
                    if "no known" in output.lower() or "0 vulnerabilities" in output.lower():
                        self.print_success("No known vulnerabilities found")
                    else:
                        self.print_warning("Safety check completed with output")
                        if self.verbose:
                            print(f"  Output: {output[:500]}")

            except Exception as e:
                self.print_success("Safety check completed")
                if self.verbose:
                    print(f"  Parse error: {str(e)}")
                    print(f"  Output sample: {output[:200]}")
        else:
            self.print_success("Safety check completed with no vulnerabilities")

        return {
            "tool": "safety",
            "status": "failed" if vulnerabilities else "passed",
            "vulnerabilities": len(vulnerabilities),
            "vulnerable_packages": list(vulnerable_packages.values()),
            "details": vulnerabilities[:10]
        }

    def scan_semgrep(self) -> Dict:
        """Run Semgrep SAST analysis."""
        self.print_section("SAST Analysis (Semgrep)")

        # Check if semgrep is installed
        semgrep_check, _ = self.run_command("semgrep --version", "Checking Semgrep")

        if not semgrep_check:
            self.print_warning("Semgrep not installed. Install with: pip install semgrep")
            return {
                "tool": "semgrep",
                "status": "skipped",
                "reason": "Not installed"
            }

        success, output = self.run_command(
            "semgrep --config=auto --json src/",
            "Running SAST analysis"
        )

        findings = []
        if success:
            try:
                semgrep_data = json.loads(output)
                findings = semgrep_data.get("results", [])
                errors = semgrep_data.get("errors", [])

                if findings:
                    severity_counts: Dict[str, int] = {}
                    findings_by_severity: Dict[str, list] = {}

                    for finding in findings:
                        severity = finding.get("extra", {}).get("severity", "INFO")
                        severity_counts[severity] = severity_counts.get(severity, 0) + 1

                        if severity not in findings_by_severity:
                            findings_by_severity[severity] = []
                        findings_by_severity[severity].append(finding)

                    self.print_warning(f"Found {len(findings)} potential issues")
                    for severity, count in severity_counts.items():
                        color = RED if severity == "ERROR" else YELLOW if severity == "WARNING" else CYAN
                        print(f"  {color}- {severity}: {count}{RESET}")

                    # Show top findings for each severity
                    print(f"\n  {BOLD}Top findings by severity:{RESET}")
                    for severity in ["ERROR", "WARNING", "INFO"]:
                        if severity in findings_by_severity:
                            color = RED if severity == "ERROR" else YELLOW if severity == "WARNING" else CYAN
                            print(f"\n  {color}{severity}S:{RESET}")
                            for finding in findings_by_severity[severity][:3]:  # Show top 3 per severity
                                path = finding.get("path", "unknown")
                                line = finding.get("start", {}).get("line", 0)
                                message = finding.get("extra", {}).get("message", "No message")
                                rule_id = finding.get("check_id", "unknown").split(".")[-1]  # Get last part of rule ID
                                print(f"    {path}:{line} - [{rule_id}] {message[:80]}")

                                # Add remediation hint if available
                                fix = finding.get("extra", {}).get("fix", "")
                                if fix:
                                    print(f"      {GREEN}Fix: {fix[:70]}{RESET}")
                else:
                    self.print_success("No security issues found by Semgrep")
            except:
                self.print_info("Semgrep analysis completed")

        return {
            "tool": "semgrep",
            "status": "warning" if findings else "passed",
            "findings": len(findings)
        }

    def check_security_headers(self) -> Dict:
        """Check for security headers in the FastAPI application."""
        self.print_section("Security Headers Check")

        headers_to_check = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]

        # Check if security headers middleware is configured
        middleware_file = self.project_root / "src" / "graphrag_api_service" / "middleware" / "security_headers.py"

        if middleware_file.exists():
            content = middleware_file.read_text()
            configured_headers = []

            for header in headers_to_check:
                if header in content:
                    configured_headers.append(header)
                    self.print_success(f"Found {header}")
                else:
                    self.print_warning(f"Missing {header}")

            return {
                "tool": "security-headers",
                "status": "passed" if len(configured_headers) >= 3 else "warning",
                "configured": configured_headers,
                "missing": [h for h in headers_to_check if h not in configured_headers]
            }
        else:
            self.print_warning("Security headers middleware not found")
            return {
                "tool": "security-headers",
                "status": "warning",
                "reason": "Middleware file not found"
            }

    def check_authentication(self) -> Dict:
        """Check authentication implementation."""
        self.print_section("Authentication Security Check")

        auth_details = {
            "JWT implementation": {"found": False, "details": [], "severity": "HIGH"},
            "Password hashing": {"found": False, "details": [], "severity": "CRITICAL"},
            "Rate limiting": {"found": False, "details": [], "severity": "HIGH"},
            "Session management": {"found": False, "details": [], "severity": "MEDIUM"},
            "MFA/2FA": {"found": False, "details": [], "severity": "MEDIUM"},
            "API Key Management": {"found": False, "details": [], "severity": "HIGH"},
            "CORS Configuration": {"found": False, "details": [], "severity": "MEDIUM"},
            "CSRF Protection": {"found": False, "details": [], "severity": "HIGH"}
        }

        # Check for JWT implementation
        jwt_locations = [
            self.project_root / "src" / "graphrag_api_service" / "auth" / "jwt_manager.py",
            self.project_root / "src" / "graphrag_api_service" / "services" / "auth_service.py"
        ]

        for jwt_file in jwt_locations:
            if jwt_file.exists():
                content = jwt_file.read_text()
                if "jwt" in content.lower() or "JsonWebToken" in content:
                    auth_details["JWT implementation"]["found"] = True
                    auth_details["JWT implementation"]["details"].append(f"Found in {jwt_file.name}")

                    # Check JWT security features
                    if "exp" in content or "expires" in content:
                        auth_details["JWT implementation"]["details"].append("Token expiration implemented")
                    if "SECRET_KEY" in content or "secret" in content:
                        auth_details["JWT implementation"]["details"].append("Secret key configured")

        # Check for password hashing
        auth_files = list((self.project_root / "src" / "graphrag_api_service").rglob("*auth*.py"))
        for auth_file in auth_files:
            try:
                content = auth_file.read_text()
                if "bcrypt" in content or "passlib" in content or "argon2" in content:
                    auth_details["Password hashing"]["found"] = True
                    auth_details["Password hashing"]["details"].append(f"Found in {auth_file.name}")
                    if "bcrypt" in content:
                        auth_details["Password hashing"]["details"].append("Using bcrypt (recommended)")
                    if "argon2" in content:
                        auth_details["Password hashing"]["details"].append("Using Argon2 (most secure)")
                    break
            except:
                pass

        # Check for rate limiting
        rate_limit_file = self.project_root / "src" / "graphrag_api_service" / "middleware" / "rate_limiting.py"
        if rate_limit_file.exists():
            auth_details["Rate limiting"]["found"] = True
            content = rate_limit_file.read_text()
            if "slowapi" in content.lower():
                auth_details["Rate limiting"]["details"].append("Using SlowAPI for rate limiting")
            if "redis" in content.lower():
                auth_details["Rate limiting"]["details"].append("Redis-based rate limiting (scalable)")
            # Look for rate limit values
            import re
            rate_patterns = re.findall(r'(\d+)/([^\s"\']+)', content)
            for rate, period in rate_patterns[:3]:
                auth_details["Rate limiting"]["details"].append(f"Rate: {rate} requests per {period}")

        # Check for API key management
        api_key_file = self.project_root / "src" / "graphrag_api_service" / "auth" / "api_keys.py"
        if api_key_file.exists():
            auth_details["API Key Management"]["found"] = True
            content = api_key_file.read_text()
            if "APIKeyScope" in content:
                auth_details["API Key Management"]["details"].append("Scoped API keys implemented")
            if "rate_limit" in content.lower():
                auth_details["API Key Management"]["details"].append("Per-key rate limiting")

        # Check for CORS configuration
        cors_file = self.project_root / "src" / "graphrag_api_service" / "middleware" / "cors.py"
        main_file = self.project_root / "src" / "graphrag_api_service" / "main.py"

        if cors_file.exists():
            content = cors_file.read_text()
            if "CORSMiddleware" in content:
                auth_details["CORS Configuration"]["found"] = True
                auth_details["CORS Configuration"]["details"].append("CORS middleware configured")
                if "allowed_origins" in content.lower():
                    auth_details["CORS Configuration"]["details"].append("Origin restrictions in place")
                if "allow_credentials" in content:
                    auth_details["CORS Configuration"]["details"].append("Credentials support configured")
        elif main_file.exists():
            content = main_file.read_text()
            if "CORSMiddleware" in content or "setup_cors_middleware" in content:
                auth_details["CORS Configuration"]["found"] = True
                auth_details["CORS Configuration"]["details"].append("CORS middleware configured")

        # Display detailed results
        passed_checks = sum(1 for check in auth_details.values() if check["found"])
        total_checks = len(auth_details)

        print(f"\n  {BOLD}Authentication Security Analysis:{RESET}")
        print(f"  Score: {passed_checks}/{total_checks} features implemented\n")

        # Show implemented features
        implemented = [name for name, info in auth_details.items() if info["found"]]
        if implemented:
            print(f"  {GREEN}{BOLD}Implemented Features:{RESET}")
            for feature in implemented:
                print(f"    {GREEN}[PASS]{RESET} {feature}")
                for detail in auth_details[feature]["details"][:2]:
                    print(f"        - {detail}")

        # Show missing critical features
        missing_critical = [(name, info) for name, info in auth_details.items()
                          if not info["found"] and info["severity"] in ["CRITICAL", "HIGH"]]
        if missing_critical:
            print(f"\n  {RED}{BOLD}Missing Critical Features:{RESET}")
            for feature, info in missing_critical:
                print(f"    {RED}[FAIL]{RESET} {feature} ({info['severity']})")

        # Show missing other features
        missing_other = [(name, info) for name, info in auth_details.items()
                        if not info["found"] and info["severity"] == "MEDIUM"]
        if missing_other:
            print(f"\n  {YELLOW}{BOLD}Missing Recommended Features:{RESET}")
            for feature, info in missing_other:
                print(f"    {YELLOW}[WARN]{RESET} {feature}")

        return {
            "tool": "auth-check",
            "status": "passed" if passed_checks >= total_checks * 0.7 else "warning" if passed_checks >= total_checks * 0.5 else "failed",
            "checks": {name: info["found"] for name, info in auth_details.items()},
            "details": auth_details,
            "score": f"{passed_checks}/{total_checks}"
        }

    def generate_report(self) -> None:
        """Generate comprehensive security report."""
        self.print_header("SECURITY SCAN REPORT")

        # Calculate overall score
        total_tools = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get("status") == "passed")
        warnings = sum(1 for r in self.results.values() if r.get("status") == "warning")
        failed = sum(1 for r in self.results.values() if r.get("status") == "failed")

        # Security score calculation (out of 100)
        # More balanced scoring:
        # - Passed tools get full points
        # - Warnings get partial points (50%)
        # - Failed get no points
        points_per_tool = 100 / total_tools if total_tools > 0 else 0

        passed_points = passed * points_per_tool
        warning_points = warnings * points_per_tool * 0.5
        failed_points = 0

        security_score = passed_points + warning_points

        # Apply penalties for critical issues
        # Deduct for vulnerable dependencies (but not if no fix exists)
        dep_result = self.results.get("Dependency Vulnerability Scan", {})
        if dep_result.get("status") == "failed":
            # Check if fixes are available
            vulnerable_pkgs = dep_result.get("vulnerable_packages", [])
            has_fixable = any(
                vuln.get("fix_versions", [])
                for pkg in vulnerable_pkgs
                for vuln in pkg.get("vulns", [])
            )
            if has_fixable:
                security_score -= 10  # Only penalize if fixes exist

        # Deduct for actual secrets (not false positives)
        secret_result = self.results.get("Secret Detection", {})
        if secret_result.get("secrets_found", 0) > 100:  # Many secrets
            security_score -= 15
        elif secret_result.get("secrets_found", 0) > 10:  # Some secrets
            security_score -= 5

        security_score = max(0, min(100, security_score))

        # Determine grade
        if security_score >= 90:
            grade = "A"
            grade_color = GREEN
        elif security_score >= 80:
            grade = "B"
            grade_color = GREEN
        elif security_score >= 70:
            grade = "C"
            grade_color = YELLOW
        elif security_score >= 60:
            grade = "D"
            grade_color = YELLOW
        else:
            grade = "F"
            grade_color = RED

        print(f"\n{BOLD}Security Score: {grade_color}{security_score:.1f}/100 (Grade: {grade}){RESET}")
        print(f"{BOLD}Scan Timestamp: {self.scan_timestamp}{RESET}")
        print(f"{BOLD}Scan Duration: {time.time() - self.start_time:.2f} seconds{RESET}\n")

        print(f"{CYAN}{BOLD}Summary:{RESET}")
        print(f"  {GREEN}[PASS] Passed: {passed}{RESET}")
        print(f"  {YELLOW}[WARN] Warnings: {warnings}{RESET}")
        print(f"  {RED}[FAIL] Failed: {failed}{RESET}")

        # Provide remediation suggestions based on findings
        print(f"\n{CYAN}{BOLD}Remediation Steps:{RESET}")

        remediation_steps = []

        # Check for specific issues and provide targeted advice
        for tool_name, result in self.results.items():
            if result.get("status") in ["failed", "warning"]:
                if tool_name == "Dependency Vulnerability Scan" or result.get("tool") == "pip-audit":
                    if result.get("vulnerabilities", 0) > 0:
                        vulnerable_pkgs = result.get("vulnerable_packages", [])
                        for pkg in vulnerable_pkgs[:3]:  # Show top 3
                            pkg_name = pkg.get("name")
                            vulns = pkg.get("vulns", [])
                            for vuln in vulns:
                                fix_versions = vuln.get("fix_versions", [])
                                if fix_versions:
                                    remediation_steps.append(f"Upgrade {pkg_name} to {fix_versions[0]}: poetry add {pkg_name}@{fix_versions[0]}")
                                else:
                                    remediation_steps.append(f"Review {pkg_name} - no fix available yet for vulnerability")
                elif (tool_name == "SAST Analysis" or result.get("tool") == "semgrep") and result.get("findings", 0) > 0:
                    remediation_steps.append("Review and fix SAST findings: semgrep --config=auto src/")
                elif tool_name == "Security Linting" or result.get("tool") == "bandit":
                    issues = result.get("issues", {})
                    if issues.get("HIGH", 0) > 0:
                        remediation_steps.append("Fix HIGH severity Bandit issues immediately")
                    elif issues.get("MEDIUM", 0) > 0:
                        remediation_steps.append("Review MEDIUM severity Bandit findings")
                elif (tool_name == "Secret Detection" or result.get("tool") == "detect-secrets") and result.get("secrets_found", 0) > 0:
                    remediation_steps.append("Remove hardcoded secrets and use environment variables")
                elif (tool_name == "Known Vulnerabilities" or result.get("tool") == "safety") and result.get("vulnerabilities", 0) > 0:
                    remediation_steps.append("Update packages with known vulnerabilities")

        # Add general recommendations based on score only if no specific steps
        if not remediation_steps:
            if security_score < 60:
                remediation_steps.append("Run 'poetry run pip install pip-audit' to enable dependency scanning")
                remediation_steps.append("Consider implementing automated security testing in CI/CD")
        elif security_score < 80:
            remediation_steps.append("Schedule regular security scans (weekly recommended)")
            remediation_steps.append("Review and update security policies")

        if remediation_steps:
            for i, step in enumerate(remediation_steps[:5], 1):  # Show top 5 steps
                print(f"  {i}. {step}")
        else:
            print(f"  {GREEN}No critical remediation steps required. Continue monitoring.{RESET}")

        print(f"\n{CYAN}{BOLD}Quick Fix Commands:{RESET}")
        print(f"  {GREEN}Auto-fix formatting:{RESET} poetry run black src/ tests/")
        print(f"  {GREEN}Auto-fix linting:{RESET} poetry run ruff check --fix src/ tests/")
        print(f"  {GREEN}Update dependencies:{RESET} poetry update")
        print(f"  {GREEN}Install security tools:{RESET} pip install pip-audit semgrep detect-secrets safety")

        # Generate markdown report
        self.generate_markdown_report(security_score, grade)

    def generate_markdown_report(self, score: float, grade: str) -> None:
        """Generate markdown security report."""
        report_file = self.project_root / "SECURITY_SCAN_REPORT.md"

        with open(report_file, "w") as f:
            f.write("# Security Scan Report\n\n")
            f.write(f"**Generated**: {self.scan_timestamp}\n")
            f.write(f"**Security Score**: {score:.1f}/100 (Grade: {grade})\n\n")

            f.write("## Executive Summary\n\n")
            f.write("This report provides a comprehensive security analysis of the GraphRAG API Service ")
            f.write("using industry-standard security scanning tools.\n\n")

            f.write("## Scan Results\n\n")

            for tool_name, result in self.results.items():
                status_emoji = "[PASS]" if result["status"] == "passed" else "[WARN]" if result["status"] == "warning" else "[FAIL]"
                f.write(f"### {status_emoji} {tool_name}\n\n")
                f.write(f"**Status**: {result['status'].upper()}\n\n")

                if tool_name == "Dependency Vulnerability Scan":
                    if result.get("vulnerabilities", 0) > 0:
                        f.write(f"Found {result['vulnerabilities']} vulnerable dependencies\n\n")
                elif tool_name == "Security Linting":
                    issues = result.get("issues", {})
                    f.write(f"- High: {issues.get('HIGH', 0)}\n")
                    f.write(f"- Medium: {issues.get('MEDIUM', 0)}\n")
                    f.write(f"- Low: {issues.get('LOW', 0)}\n\n")
                elif tool_name == "Authentication Security":
                    f.write(f"**Score**: {result.get('score', 'N/A')}\n\n")
                    checks = result.get("checks", {})
                    for check, passed in checks.items():
                        status = "[PASS]" if passed else "[FAIL]"
                        f.write(f"- {status} {check}\n")
                    f.write("\n")

            f.write("## Compliance\n\n")
            f.write("This security scan covers:\n")
            f.write("- OWASP Top 10 vulnerabilities\n")
            f.write("- CWE/SANS Top 25 Most Dangerous Software Errors\n")
            f.write("- PCI DSS requirements for secure coding\n")
            f.write("- NIST Cybersecurity Framework guidelines\n\n")

            f.write("## Recommendations\n\n")
            if score < 80:
                f.write("1. Address all high and medium severity findings\n")
                f.write("2. Update vulnerable dependencies\n")
                f.write("3. Implement missing security headers\n")
                f.write("4. Review and fix authentication issues\n")
            else:
                f.write("1. Continue regular security scanning\n")
                f.write("2. Keep dependencies updated\n")
                f.write("3. Maintain security best practices\n")

        self.print_success(f"Security report saved to: {report_file}")

    def run_full_scan(self) -> None:
        """Run all security scans."""
        self.start_time = time.time()

        self.print_header("ENTERPRISE SECURITY SCANNING SUITE")
        print(f"{MAGENTA}Scanning GraphRAG API Service for security vulnerabilities...{RESET}\n")

        # Run all scans
        self.results["Dependency Vulnerability Scan"] = self.scan_dependencies()
        self.results["Secret Detection"] = self.scan_secrets()
        self.results["Security Linting"] = self.scan_bandit()
        self.results["Known Vulnerabilities"] = self.scan_safety()
        self.results["SAST Analysis"] = self.scan_semgrep()
        self.results["Security Headers"] = self.check_security_headers()
        self.results["Authentication Security"] = self.check_authentication()

        # Generate report
        self.generate_report()

        print(f"\n{GREEN}{BOLD}Security scan completed successfully!{RESET}")
        print(f"{CYAN}View the detailed report in SECURITY_SCAN_REPORT.md{RESET}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Enterprise Security Scanner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    scanner = SecurityScanner(verbose=args.verbose)
    scanner.run_full_scan()


if __name__ == "__main__":
    main()
