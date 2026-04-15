# Quick Start - Deploy to Railway in 5 Minutes

## Step-by-Step Deployment

### 1. Sign Up & Connect GitHub (1 minute)
1. Go to: **https://railway.app/**
2. Click **"Start a New Project"**
3. Sign in with **GitHub**

### 2. Create Project from GitHub (1 minute)
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Search and select: **`glycogrit-backend`**
4. Railway starts deploying automatically!

### 3. Add PostgreSQL Database (30 seconds)
1. In your project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Done! `DATABASE_URL` is auto-set

### 4. Set Environment Variables (2 minutes)
Click your backend service → **"Variables"** tab

**Add these 3 variables**:

#### 1. ENVIRONMENT
```
ENVIRONMENT=production
```

#### 2. JWT_SECRET_KEY
Generate first:
```bash
openssl rand -hex 32
```
Then paste the output as value.

#### 3. FIREBASE_CREDENTIALS_JSON
```bash
# Copy your firebase credentials as single-line JSON
cat firebase-credentials.json | tr -d '\n'
```
Paste the output as value.

#### 4. ALLOWED_ORIGINS
```
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```
(Use your actual frontend domain)

### 5. Get Your API URL (30 seconds)
1. Click **"Settings"** → **"Domains"**
2. Click **"Generate Domain"**
3. Copy URL like: `https://glycogrit-backend-production.up.railway.app`

### 6. Test Your API (30 seconds)
```bash
# Health check
curl https://your-app.railway.app/health

# API docs
open https://your-app.railway.app/docs
```

## That's It! 🎉

Your backend is live with:
- ✅ Automatic HTTPS
- ✅ Managed PostgreSQL
- ✅ Auto-deploy on git push
- ✅ Automatic migrations
- ✅ Health monitoring

## Next Steps

1. **Update Frontend** - Point to your new Railway API URL
2. **Add Custom Domain** - In Railway Settings → Domains
3. **Monitor** - Check Logs and Metrics tabs
4. **Scale** - Increase resources as needed

## Useful Railway Commands

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# View logs
railway logs

# Run migrations
railway run alembic upgrade head

# Open dashboard
railway open
```

## Cost

- **Free Trial**: $5 credit
- **Starter**: $5/month (512MB RAM)
- **PostgreSQL**: Free tier or $5/month
- **Total**: ~$5-10/month

## Troubleshooting

**Deployment failed?**
- Check **"Deployments"** tab for error logs
- Verify environment variables are set

**Can't connect to database?**
- Railway auto-sets `DATABASE_URL` - don't override it
- Check PostgreSQL service is running

**Frontend can't reach API?**
- Update CORS: `ALLOWED_ORIGINS` with your frontend domain
- Check your API URL is correct

## Support

- **Full Guide**: [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- **Railway Docs**: https://docs.railway.app/
- **Discord**: https://discord.gg/railway

---

**Total Time**: 5 minutes ⏱️
**Total Cost**: ~$5-10/month 💰
**DevOps Required**: Zero! 🎉
