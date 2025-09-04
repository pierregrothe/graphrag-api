---
type: "agent_requested"
description: "Example description"
---

# Augment Code Quality Rules

## Rule: Python Code Quality Overhaul Process

### When user requests code quality check, ALWAYS follow this EXACT process

**PHASE 1: Automated Correction (MANDATORY - RUN ALL THREE TOOLS)**

1. **Black Formatter (MANDATORY FIRST STEP)**

   ```bash
   poetry run black src/ tests/ --line-length 100
   ```

   - This MUST be run FIRST to standardize all code formatting
   - Applies consistent style across entire codebase
   - Sets line length to 100 characters

2. **isort Import Organizer (MANDATORY SECOND STEP)**

   ```bash
   poetry run isort src/ tests/ --profile black --line-length 100
   ```

   - This MUST be run SECOND to organize all imports
   - Groups imports: standard library → third-party → local
   - Uses black-compatible profile

3. **Ruff Auto-fixer (MANDATORY THIRD STEP)**

   ```bash
   poetry run ruff check --fix src/ tests/
   ```

   - This MUST be run THIRD to fix all auto-fixable linting issues
   - Removes unused imports
   - Fixes common Python anti-patterns

**COMMIT AFTER PHASE 1**: Create commit with message: `chore: Apply automated formatting (black, isort, ruff)`

**PHASE 2: Intelligent Refactoring (MANDATORY - RUN BOTH TOOLS)**

4. **MyPy Type Checker (MANDATORY - FIX ALL ERRORS)**

   ```bash
   poetry run mypy src/graphrag_api_service --show-error-codes
   ```

   - For EVERY error reported, you MUST:
     - Identify the exact file and line number
     - Analyze why the type error exists
     - Fix it by adding type hints, Optional handling, or type conversions
     - Document: `Fixed: [file.py:line] - [error code] - [solution applied]`

   Common MyPy fixes required:
   - Add `Optional[Type]` for nullable values
   - Add return type annotations `-> ReturnType`
   - Replace `Any` with specific types
   - Add type guards for narrowing
   - Fix incompatible type assignments

5. **Flake8 Linter (MANDATORY - FIX ALL VIOLATIONS)**

   ```bash
   poetry run flake8 src/ tests/ --max-complexity=10 --max-line-length=100
   ```

   - For EVERY violation reported, you MUST:
     - Fix complexity issues by breaking functions into smaller ones
     - Fix line length issues by proper line breaking
     - Remove unused variables and imports
     - Fix PEP 8 violations

   Common Flake8 fixes required:
   - Break functions with complexity > 10 into smaller functions
   - Split long lines at appropriate breakpoints
   - Add whitespace where required by PEP 8
   - Remove trailing whitespace

6. **Pylint (OPTIONAL BUT RECOMMENDED)**

   ```bash
   poetry run pylint src/**/*.py
   ```

   - Fix critical issues only
   - Document why certain warnings are acceptable

**PHASE 3: Validation (MANDATORY)**

7. **Run ALL Tests to Ensure Nothing Broke**

   ```bash
   poetry run pytest tests/ -v
   ```

   - MUST have 100% pass rate
   - If ANY test fails, revert the breaking change

8. **Final Validation Run (MANDATORY)**
   Re-run all tools to confirm zero issues:

   ```bash
   poetry run black src/ tests/ --check
   poetry run isort src/ tests/ --check
   poetry run ruff check src/ tests/
   poetry run flake8 src/ tests/
   poetry run mypy src/graphrag_api_service
   ```

   - ALL must report zero issues/changes needed

**PHASE 4: Generate Report (MANDATORY)**

Create `CODE_QUALITY_REPORT.md` with EXACTLY this format:

```markdown
# Code Quality Report - [DATE]

## Phase 1: Automated Corrections

### Black Formatting
- Files formatted: [X]
- Lines changed: [X]

### isort Import Organization
- Files with imports reorganized: [X]
- Import groups properly ordered: Yes/No

### Ruff Auto-fixes
- Issues auto-fixed: [X]
- Types of issues fixed: [list specific types]

## Phase 2: Type Safety Fixes (MyPy)

### Critical Type Errors Fixed
1. **File: src/services/auth.py:45**
   - Error: `error: Function is missing a return type annotation [no-untyped-def]`
   - Fix: Added return type annotation `-> Optional[User]`

2. **File: src/models/workspace.py:123**
   - Error: `error: Argument 1 has incompatible type "str"; expected "int" [arg-type]`
   - Fix: Added type conversion with validation: `int(workspace_id)`

### Summary
- Total MyPy errors fixed: [X]
- Files modified: [X]
- Remaining errors requiring human review: [X]

## Phase 3: Complexity & Linting Fixes (Flake8)

### Complexity Reductions
1. **File: src/processors/data.py:200-250**
   - Issue: `C901 Function too complex (15 > 10)`
   - Fix: Refactored into 3 functions:
     - `_validate_input()` - Handles validation
     - `_process_data()` - Core processing logic
     - `_format_output()` - Output formatting

### PEP 8 Violations Fixed
1. **File: src/utils/helpers.py:89**
   - Issue: `E501 line too long (115 > 100 characters)`
   - Fix: Split line using parentheses for implicit continuation

### Summary
- Total Flake8 violations fixed: [X]
- Complexity reductions: [X] functions
- PEP 8 fixes: [X] issues

## Phase 4: Test Results

### Test Suite Status
- Total tests: [X]
- Passed: [X]
- Failed: 0
- Warnings: 0
- Coverage: [X]%

## Unresolved Issues Requiring Human Review

1. **File: src/legacy/old_api.py:456**
   - Tool: MyPy
   - Issue: Uses deprecated typing pattern
   - Reason: Requires migration strategy for backward compatibility
   - Recommendation: Schedule for next major version

## Quality Metrics Achievement

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| MyPy Errors | 0 | 0 | ✓ |
| Flake8 Violations | 0 | 0 | ✓ |
| Max Complexity | ≤10 | 10 | ✓ |
| Test Pass Rate | 100% | 100% | ✓ |
| Black Compliant | Yes | Yes | ✓ |
| isort Compliant | Yes | Yes | ✓ |
```

## Rule: Tool Installation Requirements

### Before running quality checks, ensure ALL tools are installed

```bash
poetry add --group dev black isort ruff flake8 mypy pylint pytest
```

Or with pip:

```bash
pip install black isort ruff flake8 mypy pylint pytest
```

## Rule: Tool Configuration Files Required

### Ensure these configuration files exist

**pyproject.toml** must contain:

```toml
[tool.black]
line-length = 100
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**.flake8** must contain:

```ini
[flake8]
max-line-length = 100
max-complexity = 10
exclude = .git,__pycache__,docs,build,dist,.venv,venv
ignore = E203,W503  # Black compatibility
```

## Rule: Severity Classification for Issues

### When documenting issues, ALWAYS use this classification

**CRITICAL (Fix Immediately)**

- Security vulnerabilities (SQL injection, path traversal)
- Data loss risks
- Authentication/authorization bypasses
- Memory leaks

**HIGH (Fix Before Commit)**

- Type safety violations (MyPy errors)
- Functions with complexity > 10
- Missing error handling
- Broken tests

**MEDIUM (Fix Before Release)**

- PEP 8 violations
- Missing docstrings
- Line length violations
- Import organization issues

**LOW (Fix When Possible)**

- Naming convention inconsistencies
- Optimization opportunities
- Nice-to-have refactoring

## Rule: Order of Operations is MANDATORY

### NEVER skip steps or change order

1. Black (formatting) - ALWAYS FIRST
2. isort (imports) - ALWAYS SECOND
3. Ruff --fix (auto-fixes) - ALWAYS THIRD
4. MyPy (type checking) - Fix ALL errors
5. Flake8 (linting) - Fix ALL violations
6. Pytest (testing) - MUST pass 100%

## Rule: Specific Fix Patterns

### For MyPy "no-untyped-def" errors

```python
# BEFORE:
def get_user(id):
    return User.query.get(id)

# AFTER:
def get_user(id: int) -> Optional[User]:
    return User.query.get(id)
```

### For Flake8 complexity errors

```python
# BEFORE: Function with complexity 15
def process_data(data):
    # 50 lines of nested if/for/while statements

# AFTER: Split into smaller functions
def process_data(data: dict[str, Any]) -> ProcessedData:
    validated = _validate_data(data)
    transformed = _transform_data(validated)
    return _finalize_data(transformed)

def _validate_data(data: dict[str, Any]) -> ValidatedData:
    # validation logic

def _transform_data(data: ValidatedData) -> TransformedData:
    # transformation logic

def _finalize_data(data: TransformedData) -> ProcessedData:
    # finalization logic
```

### For import organization

```python
# BEFORE (wrong order):
from .models import User
import os
from fastapi import FastAPI
import sys

# AFTER (correct order via isort):
import os
import sys

from fastapi import FastAPI

from .models import User
```

## Rule: Commands are Poetry-based

### ALWAYS use Poetry to run tools

- Use `poetry run black` NOT just `black`
- Use `poetry run mypy` NOT just `mypy`
- Use `poetry run pytest` NOT just `pytest`

This ensures correct virtual environment and dependencies.

## Rule: Never Break Tests

### If refactoring causes test failures

1. Identify which change broke the test
2. Revert that specific change
3. Document why the change couldn't be applied
4. Add to "Unresolved Issues" section of report

## Rule: Document Every Change

### For each file modified, document

- Tool that required the change
- Line numbers affected
- Specific issue fixed
- Solution applied

Example:

```
Fixed: src/api/endpoints.py:45-47
Tool: MyPy
Issue: Missing return type annotation [no-untyped-def]
Solution: Added -> JSONResponse return type
```

## Rule: Final Checklist Before Completion

### Must verify ALL of these are true

- [ ] Black reports no changes needed
- [ ] isort reports no changes needed
- [ ] Ruff reports no violations
- [ ] MyPy reports 0 errors
- [ ] Flake8 reports 0 violations
- [ ] All tests pass (100% pass rate)
- [ ] No new warnings introduced
- [ ] CODE_QUALITY_REPORT.md generated
- [ ] All changes documented
