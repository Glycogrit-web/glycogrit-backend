# CI/CD Pipeline Documentation

## Overview

This repository uses a comprehensive multi-stage CI/CD pipeline to ensure code quality, security, and reliability before merging to production branches.

## Pipeline Stages

### 1. 🔍 Code Quality & Linting (Fast - ~2-3 minutes)

**Purpose:** Catch formatting and code quality issues early

**Checks:**
- **Black**: Code formatting (must pass)
- **isort**: Import sorting (must pass)
- **Ruff**: Fast Python linter (must pass)
- **Bandit**: Security vulnerability scanner (warning only)
- **mypy**: Static type checking (warning only)

**How to fix locally:**
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check with ruff
ruff check app/ tests/ --fix

# Type check
mypy app/
```

### 2. 🧪 Unit Tests (Parallel - ~5-8 minutes)

**Purpose:** Test individual components in isolation

**Configuration:**
- Runs on Python 3.10, 3.11, and 3.12 in parallel
- Excludes slow tests (use `-m "not slow"`)
- Must pass on all Python versions

**How to run locally:**
```bash
pytest tests/unit/ -v --tb=short -m "not slow"
```

### 3. 🔗 Integration Tests (~10-15 minutes)

**Purpose:** Test component interactions and API endpoints

**Configuration:**
- Runs after unit tests pass
- Tests real database and API interactions
- Must pass to merge

**How to run locally:**
```bash
pytest tests/integration/ -v --tb=short
```

### 4. 💰 Critical Financial Tests (Parallel - ~5-10 minutes)

**Purpose:** **MUST PASS** - Tests payment processing, order calculations, and financial logic

**Configuration:**
- ⚠️ **BLOCKING** - Cannot merge if these fail
- Runs in parallel with integration tests
- Uses extensive logging for debugging
- Tagged with `@pytest.mark.financial`

**How to run locally:**
```bash
pytest tests/ -v -m financial --tb=long
```

**Why this is critical:**
- Financial bugs can cause monetary losses
- Payment calculation errors affect revenue
- Order processing must be accurate
- Regulatory compliance requirements

### 5. 🔒 Security Tests (Parallel - ~5-10 minutes)

**Purpose:** Test authentication, authorization, and security features

**Configuration:**
- Warning only (doesn't block merge yet)
- Tests SQL injection prevention, XSS protection, etc.
- Tagged with `@pytest.mark.security`

**How to run locally:**
```bash
pytest -v -m security
```

### 6. 📊 Code Coverage (~8-12 minutes)

**Purpose:** Ensure adequate test coverage

**Configuration:**
- Minimum 70% coverage required
- Generates HTML reports for detailed analysis
- Posts coverage reports to PRs automatically
- Must pass to merge

**How to run locally:**
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term --cov-fail-under=70
open htmlcov/index.html  # View detailed report
```

### 7. ✅ All Tests Status Check

**Purpose:** Final gate that ensures all required checks passed

**Checks:**
- Code quality: ✓
- Unit tests: ✓
- Integration tests: ✓
- Financial tests: ✓
- Coverage: ✓

This is the check that branch protection rules should require.

## Branch Protection Rules

### Recommended Settings

For the `master` and `main` branches:

1. **Require pull request reviews before merging**
   - Required approving reviews: 1
   - Dismiss stale pull request approvals when new commits are pushed: ✓

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging: ✓
   - Required status checks:
     - `✅ All Required Tests Passed`

3. **Require conversation resolution before merging**: ✓

4. **Require linear history**: ✓

5. **Do not allow bypassing the above settings**: ✓

### How to Configure

1. Go to: `https://github.com/Glycogrit-web/glycogrit-backend/settings/branches`
2. Click "Add branch protection rule"
3. Branch name pattern: `master`
4. Enable the settings above
5. Click "Create" or "Save changes"

## Performance Optimization

The pipeline is optimized for fast feedback:

- **Parallel execution**: Jobs run concurrently when possible
- **Caching**: pip packages are cached between runs
- **Fail-fast disabled**: See all test failures at once
- **Concurrency control**: Cancels outdated runs automatically
- **Timeout limits**: Prevents stuck jobs from blocking the queue

## Troubleshooting

### Pipeline is taking too long

- Check if jobs are running in parallel
- Look for slow tests and tag them with `@pytest.mark.slow`
- Consider splitting large test files

### Financial tests failing

1. Check the detailed logs in the "💰 Critical Financial Tests" job
2. Run locally: `pytest tests/ -v -m financial --tb=long`
3. **Do not merge until fixed** - this is a blocking requirement

### Coverage failing

1. Check which files lack coverage
2. Add tests for uncovered lines
3. View HTML report: `pytest --cov=app --cov-report=html`
4. Consider adjusting `MIN_COVERAGE` if justified

### Code quality checks failing

```bash
# Auto-fix most issues
black app/ tests/
isort app/ tests/
ruff check app/ tests/ --fix

# Then commit the changes
git add .
git commit -m "style: Fix code quality issues"
```

## Local Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install dev tools
pip install black isort ruff mypy bandit pytest-cov
```

### Pre-commit checks

Run before committing:

```bash
# Format and lint
black app/ tests/
isort app/ tests/
ruff check app/ tests/ --fix

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/ -v -m financial

# Check coverage
pytest tests/ --cov=app --cov-report=term
```

### Git hooks (optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Format check
black --check app/ tests/
isort --check-only app/ tests/

# Lint
ruff check app/ tests/

# Run unit tests
pytest tests/unit/ -v -x

echo "✅ All pre-commit checks passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Emergency Override

If you need to bypass checks in an emergency (use sparingly):

1. You can merge with admin privileges if enabled
2. Contact a repository administrator
3. Document the reason in the PR

**⚠️ Never bypass financial test failures** - these protect revenue and data integrity.

## Monitoring

- **GitHub Actions**: View all workflow runs at `/actions`
- **Codecov**: View coverage trends at codecov.io
- **Artifacts**: Download test results and coverage reports from failed runs

## Questions?

Contact the development team or open an issue.
