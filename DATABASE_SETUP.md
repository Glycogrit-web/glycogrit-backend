# Database Setup - Alembic Migrations

## What We Have

### SQLAlchemy Models
- **User** - Authentication and profile
- **Event** - Running/cycling events
- **EventCategory** - Distance categories (5K, 10K, etc.)
- **Registration** - Event sign-ups with BIB numbers
- **Payment** - Transaction records

### Alembic Setup
- **manage_db.py** - Convenient CLI for database operations
- **alembic/** - Migration files and configuration
- Models automatically generate migrations

## Quick Start - Deploy to Railway

### 1. Run Migration (Creates All Tables)

✅ **Migration file is already committed**, Railway just needs to apply it!

After deployment, simply run:
```bash
# Option A: Via API endpoint (easiest)
POST https://your-app.railway.app/api/v1/admin/run-migrations

# Option B: Via Railway shell
railway run alembic upgrade head
```

This will create all 5 tables automatically:
- users
- events
- event_categories
- registrations
- payments

### 2. Seed Test Data
```bash
POST https://your-app.railway.app/api/v1/admin/seed-data
```

This creates:
- Admin: admin@glycogrit.com / admin123
- Organizer: organizer@glycogrit.com / organizer123
- Users: john.doe@example.com / test123
- Sample event: Bangalore Marathon 2026

### 3. Verify
```bash
GET https://your-app.railway.app/api/v1/admin/db-tables
```

### 4. Clean Up

After setup, remove these endpoints from `app/main.py`:
- `/api/v1/admin/run-migrations`
- `/api/v1/admin/seed-data`
- `/api/v1/admin/db-tables`

## Local Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create initial migration
python manage_db.py migrate "initial tables"

# Apply migration
python manage_db.py upgrade

# Seed data
python manage_db.py seed
```

### Common Commands

```bash
# Create new migration (auto-generate from model changes)
python manage_db.py migrate "add column xyz"

# Apply all pending migrations
python manage_db.py upgrade

# Rollback last migration
python manage_db.py downgrade

# Show current migration
python manage_db.py current

# Show migration history
python manage_db.py history

# Reset database (⚠️ destroys all data)
python manage_db.py reset
```

## How Alembic Works

### 1. Make Model Changes

Edit models in `app/models/`:
```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    # ... add new fields here
```

### 2. Generate Migration

```bash
python manage_db.py migrate "description of changes"
```

Alembic will:
- Compare models with database
- Generate migration file in `alembic/versions/`
- Auto-detect: new tables, columns, indexes, constraints

### 3. Review Migration

Check the generated file in `alembic/versions/`:
```python
def upgrade():
    # SQL to apply changes
    op.add_column('users', sa.Column('new_field', ...))

def downgrade():
    # SQL to rollback changes
    op.drop_column('users', 'new_field')
```

### 4. Apply Migration

```bash
python manage_db.py upgrade
```

## Database Schema

### Current Tables

**users**
- Authentication (email, password_hash)
- Profile (name, city, state, country)
- Status (is_active, email_verified)

**events**
- Event details (name, description, type, status)
- Dates (event_date, registration dates)
- Location (city, state, country)
- Capacity (max_participants, current_participants)
- Pricing (registration_fee, currency)

**event_categories**
- Category details (name, distance)
- Capacity and pricing per category

**registrations**
- Registration details (registration_number, bib_number)
- Status (pending, confirmed, payment_completed)
- Participant info (name, age, gender, t_shirt_size)

**payments**
- Payment details (amount, currency, payment_method)
- Transaction info (transaction_id, gateway details)
- Status tracking (pending, completed, failed, refunded)

## Railway Deployment

### First Deploy

1. **Push code to Railway**
   ```bash
   git add .
   git commit -m "Add Alembic setup"
   git push origin master
   ```

2. **Wait for deployment**
   - Railway will auto-deploy
   - Install dependencies from requirements.txt

3. **Run migrations**
   ```bash
   # Via API endpoint
   POST https://your-app.railway.app/api/v1/admin/run-migrations

   # OR via Railway shell
   railway run alembic upgrade head
   ```

4. **Seed data (optional)**
   ```bash
   POST https://your-app.railway.app/api/v1/admin/seed-data
   ```

### Subsequent Deploys

When you add new tables/columns:

1. **Create migration locally**
   ```bash
   python manage_db.py migrate "add new feature"
   ```

2. **Commit migration file**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration for new feature"
   git push origin master
   ```

3. **Railway auto-deploys**
   - New code deployed
   - Migration file included

4. **Run migration on Railway**
   ```bash
   railway run alembic upgrade head
   ```

## Automatic Migrations on Deploy

To run migrations automatically when deploying to Railway:

Add to `Procfile`:
```
release: alembic upgrade head
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

⚠️ **Caution**: Automatic migrations can be risky. Better to run manually and verify.

## Troubleshooting

### Migration Conflicts

If Alembic says "Target database is not up to date":
```bash
# Check current version
python manage_db.py current

# Check what migrations exist
python manage_db.py history

# If stuck, stamp to specific version
alembic stamp head
```

### Reset Everything

```bash
python manage_db.py reset
```

This will:
- Drop all tables
- Recreate from models
- Seed test data

## Next Steps

1. ✅ Alembic configured
2. ✅ Core models created
3. ✅ Migration system ready
4. 🎯 Deploy to Railway
5. 🎯 Run initial migration
6. 🎯 Build authentication API
7. 🎯 Create event management endpoints

## Advanced Patterns

For async operations, caching, optimization, see:
`.claude/skills/database-patterns.md`
