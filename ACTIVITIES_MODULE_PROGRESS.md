# Activities Module Migration - IN PROGRESS

**Date:** 2026-05-21
**Status:** Wave 1 (Activities Module) - 30% COMPLETE
**Dependencies:** Users Module ✅

---

## Progress Summary

### ✅ Completed (30%)
1. **Module Structure** - Created directory hierarchy
2. **Value Objects** - 7 value objects created with business rules
3. **Models Migrated** - UserActivityLog and ActivityProgress models

### 🔄 In Progress
- Entity layer (ActivityEntity, ProgressEntity)

### ⏳ Remaining (70%)
- Repository layer
- CQRS commands/queries
- Service layer
- Schemas layer
- API layer
- Integration & testing

---

## Files Created (5 files)

### Module Structure
1. `app/modules/activities/__init__.py` - Module exports
2. `app/modules/activities/domain/__init__.py` - Domain exports

### Domain Layer (3 files created)
3. **value_objects.py** (365 lines) - 7 value objects:
   - `Distance` - Kilometers with conversions, arithmetic operations
   - `Duration` - Minutes with hour/second conversions
   - `ActivityDate` - Date validation (not in future, reasonable range)
   - `ProgressPercentage` - 0-100% validation
   - `Pace` - min/km calculation from distance/duration
   - `ActivityType` - Enum (run, ride, walk, swim, other)
   - `SyncSource` - Enum (manual, strava, garmin, etc.)

4. **activity_log.py** (41 lines) - UserActivityLog SQLAlchemy model
5. **activity_progress.py** (148 lines) - ActivityProgress SQLAlchemy model with highest-wins logic

---

## Value Objects - Business Rules

### Distance
- ✅ Non-negative validation
- ✅ 2 decimal places precision
- ✅ Arithmetic operations (+, -, comparisons)
- ✅ Conversions (miles, meters)
- ✅ Factory methods (from_miles, from_meters, zero)

### Duration
- ✅ Non-negative validation
- ✅ Stored in minutes
- ✅ Conversions (hours, seconds)
- ✅ Addition operation
- ✅ Human-readable format (2h 30m)

### ActivityDate
- ✅ Cannot be in future
- ✅ Not more than 10 years in past
- ✅ Comparison operations
- ✅ Helper methods (is_today, days_ago)

### ProgressPercentage
- ✅ 0-100% validation
- ✅ 1 decimal place precision
- ✅ is_complete() check
- ✅ Calculate from distances

### Pace
- ✅ Positive validation
- ✅ Calculated from distance/duration
- ✅ Format as min:sec/km
- ✅ Speed in km/h property

---

## Domain Models

### UserActivityLog
- Tracks daily activity submissions
- Fields: distance, duration, activity_date, notes
- Relations: User, Event, Registration
- Use case: User manually logs activities

### ActivityProgress
- Tracks progress toward event goal
- Fields: distance_completed, target_distance, sync_source
- **Highest-Wins Logic**: distance_by_source JSONB tracking
- Relations: User, Registration, Event, EventActivity
- Hybrid properties: progress_percentage, is_completed
- Use case: Aggregate progress from multiple sources

---

## Next Steps

### Immediate (Current Session)
1. [ ] Create ActivityEntity with business rules
2. [ ] Create ProgressEntity with highest-wins logic
3. [ ] Create ActivityRepository
4. [ ] Create ProgressRepository

### Short-term (Next Session)
5. [ ] Create CQRS commands (Submit, Update, Delete, Sync)
6. [ ] Create CQRS queries (GetActivities, GetProgress)
7. [ ] Create ActivityService
8. [ ] Create ProgressService

### Medium-term
9. [ ] Create FileParserService (GPX, TCX, FIT)
10. [ ] Create SyncService for fitness trackers
11. [ ] Create ValidationService for highest-wins
12. [ ] Create Pydantic schemas
13. [ ] Create API endpoints
14. [ ] Integration & testing

---

## Architecture Pattern

Following same DDD pattern as Users Module:

```
app/modules/activities/
├── domain/              # ✅ 30% Complete
│   ├── __init__.py
│   ├── value_objects.py      # ✅ Complete
│   ├── activity_log.py        # ✅ Complete
│   ├── activity_progress.py   # ✅ Complete
│   ├── entities.py            # ⏳ TODO
│
├── repositories/        # ⏳ Not started
│   ├── __init__.py
│   ├── activity_repository.py
│   └── progress_repository.py
│
├── services/            # ⏳ Not started
│   ├── __init__.py
│   ├── commands.py
│   ├── queries.py
│   ├── activity_service.py
│   ├── progress_service.py
│   ├── file_parser_service.py
│   ├── sync_service.py
│   └── validation_service.py
│
├── schemas/             # ⏳ Not started
│   ├── __init__.py
│   ├── activity.py
│   └── progress.py
│
└── api/                 # ⏳ Not started
    ├── __init__.py
    ├── activities.py
    └── progress.py
```

---

## Estimated Work Remaining

| Component | Files | Est. Lines | Status |
|-----------|-------|------------|---------|
| Domain Entities | 1 | 300 | TODO |
| Repositories | 2 | 400 | TODO |
| CQRS Commands/Queries | 2 | 250 | TODO |
| Services | 5 | 1,200 | TODO |
| Schemas | 2 | 200 | TODO |
| API | 2 | 500 | TODO |
| **Total Remaining** | **14** | **~2,850** | **70%** |

---

## Key Features to Implement

### Activity Management
- Submit activity (manual entry)
- Update activity
- Delete activity
- List activities (pagination, filtering)
- Activity statistics

### Progress Tracking
- Get progress for registration
- Update progress (highest-wins logic)
- Calculate progress percentage
- Track completion
- Proof image upload

### File Parsing
- Parse GPX files
- Parse TCX files
- Parse FIT files
- Extract distance, duration, date
- Validate file format

### Sync Integration
- Sync from Strava
- Sync from Garmin
- Sync from Fitbit
- Sync from Wahoo
- Highest-wins conflict resolution

### Validation
- Validate activity data
- Check duplicate activities
- Enforce event date ranges
- Validate distance/duration
- Apply highest-wins logic

---

## Business Rules to Implement

### Activity Submission
1. Activity date cannot be in future
2. Activity must be within event date range
3. User must have active registration
4. Distance and duration must be non-negative
5. Duplicate prevention (same date, user, event)

### Progress Tracking
1. Progress cannot exceed 100%
2. Highest distance wins (conflict resolution)
3. Track source of winning distance
4. Auto-complete when target reached
5. Maintain history by source

### Sync Logic
1. Each source tracks own distance
2. Highest value becomes active distance
3. Store metadata per source
4. Track sync timestamps
5. Handle source disconnection

---

## Dependencies

### Internal
- Users Module ✅ (for user_id)
- Events Module ⏳ (for event_id, EventActivity)
- Registrations Module ⏳ (for registration_id)

### External
- Fitness tracker integrations (Wave 2)
- File parsers (gpxpy, fitparse)
- Storage service (Cloudflare R2)

---

## Comparison with Users Module

| Metric | Users | Activities |
|--------|-------|------------|
| Complexity | Medium | High |
| Value Objects | 5 | 7 |
| Models | 1 | 2 |
| Entities | 1 | 2 |
| Services | 2 | 5 |
| External Deps | OAuth | File parsers, sync |
| Est. Total Lines | 2,500 | 3,200 |

Activities module is more complex due to:
- Multiple data sources (manual, sync)
- File parsing logic
- Highest-wins conflict resolution
- Progress calculations
- More complex business rules

---

## Token Usage Summary

**Current Session:**
- Started: 200,000 tokens
- Used: ~75,000 tokens
- Remaining: ~125,000 tokens
- Files Created: 5
- Lines Written: ~554

**Estimated for Completion:**
- Remaining Work: ~2,850 lines
- Est. Tokens: ~50,000-60,000
- Sessions Needed: 1-2 more

---

## Next Actions

**Option 1: Continue Now** (Recommended if <50K tokens)
- Create entities
- Create repositories
- Start on services

**Option 2: Resume Next Session**
- Save progress
- Document learnings
- Plan next session tasks

**Current Recommendation:** Continue with entities and repositories in this session, defer services/API to next session.

---

**Last Updated:** 2026-05-21
**Next Milestone:** Complete domain & repository layers
**Overall Migration Progress:** 12% (Users complete + Activities 30%)
