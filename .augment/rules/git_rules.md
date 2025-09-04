---
type: "agent_requested"
description: "Example description"
---

# Augment Git Commit and Push Rules

## Rule: Git Commit and Push Process

### When user requests to commit and push changes, ALWAYS follow this EXACT process

**PHASE 1: Pre-Commit Validation (MANDATORY)**

1. **Check Git Status First**

   ```bash
   git status
   ```

   - Review ALL modified files
   - Ensure no unwanted files are staged
   - Document which files will be committed

2. **Run Pre-Commit Checks (MANDATORY)**

   ```bash
   poetry run black src/ tests/ --check
   poetry run isort src/ tests/ --check
   poetry run flake8 src/ tests/
   poetry run mypy src/graphrag_api_service
   poetry run pytest tests/ -v
   ```

   - ALL checks MUST pass before proceeding
   - If ANY check fails, fix the issues first

**PHASE 2: Stage Changes (MANDATORY)**

3. **Review Changes Before Staging**

   ```bash
   git diff
   ```

   - Review each change carefully
   - Ensure no debug code or print statements
   - Verify no secrets or API keys

4. **Stage Files Appropriately**

   For ALL changes:

   ```bash
   git add -A
   ```

   For specific files only:

   ```bash
   git add src/ tests/
   git add pyproject.toml
   git add .env.example  # NEVER add .env
   ```

   NEVER stage these files:
   - `.env` (contains secrets)
   - `*.pyc` or `__pycache__/`
   - `.mypy_cache/`
   - `.pytest_cache/`
   - `node_modules/`
   - `*.log`
   - Personal notes or temporary files

**PHASE 3: Commit with Proper Message (MANDATORY)**

5. **Create Semantic Commit Message**

   Use this EXACT format:

   ```bash
   git commit -m "<type>: <description>

   <body>
   <footer>"
   ```

   **Commit Types (MUST use one):**
   - `feat:` New feature
   - `fix:` Bug fix
   - `refactor:` Code refactoring (no functionality change)
   - `chore:` Maintenance tasks (formatting, dependencies)
   - `docs:` Documentation updates
   - `test:` Test additions or fixes
   - `perf:` Performance improvements
   - `style:` Code style changes (formatting)
   - `build:` Build system changes
   - `ci:` CI/CD changes
   - `revert:` Revert previous commit

   **Examples of GOOD commit messages:**

   ```bash
   git commit -m "refactor: Reduce complexity in data processor

   - Split process_data() into 3 smaller functions
   - Reduced cyclomatic complexity from 15 to 8
   - All tests pass"
   ```

   ```bash
   git commit -m "feat: Add batch processing for workspace operations

   - Implement batch delete for multiple workspaces
   - Add progress tracking for batch operations
   - Include rollback on failure"
   ```

   ```bash
   git commit -m "fix: Resolve type errors in authentication module

   - Add Optional type hints for nullable returns
   - Fix incompatible type in JWT validation
   - Update return types to match implementation"
   ```

   ```bash
   git commit -m "chore: Apply code quality improvements

   - Format with black (22 files)
   - Organize imports with isort (15 files)
   - Fix flake8 violations (0 remaining)
   - Fix mypy type errors (0 remaining)"
   ```

**PHASE 4: Push to GitHub (MANDATORY)**

6. **Push to Correct Branch**

   For main branch:

   ```bash
   git push origin main
   ```

   For feature branch:

   ```bash
   git push origin feature/branch-name
   ```

   For first push of new branch:

   ```bash
   git push -u origin feature/branch-name
   ```

   If push is rejected (behind remote):

   ```bash
   git pull --rebase origin main
   # Resolve any conflicts if they exist
   git push origin main
   ```

**PHASE 5: Post-Push Verification (MANDATORY)**

7. **Verify Push Success**

   ```bash
   git log --oneline -5
   git status
   ```

   - Confirm commit is in log
   - Confirm working tree is clean
   - Confirm branch is up to date with remote

## Rule: Commit Message Standards

### Title Line (MANDATORY)

- Maximum 50 characters
- Start with type (feat, fix, refactor, etc.)
- Use imperative mood ("Add" not "Added")
- No period at the end

### Body (OPTIONAL but recommended for complex changes)

- Separate from title with blank line
- Maximum 72 characters per line
- Explain WHAT and WHY, not HOW
- Use bullet points for multiple items

### Footer (OPTIONAL)

- Reference issues: `Fixes #123`
- Breaking changes: `BREAKING CHANGE: description`
- Co-authors: `Co-authored-by: Name <email>`

## Rule: Branch Protection

### NEVER force push to main

```bash
# NEVER DO THIS on main branch:
git push --force origin main  # FORBIDDEN

# Only acceptable on feature branches you own:
git push --force origin feature/my-branch
```

### NEVER commit directly to main without tests passing

```bash
# ALWAYS run before committing to main:
poetry run pytest tests/ -v
```

## Rule: Handling Merge Conflicts

### When conflicts occur during pull

1. **Pull with rebase**

   ```bash
   git pull --rebase origin main
   ```

2. **Resolve conflicts**
   - Open conflicted files
   - Choose correct version or merge both
   - Remove conflict markers (`<<<<`, `====`, `>>>>`)

3. **Test after resolution**

   ```bash
   poetry run pytest tests/ -v
   ```

4. **Continue rebase**

   ```bash
   git add .
   git rebase --continue
   ```

5. **Push resolved changes**

   ```bash
   git push origin main
   ```

## Rule: Commit Frequency

### Commit guidelines

- Commit after each logical unit of work
- Don't mix unrelated changes in one commit
- Don't commit broken code to main
- Commit at least once per day when actively working

### Good commit size

- 1-400 lines of code changes
- Single responsibility per commit
- Can be reverted without breaking other features

## Rule: Emergency Rollback Process

### If bad code was pushed

1. **Immediate revert (safest)**

   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Reset to previous commit (only if no one else pulled)**

   ```bash
   git reset --hard HEAD~1
   git push --force-with-lease origin main
   ```

## Rule: Git Configuration

### Ensure proper git configuration

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Set up useful aliases

```bash
git config alias.st "status"
git config alias.co "checkout"
git config alias.br "branch"
git config alias.cm "commit -m"
git config alias.last "log -1 HEAD"
```

## Rule: Pre-Push Checklist

### MUST verify ALL before pushing

- [ ] All tests pass (`poetry run pytest`)
- [ ] No linting errors (`poetry run flake8`)
- [ ] No type errors (`poetry run mypy`)
- [ ] Code is formatted (`poetry run black --check`)
- [ ] Imports are organized (`poetry run isort --check`)
- [ ] No debug print() statements
- [ ] No commented-out code blocks
- [ ] No TODO/FIXME in committed code
- [ ] Commit message follows format
- [ ] Changes match commit description

## Rule: Handling Sensitive Files

### NEVER commit these

- `.env` files with real credentials
- Private keys or certificates
- Database dumps with real data
- Log files with sensitive information
- Personal configuration files
- API keys or tokens

### If accidentally committed

```bash
# Remove from history (if not pushed)
git rm --cached .env
git commit -m "fix: Remove sensitive file from tracking"

# If already pushed, rotate the exposed credentials immediately
```

## Rule: Commit Examples for Common Scenarios

### After code quality improvements

```bash
git add -A
git commit -m "refactor: Apply comprehensive code quality improvements

- Applied black formatting to 22 files
- Fixed 15 mypy type errors
- Reduced complexity in 5 functions
- Removed 8 unused imports
- All tests pass (66/66)"
git push origin main
```

### After fixing bugs

```bash
git add src/
git commit -m "fix: Resolve authentication token refresh issue

- Fix token expiration check logic
- Add proper error handling for invalid tokens
- Update tests for edge cases
Fixes #234"
git push origin main
```

### After adding features

```bash
git add -A
git commit -m "feat: Implement batch processing for workspace operations

- Add /api/workspaces/batch endpoint
- Support bulk delete with transaction rollback
- Include progress tracking via websockets
- Add comprehensive test coverage"
git push origin main
```

### After documentation updates

```bash
git add docs/ README.md
git commit -m "docs: Update API documentation for v2.0

- Add batch operation examples
- Update authentication guide
- Include rate limiting details
- Add troubleshooting section"
git push origin main
```

## Rule: Git Command Order (NEVER CHANGE)

1. `git status` - Check what's changed
2. `git diff` - Review changes
3. Run all quality checks
4. `git add` - Stage changes
5. `git commit -m` - Commit with message
6. `git pull --rebase` - Get latest changes
7. `git push` - Push to remote

## Rule: Commit Message Templates

### Save as .gitmessage

```
<type>: <subject>

# Why:

# What:

# How:

# Testing:

# Issues: #
```

Set template:

```bash
git config commit.template .gitmessage
```
