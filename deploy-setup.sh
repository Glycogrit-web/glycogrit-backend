#!/bin/bash

# GlycoGrit Backend - Hetzner VPS Initial Setup Script
# Run this script on your Hetzner VPS for first-time setup

set -e

echo "🚀 GlycoGrit Backend - Initial VPS Setup"
echo "========================================"

# Update system packages
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    apt install -y docker-compose-plugin
else
    echo "✅ Docker Compose already installed"
fi

# Install Git
if ! command -v git &> /dev/null; then
    echo "📥 Installing Git..."
    apt install -y git
else
    echo "✅ Git already installed"
fi

# Create deployment directory
DEPLOY_DIR="/root/glycogrit-backend"
echo "📁 Creating deployment directory: $DEPLOY_DIR"
mkdir -p $DEPLOY_DIR

# Clone repository (you'll need to provide your repo URL)
echo "📥 Cloning repository..."
read -p "Enter your GitHub repository URL (e.g., https://github.com/username/glycogrit-backend.git): " REPO_URL

if [ -d "$DEPLOY_DIR/.git" ]; then
    echo "✅ Repository already cloned, pulling latest changes..."
    cd $DEPLOY_DIR
    git pull
else
    git clone $REPO_URL $DEPLOY_DIR
    cd $DEPLOY_DIR
fi

# Set up environment file
if [ ! -f ".env" ]; then
    echo "⚙️  Setting up environment file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your production values:"
    echo "   - Update POSTGRES_PASSWORD with a secure password"
    echo "   - Update DATABASE_URL with the new password"
    echo "   - Add your Firebase credentials path"
    echo "   - Update ALLOWED_ORIGINS with your frontend domain"
    echo "   - Change JWT_SECRET_KEY to a secure random string"
    echo ""
    read -p "Press Enter to edit .env file now..."
    nano .env
else
    echo "✅ .env file already exists"
fi

# Set up Firebase credentials
echo ""
echo "🔐 Firebase Setup:"
echo "Please upload your firebase-credentials.json file to this server."
echo "You can use: scp firebase-credentials.json root@your-vps-ip:$DEPLOY_DIR/"
read -p "Press Enter after you've uploaded the file..."

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec -T backend alembic upgrade head || echo "⚠️  Migration setup - will run on first deployment"

# Install and configure Nginx
echo "🌐 Setting up Nginx reverse proxy..."
apt install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration
read -p "Enter your domain name (e.g., api.glycogrit.com): " DOMAIN_NAME

cat > /etc/nginx/sites-available/glycogrit << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/glycogrit /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t && systemctl reload nginx

# Set up SSL with Let's Encrypt
echo "🔒 Setting up SSL certificate..."
certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME || echo "⚠️  SSL setup failed - you can run 'certbot --nginx -d $DOMAIN_NAME' manually later"

# Set up automatic certificate renewal
systemctl enable certbot.timer
systemctl start certbot.timer

# Check status
echo ""
echo "✅ Setup completed!"
echo "===================="
echo ""
echo "📊 Container Status:"
docker-compose ps
echo ""
echo "🌐 Your API should be accessible at:"
echo "   http://$DOMAIN_NAME (will redirect to HTTPS)"
echo "   https://$DOMAIN_NAME"
echo ""
echo "📚 API Documentation:"
echo "   https://$DOMAIN_NAME/docs"
echo ""
echo "🔧 Useful commands:"
echo "   cd $DEPLOY_DIR"
echo "   docker-compose logs -f backend    # View logs"
echo "   docker-compose restart           # Restart services"
echo "   docker-compose ps                # Check status"
echo ""
echo "⚠️  Next steps:"
echo "   1. Verify your .env file has correct production values"
echo "   2. Ensure firebase-credentials.json is uploaded"
echo "   3. Test your API endpoints"
echo "   4. Set up GitHub Actions secrets (see DEPLOYMENT.md)"
echo ""
