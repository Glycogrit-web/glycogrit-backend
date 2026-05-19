# Production CORS Configuration Fix

## Critical Issue

**Status:** Production application failing to start
**Error:** `ValueError: Wildcard CORS origins not allowed in production environment`
**Location:** [app/main.py:49](app/main.py#L49)

## Root Cause

The application is running with `ENVIRONMENT=production` but `ALLOWED_ORIGINS` is either:
1. Not set (defaults to "*" in config)
2. Set to "*" (wildcard - insecure for production)

The security validation at [app/main.py:46-49](app/main.py#L46-L49) blocks this intentionally to prevent CORS security vulnerabilities.

## Fix Steps

### Option 1: Railway Dashboard (Recommended - Fastest)

1. Go to Railway Dashboard: https://railway.app/dashboard
2. Select your backend service
3. Click "Variables" tab
4. Add/Update the `ALLOWED_ORIGINS` variable:

   ```
   ALLOWED_ORIGINS=https://glycogrit.com,https://www.glycogrit.com
   ```

   **Important:** Use comma-separated list of your actual frontend URLs with NO spaces

5. Click "Deploy" or wait for automatic redeploy
6. Verify logs show: `✅ CORS configured with explicit origins`

### Option 2: Railway CLI

```bash
# Install Railway CLI if needed
npm install -g @railway/cli

# Login and link to project
railway login
railway link

# Set ALLOWED_ORIGINS environment variable
railway variables --set ALLOWED_ORIGINS=https://glycogrit.com,https://www.glycogrit.com

# Redeploy
railway up
```

### Option 3: Doppler (If Using Doppler for Secrets)

Based on [.env.example](glycogrit-backend/.env.example#L2), you may be using Doppler:

```bash
# Login to Doppler
doppler login

# Select your project
doppler setup

# Set ALLOWED_ORIGINS
doppler secrets set ALLOWED_ORIGINS="https://glycogrit.com,https://www.glycogrit.com"

# Sync will trigger automatic redeploy if configured
```

## Required Values

### Production Frontend URLs

Replace with your actual frontend URLs:

```bash
# Single origin
ALLOWED_ORIGINS=https://glycogrit.com

# Multiple origins (no spaces!)
ALLOWED_ORIGINS=https://glycogrit.com,https://www.glycogrit.com,https://app.glycogrit.com

# Include staging if needed
ALLOWED_ORIGINS=https://glycogrit.com,https://staging.glycogrit.com
```

### Local Development

For local testing, you can use:

```bash
# .env file for local development
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Note:** Wildcard "*" is allowed in development mode but blocked in production.

## Verification

After deploying the fix:

1. **Check Application Logs:**
   ```bash
   railway logs
   ```

   Should show:
   ```
   ✅ CORS configured with explicit origins: ['https://glycogrit.com', 'https://www.glycogrit.com']
   ```

2. **Test Health Endpoint:**
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

   Should return:
   ```json
   {
     "status": "healthy",
     "application": "GlycoGrit Backend API",
     "version": "1.0.0"
   }
   ```

3. **Test CORS from Frontend:**
   - Open browser DevTools → Network tab
   - Make API request from frontend
   - Check response headers include:
     ```
     Access-Control-Allow-Origin: https://glycogrit.com
     Access-Control-Allow-Credentials: true
     ```

## Security Best Practices

### ✅ DO:
- Use explicit frontend URLs only
- Use HTTPS in production
- Include www and non-www versions if both are used
- Test CORS thoroughly after deployment

### ❌ DON'T:
- **Never** use "*" in production
- **Never** use "http://" URLs in production (only HTTPS)
- **Never** include localhost URLs in production config
- **Never** disable CORS validation

## Code Reference

The CORS validation logic is at [app/main.py:44-71](glycogrit-backend/app/main.py#L44-L71):

```python
# CORS configuration
allowed_origins = settings.allowed_origins_list

# Validate CORS configuration
if allowed_origins == ["*"]:
    if settings.ENVIRONMENT == "production":
        logger.error("⚠️  SECURITY VIOLATION: Wildcard CORS not allowed in production!")
        raise ValueError("Wildcard CORS origins not allowed in production environment")
```

Config parsing is at [app/core/config.py:92-96](glycogrit-backend/app/core/config.py#L92-L96):

```python
@property
def allowed_origins_list(self) -> List[str]:
    """Parse ALLOWED_ORIGINS string into a list."""
    if self.ALLOWED_ORIGINS == "*":
        return ["*"]
    return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
```

## Troubleshooting

### Issue: Still getting CORS error after setting variable

**Solution:**
1. Verify variable is set: `railway variables`
2. Check for typos in variable name (must be exact: `ALLOWED_ORIGINS`)
3. Ensure no trailing commas or spaces in value
4. Force redeploy: `railway up --detach`

### Issue: Frontend getting CORS errors

**Check:**
1. Frontend URL exactly matches what's in `ALLOWED_ORIGINS`
2. Protocol matches (http vs https)
3. Port matches if included
4. Subdomain matches (www vs non-www)

**Example:**
```bash
# These are ALL different origins:
https://glycogrit.com          # ✅
https://www.glycogrit.com      # ✅ Different!
http://glycogrit.com           # ❌ Different protocol
https://glycogrit.com:443      # ⚠️  Usually same, but explicit port may differ
```

### Issue: Need to temporarily bypass for testing

**NOT RECOMMENDED but if absolutely necessary:**

```bash
# Temporarily switch to development mode
railway variables --set ENVIRONMENT=development

# Test your changes

# IMMEDIATELY switch back
railway variables --set ENVIRONMENT=production
railway variables --set ALLOWED_ORIGINS=https://glycogrit.com
```

## Related Documentation

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)
- [OWASP CORS Security](https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny)

## Quick Reference Card

```bash
# Check current environment variables
railway variables

# Set ALLOWED_ORIGINS (replace with your URLs)
railway variables --set ALLOWED_ORIGINS=https://glycogrit.com,https://www.glycogrit.com

# View logs
railway logs

# Check health
curl https://your-backend-url.railway.app/health

# Test CORS
curl -H "Origin: https://glycogrit.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://your-backend-url.railway.app/api/v1/auth/register -v
```

## Need Help?

If issues persist:
1. Check Railway logs: `railway logs`
2. Verify environment: `railway variables | grep ENVIRONMENT`
3. Verify ALLOWED_ORIGINS: `railway variables | grep ALLOWED_ORIGINS`
4. Check application startup logs for CORS configuration message
