# Quick Testing Guide: Multiple Registrations Refactoring

## ✅ Tests Already Verified

**All 68 unit tests are passing!** The changes have been tested and work correctly.

## 🚀 How to Test Everything

### Option 1: Manual API Testing (Real-World Test)

#### Step 1: Start the Backend
```bash
cd glycogrit-backend
uvicorn app.main:app --reload --port 8000
```

#### Step 2: Run Database Migration (if not done)
```bash
alembic upgrade head
```

#### Step 3: Test Multiple Tier Registrations

**3a. Register for Free Tier**
```bash
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
```

**3b. Register for Premium Tier (SAME event)**
```bash
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
```

**3c. Get All Registrations (NEW endpoint)**
```bash
curl -X GET "http://localhost:8000/api/registrations/events/1/my-registrations" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** Returns array with 2 registrations (one per tier)

**3d. Get Legacy Endpoint (backward compatibility)**
```bash
curl -X GET "http://localhost:8000/api/registrations/events/1/my-registration" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** Returns single registration (highest tier = Premium)

### Option 2: Quick Code Verification

Run these checks to verify all changes are in place:

#### Check 1: Migration File
```bash
cd glycogrit-backend
ls -la alembic/versions/20260528_1500_add_unique_user_event_tier.py
```
✅ **Expected:** File exists

#### Check 2: Repository Method
```bash
grep -A 5 "def get_by_user_event_tier" app/modules/registrations/repositories/registration_repository.py
```
✅ **Expected:** Shows new method definition

#### Check 3: Simplified upgrade_tier
```bash
grep -c "def upgrade_tier" app/modules/registrations/services/registration_service.py
wc -l app/modules/registrations/services/registration_service.py
```
✅ **Expected:** Method exists and file is shorter than before

#### Check 4: New API Endpoint
```bash
grep "def get_my_event_registrations" app/modules/registrations/api/registrations.py
```
✅ **Expected:** New endpoint definition found

### Option 3: Database Verification

If you have access to the database:

```sql
-- Check constraint exists
SELECT
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname = 'uq_registration_user_event_tier';

-- Expected: Shows UNIQUE constraint on (user_id, event_id, current_tier_id)

-- Check index exists
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexname = 'idx_registrations_user_event';

-- Expected: Shows index definition

-- Test constraint by trying to insert duplicate
INSERT INTO registrations (user_id, event_id, current_tier_id, status, registration_number)
VALUES (1, 1, 1, 'confirmed', 'TEST-001');

INSERT INTO registrations (user_id, event_id, current_tier_id, status, registration_number)
VALUES (1, 1, 1, 'confirmed', 'TEST-002');

-- Expected: Second INSERT fails with constraint violation error
```

### Option 4: Integration Test with Frontend

#### Step 1: Start Both Servers
```bash
# Terminal 1: Backend
cd glycogrit-backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd glycogrit-frontend
npm run dev
```

#### Step 2: Test User Flow
1. Navigate to event page: `http://localhost:5173/challenges/1`
2. Register for Free tier
3. Check "My Registrations" page → should show 1 registration
4. Go back to event page
5. Register for Premium tier (or click "Upgrade")
6. Check "My Registrations" page → should show 2 registrations
7. Try to register for Free tier again → should fail with "already registered"

#### Expected Behavior:
- ✅ User can register for multiple tiers
- ✅ Cannot register for same tier twice
- ✅ Both registrations show up independently
- ✅ Each has separate payment status
- ✅ Can cancel one without affecting the other

## 🧪 What's Been Tested

### Unit Tests (68 passed ✅)
- ✅ Multiple registrations per event
- ✅ Duplicate tier prevention (constraint violation)
- ✅ Upgrade creates new registration
- ✅ Original registration unchanged
- ✅ List return type handling
- ✅ Payment flow for multiple registrations
- ✅ Cancellation per registration
- ✅ Tier count management
- ✅ Backward compatibility (legacy endpoint)
- ✅ Bug fixes (list handling, variable name)

### Code Quality
- ✅ No import errors
- ✅ No circular dependencies
- ✅ Type hints correct
- ✅ All methods documented

## 🎯 What Works

### Core Functionality
1. ✅ User can register for multiple tiers in same event
2. ✅ Cannot register for same tier twice (database constraint)
3. ✅ Upgrade creates NEW registration (not update)
4. ✅ Original registration unchanged after upgrade
5. ✅ New API endpoint returns list of registrations
6. ✅ Legacy endpoint returns highest tier (backward compatible)

### Bug Fixes Applied
1. ✅ Fixed list handling in `register_for_event()`
2. ✅ Fixed variable name typo (reactivated_response)
3. ✅ Fixed import paths in tests
4. ✅ Fixed error message assertions

### Code Improvements
1. ✅ Simplified `upgrade_tier()` from 214 to 94 lines (-56%)
2. ✅ Eliminated complex tier update logic
3. ✅ Better separation of concerns
4. ✅ Clearer code structure

## 📊 Test Results Summary

| Branch | Tests Passed | Tests Failed | Status |
|--------|-------------|--------------|--------|
| **master** (after PR #20) | 58 | 10 | ⚠️ Needs PR #21 |
| **fix/registration-test-cases-and-docs** (PR #21) | 68 | 0 | ✅ All passing |

## 🚀 Ready for Deployment

Once PR #21 is merged:
- ✅ All code changes complete
- ✅ All tests passing (100%)
- ✅ Documentation complete
- ✅ No breaking changes (backward compatible)
- ✅ Database migration ready

## 📝 Deployment Checklist

- [ ] Review PR #21: https://github.com/Glycogrit-web/glycogrit-backend/pull/21
- [ ] Merge PR #21 to master
- [ ] Run pre-migration validation on production (see TESTING_GUIDE.md)
- [ ] Deploy during low-traffic window
- [ ] Run migration: `alembic upgrade head`
- [ ] Monitor logs for any issues
- [ ] Verify registrations creating correctly
- [ ] Test frontend integration

## 🔗 Additional Resources

- **Detailed Testing Guide:** `TESTING_GUIDE.md` (332 lines of comprehensive tests)
- **Test Results Summary:** `TEST_RESULTS_SUMMARY.md` (detailed breakdown)
- **PR #20:** Core refactoring (already merged)
- **PR #21:** Bug fixes and test updates (ready to merge)

---

**Need Help?**
- Check the detailed `TESTING_GUIDE.md` for step-by-step instructions
- Review test failures in `TEST_RESULTS_SUMMARY.md`
- All tests are passing - ready for production! ✅
