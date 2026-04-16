# GlycoGrit API Endpoints

Base URL: `https://your-app.railway.app`

## Authentication Endpoints

### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe",
  "city": "Bangalore",
  "state": "Karnataka"
}

Response: 201 Created
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <token>

Response: 200 OK
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "city": "Bangalore",
  "state": "Karnataka",
  "is_active": true,
  "email_verified": false
}
```

## Event Endpoints

### List Events
```http
GET /api/v1/events?category=running&difficulty=beginner&page=1&limit=20

Query Parameters:
- category: running, cycling, walking, mixed, strength (optional)
- difficulty: beginner, intermediate, advanced (optional)
- status: upcoming, ongoing, completed (optional)
- is_virtual: true/false (optional)
- page: page number (default: 1)
- limit: items per page (default: 20, max: 100)

Response: 200 OK
{
  "events": [...],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

### Get Event Details
```http
GET /api/v1/events/{event_id}

Response: 200 OK
{
  "id": 1,
  "name": "Bangalore Marathon 2026",
  "slug": "bangalore-marathon-2026",
  "description": "Join us for...",
  "event_type": "running",
  "status": "upcoming",
  "start_date": "2026-06-15",
  "end_date": "2026-06-15",
  "difficulty_level": "advanced",
  "goals": ["Complete 42.195 km", "Finish under 4 hours"],
  "rewards": ["Finisher Medal", "Certificate"],
  "banner_image_url": "https://...",
  "rules": "Must be 18+ years old...",
  "current_participants": 0,
  "max_participants": 5000,
  "is_virtual": false,
  ...
}
```

### Register for Event
```http
POST /api/v1/events/{event_id}/register
Authorization: Bearer <token>
Content-Type: application/json

{
  "category_id": 1  // optional
}

Response: 201 Created
{
  "id": 1,
  "event_id": 1,
  "user_id": 1,
  "status": "confirmed",
  "registered_at": "2026-04-16T12:00:00"
}
```

### Cancel Registration
```http
DELETE /api/v1/registrations/{registration_id}
Authorization: Bearer <token>

Response: 204 No Content
```

### Get User's Events
```http
GET /api/v1/events/users/{user_id}/events?page=1&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "events": [...],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

## Activity Tracking Endpoints

### Submit Activity
```http
POST /api/v1/events/{event_id}/activities
Authorization: Bearer <token>
Content-Type: application/json

{
  "distance": 10.5,
  "duration": 60,
  "activity_date": "2026-04-16",
  "notes": "Morning run, felt great!"
}

Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  "event_id": 1,
  "distance": 10.5,
  "duration": 60,
  "activity_date": "2026-04-16",
  "notes": "Morning run, felt great!",
  "created_at": "2026-04-16T12:00:00"
}
```

### Get User Activities
```http
GET /api/v1/users/{user_id}/activities?event_id=1&start_date=2026-04-01&end_date=2026-04-30&page=1&limit=20
Authorization: Bearer <token>

Query Parameters:
- event_id: filter by event (optional)
- start_date: filter from date (optional)
- end_date: filter until date (optional)
- page: page number (default: 1)
- limit: items per page (default: 20, max: 100)

Response: 200 OK
{
  "activities": [...],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

### Get Event Activities
```http
GET /api/v1/events/{event_id}/activities?page=1&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "activities": [...],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

## Admin Endpoints (Temporary - Remove in Production)

### Run Migrations
```http
POST /api/v1/admin/run-migrations

Response: 200 OK
{
  "status": "success",
  "message": "All migrations completed successfully!",
  "output": "...",
  "note": "⚠️ Remember to remove this endpoint after setup"
}
```

### Seed Database
```http
POST /api/v1/admin/seed-data

Response: 200 OK
{
  "status": "success",
  "message": "Test data seeded successfully!",
  "output": "...",
  "note": "⚠️ Remember to remove this endpoint after setup"
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `400` - Bad Request (validation error, business logic error)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

## Interactive API Documentation

Visit these URLs for interactive documentation:
- Swagger UI: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc`

## Test Accounts (After Seeding)

```
Admin:     admin@glycogrit.com / admin123
Organizer: organizer@glycogrit.com / organizer123
User:      john.doe@example.com / test123
```
