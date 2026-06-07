# Google Services Troubleshooting

## OAuth Issues

### Error: "redirect_uri_mismatch"
**Symptoms**: After clicking "Sign in with Google", see error message about redirect URI

**Causes**:
- Redirect URI not registered in Google Cloud Console
- Trailing slash mismatch (with vs without)
- HTTP vs HTTPS mismatch
- Localhost port mismatch in development

**Solutions**:
1. Go to Google Cloud Console → Credentials
2. Edit OAuth 2.0 Client ID
3. Add exact redirect URI from error message
4. Include both with and without trailing slash if needed
5. For local dev, add `http://localhost:5173/auth/callback`
6. Save and retry after 1-2 minutes

---

### Error: "invalid_client"
**Symptoms**: Backend logs show "invalid_client" or "unauthorized_client"

**Causes**:
- Wrong `GOOGLE_CLIENT_ID` in environment
- Wrong `GOOGLE_CLIENT_SECRET` in environment
- Extra spaces in environment variables
- Using frontend credentials on backend (or vice versa)

**Solutions**:
1. Verify `GOOGLE_CLIENT_ID` matches Google Cloud Console exactly
2. Verify `GOOGLE_CLIENT_SECRET` matches (backend only)
3. Remove any quotes, spaces, or newlines from env variables
4. Restart backend service after changing environment
5. Check Doppler sync if using Doppler

**Debug Commands**:
```bash
# Check environment variables
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Restart backend
pkill -f uvicorn && uvicorn app.main:app --reload
```

---

### Error: "access_denied"
**Symptoms**: User sees "Access blocked" or "This app isn't verified"

**Causes**:
- App not published in OAuth consent screen
- User not added as test user (in development)
- User denied permissions
- Sensitive scopes require app verification

**Solutions**:
1. **Development**: Add user email to test users in OAuth consent screen
2. **Production**: Publish app in OAuth consent screen
3. If user denied: Ask them to retry and click "Allow"
4. If app verification required: Submit app for verification (3-5 days)

---

### Error: "Token expired"
**Symptoms**: User suddenly logged out, "Unauthorized" errors

**Causes**:
- Access token expired (1-hour lifetime)
- Refresh token not working
- Backend not refreshing tokens automatically

**Solutions**:
1. Implement token refresh logic in backend
2. Check `google_token_expires_at` in database
3. Refresh tokens 5 minutes before expiry
4. If refresh token invalid, user must re-authenticate

**Backend Implementation**:
```python
def refresh_google_token(user: User):
    if user.google_token_expires_at > datetime.now() + timedelta(minutes=5):
        return  # Token still valid

    # Refresh token
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'refresh_token': decrypt(user.google_refresh_token),
        'grant_type': 'refresh_token'
    })

    if response.ok:
        tokens = response.json()
        user.google_access_token = encrypt(tokens['access_token'])
        user.google_token_expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
        db.commit()
```

---

## Google Drive API Issues

### Error: "File not found" (404)
**Symptoms**: Certificate download fails with "File not found"

**Causes**:
- File ID extraction failed
- File not shared with service account
- File deleted from Drive
- File in different folder not shared

**Solutions**:
1. Verify Drive URL format is correct
2. Check file exists in Google Drive
3. Verify folder is shared with service account email
4. Service account needs access to parent folder
5. Re-share folder if permissions changed

**Debug Steps**:
```python
# Extract file ID
file_id = url.split('/file/d/')[1].split('/')[0]
print(f"File ID: {file_id}")

# Test Drive API access
drive_service.files().get(fileId=file_id).execute()
```

---

### Error: "Insufficient permissions" (403)
**Symptoms**: "Permission denied" when accessing Drive files

**Causes**:
- Service account doesn't have access to file/folder
- Drive API not enabled in Google Cloud
- Wrong service account credentials
- Viewer permission not granted

**Solutions**:
1. Enable Google Drive API in Google Cloud Console
2. Share Drive folder with service account email
3. Grant "Viewer" role (not "Commenter" or "Editor")
4. Verify `GOOGLE_SERVICE_ACCOUNT_JSON` is correct
5. Re-generate service account key if needed

---

### Error: "Invalid credentials"
**Symptoms**: Backend logs show "invalid_grant" or credential errors

**Causes**:
- Malformed JSON in `GOOGLE_SERVICE_ACCOUNT_JSON`
- Extra spaces or newlines in environment variable
- Wrong service account key
- Service account deleted in Google Cloud

**Solutions**:
1. Re-download service account JSON from Google Cloud Console
2. Validate JSON format (use online validator)
3. Store as single-line string in environment
4. Use single quotes: `GOOGLE_SERVICE_ACCOUNT_JSON='{"type":...}'`
5. Restart backend after updating

**Validation**:
```bash
# Test JSON validity
echo $GOOGLE_SERVICE_ACCOUNT_JSON | python -m json.tool
```

---

## Google Fit API Issues

### Error: "insufficient_scope"
**Symptoms**: Fit sync fails with "insufficient scope" or "access denied"

**Causes**:
- Fit scopes not added to OAuth consent screen
- User didn't grant Fit permissions
- Token doesn't have Fit scopes

**Solutions**:
1. Add Fit scopes to OAuth consent screen:
   - `https://www.googleapis.com/auth/fitness.activity.read`
   - `https://www.googleapis.com/auth/fitness.location.read`
2. User must re-authorize and grant Fit permissions
3. Check scopes in token: `idinfo['scope']`

---

### Data Not Syncing
**Symptoms**: Activities not appearing after sync

**Causes**:
- No activities in Google Fit for date range
- Fit app not tracking activities
- Wrong data source ID
- Time zone issues

**Solutions**:
1. Check Google Fit app has recent activities
2. Verify date range (default: 7 days back)
3. Check data source ID matches Google Fit format
4. Adjust time zone conversions if needed
5. Manually test API call with user token

**Debug API Call**:
```python
# Test Fit API manually
response = service.users().dataSources().datasets().get(
    userId='me',
    dataSourceId='derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments',
    datasetId=f"{start_time}-{end_time}"
).execute()

print(f"Activities found: {len(response.get('point', []))}")
```

---

### Error: "Quota exceeded"
**Symptoms**: "Quota exceeded" or "Rate limit exceeded"

**Causes**:
- Too many API calls in short time
- Exceeded daily quota
- Multiple users syncing simultaneously

**Solutions**:
1. Implement rate limiting (1 sync per hour per user)
2. Cache activity data for 1 hour
3. Request quota increase in Google Cloud Console
4. Batch sync operations instead of per-user

---

## General Debugging Tips

### Check Environment Variables
```bash
# Backend
printenv | grep GOOGLE

# Doppler
doppler secrets get GOOGLE_CLIENT_ID
doppler secrets get GOOGLE_SERVICE_ACCOUNT_JSON
```

### Check Backend Logs
```bash
# Railway
railway logs --tail

# Local
tail -f logs/app.log | grep -i google
```

### Test API Endpoints
```bash
# Test OAuth
curl -X POST http://localhost:8000/api/v1/auth/google \
  -H "Content-Type: application/json" \
  -d '{"code":"auth-code-here"}'

# Test Fit sync
curl -X POST http://localhost:8000/api/v1/fitness/google-fit/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Verify Google Cloud Console Setup
- [ ] OAuth consent screen configured
- [ ] OAuth 2.0 client ID created
- [ ] Redirect URIs match exactly
- [ ] Required scopes added
- [ ] Service account created (for Drive)
- [ ] Service account key downloaded
- [ ] Drive folder shared with service account
- [ ] APIs enabled (OAuth, Fit, Drive)

---

## Getting Help

If issues persist after trying these solutions:

1. **Check Official Documentation**:
   - [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
   - [Google Fit API](https://developers.google.com/fit)
   - [Google Drive API](https://developers.google.com/drive)

2. **Review Backend Logs**: Look for detailed error messages

3. **Test in Isolation**: Create minimal test script to isolate issue

4. **Contact Support**: Include error messages, logs, and steps taken

---

**Last Updated**: June 7, 2026
