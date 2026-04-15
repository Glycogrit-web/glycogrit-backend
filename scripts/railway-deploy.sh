#!/bin/bash

# Railway Deployment Helper Script
# This script helps you deploy to Railway quickly

set -e

echo "🚂 Railway Deployment Helper"
echo "=============================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not installed"
    echo ""
    echo "Install it with:"
    echo "  npm install -g @railway/cli"
    echo ""
    echo "Or deploy via Railway web dashboard:"
    echo "  https://railway.app/"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Logging into Railway..."
    railway login
fi

echo "✅ Logged in to Railway"
echo ""

# Check if project is linked
if ! railway status &> /dev/null; then
    echo "🔗 Linking to Railway project..."
    railway link
fi

echo "✅ Project linked"
echo ""

# Generate JWT secret if needed
echo "🔑 Generating JWT secret..."
JWT_SECRET=$(openssl rand -hex 32)
echo "Generated: $JWT_SECRET"
echo ""

# Set environment variables
echo "⚙️  Setting environment variables..."
read -p "Set ENVIRONMENT to 'production'? (y/n): " set_env
if [ "$set_env" = "y" ]; then
    railway variables set ENVIRONMENT=production
fi

read -p "Set JWT_SECRET_KEY? (y/n): " set_jwt
if [ "$set_jwt" = "y" ]; then
    railway variables set JWT_SECRET_KEY=$JWT_SECRET
fi

read -p "Enter ALLOWED_ORIGINS (e.g., https://yourdomain.com): " allowed_origins
if [ ! -z "$allowed_origins" ]; then
    railway variables set ALLOWED_ORIGINS=$allowed_origins
fi

echo ""
echo "📦 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment initiated!"
echo ""
echo "📊 View deployment status:"
echo "  railway status"
echo ""
echo "📝 View logs:"
echo "  railway logs"
echo ""
echo "🌐 Open dashboard:"
echo "  railway open"
echo ""
echo "🎉 Done!"
