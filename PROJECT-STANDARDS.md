# Project Standards & Policies

## 🎯 Core Principles

This document outlines the mandatory standards and policies for the XAI Blockchain project.

## 🚨 MANDATORY POLICIES

### 1. Local Testing Policy

**ALL TESTING MUST BE DONE LOCALLY BEFORE PUSHING TO GITHUB**

This is **NON-NEGOTIABLE** for all contributors and team members.

#### Why This Policy Exists
- **Cost Savings**: GitHub Actions charges for compute minutes
- **Faster Feedback**: Local tests are faster than waiting for CI
- **Quality Assurance**: Catch issues before they reach the repository
- **Professional Standards**: Industry best practice

#### What to Run

**MINIMUM** (before every push):
```bash
make quick
# or
.\local-ci.ps1 -Quick
```

**RECOMMENDED** (before every push):
```bash
make ci
# or
.\local-ci.ps1
```

**COMPREHENSIVE** (for major changes):
```bash
make all
```

#### Exceptions

There are **NO EXCEPTIONS** to this policy. Even for:
- ❌ "Quick fixes"
- ❌ "Documentation only" changes
- ❌ "Emergency hotfixes"
- ❌ "Small typos"

**Always run at least `make quick`** before pushing.

#### Enforcement

- Pre-push hooks remind you to test
- Pull requests must confirm local testing
- Failed CI runs will be reviewed for compliance
- Repeated violations will require retraining

### 2. Code Quality Standards

#### Formatting
- **Black**: Code must be formatted with Black
- **isort**: Imports must be sorted
- **Line Length**: 100 characters maximum

```bash
# Auto-format code
make format
```

#### Linting
- **Flake8**: No style violations
- **Pylint**: No critical issues
- **MyPy**: Type checking must pass

```bash
# Check linting
make lint
```

#### Type Hints
- All function signatures must have type hints
- Use `typing` module for complex types
- Document return types

```python
from typing import List, Optional, Dict

def process_data(items: List[str], max_count: int = 10) -> Dict[str, int]:
    """Process data with type safety."""
    # Implementation
```

### 3. Testing Standards

#### Coverage Requirements
- **Minimum**: 80% overall coverage
- **Core Modules**: 90%+ coverage (blockchain, consensus, security)
- **Security-Critical**: 100% coverage

```bash
# Check coverage
make coverage
open htmlcov/index.html
```

#### Test Categories

All projects must include:

1. **Unit Tests**
   - Test individual functions/methods
   - Fast execution (< 0.1s per test)
   - No external dependencies
   - Located in `tests/unit/`

2. **Integration Tests**
   - Test component interactions
   - Can be slower (< 5s per test)
   - May use test databases/fixtures
   - Located in `tests/integration/`

3. **Security Tests**
   - Test security features
   - Vulnerability testing
   - Attack scenario testing
   - Located in `tests/security/`

4. **Performance Tests**
   - Benchmark critical operations
   - Regression detection
   - Scalability testing
   - Located in `tests/performance/`

### 4. Security Standards

#### Security Scanning

**MANDATORY** before every push:
```bash
make security
```

This runs:
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **pip-audit**: Dependency auditing
- **Semgrep**: SAST analysis

#### Security Requirements

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all external data
- [ ] Proper error handling (no information leakage)
- [ ] Secure random number generation
- [ ] Protection against common attacks
- [ ] Rate limiting on APIs
- [ ] Encryption for sensitive data
- [ ] Audit logs for sensitive operations

#### Vulnerability Response

**HIGH severity issues**:
- Must be fixed immediately
- Cannot be merged until resolved
- Notify team immediately

**MEDIUM severity issues**:
- Must be fixed within 48 hours
- Create issue to track

**LOW severity issues**:
- Fix in next sprint
- Document as known issue

### 5. Documentation Standards

#### Code Documentation

**Required for all code:**

```python
def complex_function(param1: str, param2: int = 0) -> bool:
    """
    Brief description of what this function does.

    Longer description if needed, explaining the algorithm,
    approach, or important implementation details.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is negative

    Example:
        >>> complex_function("test", 42)
        True

    Note:
        Any important notes about usage, performance,
        or limitations.
    """
    # Implementation with clear comments
```

#### Project Documentation

**Must be kept up-to-date:**
- `README.md` - Project overview and quick start
- `CHANGELOG.md` - All changes documented
- `CONTRIBUTING.md` - Contribution guidelines
- `DEVELOPMENT-WORKFLOW.md` - Development process
- API documentation - All public APIs

### 6. Git Standards

#### Branch Naming

```
<type>/<description>

Examples:
feature/multi-sig-wallet
fix/double-spend-bug
docs/api-documentation
refactor/transaction-validation
security/input-validation
```

#### Commit Messages

**Format**: [Conventional Commits](https://www.conventionalcommits.org/)

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `perf`: Performance
- `chore`: Maintenance
- `security`: Security fix
- `ci`: CI/CD changes

**Examples**:
```bash
feat(wallet): add multi-signature support
fix(consensus): resolve race condition in block validation
docs(api): update REST API documentation
security(validation): add input sanitization
test(blockchain): add edge case tests for fork resolution
```

#### Pull Requests

**Required in PR**:
- [ ] Descriptive title
- [ ] Complete PR template
- [ ] Local test results
- [ ] Coverage report
- [ ] Security scan results
- [ ] Related issue links
- [ ] Breaking changes documented
- [ ] Migration guide (if needed)

### 7. Performance Standards

#### Benchmarks

Critical operations must meet these benchmarks:
- Block validation: < 100ms
- Transaction validation: < 10ms
- Signature verification: < 5ms
- Hash calculation: < 1ms

```bash
# Run performance tests
make test-performance
```

#### Monitoring

All performance regressions must be:
- Detected in CI
- Documented in PR
- Justified with rationale
- Approved by maintainer

### 8. Code Review Standards

#### Reviewer Responsibilities

Reviewers must verify:
- [ ] Local tests were run (confirmed in PR)
- [ ] All CI checks pass
- [ ] Code follows standards
- [ ] Tests are comprehensive
- [ ] Documentation is complete
- [ ] Security is addressed
- [ ] Performance is acceptable
- [ ] Breaking changes are documented

#### Author Responsibilities

Authors must:
- [ ] Run `make ci` before creating PR
- [ ] Fill out PR template completely
- [ ] Respond to all review comments
- [ ] Update based on feedback
- [ ] Re-run tests after changes
- [ ] Rebase on main before merge

### 9. Continuous Integration

#### CI Pipeline Stages

1. **Linting**
   - Black formatting check
   - isort import sorting
   - Flake8 style guide
   - Pylint code analysis
   - MyPy type checking

2. **Security Scanning**
   - Bandit security scan
   - Safety vulnerability check
   - pip-audit dependency audit
   - Semgrep SAST analysis

3. **Testing**
   - Unit tests
   - Integration tests
   - Security tests
   - Performance tests

4. **Coverage**
   - Measure code coverage
   - Ensure minimum thresholds
   - Generate reports

#### Required Checks

**Must pass before merge:**
- ✅ All linting checks
- ✅ All security scans (no HIGH severity)
- ✅ All tests pass
- ✅ Coverage ≥ 80%
- ✅ No merge conflicts
- ✅ At least one approval

### 10. Dependency Management

#### Updating Dependencies

**Process**:
1. Check for updates: `make deps-update`
2. Review changes and compatibility
3. Update `requirements.txt`
4. Run full test suite
5. Run security scans
6. Document in CHANGELOG

#### Security Updates

**HIGH priority vulnerabilities**:
- Update immediately
- Test thoroughly
- Deploy ASAP

**MEDIUM/LOW priority**:
- Update in next release
- Test in development first

#### Version Pinning

- Pin exact versions in `requirements.txt`
- Use ranges in `setup.py` for libraries
- Document compatibility requirements

## 🎓 Training & Onboarding

### New Contributors

All new contributors must:
1. Read this document completely
2. Read `DEVELOPMENT-WORKFLOW.md`
3. Read `CONTRIBUTING.md`
4. Set up pre-commit hooks
5. Run through example PR process
6. Have first PR reviewed by maintainer

### Ongoing Education

- Weekly code quality reviews
- Monthly security training
- Quarterly performance reviews
- Annual blockchain best practices update

## 📊 Metrics & Reporting

### Quality Metrics

Track these metrics:
- Test coverage percentage
- Failed CI runs per month
- Average PR review time
- Security vulnerabilities found
- Performance benchmark trends

### Goals

- **Coverage**: Maintain > 80%
- **Failed CI**: < 5% of total runs
- **Review Time**: < 24 hours
- **Security Issues**: 0 HIGH severity
- **Performance**: No regressions

## 🔧 Tools & Resources

### Required Tools

- Python 3.11+
- Git
- Make
- pre-commit
- pytest
- Black, isort, Flake8, Pylint, MyPy
- Bandit, Safety, pip-audit, Semgrep

### Recommended IDE Setup

**VS Code Extensions**:
- Python
- Pylint
- Black Formatter
- Better Comments
- GitLens
- Error Lens

**PyCharm**:
- Built-in Python support
- Enable all inspections
- Configure Black as formatter

### Learning Resources

- [Python Style Guide (PEP 8)](https://peps.python.org/pep-0008/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Testing Best Practices](https://docs.pytest.org/)
- [Security Best Practices](https://owasp.org/)

## 📞 Support & Questions

### Getting Help

1. Check documentation first
2. Search existing issues
3. Ask in team chat
4. Create issue if needed

### Reporting Issues

- Standard issues: Use issue templates
- Security issues: Email security@domain.com
- Critical bugs: Notify team immediately

## ✅ Compliance Checklist

Before every push to GitHub:

- [ ] `make format` - Code is formatted
- [ ] `make lint` - No linting errors
- [ ] `make security` - No HIGH severity issues
- [ ] `make test` - All tests pass
- [ ] `make coverage` - Coverage ≥ 80%
- [ ] `make ci` - Full CI pipeline passes
- [ ] Commit messages follow convention
- [ ] PR template will be filled out
- [ ] Documentation is updated
- [ ] Ready for code review

---

## 📝 Summary

**Key Takeaways**:

1. **ALWAYS** run `make ci` before pushing
2. **NEVER** skip local testing
3. **MAINTAIN** 80%+ test coverage
4. **FIX** security issues immediately
5. **FOLLOW** code style guidelines
6. **DOCUMENT** all public APIs
7. **REVIEW** code thoroughly
8. **KEEP** dependencies updated

**Remember**: These standards exist to maintain quality, security, and professionalism. Following them saves time and money in the long run.

---

**Last Updated**: January 2025
**Version**: 1.0
**Status**: ACTIVE - MANDATORY COMPLIANCE
