#!/bin/bash

# Complete Testing Script for Multiple Registrations Refactoring
# This script tests all changes from PR #20 and PR #21

set -e  # Exit on error

echo "🧪 Testing Multiple Registrations Per Event Refactoring"
echo "======================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${YELLOW}━━━ $1 ━━━${NC}"
    echo ""
}

# Test 1: Unit Tests
print_section "Test 1: Running Unit Tests"
echo "Running all registration service tests..."
if python -m pytest tests/unit/test_registration_service.py -v --tb=short -q > /tmp/test_output.txt 2>&1; then
    PASSED=$(grep -o "[0-9]* passed" /tmp/test_output.txt | awk '{print $1}')
    echo "Result: $PASSED tests passed"
    print_result 0 "All unit tests passed ($PASSED/68)"
else
    cat /tmp/test_output.txt
    print_result 1 "Unit tests failed"
fi

# Test 2: Check Database Migration File Exists
print_section "Test 2: Database Migration"
if [ -f "alembic/versions/20260528_1500_add_unique_user_event_tier.py" ]; then
    print_result 0 "Migration file exists"

    # Check migration has correct constraint
    if grep -q "uq_registration_user_event_tier" alembic/versions/20260528_1500_add_unique_user_event_tier.py; then
        print_result 0 "Migration contains UNIQUE constraint"
    else
        print_result 1 "Migration missing UNIQUE constraint"
    fi

    # Check migration has index
    if grep -q "idx_registrations_user_event" alembic/versions/20260528_1500_add_unique_user_event_tier.py; then
        print_result 0 "Migration contains performance index"
    else
        print_result 1 "Migration missing performance index"
    fi
else
    print_result 1 "Migration file not found"
fi

# Test 3: Repository Layer Changes
print_section "Test 3: Repository Layer"
REPO_FILE="app/modules/registrations/repositories/registration_repository.py"

# Check get_by_user_and_event returns list
if grep -q "def get_by_user_and_event.*-> list\[Registration\]" $REPO_FILE; then
    print_result 0 "get_by_user_and_event returns list"
else
    print_result 1 "get_by_user_and_event return type incorrect"
fi

# Check new method exists
if grep -q "def get_by_user_event_tier" $REPO_FILE; then
    print_result 0 "get_by_user_event_tier method exists"
else
    print_result 1 "get_by_user_event_tier method missing"
fi

# Test 4: Service Layer Changes
print_section "Test 4: Service Layer"
SERVICE_FILE="app/modules/registrations/services/registration_service.py"

# Check upgrade_tier method is simplified
UPGRADE_LINES=$(sed -n '/def upgrade_tier/,/^    def [^_]/p' $SERVICE_FILE | wc -l)
if [ $UPGRADE_LINES -lt 120 ]; then
    print_result 0 "upgrade_tier method simplified ($UPGRADE_LINES lines, was 214)"
else
    print_result 1 "upgrade_tier method still too complex ($UPGRADE_LINES lines)"
fi

# Check bug fix for list handling
if grep -q "existing_registrations = self.repository.get_by_user_and_event" $SERVICE_FILE; then
    print_result 0 "List handling bug fix applied"
else
    print_result 1 "List handling bug fix missing"
fi

# Check variable name fix
if grep -q 'return.*"registration": reactivated_response' $SERVICE_FILE; then
    print_result 0 "Variable name bug fix applied"
else
    print_result 1 "Variable name bug fix missing"
fi

# Test 5: API Endpoints
print_section "Test 5: API Endpoints"
API_FILE="app/modules/registrations/api/registrations.py"

# Check new endpoint exists
if grep -q "def get_my_event_registrations" $API_FILE; then
    print_result 0 "New /my-registrations endpoint exists"
else
    print_result 1 "New endpoint missing"
fi

# Check legacy endpoint exists
if grep -q "LEGACY ENDPOINT" $API_FILE; then
    print_result 0 "Legacy endpoint maintained for backward compatibility"
else
    print_result 1 "Legacy endpoint documentation missing"
fi

# Test 6: Documentation
print_section "Test 6: Documentation"

if [ -f "TESTING_GUIDE.md" ]; then
    print_result 0 "TESTING_GUIDE.md exists"
else
    print_result 1 "TESTING_GUIDE.md missing"
fi

if [ -f "TEST_RESULTS_SUMMARY.md" ]; then
    print_result 0 "TEST_RESULTS_SUMMARY.md exists"
else
    print_result 1 "TEST_RESULTS_SUMMARY.md missing"
fi

# Test 7: Import Tests (Check for circular dependencies)
print_section "Test 7: Import Tests"
if python -c "
from app.modules.registrations.repositories.registration_repository import RegistrationRepository
from app.modules.registrations.services.registration_service import RegistrationService
print('Imports successful')
" 2>/dev/null; then
    print_result 0 "No import errors or circular dependencies"
else
    print_result 1 "Import errors detected"
fi

# Summary
print_section "Test Summary"
TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
fi
echo "Pass Rate: $PASS_RATE%"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Ready for deployment.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review.${NC}"
    exit 1
fi
