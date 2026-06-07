# Google Fit API Integration

## Overview

Google Fit API enables automatic activity synchronization for challenge progress tracking. Users connect their Google Fit account to sync running, cycling, and walking activities.

---

## OAuth Scopes Required

Add to your OAuth consent screen:
- `https://www.googleapis.com/auth/fitness.activity.read`
- `https://www.googleapis.com/auth/fitness.location.read`

---

## User Connection Flow

1. User clicks "Connect Google Fit" in dashboard
2. Redirected to Google OAuth with Fit scopes
3. User grants fitness data permissions
4. Callback receives authorization code
5. Backend exchanges for access/refresh tokens
6. Tokens stored in database
7. Background sync fetches activities

---

## Code Implementation

### Frontend Connection

**File**: `src/components/progress/SyncCard.tsx`

```tsx
const handleConnectFit = () => {
  const scopes = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.location.read'
  ];

  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${GOOGLE_CLIENT_ID}` +
    `&redirect_uri=${window.location.origin}/fitness/callback` +
    `&response_type=code` +
    `&scope=${scopes.join(' ')}` +
    `&access_type=offline`;

  window.location.href = authUrl;
};
```

### Backend Sync Service

**File**: `app/modules/fitness/services/google_fit_service.py`

```python
class GoogleFitService:
    def sync_activities(self, user: User, days_back: int = 7):
        """Fetch and sync activities from Google Fit"""
        # Refresh token if expired
        if user.google_fit_token_expires_at < datetime.now():
            self.refresh_access_token(user)

        # Build Fit API client
        credentials = google.oauth2.credentials.Credentials(
            token=decrypt(user.google_fit_access_token)
        )
        service = build('fitness', 'v1', credentials=credentials)

        # Fetch activities
        end_time = int(datetime.now().timestamp() * 1000000000)
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000000000)

        dataset = f"{start_time}-{end_time}"
        response = service.users().dataSources().datasets().get(
            userId='me',
            dataSourceId='derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments',
            datasetId=dataset
        ).execute()

        # Process and store activities
        for point in response.get('point', []):
            self.process_activity_point(user, point)
```

---

## Activity Data Synced

| Field | Description | Unit |
|-------|-------------|------|
| Activity Type | Running, cycling, walking | String |
| Distance | Total distance covered | Kilometers |
| Duration | Activity duration | Minutes |
| Calories | Estimated calories burned | kcal |
| Start Time | Activity start timestamp | DateTime |
| End Time | Activity end timestamp | DateTime |

---

## Troubleshooting

### Error: "insufficient_scope"
**Solution**: Add Fit scopes to OAuth consent screen and re-authorize

### Data Not Syncing
**Solution**: Check token expiry, refresh tokens, verify Fit app has data

---

**Last Updated**: June 7, 2026
