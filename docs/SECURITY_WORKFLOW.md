# Security Workflow Guide

## Overview

This guide explains how to test the security workflow locally before pushing code to GitHub, ensuring your changes pass
all security checks in CI/CD.

## Quick Start

### Fast Security Check (< 30 seconds)

```bash
# Python
python scripts/test_security_workflow.py --mode fast

# PowerShell
.\scripts\security-check.ps1 -Mode fast
```

### PR Simulation (1-2 minutes)

```bash
# Python
python scripts/test_security_workflow.py --mode pr

# PowerShell
.\scripts\security-check.ps1 -Mode pr
```

### Comprehensive Analysis (2-3 minutes)

```bash
# Python
python scripts/test_security_workflow.py --mode comprehensive

# PowerShell
.\scripts\security-check.ps1 -Mode comprehensive
```

## Security Check Modes

### Fast Mode

- **Purpose**: Quick pre-commit checks
- **Duration**: < 30 seconds
- **Checks**:
    - Dependency vulnerabilities (cached)
    - Secret detection (src/ only)
    - Code quality (Black, Ruff)
- **Use When**: Before every commit

### PR Mode

- **Purpose**: Simulate GitHub Actions PR workflow
- **Duration**: 1-2 minutes
- **Checks**:
    - Dependency vulnerabilities (full scan)
    - Secret detection
    - SAST analysis (Bandit)
- **Use When**: Before pushing to remote

### Comprehensive Mode

- **Purpose**: Full security analysis
- **Duration**: 2-3 minutes
- **Checks**:
    - All PR mode checks
    - Full security scanner
    - Detailed vulnerability analysis
- **Use When**: Before merging to main

## Security Gates

### Passing Criteria

- **Fast Mode**: Score ≥ 60/100, no critical issues
- **PR Mode**: Score ≥ 70/100, no secrets
- **Comprehensive Mode**: Score ≥ 80/100

### Common Failures and Fixes

#### 1. Vulnerable Dependencies

```bash
# Check vulnerabilities
poetry run pip-audit

# Update all dependencies
poetry update

# Update specific package
poetry add package@latest
```

#### 2. Hardcoded Secrets

```bash
# Scan for secrets
detect-secrets scan --all-files src/

# Add to .gitignore
echo "path/to/secret" >> .gitignore

# Use environment variables instead
```

#### 3. Code Quality Issues

```bash
# Auto-fix formatting
poetry run black src/ tests/

# Auto-fix linting
poetry run ruff check --fix src/ tests/

# Type checking
poetry run mypy src/graphrag_api_service
```

#### 4. Security Issues (Bandit)

```bash
# Run Bandit scan
poetry run bandit -r src/ -ll

# Add inline suppression for false positives
# nosec B608 - Explanation here
```

## Pre-commit Integration

The security checks are integrated with pre-commit hooks:

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

### Configuration

- **On Commit**: Fast security check
- **On Push**: PR simulation
- **Manual**: `pre-commit run --all-files`

### Bypass (Emergency Only)

```bash
# Skip all hooks
git commit --no-verify

# Skip specific hook
SKIP=security-check-fast git commit
```

## GitHub Actions Integration

### Workflow Files

- `.github/workflows/security.yml` - Daily comprehensive scan
- `.github/workflows/security-best-practices.yml` - PR and push checks
- `.github/workflows/ci-cd.yml` - Main CI/CD pipeline

### Security Policies

- `.github/SECURITY_POLICIES.md` - Thresholds and requirements
- `.github/pull_request_template.md` - PR security checklist

## Auto-Fix Capabilities

### Run with Auto-Fix

```bash
# Python
python scripts/test_security_workflow.py --mode fast --fix

# PowerShell
.\scripts\security-check.ps1 -Mode fast -Fix
```

### What Can Be Fixed

- ✅ Code formatting (Black)
- ✅ Import sorting (Ruff)
- ✅ Simple linting issues (Ruff)
- ✅ Some type hints (mypy)
- ❌ Security vulnerabilities (manual review required)
- ❌ Hardcoded secrets (manual removal required)

## Security Score Calculation

### Score Components

- **Base Score**: 100 points
- **Per Vulnerability**: -10 points
- **Per Secret**: -5 points
- **Per High Issue**: -15 points
- **Per Medium Issue**: -10 points
- **Per Low Issue**: -5 points

### Grade System

- **A**: 90-100 (Excellent)
- **B**: 80-89 (Good)
- **C**: 70-79 (Acceptable)
- **D**: 60-69 (Needs Improvement)
- **F**: Below 60 (Failing)

## Troubleshooting

### Timeout Issues

```bash
# Increase timeout for slow systems
python scripts/test_security_workflow.py --mode fast --timeout 120
```

### False Positives

#### Bandit

```python
# Add inline suppression
result = conn.execute(query, values)  # nosec B608 - Query uses parameterized values
```

#### Semgrep

```python
# Add inline suppression
# nosemgrep: sqlalchemy-execute-raw-query
```

#### Secrets

```bash
# Create baseline
detect-secrets scan --baseline .secrets.baseline

# Audit baseline
detect-secrets audit .secrets.baseline
```

### Cache Issues

```bash
# Clear pip cache
pip cache purge

# Clear mypy cache
rm -rf .mypy_cache/

# Clear pytest cache
rm -rf .pytest_cache/
```

## Best Practices

### Daily Workflow

1. Run fast check before commits
2. Run PR mode before pushing
3. Review security report
4. Fix issues before pushing

### Weekly Maintenance

1. Run comprehensive scan
2. Update dependencies
3. Review new CVEs
4. Update security baseline

### Monthly Review

1. Review false positives
2. Update suppression rules
3. Review security policies
4. Update documentation

## Tool Versions

Ensure you have the latest versions:

```bash
# Update security tools
pip install --upgrade pip-audit detect-secrets bandit safety semgrep

# Update pre-commit
pre-commit autoupdate

# Update Poetry dependencies
poetry update
```

## Support

### Getting Help

- Run with `--verbose` for detailed output
- Check `SECURITY_SCAN_REPORT.md` for details
- Review GitHub Actions logs
- Open an issue if needed

### Useful Commands

```bash
# Show all options
python scripts/test_security_workflow.py --help

# Verbose output
python scripts/test_security_workflow.py --mode pr --verbose

# Generate detailed report
python scripts/run_security_scan.py --verbose > security_analysis.txt
```

## Compliance

This workflow helps maintain compliance with:

- OWASP Top 10
- CWE/SANS Top 25
- PCI DSS (if handling payment data)
- SOC 2 Type II
- NIST Cybersecurity Framework
