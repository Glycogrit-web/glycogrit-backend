# Facebook Login Setup Guide

## Step 1: Create Facebook App

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Click **My Apps** → **Create App**
3. Select **Consumer** as app type
4. Fill in app details:
   - **App Name**: GlycoGrit
   - **App Contact Email**: Your email
5. Click **Create App**

---

## Step 2: Add Facebook Login Product

1. In app dashboard, click **Add Products**
2. Find **Facebook Login** → Click **Set Up**
3. Select **Web** as platform
4. Enter **Site URL**: `https://glycogrit.com`
5. Save settings

---

## Step 3: Configure OAuth Redirect URIs

1. Go to **Facebook Login** → **Settings**
2. Add **Valid OAuth Redirect URIs**:
   - `https://glycogrit.com/auth/callback`
   - `https://www.glycogrit.com/auth/callback`
   - `http://localhost:5173/auth/callback` (development)
3. Save changes

---

## Step 4: Configure App Settings

1. Go to **Settings** → **Basic**
2. Add **App Domains**:
   - `glycogrit.com`
   - `www.glycogrit.com`
3. Add **Privacy Policy URL**: `https://glycogrit.com/privacy`
4. Add **Terms of Service URL**: `https://glycogrit.com/terms`
5. Add **User Data Deletion URL**: `https://glycogrit.com/data-deletion`
6. Save changes

---

## Step 5: Get App Credentials

1. In **Settings** → **Basic**
2. Copy **App ID**
3. Click **Show** next to App Secret, copy it
4. Save both securely

---

## Step 6: Configure Environment Variables

**Frontend** (.env):
```bash
VITE_FACEBOOK_APP_ID=your-app-id
```

**Backend**:
```bash
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

---

## Step 7: Go Live

1. In app dashboard, toggle **App Mode** to **Live**
2. App is now available to all Facebook users

---

**Last Updated**: June 7, 2026
