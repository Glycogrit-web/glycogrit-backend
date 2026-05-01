# GlycoGrit Backend Test Suite

## 🎯 Purpose

This comprehensive test suite protects against financial losses and security vulnerabilities in the payment and registration system.

## 🚨 Critical Tests

### Financial Tests (`@pytest.mark.financial`)
These tests **MUST PASS** before deployment. They prevent:
- Wrong payment amounts (e.g., charging ₹500 instead of ₹20)
- Duplicate payment orders
- Users getting upgraded without payment
- Double charging
- Incorrect tier pricing calculations

### Security Tests (`@pytest.mark.security`)
These tests **MUST PASS** before deployment. They prevent:
- Fake payment confirmations (signature verification)
- Unauthorized access to other users' registrations
- Webhook replay attacks

## 📁 Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── unit/
│   └── test_payment_service.py    # Unit tests for payment logic
├── integration/
│   └── test_payment_registration_flow.py  # Full flow tests
└── e2e/
    └── (end-to-end tests with real browser)
```

## 🚀 Running Tests

### Run All Tests
```bash
./run_tests.sh
```

### Run Specific Test Categories
```bash
# Financial tests only (CRITICAL)
pytest -m financial -v

# Security tests only (CRITICAL)
pytest -m security -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_payment_service.py -v

# Specific test function
pytest tests/unit/test_payment_service.py::TestPaymentCreation::test_create_payment_order_tier_upgrade_correct_amount -v
```

### Run Tests with Coverage
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html to view coverage report
```

## 🎭 Test Markers

- `@pytest.mark.financial` - Critical financial tests
- `@pytest.mark.security` - Critical security tests
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests that take >1 second

## 🔧 Setup

### Install Test Dependencies
```bash
pip install -r requirements-test.txt
```

### Run Tests Locally
```bash
# Activate virtual environment
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Run tests
pytest -v
```

## 🤖 Automated Testing

Tests run automatically on:
- Every push to `master`, `main`, `staging`, `develop`
- Every pull request
- Before deployment (GitHub Actions)

### GitHub Actions Workflow
- Location: `.github/workflows/test-on-push.yml`
- Runs on: Python 3.10 and 3.11
- **Deployment blocked if financial or security tests fail**

## 📊 Coverage Requirements

- Minimum coverage: **70%**
- Critical modules (payment_service, registration_service): **90%+**
- View coverage: `pytest --cov=app --cov-report=html`

## 🐛 Writing New Tests

### For New Payment Features
1. Add tests to `tests/unit/test_payment_service.py`
2. Mark critical tests with `@pytest.mark.financial`
3. Test edge cases and failure scenarios
4. Ensure tests check financial correctness

### For New Security Features
1. Add tests to appropriate test file
2. Mark with `@pytest.mark.security`
3. Test authentication, authorization, and input validation

### Test Template
```python
import pytest

@pytest.mark.financial  # or @pytest.mark.security
class TestNewFeature:
    """Description of what's being tested."""

    @pytest.mark.financial
    def test_specific_scenario(self, db, test_user, test_registration):
        """
        CRITICAL: Describe what financial loss this prevents.
        Bug reference: Issue #123
        """
        # Arrange
        # ...

        # Act
        # ...

        # Assert
        assert expected_result, "Clear failure message"
```

## 🚫 Common Test Failures

### "Financial tests failed"
- **DO NOT DEPLOY**
- Review payment logic changes
- Check tier pricing calculations
- Verify no duplicate orders

### "Security tests failed"
- **DO NOT DEPLOY**
- Review authentication changes
- Check webhook signature verification
- Verify authorization checks

### "Coverage below 70%"
- Add tests for new code
- Remove dead code
- Mark test-only code with `# pragma: no cover`

## 📚 Test Scenarios Covered

### Payment Creation
- ✅ Tier upgrade calculates differential price
- ✅ No duplicate pending payments
- ✅ Correct amount for each tier combination
- ✅ Zero-price upgrades rejected
- ✅ Already-paid registrations rejected

### Webhook Processing
- ✅ Payment confirmation updates tier
- ✅ Idempotent (handles multiple events)
- ✅ Invalid signature rejected
- ✅ Failed payments marked correctly

### Registration Flow
- ✅ Cannot upgrade to sold-out tier
- ✅ Cannot upgrade to same tier
- ✅ Cannot downgrade via upgrade endpoint
- ✅ Free tier upgrades auto-confirm
- ✅ Cannot modify other users' registrations

### Edge Cases
- ✅ Token expiration during payment
- ✅ Webhook arrives before frontend verification
- ✅ Payment order reuse on retry
- ✅ Multiple upgrade attempts
- ✅ Concurrent tier registrations

## 🔍 Debugging Failed Tests

### View detailed test output
```bash
pytest -vv --tb=long
```

### Run single failing test
```bash
pytest tests/unit/test_payment_service.py::TestClassName::test_method_name -vv
```

### Drop into debugger on failure
```bash
pytest --pdb
```

### Print database state
```python
def test_something(db):
    # ... test code ...

    # Debug: print all payments
    payments = db.query(Payment).all()
    for p in payments:
        print(f"Payment {p.id}: {p.amount} - {p.status}")
```

## 🎯 Test Maintenance

- Review and update tests when payment logic changes
- Add tests for every bug fix
- Keep financial and security tests up to date
- Run full test suite before major releases

## 📞 Support

If tests fail and you're unsure why:
1. Read the test description and comments
2. Check recent code changes in the tested module
3. Review the error message and assertion
4. Ask team members if still unclear

**Remember: Failed financial/security tests = DO NOT DEPLOY!**
