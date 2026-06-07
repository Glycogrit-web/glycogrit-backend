# Google OAuth 2.0 Setup Guide

## Overview

This guide walks you through setting up Google OAuth 2.0 for user authentication in GlycoGrit. Users can sign in with their Google accounts instead of creating separate credentials.

---

## Prerequisites

- Google Cloud Console account (free)
- Admin access to GlycoGrit backend
- Access to environment variable configuration (Doppler or .env)

---

## Step 1: Create Google Cloud Project

### 1.1 Navigate to Google Cloud Console
1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Sign in with your Google account

### 1.2 Create New Project
1. Click the project dropdown at the top
2. Click **"New Project"**
3. **Project Name**: `GlycoGrit Production` (or your preferred name)
4. **Organization**: Leave as "No organization" unless you have one
5. Click **"Create"**
6. Wait for project creation (10-30 seconds)
7. Select the new project from the dropdown

---

## Step 2: Enable Google+ API

### 2.1 Navigate to APIs & Services
1. Click the **☰ hamburger menu** (top-left)
2. Go to **"APIs & Services" → "Library"**

### 2.2 Enable Required APIs
1. Search for **"Google+ API"**
2. Click on it
3. Click **"Enable"**
4. Wait for API to enable (~10 seconds)

> **📖 Note:** The Google+ API is used for fetching user profile information (name, email, picture) during authentication.

---

## Step 3: Configure OAuth Consent Screen

### 3.1 Navigate to Consent Screen
1. Go to **"APIs & Services" → "OAuth consent screen"**
2. Select **"External"** (unless you have a Google Workspace)
3. Click **"Create"**

### 3.2 App Information
Fill in the required fields:

**App name**: `GlycoGrit`

**User support email**: Your email address

**App logo** (optional): Upload GlycoGrit logo (120x120px)

**Application home page**: `https://glycogrit.com` (or your domain)

**Application privacy policy**: `https://glycogrit.com/privacy`

**Application terms of service**: `https://glycogrit.com/terms`

**Authorized domains**:
- `glycogrit.com`
- `www.glycogrit.com`

**Developer contact email**: Your email address

Click **"Save and Continue"**

### 3.3 Scopes
1. Click **"Add or Remove Scopes"**
2. Select the following scopes:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
3. Click **"Update"**
4. Click **"Save and Continue"**

### 3.4 Test Users (Development Only)
For development/testing, add test users:
1. Click **"Add Users"**
2. Enter email addresses of testers
3. Click **"Add"**
4. Click **"Save and Continue"**

> **⚠️ Warning:** In production, remove test user restriction by publishing the app (see Step 6).

### 3.5 Summary
Review your settings and click **"Back to Dashboard"**

---

## Step 4: Create OAuth Credentials

### 4.1 Navigate to Credentials
1. Go to **"APIs & Services" → "Credentials"**
2. Click **"+ Create Credentials"**
3. Select **"OAuth client ID"**

### 4.2 Configure OAuth Client
**Application type**: Select **"Web application"**

**Name**: `GlycoGrit Web Client`

**Authorized JavaScript origins**:
- `https://glycogrit.com`
- `https://www.glycogrit.com`
- `http://localhost:5173` (for local development)

**Authorized redirect URIs**:
- `https://glycogrit.com/auth/callback`
- `https://www.glycogrit.com/auth/callback`
- `http://localhost:5173/auth/callback` (for local development)

Click **"Create"**

### 4.3 Save Credentials
A popup will appear with:
- **Client ID**: `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxxxxx`

> **✅ Tip:** Click the **download icon** to download credentials as JSON (backup copy).

**DO NOT CLOSE THIS POPUP YET** - you'll need these values in the next step.

---

## Step 5: Configure Backend Environment

### 5.1 Backend Environment Variables
Add the following to your backend environment (Doppler, .env, or Railway):

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
```

> **🚫 Danger:** NEVER commit these credentials to Git. Always use environment variables or secret management tools.

### 5.2 Frontend Environment Variables
Add to frontend environment (Vite .env file):

```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

> **📖 Note:** Frontend only needs the Client ID (public value). Client Secret stays on backend only.

### 5.3 Verify Configuration
Restart backend and frontend services after adding environment variables.

---

## Step 6: Publish OAuth App (Production)

### 6.1 Navigate to Publishing Status
1. Go to **"OAuth consent screen"**
2. Click **"Publish App"** button
3. Read the warning
4. Click **"Confirm"**

> **⚠️ Warning:** Publishing makes your app available to any Google user. Do this only after thorough testing.

### 6.2 Verification (Optional)
For apps requesting sensitive scopes:
- Google may require verification
- This is NOT needed for basic profile scopes
- Takes 3-5 business days if required

---

## Code Implementation

### Backend OAuth Configuration

**File**: `app/core/auth.py`

```python
from google.auth.transport import requests
from google.oauth2 import id_token

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

def verify_google_token(token: str):
    """Verify Google OAuth token and extract user info"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer')

        return {
            'email': idinfo['email'],
            'name': idinfo['name'],
            'picture': idinfo['picture'],
            'google_id': idinfo['sub']
        }
    except ValueError:
        return None
```

### Frontend OAuth Integration

**File**: `src/pages/Login.tsx`

```tsx
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function Login() {
  const handleGoogleLogin = async (credentialResponse: any) => {
    try {
      // Send token to backend
      const response = await apiClient.post('/auth/google', {
        token: credentialResponse.credential
      });

      // Store JWT and redirect
      localStorage.setItem('token', response.data.token);
      navigate('/dashboard');
    } catch (error) {
      console.error('Google login failed:', error);
      toast.error('Failed to sign in with Google');
    }
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <GoogleLogin
        onSuccess={handleGoogleLogin}
        onError={() => toast.error('Google login failed')}
      />
    </GoogleOAuthProvider>
  );
}
```

---

## Testing OAuth Flow

### Test Checklist
- [ ] Click "Sign in with Google" button
- [ ] Redirected to Google consent screen
- [ ] See app name, logo, and permissions requested
- [ ] Click "Allow" or "Continue"
- [ ] Redirected back to application
- [ ] User logged in with Google account
- [ ] User profile loaded (name, email, picture)
- [ ] Session persists after page refresh

### Local Development Testing
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open `http://localhost:5173`
4. Test Google sign-in flow
5. Check browser console for errors
6. Verify backend logs show OAuth exchange

---

## Troubleshooting

### Error: "redirect_uri_mismatch"
**Cause**: Redirect URI not authorized in Google Cloud Console

**Solution**:
1. Go to **"Credentials"** in Google Cloud Console
2. Edit OAuth client
3. Add exact redirect URI (check for trailing slashes)
4. Save and retry

---

### Error: "invalid_client"
**Cause**: Client ID or Client Secret incorrect

**Solution**:
1. Verify `GOOGLE_CLIENT_ID` matches Google Cloud Console
2. Verify `GOOGLE_CLIENT_SECRET` matches (backend only)
3. Restart backend after changing environment variables
4. Check for extra spaces or quotes in env values

---

### Error: "access_denied"
**Cause**: User denied permissions or app not published

**Solution**:
1. If testing: Add user as test user in OAuth consent screen
2. If production: Publish OAuth app (Step 6)
3. User may need to clear Google account permissions and retry

---

### Error: "Token verification failed"
**Cause**: Token expired or invalid

**Solution**:
1. Tokens expire after 1 hour
2. Frontend should request new token on expiry
3. Check backend token verification logic
4. Verify clock sync between backend and Google (NTP)

---

## Security Best Practices

### ✅ Do's
- Store Client Secret in secure environment variables
- Use HTTPS for all redirect URIs in production
- Validate token issuer on backend
- Set appropriate token expiry times
- Log OAuth failures for security monitoring

### 🚫 Don'ts
- Never commit credentials to Git
- Don't expose Client Secret to frontend
- Don't skip token verification on backend
- Don't use HTTP redirect URIs in production
- Don't share OAuth credentials across environments (dev/prod)

---

## Next Steps

1. **[Google Fit API Setup](./google-fit-api.md)** - Enable activity sync
2. **[Google Drive API Setup](./google-drive-api.md)** - Setup certificate storage
3. **[Troubleshooting Guide](./troubleshooting.md)** - Common OAuth issues

---

**Last Updated**: June 7, 2026
**Version**: 1.0
