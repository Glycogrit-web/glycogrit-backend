# Database Schema & Data Flow Explanation

## Overview
This document clarifies the purpose of each table and how data flows through the system for activity tracking.

## Table Purposes

### 1. `event_activities` (EventActivity model)
**Purpose:** Defines WHAT activities are available for an event
- Example records: "5K Run", "10K Run", "Half Marathon (21.1 km)"
- Contains: activity name, type, distance, max participants
- Created by: Event organizers when setting up an event
- **This is the TEMPLATE/DEFINITION** - not user progress

### 2. `activity_progress` (ActivityProgress model)
**Purpose:** Tracks EACH USER'S progress for THEIR CHOSEN activity
- One record per registration (1 user + 1 event + 1 activity choice)
- Contains: 
  - `target_distance`: Copied from event_activities.distance at registration
  - `distance_completed`: Aggregated from user_activity_logs
  - `progress_percentage`: CALCULATED dynamically (distance_completed / target_distance * 100)
  - `is_completed`: CALCULATED dynamically (progress_percentage >= 100)
- Updated by: Auto-sync from user_activity_logs when activities are logged

**Key Fields Explained:**
- ✅ `target_distance`: Static value copied from event_activities at registration time
- ✅ `distance_completed`: Aggregated sum from user_activity_logs
- ✅ `progress_percentage`: CALCULATED field (could be @property)
- ✅ `is_completed`: CALCULATED field (could be @property)

### 3. `user_activity_logs` (UserActivityLog model)
**Purpose:** Stores INDIVIDUAL activity entries (runs, walks, cycles)
- Example: "User ran 3.5 km on 2026-04-29"
- Contains: date, distance, duration, activity type, proof images
- Created by: Users logging activities manually OR synced from Strava/Garmin
- **This is the RAW DATA** - individual entries

**Data Flow:**
```
User logs activity → user_activity_logs (new record)
                   ↓
            Trigger update on activity_progress
                   ↓
            Sum all user_activity_logs for this event
                   ↓
            Update distance_completed in activity_progress
                   ↓
            Recalculate progress_percentage and is_completed
```

### 4. `user_challenge_progress` (UserChallengeProgress model)
**Purpose:** LEGACY/DEPRECATED - Was used before activity_progress system
- Contains aggregated stats: total_distance_km, total_activities, streaks
- **Should be phased out** in favor of activity_progress
- Current status: Still used for Strava sync and proof uploads

**⚠️ REDUNDANCY ISSUE:** This table duplicates data from activity_progress

**Recommended Action:**
- Move proof_image_url to activity_progress
- Move Strava sync metadata to activity_progress
- Deprecate this table entirely

### 5. `challenge_activities` (ChallengeActivity model)
**Purpose:** Stores Strava-synced activities (DEPRECATED in favor of user_activity_logs)
- Was used to store activities pulled from Strava API
- Contains: Strava activity ID, distance, duration, elevation
- **⚠️ REDUNDANT** with user_activity_logs

**Recommended Action:**
- Migrate to user_activity_logs (which has source tracking)
- Deprecate this table

### 6. `user_goodies` (UserGoodie model)
**Purpose:** Tracks rewards/goodies earned by users
- Example: "User earned Bronze medal for completing 5K"
- Status: Currently UNUSED - reward system not yet implemented
- Future use: Will track badges, certificates, rewards

## Correct Data Flow

### Registration Flow:
```
1. User selects event activity (e.g., "Half Marathon - 21.1 km")
2. Registration record created with activity_id
3. ActivityProgress record AUTO-CREATED with:
   - target_distance = event_activities.distance (21.1)
   - distance_completed = 0
   - progress_percentage = 0
   - is_completed = False
```

### Activity Logging Flow:
```
1. User logs activity (manual or Strava sync)
2. UserActivityLog record created
3. ActivityProgress.distance_completed = SUM(user_activity_logs.distance) WHERE event_id AND user_id
4. ActivityProgress.progress_percentage = (distance_completed / target_distance) * 100
5. ActivityProgress.is_completed = progress_percentage >= 100
```

### Progress Display Flow:
```
Frontend → GET /api/v1/activity-progress/event/{event_id}/my-progress
         → Backend joins activity_progress with event_activities
         → Returns:
            - distance_completed (from activity_progress)
            - target_distance (from activity_progress, originally from event_activities)
            - activity_name (from event_activities via JOIN)
            - activity_distance (from event_activities - same as target_distance)
            - progress_percentage (CALCULATED)
            - is_completed (CALCULATED)
```

## Schema Cleanup Recommendations

### Immediate Actions:
1. ✅ **FIXED**: Add relationship between EventActivity and ActivityProgress
2. ⏳ **TODO**: Remove calculated fields from activity_progress table:
   - Make `progress_percentage` a @property instead of database field
   - Make `is_completed` a @property instead of database field
   - These should be calculated on-the-fly, not stored

### Phase 2 - Deprecate user_challenge_progress:
1. Move `proof_image_url` to activity_progress
2. Move `last_sync_source`, `last_sync_at` to activity_progress (already exists!)
3. Drop table after data migration

### Phase 3 - Deprecate challenge_activities:
1. All Strava activities should go into user_activity_logs with source='strava'
2. Migrate existing challenge_activities data
3. Drop table

## Field-by-Field Analysis

### activity_progress Table:

| Field | Purpose | Should Be | Notes |
|-------|---------|-----------|-------|
| `target_distance` | Goal distance | ✅ Stored | Static value from event_activities |
| `distance_completed` | Progress | ✅ Stored | Aggregated from user_activity_logs |
| `progress_percentage` | % complete | ❌ Remove | SHOULD BE @property: (distance_completed/target_distance)*100 |
| `is_completed` | Done? | ❌ Remove | SHOULD BE @property: progress_percentage >= 100 |
| `last_sync_at` | When synced | ✅ Stored | Metadata for sync tracking |
| `sync_source` | Where from | ✅ Stored | 'manual', 'strava', 'garmin' |

### user_challenge_progress Table (LEGACY):

| Field | Purpose | Redundant? | Notes |
|-------|---------|------------|-------|
| `total_distance_km` | Total distance | ✅ YES | Same as activity_progress.distance_completed |
| `total_activities` | Activity count | ✅ YES | COUNT(user_activity_logs) |
| `total_duration_minutes` | Total time | ⚠️ Maybe | Could be SUM(user_activity_logs.duration) |
| `goal_distance_km` | Target | ✅ YES | Same as activity_progress.target_distance |
| `progress_percentage` | % done | ✅ YES | Calculated field |
| `current_streak_days` | Streak | ⚠️ Complex | Requires date-based calculation |
| `completion_status` | Status | ✅ YES | Same as activity_progress.is_completed |
| `proof_image_url` | Proof pic | ❌ NO | Unique, should move to activity_progress |

## Summary

**Current Issues:**
1. ✅ **FIXED**: Missing relationship causing 500 error
2. ⚠️ **PENDING**: Redundancy between activity_progress and user_challenge_progress
3. ⚠️ **PENDING**: Calculated fields stored in database (should be @property)
4. ⚠️ **PENDING**: Two tables for activity logging (challenge_activities vs user_activity_logs)

**Correct Architecture:**
```
event_activities (TEMPLATES)
       ↓
activity_progress (USER PROGRESS - per registration)
       ↑
user_activity_logs (RAW DATA - individual activities)
```

**What to Remove:**
- `user_challenge_progress` → Merge into activity_progress
- `challenge_activities` → Merge into user_activity_logs
- Calculated fields in database → Convert to @property

**What to Keep:**
- `event_activities` - Activity definitions
- `activity_progress` - User progress tracking
- `user_activity_logs` - Individual activity entries
- `user_goodies` - Future reward system
