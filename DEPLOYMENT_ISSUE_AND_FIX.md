# Deployment Issue & Next Steps

## Current Problem

You're still seeing: "Complete 50 km..." and getting a 500 error from:
```
GET /api/v1/activity-progress/event/27/my-progress
```

## Why This Is Happening

### 1. Railway Hasn't Deployed Yet
- Commits are pushed: ✅ `7c0fddb` and `ed81c02`
- Railway deployment: ❌ NOT YET DEPLOYED
- Check Railway dashboard: https://railway.app

**The 500 error happens because:**
- Railway is still running the old code (without the relationship fix)
- When backend tries `joinedload(ActivityProgress.activity)`, it fails
- Frontend falls back to old `user_challenge_progress` table showing "50 km"

### 2. You're Right About progress_percentage!
Currently it's stored in the database:
```python
progress_percentage = Column(Numeric(5, 2))  # ❌ Can get stale
```

It SHOULD be calculated dynamically:
```python
@property
def progress_percentage(self) -> float:
    return (self.distance_completed / self.target_distance) * 100  # ✅ Always fresh
```

## Immediate Actions

### Option 1: Wait for Railway (Recommended)
1. Check Railway dashboard
2. Verify it's deploying commit `ed81c02`
3. Wait for deployment to complete (usually 2-5 minutes)
4. Hard refresh browser

### Option 2: Manual Railway Deploy (If stuck)
If Railway isn't auto-deploying:
1. Go to Railway dashboard
2. Click "Deploy" or "Redeploy"
3. Check deployment logs for errors

### Option 3: Check Railway Logs
```bash
# If you have Railway CLI
railway logs
```

Look for:
- Migration errors
- Python import errors
- SQLAlchemy relationship errors

## The Fix for Calculated Fields

Since you're right that `progress_percentage` should be calculated, here's what we should do:

### Step 1: Make progress_percentage a @property
```python
# In app/models/activity_progress.py

# Remove this line (or keep for backward compat):
# progress_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)

# Add this property:
@property
def progress_percentage_calculated(self) -> float:
    """Calculate progress percentage dynamically"""
    if not self.target_distance or self.target_distance == 0:
        return 0.0
    return min(float(self.distance_completed / self.target_distance * 100), 100.0)

@property
def is_completed_calculated(self) -> bool:
    """Check if completed dynamically"""
    return self.progress_percentage_calculated >= 100.0
```

### Step 2: Update API to Use Calculated Values
```python
# In app/api/activity_progress.py
progress_dict = {
    **{k: v for k, v in progress.__dict__.items() if not k.startswith('_')},
    "progress_display": progress.progress_display,
    "remaining_distance": progress.remaining_distance,
    "progress_percentage": progress.progress_percentage_calculated,  # ← Use property
    "is_completed": progress.is_completed_calculated,  # ← Use property
    "activity_name": progress.activity.name if progress.activity else None,
    "activity_type": progress.activity.activity_type if progress.activity else None,
    "activity_distance": progress.activity.distance if progress.activity else None,
}
```

## Why You're Seeing "Complete 50 km"

The frontend is falling back to `user_challenge_progress` table because:
1. New API endpoint returns 500 error
2. Frontend catches error and uses old progress
3. Old table has hardcoded 50 km goal

```typescript
// In ChallengeProgressPage.tsx
const displayProgress = activityProgress ? {
    // ✅ Uses new data (21.1 km)
    goal_distance_km: activityProgress.activity_distance
} : {
    // ❌ Falls back to old data (50 km hardcoded)
    goal_distance_km: progress?.goal_distance_km || 50
};
```

## Verification Steps

### 1. Check Railway Deployment
Go to Railway dashboard and verify:
- Latest commit deployed: `ed81c02`
- Build status: Success
- Deployment status: Live
- No error logs

### 2. Test the Endpoint Directly
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://web-production-188d1.up.railway.app/api/v1/activity-progress/event/27/my-progress
```

**Expected (after deployment):**
```json
{
  "distance_completed": 7.0,
  "target_distance": 21.1,
  "progress_percentage": 33.2,
  "activity_distance": 21.1,
  "activity_name": "Total Distance (Half Marathon)"
}
```

**Currently getting:**
```
500 Internal Server Error
```

### 3. Check Migrations Ran
```sql
-- Check if new columns exist
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'activity_progress' 
AND column_name IN ('proof_image_url', 'total_activities', 'total_duration_minutes');
```

## Timeline

**What's deployed:** Old code (before `7c0fddb`)
**What's pushed:** Commits `7c0fddb` + `ed81c02`
**What Railway needs to do:**
1. Pull latest code from master
2. Run `pip install -r requirements.txt`
3. Run `alembic upgrade head` (migrations)
4. Restart the service

**ETA:** Usually 2-5 minutes, but can take up to 15 minutes if Railway is busy

## Manual Deployment (If Needed)

If Railway is stuck, you can manually trigger:

### Via Railway CLI:
```bash
railway up
```

### Via Railway Dashboard:
1. Go to project
2. Click "Deployments"
3. Click "Deploy" on latest commit
4. Watch logs for errors

## Summary

**The Issue:** Railway hasn't deployed the fixes yet
**The Error:** 500 error because relationship doesn't exist in deployed code
**The Fallback:** Frontend uses old table with 50 km hardcoded
**The Fix:** Wait for Railway to deploy OR manually trigger deployment

**Your Observation:** Correct! `progress_percentage` should be calculated, not stored. We can fix this in the next update after deployment works.
