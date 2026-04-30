# Schema Cleanup Plan - Removing Redundant Calculated Fields

## Summary
The `user_challenge_progress` table stores many redundant/calculated fields that should be dynamic or stored elsewhere.

## Immediate Actions Needed

### 1. Convert Calculated Fields to Properties
These fields should be calculated dynamically, NOT stored:
- ❌ `progress_percentage` → Should be `@property`
- ❌ `is_completed` → Should be `@property`
- ❌ `completion_status` → Should be `@property`

### 2. Remove Duplicate Fields
These already exist in `activity_progress`:
- ❌ `total_distance_km` = `activity_progress.distance_completed`
- ❌ `goal_distance_km` = `activity_progress.target_distance`

### 3. Move to Correct Table
- `total_activities` → COUNT from `user_activity_logs`
- `total_duration_minutes` → SUM from `user_activity_logs`
- ✅ `proof_image_url` → Should be in `activity_progress`

## The Real Problem

**You're seeing cached/old data because:**
1. ✅ Backend code is correct (relationship fixed)
2. ⏳ Railway hasn't deployed the fix yet
3. 🔄 Browser showing cached frontend

**Once deployed, the new endpoint will work:**
- GET `/api/v1/activity-progress/event/27/my-progress`
- Returns activity_progress data with dynamic fields
- No more hardcoded 50 km!
