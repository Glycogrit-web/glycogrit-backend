# Railway Deployment Guide - GlycoGrit Backend

## Why Railway?

✅ **Zero DevOps** - No server management
✅ **Auto-Deploy** - Push code, it deploys automatically
✅ **Built-in PostgreSQL** - Managed database included
✅ **Automatic SSL** - HTTPS out of the box
✅ **Fair Pricing** - ~$5-20/month for 3K users
✅ **Easy Scaling** - Upgrade with one click

## Cost Estimate

| Service | Cost |
|---------|------|
| Backend (512MB RAM) | $5/month |
| PostgreSQL (shared) | Free tier or $5/month |
| **Total** | **~$5-10/month** |

**Perfect for startups!** Scale up as you grow, no server management needed.

---

## Quick Deploy (5 Minutes)

### Step 1: Sign Up for Railway

1. Go to: https://railway.app/
2. Click **"Start a New Project"**
3. Sign in with **GitHub**

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Search for: `glycogrit-backend`
4. Click your repository

### Step 3: Add PostgreSQL Database

1. In your project, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway automatically creates and links the database
3. The `DATABASE_URL` environment variable is automatically set!

### Step 4: Configure Environment Variables

Click on your backend service → **"Variables"** tab

**Add these variables**:

```env
# Environment
ENVIRONMENT=production

# CORS (update with your frontend domain)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# JWT Secret (generate a random string)
JWT_SECRET_KEY=<generate-random-32-character-string>

# Firebase Credentials (JSON as string)
FIREBASE_CREDENTIALS_JSON=<paste-firebase-json-content-as-string>
```

**To generate JWT secret**:
```bash
openssl rand -hex 32
```

**For Firebase credentials**:
```bash
# Read your firebase-credentials.json and copy content
cat firebase-credentials.json
# Copy the entire JSON content and paste as FIREBASE_CREDENTIALS_JSON value
```

### Step 5: Deploy!

1. Railway automatically deploys on first setup
2. Click **"Deployments"** tab to watch progress
3. Once deployed, click **"Domains"** to get your API URL

### Step 6: Add Custom Domain (Optional)

1. Click **"Settings"** → **"Domains"**
2. Click **"Generate Domain"** (gets a free `.railway.app` domain)
3. Or add your custom domain:
   - Click **"Custom Domain"**
   - Enter: `api.glycogrit.com`
   - Add CNAME record in your DNS:
     ```
     CNAME api -> <your-railway-domain>.railway.app
     ```

### Step 7: Run Database Migrations

Click on your backend service → **"Settings"** → **"Deploy"**

Add to **"Start Command"**:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or run manually in **"Terminal"** (in Railway dashboard):
```bash
alembic upgrade head
```

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | *Auto-set by Railway* |
| `ENVIRONMENT` | Environment type | `production` |
| `ALLOWED_ORIGINS` | Frontend domains | `https://yourdomain.com` |
| `JWT_SECRET_KEY` | JWT signing key | Random 32-char string |

### Firebase Authentication

**Option 1: File Path** (simpler)
```env
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
```
Then upload file via Railway CLI or commit it (not recommended for security).

**Option 2: JSON String** (recommended for Railway)
```env
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```
Paste entire JSON content as environment variable value.

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` (Railway sets automatically) |
| `HOST` | Server host | `0.0.0.0` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |

---

## Verify Deployment

### Check Health Endpoint

```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status":"healthy"}
```

### Check API Documentation

Open in browser:
- `https://your-app.railway.app/docs` - Swagger UI
- `https://your-app.railway.app/redoc` - ReDoc

### Check Database Connection

```bash
curl https://your-app.railway.app/
```

Should return:
```json
{
  "message": "GlycoGrit Backend API",
  "version": "1.0.0",
  "status": "running"
}
```

---

## Automatic Deployments

Railway automatically deploys when you push to your GitHub repository!

```bash
# Make changes
git add .
git commit -m "Update API endpoints"
git push origin master

# Railway automatically:
# 1. Detects push
# 2. Builds Docker image
# 3. Runs migrations (if configured)
# 4. Deploys new version
# 5. Zero downtime!
```

Watch deployments in Railway dashboard: **"Deployments"** tab

---

## Monitoring & Logs

### View Logs

In Railway dashboard:
1. Click your backend service
2. Click **"Logs"** tab
3. See real-time application logs

### Metrics

Click **"Metrics"** tab to see:
- CPU usage
- Memory usage
- Request count
- Response times

### Set Up Alerts

1. Click **"Settings"** → **"Alerts"**
2. Configure alerts for:
   - High CPU usage
   - High memory usage
   - Deployment failures
   - Crash loops

---

## Scaling

### Vertical Scaling (More Resources)

1. Click **"Settings"** → **"Resources"**
2. Increase:
   - **Memory**: 512MB → 1GB → 2GB → 4GB
   - **CPU**: Shared → Dedicated
3. Click **"Apply"**
4. Automatic restart with new resources

### Horizontal Scaling (More Instances)

1. Click **"Settings"** → **"Replicas"**
2. Set replica count: 1 → 2 → 3+
3. Railway automatically load balances

**Cost**:
- Each replica costs the same as base instance
- 2 replicas = 2x cost

---

## Database Management

### Access Database

In Railway dashboard:
1. Click PostgreSQL service
2. Click **"Data"** tab
3. Browse tables and run queries

Or connect via CLI:
1. Click **"Connect"** tab
2. Copy connection command
3. Run in terminal:
   ```bash
   psql <connection-string>
   ```

### Backups

Railway automatically backs up PostgreSQL:
- Daily backups
- Retention: 7 days (free tier)
- Restore from **"Backups"** tab

### Manual Backup

```bash
# Get DATABASE_URL from Railway
export DATABASE_URL="postgresql://..."

# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore backup
psql $DATABASE_URL < backup_20260415.sql
```

---

## Troubleshooting

### Deployment Failed

**Check build logs**:
1. Go to **"Deployments"** tab
2. Click failed deployment
3. Check **"Build Logs"** and **"Deploy Logs"**

**Common issues**:
- Missing environment variables
- Python dependencies error → Check `requirements.txt`
- Port mismatch → Railway sets `$PORT` automatically

### Application Crashes

**Check logs**:
1. **"Logs"** tab
2. Look for error messages

**Common issues**:
- Database connection error → Check `DATABASE_URL`
- Firebase credentials missing → Check `FIREBASE_CREDENTIALS_JSON`
- Missing migrations → Run `alembic upgrade head`

### Database Connection Issues

**Verify DATABASE_URL**:
```bash
# In Railway dashboard → Backend service → Variables
# DATABASE_URL should be set automatically
```

**Test connection manually**:
```bash
# In Railway terminal
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### Can't Access API

**Check domain**:
1. **"Domains"** tab
2. Verify domain is active
3. Test with curl or browser

**Check CORS**:
- Update `ALLOWED_ORIGINS` with your frontend domain
- Include both `https://domain.com` and `https://www.domain.com`

---

## Cost Optimization

### Tips to Reduce Costs

1. **Start Small**: 512MB RAM is enough initially
2. **Monitor Usage**: Check metrics regularly
3. **Scale When Needed**: Only increase resources when hitting limits
4. **Use Free Tier**: PostgreSQL free tier covers ~10K rows
5. **Efficient Code**: Optimize queries and API endpoints

### Cost Breakdown by Scale

| Users | Backend | PostgreSQL | Total/Month |
|-------|---------|------------|-------------|
| 0-1K | $5 | Free | **$5** |
| 1K-5K | $5 | $5 | **$10** |
| 5K-10K | $10 | $10 | **$20** |
| 10K-50K | $20 | $15 | **$35** |

---

## Migration Guide (Switch Platforms Later)

The code is modular and platform-agnostic. If you need to migrate to another platform:

### Export Your Data

```bash
# Export database from Railway
railway run pg_dump $DATABASE_URL > production_backup.sql
```

### Import to New Platform

```bash
# Import to new database
psql <new-database-url> < production_backup.sql
```

---

## Railway CLI (Optional)

### Install Railway CLI

```bash
npm install -g @railway/cli
```

### Login

```bash
railway login
```

### Link Project

```bash
cd /path/to/glycogrit-backend
railway link
```

### Useful Commands

```bash
# View logs
railway logs

# Run migrations
railway run alembic upgrade head

# Open dashboard
railway open

# Deploy manually
railway up

# Set environment variable
railway variables set JWT_SECRET_KEY=<value>

# SSH into container
railway shell
```

---

## Support

- **Railway Docs**: https://docs.railway.app/
- **Railway Discord**: https://discord.gg/railway
- **Support**: support@railway.app

---

## Summary

✅ **Deployed in 5 minutes**
✅ **Zero server management**
✅ **Automatic deployments**
✅ **Built-in database**
✅ **Automatic SSL**
✅ **Fair pricing (~$5-20/month)**
✅ **Easy to scale**
✅ **Can migrate to Hetzner anytime**

**Ready to deploy?** Follow Step 1 above and you'll be live in minutes! 🚀
