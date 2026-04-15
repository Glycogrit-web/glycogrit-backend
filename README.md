# GlycoGrit Backend

FastAPI backend for GlycoGrit - a cycling community platform inspired by PedalPulse.

## Architecture

- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 16
- **Authentication**: Firebase JWT validation
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Containerization**: Docker & Docker Compose
- **Deployment**: Hetzner VPS (recommended)

## Features

- Firebase JWT-based authentication
- User management and profiles
- Ride planning and management
- Event listings and registration
- RESTful API with automatic documentation
- Database migrations with Alembic
- Docker support for easy deployment

## Project Structure

```
glycogrit-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py         # Authentication endpoints
│   │       │   ├── users.py        # User management
│   │       │   ├── rides.py        # Ride management
│   │       │   └── events.py       # Event management
│   │       └── api.py              # API router configuration
│   ├── core/
│   │   ├── config.py               # Configuration settings
│   │   ├── database.py             # Database connection
│   │   └── firebase.py             # Firebase integration
│   ├── middleware/
│   │   └── auth.py                 # Authentication middleware
│   ├── models/
│   │   ├── user.py                 # User model
│   │   ├── ride.py                 # Ride model
│   │   └── event.py                # Event model
│   ├── schemas/
│   │   ├── user.py                 # User Pydantic schemas
│   │   ├── ride.py                 # Ride Pydantic schemas
│   │   └── event.py                # Event Pydantic schemas
│   └── main.py                     # FastAPI application
├── alembic/                        # Database migrations
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile                      # Docker image configuration
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment variables template
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (if running without Docker)
- Firebase project with Admin SDK credentials

### Local Development Setup

1. **Clone the repository**

```bash
git clone https://github.com/glycogrit-team/glycogrit-backend.git
cd glycogrit-backend
```

2. **Set up environment variables**

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
POSTGRES_USER=glycogrit
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=glycogrit
DATABASE_URL=postgresql://glycogrit:your_secure_password@localhost:5432/glycogrit
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

3. **Add Firebase credentials**

Download your Firebase Admin SDK credentials JSON file and save it as `firebase-credentials.json` in the project root.

4. **Run with Docker Compose** (Recommended)

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- FastAPI backend on port 8000

5. **Run migrations**

```bash
# Create initial migration
docker-compose exec backend alembic revision --autogenerate -m "Initial migration"

# Apply migrations
docker-compose exec backend alembic upgrade head
```

### Alternative: Local Development without Docker

1. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Run PostgreSQL** (ensure it's running on localhost:5432)

4. **Run migrations**

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

5. **Start the server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API Endpoints

### Authentication

- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/verify` - Verify Firebase token

### Users

- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/me` - Update current user profile
- `DELETE /api/v1/users/me` - Delete current user

### Rides

- `GET /api/v1/rides/` - List all rides (with filters)
- `GET /api/v1/rides/{ride_id}` - Get ride by ID
- `POST /api/v1/rides/` - Create new ride (auth required)
- `PUT /api/v1/rides/{ride_id}` - Update ride (organizer only)
- `DELETE /api/v1/rides/{ride_id}` - Delete ride (organizer only)
- `GET /api/v1/rides/upcoming/all` - Get upcoming rides

### Events

- `GET /api/v1/events/` - List all events (with filters)
- `GET /api/v1/events/{event_id}` - Get event by ID
- `GET /api/v1/events/featured` - Get featured events
- `GET /api/v1/events/upcoming` - Get upcoming events
- `POST /api/v1/events/` - Create new event (auth required)
- `PUT /api/v1/events/{event_id}` - Update event (auth required)
- `DELETE /api/v1/events/{event_id}` - Delete event (auth required)

## Authentication

The API uses Firebase JWT tokens for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <firebase_id_token>
```

### Frontend Integration

```javascript
// Get Firebase ID token from client
const idToken = await firebase.auth().currentUser.getIdToken();

// Make authenticated request
fetch('http://localhost:8000/api/v1/auth/me', {
  headers: {
    'Authorization': `Bearer ${idToken}`
  }
});
```

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Production Deployment

### Recommended: Hetzner VPS Setup

1. **Provision Hetzner VPS** (CPX11 - €4.51/month)
   - 2 vCPU
   - 2 GB RAM
   - 40 GB SSD

2. **Install Docker & Docker Compose**

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

3. **Clone repository and configure**

```bash
git clone https://github.com/glycogrit-team/glycogrit-backend.git
cd glycogrit-backend
cp .env.example .env
# Edit .env with production values
```

4. **Update docker-compose.yml for production**

```yaml
backend:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  environment:
    ENVIRONMENT: production
```

5. **Run in production mode**

```bash
docker-compose up -d
```

6. **Set up reverse proxy** (Nginx or Caddy)

```nginx
server {
    listen 80;
    server_name api.glycogrit.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Monitoring & Logs

```bash
# View logs
docker-compose logs -f backend

# Check container status
docker-compose ps

# Restart services
docker-compose restart
```

## Cost Estimation

**For 3,000 users:**

- Hetzner VPS (CPX11): €4.51/month (~$5/month)
- PostgreSQL: Included
- Cloudflare R2 (storage): ~$1/month
- **Total: ~$6-9/month**

**Scaling:**
- 10K users: Upgrade to CPX21 (€8.21/month)
- 30K users: Upgrade to CPX31 (€15.32/month)

## Security

- Firebase handles authentication
- PostgreSQL for user data
- CORS configured for frontend domains
- Environment variables for sensitive data
- Never commit `firebase-credentials.json` or `.env`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/glycogrit-team/glycogrit-backend/issues
- Email: support@glycogrit.com
