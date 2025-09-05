## Description
<!-- Provide a brief description of the changes in this PR -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Security fix (addresses a security vulnerability)
- [ ] Documentation update

## Security Checklist
### Code Security
- [ ] No hardcoded secrets, passwords, or API keys
- [ ] Input validation implemented for all user inputs
- [ ] Output encoding applied where necessary
- [ ] SQL queries use parameterized statements
- [ ] No use of dangerous functions (eval, exec, etc.)

### Authentication & Authorization
- [ ] Authentication required for protected endpoints
- [ ] Authorization checks implemented
- [ ] Session management properly handled
- [ ] Rate limiting applied where appropriate

### Dependencies
- [ ] No new dependencies with known vulnerabilities
- [ ] Dependencies are from trusted sources
- [ ] Minimal permissions/scope for dependencies
- [ ] License compatibility verified

### Sensitive Data
- [ ] No sensitive data in logs
- [ ] PII/sensitive data encrypted at rest
- [ ] Secure transmission (HTTPS/TLS)
- [ ] Data retention policies followed

## Security Scan Results
<!-- Automated scans will post results here -->
- [ ] Dependency scan passed
- [ ] Secret detection passed
- [ ] SAST analysis passed
- [ ] Security score meets threshold

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Security tests added (if applicable)
- [ ] All tests passing

## Additional Notes
<!-- Any additional information about security considerations -->

## Reviewer Checklist
- [ ] Code follows security best practices
- [ ] No obvious security vulnerabilities
- [ ] Appropriate error handling
- [ ] Logging doesn't expose sensitive data
- [ ] Documentation updated if needed
