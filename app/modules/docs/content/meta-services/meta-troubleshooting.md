# Meta Services Troubleshooting

## Facebook Login Issues

### Error: "URL Blocked"
**Cause**: Redirect URI not whitelisted

**Solution**:
1. Go to Facebook Login settings
2. Add your redirect URI to Valid OAuth Redirect URIs
3. Must match exactly (check for trailing slashes)

---

### Error: "App Not Setup"
**Cause**: Facebook Login product not added

**Solution**:
1. Go to app dashboard
2. Click "Add Products"
3. Set up Facebook Login

---

### Error: "Invalid App ID"
**Cause**: Wrong App ID in environment variable

**Solution**:
1. Verify App ID in Meta dashboard (Settings → Basic)
2. Update `VITE_FACEBOOK_APP_ID` (frontend)
3. Update `FACEBOOK_APP_ID` (backend)
4. Restart services

---

### Error: "App in Development Mode"
**Cause**: App not made public/live

**Solution**:
1. Complete app configuration
2. Add Privacy Policy and Terms URLs
3. Toggle "App Mode" to "Live"

---

### Token Expired
**Cause**: Access token expired (1-2 hours default)

**Solution**:
1. Implement token refresh logic
2. Exchange for long-lived token (60 days)
3. Store refresh token in database

---

## Rate Limiting

### "Too Many Calls"
**Cause**: Exceeded Graph API rate limit

**Solution**:
1. Implement caching for profile data
2. Use batch requests
3. Add exponential backoff
4. Monitor usage in Meta dashboard

---

## Debugging

**Test Graph API**:
```bash
curl "https://graph.facebook.com/v18.0/me?access_token=YOUR_TOKEN&fields=id,name,email"
```

**Verify Token**:
```bash
curl "https://graph.facebook.com/debug_token?input_token=USER_TOKEN&access_token=APP_ID|APP_SECRET"
```

---

**Last Updated**: June 7, 2026
