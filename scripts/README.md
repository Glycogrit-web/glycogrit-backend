# Sample Events Scripts

This directory contains scripts to populate the database with sample events/challenges for testing and demonstration purposes.

## 📁 Available Scripts

### 1. `insert_sample_events_fixed.sql` ⭐ **RECOMMENDED** ✅
**SQL script for Railway PostgreSQL console - FIXED VERSION**

The easiest way to add sample data to your Railway database. This is the **FIXED VERSION** that includes all required database fields.

**How to use:**
1. Go to Railway Dashboard → Your Project → PostgreSQL
2. Click on "Data" or "Query" tab
3. Copy and paste the contents of `insert_sample_events_fixed.sql`
4. Click "Execute" or "Run"
5. Verify: You should see 8 new events added

**⚠️ Important:** The original `insert_sample_events.sql` was missing required fields (event_date, registration_start_date, registration_end_date, location_name, city, state, country, organizer_id). **Use `insert_sample_events_fixed.sql` instead!**

**What it creates:**
- 8 diverse sample events with varying:
  - Event types: running, cycling, marathon, mixed
  - Difficulty levels: beginner, intermediate, advanced
  - Price points: free and paid events
  - Locations: virtual and in-person events
  - Durations: 1 day to 12 weeks

---

### 2. `add_events_via_api.py`
**Python script using REST API (no database drivers needed)**

Uses the Railway backend API to create events. Requires admin credentials.

**Requirements:**
```bash
pip install requests
```

**How to use:**
```bash
# Update the script with your admin credentials if different
python scripts/add_events_via_api.py
```

**Configuration:**
- `API_BASE_URL`: Railway backend URL (currently set to production)
- `ADMIN_EMAIL`: Admin user email (default: admin@glycogrit.com)
- `ADMIN_PASSWORD`: Admin user password (default: admin123)

**Note:** This requires a CREATE endpoint for events to be added to the API.

---

### 3. `add_sample_events.py`
**Python script for direct database seeding**

Directly inserts data into the database using SQLAlchemy.

**Requirements:**
```bash
pip install psycopg2-binary sqlalchemy
```

**How to use:**
```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Run the script
python scripts/add_sample_events.py
```

**Note:** This won't work locally without the Railway database credentials.

---

## 📊 Sample Events Created

All scripts create the same 8 events:

1. **30-Day Running Challenge** (Running, Beginner, Free)
   - Virtual, 30 days, Build running habit

2. **Mumbai Half Marathon Training** (Marathon, Intermediate, ₹1,500)
   - In-person, 12 weeks, Half marathon prep

3. **Cycling Century Challenge** (Cycling, Advanced, ₹500)
   - Virtual, 1 day, 100km ride

4. **5K for Beginners** (Running, Beginner, Free)
   - Virtual, 8 weeks, Couch to 5K

5. **Delhi 10K Trail Run** (Running, Intermediate, ₹800)
   - In-person, 1 day, Trail running

6. **Ultimate Fitness Challenge** (Mixed, Advanced, ₹2,000)
   - Virtual, 6 weeks, Multi-sport

7. **Bangalore Night Riders - 50K** (Cycling, Intermediate, ₹600)
   - In-person, 1 day, Night cycling

8. **21-Day Yoga & Run Combo** (Mixed, Beginner, ₹500)
   - Virtual, 21 days, Wellness focused

---

## ✅ Verification

After running any script, verify the data was added:

**Via API:**
```bash
curl https://web-production-188d1.up.railway.app/api/v1/events?limit=100
```

**Via SQL:**
```sql
SELECT COUNT(*) as total_events FROM events;
SELECT name, event_type, difficulty_level, registration_fee FROM events ORDER BY created_at DESC;
```

**Expected Result:**
- Total events: 9 (1 existing + 8 new)
- All events should have proper difficulty_level, goals, rewards, and rules

---

## 🎯 Next Steps

After adding sample events:

1. **Test Frontend:**
   - Visit http://localhost:5174/challenges (local)
   - Or visit your Vercel deployment
   - You should see 9 challenges displayed

2. **Test Filters:**
   - Filter by category (Running, Cycling, Marathon, Mixed)
   - Filter by difficulty (Beginner, Intermediate, Advanced)
   - Click on individual challenges to view details

3. **Test API:**
   - GET /api/v1/events?category=running
   - GET /api/v1/events?difficulty=beginner
   - GET /api/v1/events/2 (or any event ID)

---

## 🔧 Troubleshooting

**Script shows "already exists":**
- Events with the same slug already exist
- This is safe - the script skips duplicates

**Connection error:**
- Verify DATABASE_URL is correct
- Check Railway database is running
- Ensure you have network access

**Permission denied:**
- Check admin credentials are correct
- Verify user has permission to create events

---

## 📝 Notes

- All scripts use `ON CONFLICT DO NOTHING` to prevent duplicates
- Event slugs are unique - running scripts multiple times is safe
- Dates are relative to CURRENT_DATE for realistic data
- All events have proper JSONB fields for goals and rewards
