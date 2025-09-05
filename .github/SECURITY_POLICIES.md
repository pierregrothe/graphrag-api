# Security Policies Configuration

## Security Scanning Policies

### Pull Request Requirements

- **Critical Vulnerabilities**: Block merge
- **High Vulnerabilities**: Require approval from security team
- **Medium Vulnerabilities**: Warning only
- **Low Vulnerabilities**: Informational

### Dependency Vulnerability Thresholds

```yaml
blocking:
  - severity: CRITICAL
    action: block
  - severity: HIGH
    count: > 5
    action: block

warnings:
  - severity: HIGH
    count: <= 5
    action: warn
  - severity: MEDIUM
    action: warn
```

### Secret Detection Policy

- **Any detected secret**: Block merge immediately
- **False positives**: Add to `.gitleaksignore`
- **Remediation**: Rotate exposed secrets immediately

### SAST Findings Policy

| Severity | New Code | Existing Code | Action |
|----------|----------|---------------|---------|
| Critical | 0 tolerance | Fix in 7 days | Block |
| High | 0 tolerance | Fix in 14 days | Warn |
| Medium | Best effort | Fix in 30 days | Info |
| Low | Track only | Technical debt | Info |

### Security Score Requirements

- **Production (main)**: Minimum score 80/100
- **Development (develop)**: Minimum score 70/100
- **Feature branches**: Minimum score 60/100

### Compliance Requirements

- **OWASP Top 10**: Full coverage required
- **CWE Top 25**: 90% coverage required
- **PCI DSS**: Required for payment processing
- **SOC 2**: Annual audit required

## Security Tool Configuration

### Required Security Tools

1. **Dependency Scanning**
   - pip-audit (Python)
   - npm audit (JavaScript)
   - OWASP Dependency Check

2. **Secret Detection**
   - Gitleaks
   - TruffleHog
   - detect-secrets

3. **SAST Tools**
   - Semgrep
   - CodeQL
   - Bandit (Python)

4. **Container Security**
   - Trivy
   - Snyk Container
   - Docker Scout

### Tool-Specific Settings

#### Semgrep Rules

```yaml
rules:
  - p/security-audit
  - p/owasp-top-ten
  - p/python
  - p/secrets
  - p/jwt
custom_rules:
  - ./security/custom-rules.yml
```

#### Bandit Configuration

```ini
[bandit]
exclude = /test,/tests,/migrations
skips = B101,B601
severity = medium
confidence = medium
```

#### CodeQL Queries

```yaml
queries:
  - security-extended
  - security-and-quality
custom:
  - ./security/codeql-queries
```

## Incident Response

### Security Vulnerability Process

1. **Detection**: Automated scanning or manual discovery
2. **Triage**: Assess severity and impact
3. **Remediation**: Fix according to SLA
4. **Verification**: Confirm fix with rescan
5. **Documentation**: Update security log

### SLA by Severity

- **Critical**: Fix within 24 hours
- **High**: Fix within 7 days
- **Medium**: Fix within 30 days
- **Low**: Track as technical debt

### Escalation Path

1. Development Team Lead
2. Security Team
3. CTO/CISO
4. External Security Consultant

## Exceptions and Waivers

### Exception Process

1. Document the risk
2. Provide business justification
3. Define compensating controls
4. Set expiration date
5. Obtain approval from security team

### Waiver Template

```markdown
**Risk ID**: SEC-2024-001
**Tool**: Semgrep
**Finding**: SQL Injection (CWE-89)
**File**: src/database/query.py
**Justification**: Input is sanitized at API layer
**Compensating Control**: WAF rules + input validation
**Expiration**: 2024-12-31
**Approved By**: Security Team Lead
```

## Monitoring and Metrics

### Key Security Metrics

- Mean Time to Remediate (MTTR)
- Vulnerability Discovery Rate
- False Positive Rate
- Security Score Trend
- Dependency Update Lag

### Dashboard Requirements

- Real-time security score
- Open vulnerability count by severity
- Remediation velocity
- Tool coverage percentage
- Compliance status

## Continuous Improvement

### Quarterly Reviews

- Review false positive rates
- Update tool configurations
- Assess new security tools
- Review and update policies

### Annual Assessments

- Third-party penetration testing
- Security architecture review
- Compliance audit
- Tool effectiveness analysis
