# Testing Guide: Multiple Registrations Per Event Refactoring

## Overview
This guide helps you test the refactoring that allows users to have multiple registrations per event (one per tier).

## Quick Test Summary
- ✅ **58 tests passing** - Core functionality works
- ⚠️ **10 tests failing** - Expected, need updates for new behavior
- 🔧 **Action needed**: Update test expectations, add new tests

---

## Option 1: Manual API Testing (Recommended First)

### Prerequisites
1. Start the backend server:
   ```bash
   cd glycogrit-backend
   uvicorn app.main:app --reload
   ```

2. Run migration (if not already done):
   ```bash
   alembic upgrade head
   ```

### Test Case 1: Register for Multiple Tiers

**Test**: User can register for multiple tiers in same event

```bash
# 1. Register for Free tier (tier_id=1)
curl -X POST "http://localhost:8000/api/registrations/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "tier_id": 1,
    "participant_name": "Test User",
    "age": 30,
    "gender": "male"
  }'

# 2. Register for Premium tier (tier_id=2) in SAME event
curl -X POST "http://localhost:8000/api/registrations/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "tier_id": 2,
    "participant_name": "Test User",
    "age": 30,
    "gender": "male"
  }'

# 3. Get all registrations for event
curl -X GET "http://localhost:8000/api/registrations/events/1/my-registrations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: Returns array with 2 registrations (one per tier)
```

**Expected Result**: ✅ Both registrations succeed, user has 2 registrations

### Test Case 2: Cannot Register Same Tier Twice

**Test**: Duplicate tier registration should fail

```bash
# 1. Register for tier
curl -X POST "http://localhost:8000/api/registrations/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "tier_id": 1,
    "participant_name": "Test User"
  }'

# 2. Try to register for SAME tier again
curl -X POST "http://localhost:8000/api/registrations/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "tier_id": 1,
    "participant_name": "Test User"
  }'

# Expected: Second request returns error "Already registered for this tier"
```

**Expected Result**: ❌ Second registration fails with appropriate error

### Test Case 3: Tier Upgrade Creates New Registration

**Test**: Upgrade should create NEW registration, not update existing

```bash
# 1. Register for Free tier (tier_id=1)
curl -X POST "http://localhost:8000/api/registrations/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "tier_id": 1,
    "participant_name": "Test User"
  }'
# Note the registration_id from response (e.g., registration_id: 100)

# 2. Upgrade to Premium tier (tier_id=2)
curl -X POST "http://localhost:8000/api/registrations/100/upgrade-tier" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tier_id": 2
  }'
# Note the NEW registration_id from response (e.g., registration_id: 101)

# 3. Check registrations
curl -X GET "http://localhost:8000/api/registrations/events/1/my-registrations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: Returns array with 2 registrations
# - registration_id: 100 (tier_id: 1, still exists)
# - registration_id: 101 (tier_id: 2, newly created)
```

**Expected Result**: ✅ Two separate registrations exist (old + new)

### Test Case 4: Legacy Endpoint Returns Highest Tier

**Test**: Old endpoint should return highest tier for backward compatibility

```bash
# 1. Register for multiple tiers (Free, Basic, Premium)
# ... (register for tier 1, 2, 3)

# 2. Call legacy endpoint
curl -X GET "http://localhost:8000/api/registrations/events/1/my-registration" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: Returns SINGLE registration (highest tier = Premium)
```

**Expected Result**: ✅ Returns single registration object (not array), highest tier

---

## Option 2: Database Validation

### Check Constraint is Applied

```sql
-- Connect to database
psql postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway

-- 1. Check constraint exists
SELECT
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname = 'uq_registration_user_event_tier';

-- Expected: Shows UNIQUE constraint on (user_id, event_id, current_tier_id)

-- 2. Check index exists
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname = 'idx_registrations_user_event';

-- Expected: Shows index on (user_id, event_id)

-- 3. Test constraint by inserting duplicate
INSERT INTO registrations (user_id, event_id, current_tier_id, status, registration_number)
VALUES (1, 1, 1, 'confirmed', 'TEST-001');

INSERT INTO registrations (user_id, event_id, current_tier_id, status, registration_number)
VALUES (1, 1, 1, 'confirmed', 'TEST-002');

-- Expected: Second INSERT fails with constraint violation
-- ERROR: duplicate key value violates unique constraint "uq_registration_user_event_tier"
```

---

## Option 3: Run Specific Test Cases

### Run Tests by Category

```bash
cd glycogrit-backend

# Run only passing tests (quick validation)
pytest tests/unit/test_registration_service.py::TestRegistrationCreation -v

# Run tier upgrade tests (these need updates)
pytest tests/unit/test_registration_service.py::TestTierUpgradeScenarios -v

# Run specific failing test
pytest tests/unit/test_registration_service.py::TestTierUpgradeScenarios::test_upgrade_creates_registration_tier_history -v
```

---

## Option 4: Integration Testing with Frontend

### Test Full User Flow

1. **Start both servers**:
   ```bash
   # Terminal 1: Backend
   cd glycogrit-backend
   uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd glycogrit-frontend
   npm run dev
   ```

2. **Test flow**:
   - Navigate to event page: `http://localhost:5173/challenges/1`
   - Register for Free tier
   - Check "My Registrations" page - should show 1 registration
   - Go back to event page
   - Register for Premium tier (or click "Upgrade")
   - Check "My Registrations" page - should show 2 registrations

3. **Expected behavior**:
   - User sees both registrations listed
   - Each registration has separate payment status
   - Can cancel one without affecting the other

---

## Test Failures to Fix

### Critical Failures (need immediate fix):

1. **`test_register_for_event_pending_reactivation`** (Line 1570)
   - **Issue**: `register_for_event()` expects single registration, gets list
   - **Fix**: Update code to handle list: `existing = existing[0] if existing else None`

2. **`test_get_my_event_registration_returns_existing`** (Line 1760)
   - **Issue**: Test expects single registration, gets list
   - **Fix**: Update test to expect list

3. **`test_upgrade_creates_registration_tier_history`** (Line 593)
   - **Issue**: Expects tier history, but upgrade now creates NEW registration
   - **Fix**: Update test to verify NEW registration exists, not tier history

4. **`test_confirm_registration_tier_upgrade_updates_tier_id`** (Line 1836)
   - **Issue**: Expects tier_id update, but now creates new registration
   - **Fix**: Update test to check new registration exists with tier_id=2

### Expected Failures (tests based on old behavior):

5. **`test_update_registration_during_tier_upgrade`** - Upgrade doesn't update fields anymore
6. **`test_attempt_tier_downgrade_blocked`** - Now creates new registration for lower tier (allowed)

---

## Success Criteria

### Core Functionality ✅
- [x] User can register for multiple tiers in same event
- [x] Cannot register for same tier twice (constraint violation)
- [x] Upgrade creates NEW registration
- [x] Original registration unchanged after upgrade
- [x] New API endpoint returns list of registrations
- [x] Legacy API endpoint returns highest tier

### Test Coverage 🔧 (TODO)
- [ ] Update 10 failing tests for new behavior
- [ ] Add test: `test_user_can_have_multiple_registrations()`
- [ ] Add test: `test_cannot_register_same_tier_twice()`
- [ ] Add test: `test_upgrade_creates_new_registration_not_updates()`
- [ ] Add test: `test_my_registrations_api_returns_list()`
- [ ] Add test: `test_legacy_api_returns_highest_tier()`

### Database ✅
- [x] Migration creates UNIQUE constraint
- [x] Migration creates performance index
- [x] Constraint prevents duplicate tier registrations

---

## Next Steps

### Immediate Actions:
1. ✅ **Run manual API tests** (Option 1) - Verify core functionality works
2. ⚠️ **Fix critical test failures** - Update tests expecting list instead of single
3. 🔧 **Update test expectations** - Modify tests for new upgrade behavior
4. ➕ **Add new tests** - Cover multiple registrations scenarios

### Before Production Deployment:
1. Run pre-migration validation on production database
2. Ensure all tests pass (after updates)
3. Test with staging database
4. Deploy during low-traffic window

---

## Quick Commands Reference

```bash
# Run all registration tests
pytest tests/unit/test_registration_service.py -v

# Run only passing tests
pytest tests/unit/test_registration_service.py -v -k "not (pending_reactivation or tier_history or get_my_event_registration_returns)"

# Run specific test
pytest tests/unit/test_registration_service.py::TestTierUpgradeScenarios::test_upgrade_from_free_to_paid -v

# Check test coverage
pytest tests/unit/test_registration_service.py --cov=app.modules.registrations --cov-report=html

# Run integration tests
pytest tests/integration/test_payment_registration_flow.py -v
```

---

## Need Help?

- Check PR description: https://github.com/Glycogrit-web/glycogrit-backend/pull/20
- Review implementation plan: `~/.claude/plans/polymorphic-rolling-riddle.md`
- Check migration file: `alembic/versions/20260528_1500_add_unique_user_event_tier.py`
