# Security Exceptions and Accepted Risks

## Vulnerable Dependencies

### ecdsa 0.19.1
- **CVE**: CVE-2024-23342
- **Risk**: Minerva timing attack on P-256 curve
- **Required By**: python-jose (JWT implementation)
- **Mitigation**:
  - Not using ECDSA for signing, only RSA
  - JWT operations are server-side only
  - No fix available from upstream
- **Accepted**: Yes, low risk in our use case
- **Review Date**: 2025-09-05

### future 1.0.0
- **CVE**: CVE-2025-50817
- **Risk**: Arbitrary code execution via test.py import
- **Required By**: graphrag (transitive dependency)
- **Mitigation**:
  - No test.py file in our codebase
  - Server environment controlled
  - No fix available from upstream
- **Accepted**: Yes, controlled environment
- **Review Date**: 2025-09-05

## False Positive Suppressions

### SQL Injection Warnings (Semgrep)
- **Files**: sqlite_models.py, connection_pool.py
- **Reason**: Using parameterized queries with whitelisted fields
- **Suppression**: Added `# nosemgrep` comments
- **Review Date**: 2025-09-05

### Credential Disclosure (Semgrep)
- **Files**: api_keys.py
- **Reason**: Logging sanitized key IDs only (first 8 chars)
- **Suppression**: Added `# nosemgrep` comments
- **Review Date**: 2025-09-05
