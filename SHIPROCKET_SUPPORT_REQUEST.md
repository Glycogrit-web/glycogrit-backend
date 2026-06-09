# Shiprocket API Access Request - Cloudflare/WAF Blocking Issue

## Summary
Our production server hosted on Railway (railway.app) is being blocked by Cloudflare/WAF when trying to access the Shiprocket API. Local testing with the same credentials works perfectly, confirming this is an IP-based blocking issue.

## Issue Details

### What's Happening
- **Environment**: Production server on Railway (web-production-188d1.up.railway.app)
- **API User**: admin@glycogrit.com
- **Error**: 403 Forbidden with HTML response from Cloudflare
- **Endpoint Affected**: `https://apiv2.shiprocket.in/v1/external/auth/login` (and all other endpoints)

### Error Response
```html
<html>
<head><title>403 Forbidden</title></head>
<body>
<center><h1>403 Forbidden</h1></center>
</body>
</html>
```

### What Works
✅ Same API credentials work perfectly from local machine
✅ Same API credentials work perfectly from other servers
✅ Authentication succeeds and returns valid JWT token locally
✅ Order creation succeeds with correct pickup location ("Home")

### What Doesn't Work
❌ Any request from Railway production server gets HTML 403
❌ Blocked at Cloudflare/WAF level before reaching Shiprocket API
❌ Happens for all endpoints (auth, orders, webhooks)

## Request

We need Railway's IP address ranges whitelisted in your Cloudflare/WAF configuration to allow API access from our production server.

### Our Production Details
- **Hosting Provider**: Railway (railway.app)
- **Application URL**: https://web-production-188d1.up.railway.app
- **API User Email**: admin@glycogrit.com
- **Business Account**: teamglycogrit@gmail.com

### Railway IP Ranges (approximate)
Railway uses dynamic IP addresses from AWS/GCP ranges. Common ranges include:
- AWS us-west-2: Multiple IP blocks
- GCP us-central1: Multiple IP blocks

**Note**: Railway doesn't provide exact IP ranges for shared infrastructure. We recommend:
1. Whitelisting our specific application domain/hostname, OR
2. Allowing API user (admin@glycogrit.com) from all IPs, OR
3. Providing Railway-specific IP ranges that we can request static IPs from

## Technical Verification

### Test Script Output (Local - Success)
```bash
✅ SUCCESS: Authentication successful!
   Token (first 20 chars): eyJhbGciOiJIUzI1NiI...
   Token Length: 786 characters
   ✅ API call successful - Token is valid!
```

### Production Server Output (Railway - Blocked)
```
❌ 403 Forbidden during authentication
   Email: admin@glycogrit.com
   This indicates Cloudflare/WAF is blocking Railway's IP
   Response: <html><head><title>403 Forbidden</title></head>...
```

## Impact

Our fitness platform (GlycoGrit) relies on Shiprocket for automated reward fulfillment to users who complete challenges. This blocking prevents:
- Automatic order creation for physical rewards
- Shipment tracking updates
- Label generation
- Pickup scheduling

We have successfully configured and tested the integration locally, but production deployment is blocked by this firewall issue.

## Requested Action

Please whitelist Railway's IP ranges or allow API access for admin@glycogrit.com from all IP addresses. We're using proper API user credentials (not the main account) and following all API best practices.

## Contact Information
- **Business Email**: teamglycogrit@gmail.com
- **API User Email**: admin@glycogrit.com
- **Support Priority**: High (blocking production deployment)

## Additional Notes

We've verified:
- ✅ Correct API user credentials (admin@glycogrit.com)
- ✅ Correct pickup location configuration ("Home")
- ✅ Proper JWT token handling (fresh token for each request)
- ✅ All payload fields formatted correctly
- ✅ Name splitting (first_name/last_name) implemented
- ✅ SSL verification enabled
- ✅ Proper error handling

The only remaining issue is the IP-based blocking at your Cloudflare/WAF layer.

Thank you for your assistance!

---
Generated: 2026-06-10
Application: GlycoGrit Fitness Platform
