# Google Services Overview

## Introduction

GlycoGrit integrates with three Google services to provide authentication, activity tracking, and certificate distribution. This overview provides a high-level understanding of how these services work together.

## Services Used

### 1. Google OAuth 2.0
**Purpose**: User authentication and authorization

**Key Features**:
- Sign in with Google
- Secure token-based authentication
- Automatic user account creation
- Profile information retrieval (name, email, profile picture)

**User Flow**:
1. User clicks "Sign in with Google"
2. Redirected to Google OAuth consent screen
3. User grants permissions
4. Returns with authorization code
5. Backend exchanges code for access/refresh tokens
6. User account created or logged in

**Documentation**: [OAuth 2.0 Setup Guide](./oauth-setup.md)

---

### 2. Google Fit API
**Purpose**: Activity data synchronization

**Key Features**:
- Sync running, cycling, walking activities
- Track distance, duration, calories
- Automatic progress updates for challenges
- Historical data import (up to 7 days)

**User Flow**:
1. User connects Google Fit from dashboard
2. Grants Fit API permissions
3. Backend fetches activity data
4. Activities sync to user's challenge progress
5. Periodic background sync keeps data updated

**Documentation**: [Google Fit API Guide](./google-fit-api.md)

---

### 3. Google Drive API
**Purpose**: Certificate storage and streaming

**Key Features**:
- Service account for secure access
- Read-only access to shared Drive folder
- PDF streaming without exposing URLs
- Unlimited certificate downloads
- No direct user access to Drive

**User Flow**:
1. Admin generates certificates via Autocrat
2. Certificates stored in Google Drive
3. Admin uploads certificate URLs via CSV
4. Backend streams PDFs through service account
5. Users download without knowing Drive URL

**Documentation**: [Google Drive API Guide](./google-drive-api.md)

---

## Architecture Overview

```
┌─────────────┐
│             │
│    User     │
│             │
└──────┬──────┘
       │
       ┼───────────────────────────────────────────────┐
       │                                               │
       │  1. Sign in with Google                      │  3. Download Certificate
       │  2. Connect Google Fit                       │
       │                                               │
┌──────▼──────┐                              ┌────────▼────────┐
│             │                              │                 │
│  Frontend   │◄────────────────────────────►│     Backend     │
│   (React)   │                              │    (FastAPI)    │
│             │                              │                 │
└─────────────┘                              └────────┬────────┘
                                                      │
                                                      │
                    ┌─────────────────────────────────┼────────────────────────────┐
                    │                                 │                            │
                    │                                 │                            │
           ┌────────▼────────┐              ┌────────▼────────┐         ┌─────────▼─────────┐
           │                 │              │                 │         │                   │
           │  Google OAuth   │              │  Google Fit API │         │ Google Drive API  │
           │                 │              │                 │         │ (Service Account) │
           │  - User Login   │              │  - Activities   │         │                   │
           │  - Profile Info │              │  - Distance     │         │ - Certificate PDFs│
           │                 │              │  - Duration     │         │ - Read-only       │
           └─────────────────┘              └─────────────────┘         └───────────────────┘
```

---

## Data Flow

### Authentication Flow (OAuth)
```
User → Frontend → Google OAuth → Backend → JWT Token → User Session
```

### Activity Sync Flow (Fit API)
```
Google Fit → User grants permission → Backend fetches → Database → Challenge Progress Updated
```

### Certificate Download Flow (Drive API)
```
Admin (Autocrat) → Drive → CSV → Backend → Service Account → Stream PDF → User
```

---

## Security Model

### OAuth Tokens
- **User tokens**: Stored in database, encrypted
- **Refresh tokens**: Used to obtain new access tokens
- **Scope**: Limited to profile and Fit data
- **Expiry**: Access tokens expire after 1 hour

### Service Account
- **Purpose**: Read-only access to certificate folder
- **Credentials**: Stored securely in environment variables
- **Permissions**: No write access, folder-level sharing only
- **Audit**: All certificate downloads logged

### User Data
- **Personal Info**: Email, name, profile picture only
- **Activity Data**: Synced only with explicit user consent
- **Certificates**: No direct Drive URL exposure to users

---

## Environment Variables

### Required Configuration

**OAuth (User Authentication)**:
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Service Account (Drive API)**:
```bash
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

**Frontend (OAuth Redirect)**:
```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

---

## Key Files Reference

### Backend

**OAuth**:
- `app/core/auth.py` - OAuth configuration
- `app/modules/auth/api/google_auth.py` - Google auth endpoints

**Google Fit**:
- `app/modules/fitness/api/google_fit_api.py` - Fit API endpoints
- `app/modules/fitness/services/google_fit_service.py` - Fit data sync logic

**Google Drive**:
- `app/modules/certificates/services/google_drive_service.py` - Drive service account logic
- `app/modules/certificates/api/certificates.py` - Certificate download endpoint

### Frontend

**OAuth**:
- `src/pages/Login.tsx` - Login page with Google button
- `src/pages/AuthCallback.tsx` - OAuth callback handler

**Google Fit**:
- `src/pages/FitnessCallback.tsx` - Fit API callback handler
- `src/components/progress/SyncCard.tsx` - Connect Fit UI

**Certificates**:
- `src/components/features/CertificateCard.tsx` - Download certificate UI

---

## Common Integration Patterns

### 1. User Token Management
```python
# Store OAuth tokens securely
user.google_access_token = encrypt(access_token)
user.google_refresh_token = encrypt(refresh_token)
user.google_token_expires_at = datetime + timedelta(hours=1)
```

### 2. Token Refresh
```python
# Automatically refresh expired tokens
if user.google_token_expires_at < datetime.now():
    new_tokens = refresh_google_token(user.google_refresh_token)
    user.google_access_token = encrypt(new_tokens['access_token'])
```

### 3. Service Account Access
```python
# Use service account for Drive API
credentials = service_account.Credentials.from_service_account_info(
    json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
```

---

## Quick Links

- **[OAuth 2.0 Setup Guide](./oauth-setup.md)** - Configure Google authentication
- **[Google Drive API Guide](./google-drive-api.md)** - Setup certificate storage
- **[Google Fit API Guide](./google-fit-api.md)** - Enable activity sync
- **[Architecture Details](./architecture.md)** - Deep dive into code architecture
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions

---

## Support

For issues with Google API integrations:
1. Check the [Troubleshooting Guide](./troubleshooting.md)
2. Review Google Cloud Console logs
3. Verify environment variables are set correctly
4. Check service account permissions (for Drive API)

---

**Last Updated**: June 7, 2026
**Version**: 1.0
