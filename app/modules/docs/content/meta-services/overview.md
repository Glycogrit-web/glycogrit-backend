# Meta Services (Facebook/Instagram) Overview

## Introduction

GlycoGrit integrates with Meta services (Facebook and Instagram) for social authentication and marketing features. This guide covers Facebook Login for authentication and potential Instagram integration for social sharing.

---

## Services Overview

### 1. Facebook Login
**Purpose**: User authentication via Facebook account

**Key Features**:
- Sign in with Facebook
- One-click registration
- Profile data retrieval (name, email, profile picture)
- Friends list access (optional)
- Automatic account linking

**Status**: ✅ Implemented

---

### 2. Instagram Integration (Future)
**Purpose**: Social media engagement and content sharing

**Potential Features**:
- Share challenge achievements to Instagram Stories
- Post certificate completion to Instagram feed
- Import Instagram photos as proof of activity
- Community highlights and user-generated content

**Status**: 🔮 Planned/Future Enhancement

---

## Architecture Overview

```
┌─────────────┐
│    User     │
│  (Browser)  │
└──────┬──────┘
       │
       │ 1. Click "Login with Facebook"
       │
┌──────▼──────┐
│  Frontend   │
│   (React)   │
└──────┬──────┘
       │
       │ 2. Redirect to Facebook
       │
┌──────▼──────────────┐
│  Facebook OAuth     │
│  Consent Screen     │
└──────┬──────────────┘
       │
       │ 3. User approves
       │
┌──────▼──────┐
│  Callback   │
│  Handler    │
└──────┬──────┘
       │
       │ 4. Exchange code for token
       │
┌──────▼──────┐
│   Backend   │
│  (FastAPI)  │
└──────┬──────┘
       │
       │ 5. Verify token with Facebook
       │
┌──────▼───────────┐
│  Facebook Graph  │
│      API         │
└──────┬───────────┘
       │
       │ 6. Return user data
       │
┌──────▼──────┐
│  Database   │
│ (User save) │
└──────┬──────┘
       │
       │ 7. Return JWT token
       │
┌──────▼──────┐
│    User     │
│ (Logged in) │
└─────────────┘
```

---

## Facebook Login Integration

### Why Facebook Login?

**Benefits**:
- **User Convenience**: One-click sign-in
- **Higher Conversion**: Reduces friction in sign-up
- **Trusted Brand**: Users comfortable with Facebook auth
- **Profile Data**: Pre-filled user information
- **Global Reach**: 3+ billion Facebook users

**Use Cases**:
- Quick registration for new users
- Alternative to Google OAuth
- Social graph access for friend features (future)

---

## Data Retrieved from Facebook

### Basic Profile
- **Name**: Full name from Facebook profile
- **Email**: Primary email address
- **Profile Picture**: Avatar URL
- **Facebook ID**: Unique identifier

### Optional Permissions (Not currently used)
- Friends list
- Birthday
- Location
- Posts (with extended permissions)

> **📖 Note:** GlycoGrit currently only requests basic profile and email permissions.

---

## Environment Variables

### Required Configuration

**Frontend**:
```bash
VITE_FACEBOOK_APP_ID=your-facebook-app-id
```

**Backend**:
```bash
FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-app-secret
```

**Where to Find**:
- App ID: Meta for Developers Dashboard → Your App → Settings → Basic
- App Secret: Same location (click "Show" to reveal)

---

## Facebook App Configuration

### App Settings
- **App Name**: GlycoGrit
- **App Type**: Consumer
- **Category**: Health & Fitness
- **Privacy Policy URL**: https://glycogrit.com/privacy
- **Terms of Service URL**: https://glycogrit.com/terms

### Products Added
- ✅ **Facebook Login**
- 🔮 Instagram Basic Display (future)
- 🔮 Instagram Graph API (future)

### Permissions Requested
- `public_profile` - Name, profile picture
- `email` - Email address

---

## Security Model

### Access Tokens
- **User tokens**: Short-lived (1-2 hours)
- **Long-lived tokens**: Extended to 60 days
- **Storage**: Encrypted in database
- **Refresh**: Automatic on expiry

### Token Validation
```python
# Verify token with Facebook
response = requests.get(
    'https://graph.facebook.com/debug_token',
    params={
        'input_token': user_token,
        'access_token': f'{app_id}|{app_secret}'
    }
)

if response.json()['data']['is_valid']:
    # Token is valid, proceed
    user_id = response.json()['data']['user_id']
```

### App Secret Protection
- Never expose app secret to frontend
- Store in secure environment variables
- Backend-only verification
- Rotate periodically

---

## Implementation Status

### ✅ Implemented Features
- Facebook Login button on login page
- OAuth callback handler
- Token verification
- User creation/login flow
- Profile data sync
- Account linking (Facebook + email login)

### 🔮 Future Enhancements
- Instagram Story sharing
- Instagram proof uploads
- Social achievement sharing
- Friend challenges
- Community leaderboards

---

## Integration Files

### Frontend
- `src/pages/Login.tsx` - Facebook login button
- `src/pages/AuthCallback.tsx` - OAuth callback
- `src/contexts/AuthContext.tsx` - Auth state

### Backend
- `app/modules/auth/api/facebook_auth.py` - Facebook auth endpoints
- `app/modules/auth/services/facebook_service.py` - Facebook Graph API
- `app/core/config.py` - Facebook configuration

---

## Instagram Integration (Future)

### Potential Use Cases

**1. Story Sharing**
```
User completes challenge → Generate shareable image → Post to Instagram Story
```

**2. Feed Posts**
```
User unlocks certificate → Share achievement → Post to Instagram feed with link
```

**3. Proof Uploads**
```
User runs activity → Posts to Instagram → Import as proof image in GlycoGrit
```

**4. Community Gallery**
```
Users tag #GlycoGrit → Fetch public posts → Display in community gallery
```

### APIs Required
- **Instagram Basic Display API**: View user's Instagram content
- **Instagram Graph API**: Post content, read insights
- **Instagram Mentions API**: Monitor brand mentions

### Permissions Needed
- `instagram_basic` - Read profile and media
- `instagram_content_publish` - Post content
- `instagram_manage_insights` - Access analytics

> **⚠️ Warning:** Instagram APIs require business verification and are more restrictive than Facebook Login.

---

## Common Operations

### Get User Profile (Facebook)
```python
import requests

def get_facebook_profile(access_token: str):
    """Fetch user profile from Facebook"""
    response = requests.get(
        'https://graph.facebook.com/v18.0/me',
        params={
            'fields': 'id,name,email,picture',
            'access_token': access_token
        }
    )

    if response.ok:
        data = response.json()
        return {
            'facebook_id': data['id'],
            'name': data['name'],
            'email': data.get('email'),
            'picture': data['picture']['data']['url']
        }
```

### Exchange Short Token for Long-Lived Token
```python
def extend_access_token(short_token: str) -> str:
    """Exchange short-lived token for long-lived (60 days)"""
    response = requests.get(
        'https://graph.facebook.com/v18.0/oauth/access_token',
        params={
            'grant_type': 'fb_exchange_token',
            'client_id': FACEBOOK_APP_ID,
            'client_secret': FACEBOOK_APP_SECRET,
            'fb_exchange_token': short_token
        }
    )

    if response.ok:
        return response.json()['access_token']
```

---

## Rate Limits

### Facebook Graph API
- **Default**: 200 calls per hour per user
- **App-level**: Varies by app usage
- **Batch requests**: Up to 50 operations per batch

### Best Practices
- Cache profile data (refresh daily)
- Use batch requests when possible
- Implement exponential backoff on rate limit errors
- Monitor usage in Meta dashboard

---

## Costs

### Facebook Login
- **Free**: No costs for authentication
- **No limits**: Unlimited logins

### Instagram API (Future)
- **Free**: Basic Display API
- **Paid**: Advanced features may require business account
- **Rate limits**: Apply based on usage tier

---

## Quick Links

- **[Facebook Login Setup](./facebook-setup.md)** - Configure Facebook OAuth
- **[Instagram Integration](./instagram-integration.md)** - Future Instagram features
- **[Troubleshooting](./meta-troubleshooting.md)** - Common issues

---

## Support Resources

- **Meta for Developers**: [developers.facebook.com](https://developers.facebook.com)
- **Facebook Login Docs**: [developers.facebook.com/docs/facebook-login](https://developers.facebook.com/docs/facebook-login)
- **Instagram API Docs**: [developers.facebook.com/docs/instagram](https://developers.facebook.com/docs/instagram)
- **Graph API Explorer**: Test API calls interactively

---

**Last Updated**: June 7, 2026
**Version**: 1.0
