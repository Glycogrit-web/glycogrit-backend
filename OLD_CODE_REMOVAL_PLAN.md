# Old Code Removal Plan

**Status**: Ready to Execute
**Goal**: Remove all deprecated old API and service code
**Date**: 2026-05-21

---

## Phase 1: Remove Old API Files (23 files)

### Old API Directory: `app/api/`

```bash
cd /Users/ygahlot/mac-one-Personal-projects/runnersParadise/glycogrit-backend/app/api

# Remove old API files
rm activities.py              # → app/modules/activities/api/activities.py
rm activity_progress.py       # → app/modules/activities/api/progress.py
rm progress.py                # → app/modules/activities/api/progress.py
rm auth.py                    # → app/modules/users/api/auth.py
rm challenges.py              # → app/modules/challenges/api/challenges.py
rm rewards.py                 # → app/modules/rewards/api/rewards.py
rm events.py                  # → app/modules/events/api/events.py
rm event_tiers.py             # → integrated in events module
rm registrations.py           # → app/modules/registrations/api/registrations.py
rm certificates.py            # → app/modules/certificates/api/certificates.py
rm gallery.py                 # → app/modules/gallery/api/gallery.py
rm statistics.py              # → app/modules/statistics/api/statistics.py
rm payments.py                # → app/modules/payments/api/routes.py
rm webhooks.py                # → app/modules/webhooks/api/webhooks.py
rm webhooks_v2.py             # → app/modules/webhooks/api/webhooks.py

# Remove old fitness tracker APIs (replaced by unified API)
rm fitness_trackers.py        # → app/modules/fitness_trackers/api/fitness_trackers.py
rm strava.py                  # → unified in fitness_trackers
rm garmin.py                  # → unified in fitness_trackers
rm fitbit.py                  # → unified in fitness_trackers
rm google_fit.py              # → unified in fitness_trackers
rm wahoo.py                   # → unified in fitness_trackers

# Keep base.py if it has shared utilities, otherwise remove
rm base.py

# Remove __pycache__
rm -rf __pycache__
```

**Total**: 23 files, ~8,761 lines

---

## Phase 2: Remove Old Service Files (4 files)

### Old Services: `app/services/`

```bash
cd /Users/ygahlot/mac-one-Personal-projects/runnersParadise/glycogrit-backend/app/services

# Remove duplicated service files
rm activity_service.py        # → app/modules/activities/services/activity_service.py
rm user_service.py            # → app/modules/users/services/user_service.py
rm certificate_service.py     # → app/modules/certificates/services/certificate_service.py
rm fitness_tracker_service.py # → app/modules/fitness_trackers/services/fitness_tracker_service.py
```

**Total**: 4 files, ~5,383 lines

---

## Phase 3: Update main.py

Remove all old router imports and include only new DDD routers:

```python
# File: app/main.py

# ===== REMOVE THESE OLD IMPORTS =====
# from app.api import (
#     auth, activities, activity_progress, progress,
#     events, event_tiers, registrations, payments,
#     challenges, fitness_trackers, rewards,
#     statistics, certificates, gallery, webhooks,
#     strava, garmin, fitbit, wahoo, google_fit
# )

# ===== ADD THESE NEW IMPORTS =====
# Wave 1: Core
from app.modules.users.api.auth import router as auth_router
from app.modules.users.api.users import router as users_router
from app.modules.activities.api.activities import router as activities_router
from app.modules.activities.api.progress import router as progress_router
from app.modules.registrations import registrations_router

# Wave 2: Integrations
from app.modules.fitness_trackers.api.fitness_trackers import router as fitness_trackers_router

# Wave 3: Engagement
from app.modules.certificates.api.certificates import router as certificates_router
from app.modules.rewards import rewards_router
from app.modules.challenges import challenges_router

# Wave 4: Supporting
from app.modules.statistics.api.statistics import router as statistics_router
from app.modules.gallery import gallery_router
from app.modules.payments.api.routes import router as payments_router
from app.modules.events import events_router
from app.modules.webhooks import webhooks_router

# ===== INCLUDE NEW ROUTERS =====
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(activities_router)
app.include_router(progress_router)
app.include_router(registrations_router)
app.include_router(fitness_trackers_router)
app.include_router(certificates_router)
app.include_router(rewards_router)
app.include_router(challenges_router)
app.include_router(statistics_router)
app.include_router(gallery_router)
app.include_router(payments_router)
app.include_router(events_router)
app.include_router(webhooks_router)
```

---

## Phase 4: Clean Up Empty Directories

```bash
# If app/api/ is empty, remove it
rmdir app/api/ 2>/dev/null || echo "Directory not empty or doesn't exist"
```

---

## Execution Script

Create this script to execute the cleanup:

```bash
#!/bin/bash
# File: cleanup_old_code.sh

set -e  # Exit on error

echo "🧹 Starting old code cleanup..."

# Backup first
echo "📦 Creating backup..."
cd /Users/ygahlot/mac-one-Personal-projects/runnersParadise
tar -czf glycogrit-backend-backup-$(date +%Y%m%d-%H%M%S).tar.gz glycogrit-backend/

# Phase 1: Remove old API files
echo "🗑️  Phase 1: Removing old API files..."
cd glycogrit-backend/app/api
rm -f activities.py activity_progress.py progress.py auth.py
rm -f challenges.py rewards.py events.py event_tiers.py
rm -f registrations.py certificates.py gallery.py statistics.py
rm -f payments.py webhooks.py webhooks_v2.py
rm -f fitness_trackers.py strava.py garmin.py fitbit.py google_fit.py wahoo.py
rm -f base.py
rm -rf __pycache__

echo "✅ Removed old API files"

# Phase 2: Remove old service files
echo "🗑️  Phase 2: Removing old service files..."
cd ../services
rm -f activity_service.py user_service.py certificate_service.py fitness_tracker_service.py

echo "✅ Removed old service files"

# Phase 3: Remove empty api directory
echo "🗑️  Phase 3: Cleaning up empty directories..."
cd ..
rmdir api 2>/dev/null && echo "✅ Removed empty api/ directory" || echo "⚠️  api/ directory not empty or doesn't exist"

echo "✨ Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Update main.py with new router imports"
echo "2. Run tests: pytest"
echo "3. Start server: uvicorn app.main:app --reload"
echo "4. Test all endpoints at http://localhost:8000/docs"
```

Make it executable:
```bash
chmod +x cleanup_old_code.sh
```

---

## Safety Checklist

Before running cleanup:

- [ ] Create backup (done automatically by script)
- [ ] Ensure new APIs are tested and working
- [ ] Update main.py with new router imports
- [ ] Commit current state to git
- [ ] Have rollback plan ready

---

## Verification After Cleanup

```bash
# 1. Check file counts
find app/modules -name "*.py" | wc -l   # Should be ~262
find app/api -name "*.py" 2>/dev/null | wc -l  # Should be 0 or directory gone

# 2. Check imports
grep -r "from app.api" app/ | grep -v ".pyc" | grep -v "__pycache__"
# Should return no results (or only comments)

# 3. Start server
uvicorn app.main:app --reload
# Should start without import errors

# 4. Check endpoints
curl http://localhost:8000/docs
# Should show all new DDD endpoints
```

---

## Expected Results

### Before Cleanup
- Total files: 271
- API files: 23 (old) + 14 (new) = 37
- Lines of code: ~55,128

### After Cleanup
- Total files: ~235 (-36 files)
- API files: 14 (new only)
- Lines of code: ~40,000 (-15,128 lines)
- Reduction: ~27% smaller codebase

---

## Rollback Plan

If issues occur:

```bash
# Restore from backup
cd /Users/ygahlot/mac-one-Personal-projects/runnersParadise
tar -xzf glycogrit-backend-backup-YYYYMMDD-HHMMSS.tar.gz

# Or use git
cd glycogrit-backend
git checkout app/api/
git checkout app/services/
```

---

**Status**: Ready to execute after testing
**Risk**: Low (backup created automatically)
**Impact**: 27% reduction in codebase size
