# Railway Configuration Guide

## Required Railway Settings for Docker Deployment

### 1. Build Configuration

**Settings → Build → Builder:**
- Set in `railway.json`: `"builder": "DOCKERFILE"`
- Railway will use the Dockerfile for building

### 2. Deploy Configuration - Custom Start Command

**Settings → Deploy → Custom Start Command:**

Railway's Custom Start Command **overrides** the Dockerfile's CMD/ENTRYPOINT.

**Current Issue:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
❌ This fails because `$PORT` is not being expanded (treated as literal string '$PORT')

**Solution - Update to:**
```bash
sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4"
```

**Why this works:**
- `sh -c` invokes a shell that properly expands variables
- `${PORT:-8000}` uses PORT from Railway, falls back to 8000
- `--workers 4` for production performance

### 3. Health Check Configuration

**Settings → Deploy → Healthcheck Path:**
- Already configured in `railway.json`: `"/health"`
- Timeout: `100` seconds

### 4. Restart Policy

**Settings → Deploy → Restart Policy:**
- Already configured in `railway.json`: `"ON_FAILURE"`
- Max retries: `3`

---

## Step-by-Step: Update Railway Custom Start Command

1. Go to Railway Dashboard
2. Select your `glycogrit-backend` service
3. Click **Settings** tab
4. Scroll to **Deploy** section
5. Find **Custom Start Command**
6. Replace the existing command with:
   ```bash
   sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4"
   ```
7. Click outside the input to save
8. Trigger a new deployment (or wait for auto-deploy)

---

## Alternative: Remove Custom Start Command

If you want to use the Dockerfile's configuration instead:

1. Go to Railway Settings → Deploy
2. Find **Custom Start Command**
3. **Delete** the entire command (leave it empty)
4. Railway will use the Dockerfile's CMD/ENTRYPOINT
5. Redeploy

**Note:** This requires the Dockerfile to have proper CMD configuration.

---

## Verification

After updating the custom start command:

1. Check Railway deployment logs:
   ```
   Starting uvicorn on port 8000...  # or whatever PORT Railway assigns
   ```

2. Test the health endpoint:
   ```bash
   curl https://your-app.up.railway.app/health
   ```

3. Should return:
   ```json
   {
     "status": "healthy",
     "message": "Application is running",
     ...
   }
   ```

---

## Environment Variables

Railway automatically provides:
- `PORT` - Dynamic port assigned by Railway (usually 8000)
- Other variables are injected from Doppler integration

No manual PORT configuration needed!

---

## Troubleshooting

### Error: "Invalid value for '--port': '$PORT' is not a valid integer"

**Cause:** Custom start command not using shell to expand variables

**Fix:** Use `sh -c "..."` wrapper as shown above

### Error: "Permission denied"

**Cause:** User permissions issue in Dockerfile

**Fix:** Already fixed in current Dockerfile (uses appuser with proper permissions)

---

## Current Configuration Status

✅ **Dockerfile:** Multi-stage build with non-root user
✅ **railway.json:** Dockerfile builder, health check, restart policy
⚠️ **Custom Start Command:** Needs update (see above)
✅ **Doppler Integration:** Environment variables configured

---

**Last Updated:** April 17, 2026
