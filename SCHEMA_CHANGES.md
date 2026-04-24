# Database Schema Changes

## Challenge Tracking Enhancement - 2026-04-24

### Events Table
Added columns to support challenge lifecycle management:

```sql
ALTER TABLE events ADD COLUMN auto_started_at TIMESTAMP;
ALTER TABLE events ADD COLUMN auto_completed_at TIMESTAMP;
ALTER TABLE events ADD COLUMN sync_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE events ADD COLUMN completion_criteria JSONB;
```

**Purpose:**
- `auto_started_at`: Track when challenge was automatically started
- `auto_completed_at`: Track when challenge was automatically completed
- `sync_enabled`: Enable/disable automatic activity sync for the challenge
- `completion_criteria`: Store challenge completion rules (min_distance_km, min_activities, min_days)

### User Challenge Progress Table
Added columns for completion tracking and evaluation:

```sql
ALTER TABLE user_challenge_progress ADD COLUMN completion_status VARCHAR(50);
ALTER TABLE user_challenge_progress ADD COLUMN completion_percentage INTEGER DEFAULT 0;
ALTER TABLE user_challenge_progress ADD COLUMN evaluation_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE user_challenge_progress ADD COLUMN badge_earned VARCHAR(100);
ALTER TABLE user_challenge_progress ADD COLUMN last_activity_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE user_challenge_progress ADD COLUMN current_streak_days INTEGER DEFAULT 0;
```

**Purpose:**
- `completion_status`: Track challenge outcome (failed, completed, exceeded, outstanding)
- `completion_percentage`: Percentage of goal achieved
- `evaluation_date`: When the challenge was evaluated
- `badge_earned`: Badge awarded for challenge completion
- `last_activity_date`: Date of user's last activity in this challenge
- `current_streak_days`: Current consecutive days of activity

## Migration Notes

These schema changes were applied directly to the database using Python scripts.
For future deployments, these changes should be converted to proper Alembic migrations.

To create Alembic migrations:

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Add challenge tracking columns"

# Apply migration
alembic upgrade head
```

## Related Models

- `app/models/event.py` - Event model with challenge tracking fields
- `app/models/strava_connection.py` - UserChallengeProgress model
- `app/models/user.py` - User model with fitness_trackers relationship
