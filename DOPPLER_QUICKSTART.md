# Doppler Secrets Management - Quick Start Guide

## What is Doppler?

Doppler is a secrets management platform that:
- Stores environment variables securely
- Syncs secrets across teams and environments
- Integrates with CI/CD (GitHub Actions, GitLab CI, etc.)
- Provides audit logs for secret access
- **Free tier**: Up to 5 users, unlimited secrets

## Why Use Doppler?

✅ **No .env files in git** - Secrets never committed
✅ **Team collaboration** - Everyone has access to secrets
✅ **Environment management** - Dev, staging, production configs
✅ **CI/CD integration** - Automatic secret injection
✅ **Audit trail** - Know who accessed what and when
✅ **Secret rotation** - Update secrets in one place

## Quick Setup (5 minutes)

### Step 1: Install Doppler CLI

**macOS**:
```bash
brew install dopplerhq/cli/doppler
```

**Linux**:
```bash
(curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh || wget -t 3 -qO- https://cli.doppler.com/install.sh) | sudo sh
```

**Windows**:
```powershell
scoop install doppler
```

**Verify installation**:
```bash
doppler --version
```

### Step 2: Sign Up for Doppler

1. Go to [https://dashboard.doppler.com/register](https://dashboard.doppler.com/register)
2. Sign up with GitHub or email
3. Create a new project: **glycogrit-backend**

### Step 3: Login via CLI

```bash
doppler login
```

This opens your browser for authentication.

### Step 4: Setup Project

```bash
# Navigate to your project directory
cd /path/to/glycogrit-backend

# Initialize Doppler
doppler setup
```

**Follow the prompts**:
- Select project: `glycogrit-backend`
- Select config: `dev` (for local development)

This creates a `.doppler.yaml` file (already included in this repo).

### Step 5: Add Your Secrets

```bash
# Open Doppler dashboard
doppler open

# Or add secrets via CLI
doppler secrets set POSTGRES_PASSWORD="your-secure-password"
doppler secrets set JWT_SECRET_KEY="your-jwt-secret"
doppler secrets set FIREBASE_CREDENTIALS_PATH="./firebase-credentials.json"
```

### Step 6: Run Your Application with Doppler

**Instead of**:
```bash
uvicorn app.main:app --reload
```

**Use**:
```bash
doppler run -- uvicorn app.main:app --reload
```

**With Docker Compose**:
```bash
doppler run -- docker-compose up
```

## Environment Configurations

### Development (dev)
Local development on your machine.

```bash
doppler setup --config dev
doppler run -- uvicorn app.main:app --reload
```

### Staging (stg)
Testing environment before production.

```bash
doppler setup --config stg
doppler run -- docker-compose up
```

### Production (prd)
Live production environment.

```bash
doppler setup --config prd
doppler run -- docker-compose up
```

## Secrets to Add

Add these secrets in Doppler dashboard:

### Database
```
POSTGRES_USER=glycogrit
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=glycogrit
POSTGRES_PORT=5432
DATABASE_URL=postgresql://glycogrit:<password>@localhost:5432/glycogrit
```

### Backend
```
BACKEND_PORT=8000
ENVIRONMENT=development
```

### Firebase
```
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
```

### CORS
```
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### JWT
```
JWT_SECRET_KEY=<generate-random-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Generate secure secrets**:
```bash
# Generate JWT secret (32 bytes)
openssl rand -hex 32

# Generate password (16 characters)
openssl rand -base64 16
```

## CI/CD Integration (GitHub Actions)

### Step 1: Get Doppler Service Token

```bash
# Create a service token for GitHub Actions
doppler configs tokens create github-actions --config prd
```

Copy the token (starts with `dp.st.`).

### Step 2: Add to GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click **New repository secret**
4. Name: `DOPPLER_TOKEN`
5. Value: Paste the service token

### Step 3: Update GitHub Actions Workflow

Already configured in [.github/workflows/deploy.yml](.github/workflows/deploy.yml):

```yaml
- name: Install Doppler CLI
  uses: dopplerhq/cli-action@v2

- name: Deploy with Doppler secrets
  env:
    DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
  run: |
    doppler run --config prd -- docker-compose up -d
```

## Common Commands

### View Secrets
```bash
# List all secrets
doppler secrets

# Get specific secret
doppler secrets get DATABASE_URL

# Download secrets as .env file (for debugging)
doppler secrets download --no-file --format env > .env.local
```

### Switch Environments
```bash
# Switch to staging
doppler setup --config stg

# Switch to production
doppler setup --config prd

# Check current config
doppler configure get
```

### Update Secrets
```bash
# Update single secret
doppler secrets set JWT_SECRET_KEY="new-secret"

# Bulk upload from file
doppler secrets upload .env.example
```

### Team Management
```bash
# Invite team member (via dashboard)
doppler open

# Or via CLI
doppler workplace users add user@example.com
```

## Vercel Integration (Optional)

If deploying to Vercel:

```bash
# Install Vercel CLI
npm i -g vercel

# Link Doppler to Vercel
doppler integration setup vercel

# Deploy with Doppler secrets
doppler run -- vercel deploy
```

## Migration from .env to Doppler

### Step 1: Upload Existing .env
```bash
# Upload all secrets from .env file
doppler secrets upload .env --config dev
```

### Step 2: Verify Secrets
```bash
# Check all secrets are uploaded
doppler secrets
```

### Step 3: Update Your Workflow
```bash
# Before
python app/main.py

# After
doppler run -- python app/main.py
```

### Step 4: Remove .env from Git (if tracked)
```bash
# Remove from git history
git rm --cached .env

# Ensure it's in .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Commit
git add .gitignore
git commit -m "Remove .env from git, using Doppler"
```

## Security Best Practices

1. **Never commit .env files** - Use `.gitignore`
2. **Use service tokens for CI/CD** - Not personal tokens
3. **Rotate secrets regularly** - Update in Doppler, not code
4. **Use different configs** - dev, stg, prd separation
5. **Enable audit logs** - Track secret access
6. **Limit access** - Only give team members necessary permissions

## Troubleshooting

### Issue: "Command not found: doppler"
**Solution**: Install Doppler CLI (see Step 1)

### Issue: "Project not found"
**Solution**: Run `doppler setup` and select the correct project

### Issue: "Unauthorized"
**Solution**: Run `doppler login` to re-authenticate

### Issue: Secrets not loading
```bash
# Check current config
doppler configure get

# Verify secrets exist
doppler secrets

# Test run with debug
doppler run --debug -- echo "test"
```

### Issue: CI/CD failing
**Solution**: Ensure `DOPPLER_TOKEN` is added to GitHub secrets

## NPM Scripts (Optional)

Add to `package.json` or create shell scripts:

```bash
# scripts/dev.sh
#!/bin/bash
doppler run -- uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# scripts/prod.sh
#!/bin/bash
doppler run --config prd -- uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Make executable
chmod +x scripts/*.sh
```

## Cost

- **Free tier**: Up to 5 users, unlimited secrets, unlimited projects
- **Team tier**: $12/user/month (if you need more than 5 users)

For small teams and startups, the free tier is more than sufficient.

## Documentation

- **Doppler Docs**: https://docs.doppler.com/
- **CLI Reference**: https://docs.doppler.com/docs/cli
- **Integrations**: https://docs.doppler.com/docs/integrations

## Support

- **Dashboard**: https://dashboard.doppler.com/
- **Community**: https://community.doppler.com/
- **Support Email**: support@doppler.com

## Summary

**Before Doppler**:
```bash
# Secrets in .env (risky)
cat .env
export $(cat .env | xargs)
uvicorn app.main:app
```

**With Doppler**:
```bash
# Secrets in Doppler (secure)
doppler run -- uvicorn app.main:app
```

**Benefits**:
- ✅ No secrets in git
- ✅ Team collaboration
- ✅ Environment management
- ✅ CI/CD integration
- ✅ Audit trail
- ✅ Free for small teams

---

**Ready to start?** Run `doppler login` and follow Step 4 above!
