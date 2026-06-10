# Shiprocket Proxy Setup Guide

## Problem
Railway's IP address is blocked by Shiprocket's Cloudflare/WAF firewall. This prevents the backend from creating orders directly.

## Solution
Route Shiprocket API requests through a local proxy server running on your machine.

## One-Time Setup

### 1. Install ngrok (if not installed)
```bash
brew install ngrok
```

### 2. Start the Proxy Server (Terminal 1)
```bash
cd /Users/ygahlot/mac-one-Personal-projects/runnersParadise/glycogrit-backend
doppler run -- python3 shiprocket_proxy.py
```

You should see:
```
Starting proxy server on http://localhost:8001
```

### 3. Expose Proxy via ngrok (Terminal 2)
```bash
ngrok http 8001
```

You should see output like:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8001
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

### 4. Update Railway Environment Variable

Go to Railway dashboard and add:
```
SHIPROCKET_PROXY_URL=https://abc123.ngrok.io
```

(Replace with your actual ngrok URL)

### 5. Redeploy Railway Backend

Railway will automatically redeploy when you update the environment variable.

### 6. Test

Click "Ready to Ship" in the admin dashboard. Orders should now be created successfully!

## How It Works

```
Railway Backend → ngrok tunnel → Your Local Proxy → Shiprocket API
     (blocked)                    (allowed)          (✅ success)
```

1. Railway sends request to your ngrok URL
2. ngrok forwards to your local proxy (localhost:8001)
3. Local proxy forwards to Shiprocket from your IP (not blocked)
4. Response flows back through the same path

## Daily Usage

Every time you want to use Shiprocket:

1. **Terminal 1**: `doppler run -- python3 shiprocket_proxy.py`
2. **Terminal 2**: `ngrok http 8001`
3. Make sure ngrok URL hasn't changed (if it did, update Railway env var)

## Important Notes

- ⚠️ **Keep both terminals running** while using Shiprocket features
- ⚠️ **Free ngrok URLs change** every time you restart ngrok
- ⚠️ Consider **ngrok paid plan** ($10/month) for permanent URL
- ⚠️ **Don't close your laptop** or the proxy will stop working

## Alternative: Permanent Solution

Contact Shiprocket support to whitelist Railway's IP ranges:
- Use [SHIPROCKET_SUPPORT_REQUEST.md](SHIPROCKET_SUPPORT_REQUEST.md)
- Ask them to whitelist Railway IPs or disable IP blocking for your API user

## Troubleshooting

### Proxy not starting
- Make sure port 8001 is not in use: `lsof -i :8001`
- Check Doppler is configured: `doppler setup`

### ngrok tunnel closed
- Restart ngrok: `ngrok http 8001`
- Update Railway env var with new URL

### Still getting 403 errors
- Check proxy logs (Terminal 1) for errors
- Verify ngrok URL is correct in Railway
- Restart Railway deployment after env var change

### Token expired
Run the token update script:
```bash
doppler run -- python3 update_shiprocket_token.py
```

## Token Management

The token needs to be refreshed every 9 days (or when permissions change):

```bash
# From backend directory
doppler run -- python3 update_shiprocket_token.py
```

This updates the Railway database with a fresh token generated from your local machine.
