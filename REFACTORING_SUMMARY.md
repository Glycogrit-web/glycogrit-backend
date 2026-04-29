# Activity Structure Refactoring Summary

## Overview
Major refactoring to simplify and clarify the activity/category structure for event registration.

## Key Changes

### 1. Database Schema Changes (Migration: 20260430_0350_3451509c9ce5)

**Tables Renamed:**
- `event_categories` → `event_activities` (represents selectable activities like "5K Run", "10K Cycle")
- `event_activities` → `user_activity_logs` (tracks daily user activity submissions)

**Tables Dropped:**
- `event_activity_types` (redundant - activity type now in event_activities)

**Columns Added:**
- `event_activities.activity_type` (VARCHAR(50)) - stores "running", "cycling", "walking", etc.
- `registrations.event_activity_id` (INT, FK to event_activities) - replaces event_category_id

**Columns Removed:**
- `events.event_type` (no longer needed - events support multiple activity types through event_activities)
- `registrations.event_category_id` (renamed to event_activity_id)

### 2. Model Changes

**app/models/event.py:**
- Removed `event_type` field from Event model
- Renamed `EventCategory` class → `EventActivity`
- Updated relationship: `categories` → `activities`
- Removed `activity_types` relationship (EventActivityType removed)
- Added `activity_type` field to EventActivity model

**app/models/registration.py:**
- Changed `event_category_id` → `event_activity_id`
- Updated relationship: `category` → `activity`

**app/models/activity.py → user_activity_log.py:**
- Renamed file and class
- `EventActivity` → `UserActivityLog`
- Updated table name: `event_activities` → `user_activity_logs`

**app/models/event_activity_type.py:**
- File deleted (model removed)

**app/models/__init__.py:**
- Updated imports to reflect new model names

### 3. Repository Changes

**app/repositories/event_repository.py:**
- `EventCategoryRepository` → `EventActivityRepository`
- Updated all method signatures and queries
- Removed `get_events_by_type()` method (event_type no longer exists)
- Updated filters in `get_events_with_filters()`
- Added `get_activities_by_type()` method

### 4. API Changes Needed

**app/api/events.py:**
Need to update:
- Line 69: `Event.event_type == category` (remove event_type filter or replace logic)
- Line 365-516: All category endpoints → activity endpoints
  - `get_event_categories` → `get_event_activities`
  - `create_event_category` → `create_event_activity`
  - `update_event_category` → `update_event_activity`
  - `delete_event_category` → `delete_event_activity`
- Update `CategoryResponse` → `ActivityResponse` schema
- Update all references to EventCategoryRepository → EventActivityRepository

**app/api/registrations.py:**
Need to update:
- Change `event_category_id` → `event_activity_id` in request/response schemas
- Update registration creation logic to use event_activity_id
- Update validation logic

**app/api/activities.py:**
- May need to check if this file deals with user_activity_logs (renamed from event_activities)

### 5. Pydantic Schema Changes

Create/Update these schemas:
```python
class ActivityResponse(BaseModel):
    id: int
    event_id: int
    name: str  # "5K Run", "10K Cycle"
    activity_type: Optional[str]  # "running", "cycling"
    distance: Optional[float]
    description: Optional[str]
    max_participants: Optional[int]
    current_participants: int
    registration_fee: Optional[float]
    created_at: datetime

class ActivityCreate(BaseModel):
    name: str
    activity_type: str  # required: "running", "cycling", "walking", etc.
    distance: Optional[float]
    description: Optional[str]
    max_participants: Optional[int]
    registration_fee: Optional[float]

class RegistrationCreate(BaseModel):
    event_id: int
    event_activity_id: int  # REQUIRED - user must select an activity
    tier_id: Optional[int]
    # ... other fields
```

### 6. Frontend Changes Needed

**Types/Interfaces:**
```typescript
// src/types/challenge.ts or event.ts
interface EventActivity {
  id: number;
  event_id: number;
  name: string;  // "5K Run", "10K Cycle"
  activity_type: string;  // "running", "cycling"
  distance?: number;
  description?: string;
  max_participants?: number;
  current_participants: number;
  registration_fee?: number;
}

interface Event {
  id: number;
  name: string;
  // ... other fields
  // REMOVED: event_type
  activities: EventActivity[];  // renamed from categories
}

interface Registration {
  // ... other fields
  event_activity_id: number;  // renamed from event_category_id
  activity?: EventActivity;  // renamed from category
}
```

**Components to Update:**
1. **EventCheckout.tsx** - Add activity selection UI (like in the image)
   - Show all available activities for the event
   - Make it required to select one activity
   - Display activity type icon (run/cycle/walk)
   - Show distance and price

2. **ChallengeCard.tsx** / **EventCard.tsx**
   - Remove references to `event.event_type`
   - Show available activities instead

3. **ChallengeDetail.tsx** / **EventDetail.tsx**
   - Update to show `activities` instead of `categories`
   - Remove event_type display

4. **Filters/Search components**
   - Remove event_type filter
   - Add activity_type filter based on activities

**API Client:**
```typescript
// src/lib/api-client.ts
async getEventActivities(eventId: string): Promise<EventActivity[]>
async createEventActivity(eventId: string, data: ActivityCreate): Promise<EventActivity>
async updateEventActivity(activityId: string, data: ActivityUpdate): Promise<EventActivity>
async deleteEventActivity(activityId: string): Promise<void>
```

### 7. Migration Steps

**To apply migration:**
```bash
cd glycogrit-backend
alembic upgrade head
```

**To rollback (if needed):**
```bash
alembic downgrade -1
```

### 8. Testing Checklist

- [ ] Run migration successfully
- [ ] Verify tables renamed correctly
- [ ] Test event creation with activities
- [ ] Test registration with activity selection
- [ ] Verify existing registrations migrated correctly
- [ ] Test frontend activity selection in checkout
- [ ] Test API endpoints for activities CRUD
- [ ] Verify progress tracking still works
- [ ] Test leaderboard functionality
- [ ] Verify admin can see all participants with activities

### 9. Database Validation Queries

After migration, run these to verify:
```sql
-- Check table rename successful
SELECT COUNT(*) FROM event_activities;
SELECT COUNT(*) FROM user_activity_logs;

-- Check activity_type column added
SELECT id, name, activity_type, distance FROM event_activities LIMIT 10;

-- Check registrations migrated
SELECT id, event_activity_id FROM registrations WHERE event_activity_id IS NOT NULL LIMIT 10;

-- Check event_type removed
\d events  -- should not show event_type column

-- Verify foreign keys
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE table_name = 'registrations' AND column_name = 'event_activity_id';
```

### 10. Next Steps

1. ✅ Migration created
2. ✅ Models updated
3. ✅ Repositories updated
4. ⏳ Update API endpoints (events.py, registrations.py)
5. ⏳ Update Pydantic schemas
6. ⏳ Update frontend types
7. ⏳ Update EventCheckout component
8. ⏳ Update other frontend components
9. ⏳ Run migration
10. ⏳ Test all flows

## Breaking Changes

This is a **BREAKING CHANGE**. All clients must be updated to:
1. Send `event_activity_id` instead of `event_category_id` during registration
2. Remove `event_type` from event creation/update
3. Use `activities` instead of `categories` when fetching event details
4. Display activity selection UI during registration

## Notes

- The `activity_type` field in `event_activities` allows filtering/grouping (e.g., show all running activities)
- Each event can have multiple activities with different types (e.g., "5K Run" + "5K Cycle")
- Users MUST select an activity when registering
- The activity determines the distance goal for that user's registration
- User progress tracking should use the selected activity's distance as the goal
