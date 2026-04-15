# Deployment Guide - Hetzner VPS with GitHub Actions CI/CD

This guide will help you set up automatic deployment to your Hetzner VPS whenever you push to the `master` or `main` branch.

## Overview

The CI/CD pipeline automatically:
- Pulls latest code from GitHub
- Rebuilds Docker containers
- Runs database migrations
- Performs health checks
- Cleans up old Docker images

## Prerequisites

1. A Hetzner VPS (CPX11 or higher recommended)
2. GitHub repository with this code
3. SSH access to your VPS
4. A domain name (optional but recommended)

## Step 1: Initial VPS Setup

### 1.1 Provision Hetzner VPS

1. Go to [Hetzner Cloud](https://www.hetzner.com/cloud)
2. Create a new project
3. Add a server:
   - **Location**: Choose closest to your users
   - **Image**: Ubuntu 22.04 or 24.04
   - **Type**: CPX11 (2 vCPU, 2GB RAM) - €4.51/month
   - **SSH Key**: Add your SSH public key
4. Note the server IP address

### 1.2 Run Initial Setup Script

Copy the setup script to your VPS and run it:

```bash
# From your local machine, copy the setup script to VPS
scp deploy-setup.sh root@YOUR_VPS_IP:/root/

# SSH into your VPS
ssh root@YOUR_VPS_IP

# Run the setup script
cd /root
chmod +x deploy-setup.sh
./deploy-setup.sh
```

The script will:
- Install Docker and Docker Compose
- Install Git and Nginx
- Clone your repository
- Set up environment variables
- Configure Nginx reverse proxy
- Set up SSL with Let's Encrypt
- Start the application

### 1.3 Manual Setup (Alternative)

If you prefer manual setup, follow these commands:

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install -y docker-compose-plugin

# Install Git
apt install -y git

# Clone repository
cd /root
git clone https://github.com/YOUR_USERNAME/glycogrit-backend.git
cd glycogrit-backend

# Set up environment
cp .env.example .env
nano .env  # Edit with production values

# Upload Firebase credentials
# From your local machine:
# scp firebase-credentials.json root@YOUR_VPS_IP:/root/glycogrit-backend/

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

## Step 2: Configure GitHub Actions Secrets

GitHub Actions needs SSH access to your VPS. Set up these secrets in your GitHub repository:

### 2.1 Generate SSH Key for Deployment (if needed)

On your VPS:

```bash
# Generate a new SSH key (or use existing)
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""

# Add the public key to authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# Display the private key (you'll need this for GitHub)
cat ~/.ssh/github_deploy
```

### 2.2 Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `VPS_HOST` | Your VPS IP address or domain | `123.45.67.89` or `api.glycogrit.com` |
| `VPS_USERNAME` | SSH username (usually `root`) | `root` |
| `VPS_SSH_KEY` | Private SSH key content | Contents of `~/.ssh/github_deploy` |
| `VPS_PORT` | SSH port (optional, defaults to 22) | `22` |
| `DEPLOY_PATH` | Path to your project on VPS | `/root/glycogrit-backend` |

### How to Add Each Secret:

**VPS_HOST:**
```
Name: VPS_HOST
Value: 123.45.67.89
```

**VPS_USERNAME:**
```
Name: VPS_USERNAME
Value: root
```

**VPS_SSH_KEY:**
```
Name: VPS_SSH_KEY
Value: (paste entire private key)
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
(all lines)
...
-----END OPENSSH PRIVATE KEY-----
```

**DEPLOY_PATH:**
```
Name: DEPLOY_PATH
Value: /root/glycogrit-backend
```

## Step 3: Test the Deployment

### 3.1 Automatic Deployment (Push to master/main)

```bash
# Make a small change
echo "# Test deployment" >> README.md

# Commit and push
git add .
git commit -m "Test CI/CD deployment"
git push origin master  # or 'main'
```

Go to your GitHub repository → **Actions** tab to watch the deployment progress.

### 3.2 Manual Deployment (GitHub UI)

1. Go to **Actions** tab in your GitHub repository
2. Click **Deploy to Hetzner VPS** workflow
3. Click **Run workflow**
4. Select branch and click **Run workflow**

## Step 4: Verify Deployment

### 4.1 Check Application Health

```bash
# From your local machine
curl https://YOUR_DOMAIN/health

# Expected response:
# {"status":"healthy"}
```

### 4.2 Check Container Status on VPS

```bash
# SSH into VPS
ssh root@YOUR_VPS_IP

# Check containers
cd /root/glycogrit-backend
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 4.3 Access API Documentation

Open in browser:
- `https://YOUR_DOMAIN/docs` - Swagger UI
- `https://YOUR_DOMAIN/redoc` - ReDoc

## Step 5: Domain and SSL Setup (Optional but Recommended)

### 5.1 Point Domain to VPS

In your domain registrar's DNS settings, add an A record:

```
Type: A
Name: api (or @)
Value: YOUR_VPS_IP
TTL: 3600
```

### 5.2 Set Up SSL Certificate

The `deploy-setup.sh` script does this automatically, but you can also do it manually:

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d api.glycogrit.com

# Auto-renewal is set up automatically
certbot renew --dry-run
```

## Troubleshooting

### Deployment Failed

**Check GitHub Actions logs:**
1. Go to **Actions** tab in GitHub
2. Click on the failed workflow run
3. Review the error logs

**Common issues:**

1. **SSH connection failed**
   - Verify `VPS_HOST` and `VPS_SSH_KEY` secrets
   - Check SSH key is in `~/.ssh/authorized_keys` on VPS
   - Ensure VPS firewall allows SSH (port 22)

2. **Docker containers not starting**
   ```bash
   # SSH into VPS
   ssh root@YOUR_VPS_IP
   cd /root/glycogrit-backend

   # Check logs
   docker-compose logs

   # Restart containers
   docker-compose restart
   ```

3. **Database migration failed**
   ```bash
   # Run migrations manually
   docker-compose exec backend alembic upgrade head
   ```

4. **Health check failed**
   ```bash
   # Check if containers are running
   docker-compose ps

   # Check backend logs
   docker-compose logs backend

   # Test locally on VPS
   curl http://localhost:8000/health
   ```

### View Application Logs

```bash
# SSH into VPS
ssh root@YOUR_VPS_IP
cd /root/glycogrit-backend

# View all logs
docker-compose logs

# Follow backend logs
docker-compose logs -f backend

# Follow database logs
docker-compose logs -f db

# View last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart only backend
docker-compose restart backend

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

## Monitoring and Maintenance

### Check Container Status

```bash
docker-compose ps
docker stats  # Real-time resource usage
```

### Database Backups

```bash
# Manual backup
docker-compose exec db pg_dump -U glycogrit glycogrit > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20260415.sql | docker-compose exec -T db psql -U glycogrit -d glycogrit
```

### Update SSL Certificate

SSL certificates auto-renew, but you can manually renew:

```bash
certbot renew
systemctl reload nginx
```

### View Nginx Logs

```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Rollback Deployment

If a deployment breaks your application:

```bash
# SSH into VPS
ssh root@YOUR_VPS_IP
cd /root/glycogrit-backend

# Revert to previous commit
git log --oneline  # Find the previous commit hash
git reset --hard COMMIT_HASH

# Rebuild and restart
docker-compose up -d --build

# Run migrations (if needed)
docker-compose exec backend alembic downgrade -1
```

## Cost Optimization

### For 3K users:
- Hetzner CPX11: €4.51/month
- Domain: ~$12/year (~$1/month)
- **Total: ~$6/month**

### Scaling:
- **10K users**: Upgrade to CPX21 (€8.21/month)
- **30K users**: Upgrade to CPX31 (€15.32/month)

To upgrade VPS:
1. Create snapshot of current VPS
2. Resize VPS in Hetzner Cloud Console
3. Restart services

## Security Best Practices

1. **Change default PostgreSQL password** in `.env`
2. **Use strong JWT secret** - generate with: `openssl rand -hex 32`
3. **Keep system updated**: `apt update && apt upgrade -y`
4. **Enable firewall**:
   ```bash
   ufw allow 22    # SSH
   ufw allow 80    # HTTP
   ufw allow 443   # HTTPS
   ufw enable
   ```
5. **Regular backups** of database
6. **Never commit** `.env` or `firebase-credentials.json` to Git

## Getting Help

- **GitHub Actions failing**: Check Actions tab for error logs
- **Application not responding**: Check `docker-compose logs`
- **SSL issues**: Run `certbot renew --dry-run`
- **Database issues**: Check `docker-compose logs db`

## Summary

After setup, your deployment workflow is:

1. **Write code** locally
2. **Push to master/main** branch
3. **GitHub Actions automatically**:
   - Connects to your VPS
   - Pulls latest code
   - Rebuilds containers
   - Runs migrations
   - Performs health check
4. **Your app is live** 🎉

**Congratulations!** You now have a production-grade CI/CD pipeline at startup costs ($6/month instead of $20-30/month with Railway).
