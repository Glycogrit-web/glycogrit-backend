# Shiprocket Configuration Reference

## Account Details

### API Access Account
- **Email**: `admin@glycogrit.com`
- **Password**: `V56$%zynS8M$FNB0@6ml^u6zHPXopv^I`
- **Company ID**: 10122624
- **2FA**: Disabled (required for API access)

### Primary Account (Web Access Only)
- **Email**: `teamglycogrit@gmail.com`
- **Password**: `YAGa@2558:GW$62`
- **Contact**: 9694130492
- **2FA**: Enabled (cannot be used for CLI/API)

## Pickup Location

### Default Warehouse
```
Name: Gahlot House
Address: Ground Floor
         Gyan Sarover Colony
         Tiraya, Rajasthan 324008
         India
City: Kota
State: Rajasthan
Pincode: 324008
Country: India
```

### Usage in API
When creating orders, use:
```python
{
  "pickup_location": "Home",  # As configured in database
  "pickup_address": "Ground Floor, Gyan Sarover Colony, Tiraya",
  "pickup_city": "Kota",
  "pickup_state": "Rajasthan",
  "pickup_pincode": "324008"
}
```

## Package Dimensions (Defaults)

As configured in database:

```python
default_length = 15   # cm
default_breadth = 10  # cm
default_height = 5    # cm
default_weight = 0.5  # kg
```

These are used for:
- Medals
- Certificates
- Other small rewards

## Database Configuration

The Shiprocket configuration is stored in:
- **Table**: `shiprocket_config`
- **Database**: Railway PostgreSQL
- **Connection**: `postgresql://postgres:...@nozomi.proxy.rlwy.net:29493/railway`

### Current Active Config
```sql
SELECT
  email,
  default_pickup_location,
  default_length,
  default_breadth,
  default_height,
  default_weight,
  auto_generate_label,
  auto_schedule_pickup
FROM shiprocket_config
WHERE is_active = TRUE;
```

Result:
```
email: admin@glycogrit.com
default_pickup_location: Home
default_length: 15
default_breadth: 10
default_height: 5
default_weight: 0.5
auto_generate_label: TRUE
auto_schedule_pickup: FALSE
```

## Shiprocket Dashboard Access

### Web Portal
- URL: https://app.shiprocket.in/
- Login with: `teamglycogrit@gmail.com` (2FA enabled)

### API Documentation
- URL: https://apidocs.shiprocket.in/
- Base URL: `https://apiv2.shiprocket.in/v1/external`

## CLI Usage

### Authentication
```bash
./shiprocket login
```

Use credentials:
- Email: `admin@glycogrit.com`
- Password: `V56$%zynS8M$FNB0@6ml^u6zHPXopv^I`

### Credentials Storage
```
~/.shiprocket/credentials.json
```

File permissions: `600` (read/write owner only)
Directory permissions: `700` (owner only)

## Security Notes

1. **API Account** (`admin@glycogrit.com`)
   - No 2FA (required for programmatic access)
   - Only for API/CLI usage
   - Password stored in database (encrypted in production)
   - Token validity: 10 days

2. **Primary Account** (`teamglycogrit@gmail.com`)
   - 2FA enabled (more secure)
   - For web dashboard access only
   - Cannot be used for CLI/API

3. **Recommendation**
   - Keep `admin@glycogrit.com` for automation
   - Use `teamglycogrit@gmail.com` for manual operations
   - Consider IP whitelisting for API account

## Order Creation Flow

1. **Create Order** (`POST /orders/create/adhoc`)
   - Order reference: `RNR-EVT-{event_id}-USR-{user_id}-RWD-{reward_id}`
   - Pickup location: Home (Kota warehouse)
   - Package dimensions from config

2. **Assign AWB** (`POST /courier/assign/awb`)
   - Gets tracking number
   - Selects best courier automatically

3. **Generate Label** (`POST /courier/generate/label`)
   - Auto-generated if `auto_generate_label = TRUE`
   - Returns PDF URL

4. **Schedule Pickup** (`POST /courier/generate/pickup`)
   - Manual trigger (not auto)
   - Schedule when ready to ship

5. **Track Shipment** (`GET /courier/track/shipment/{id}`)
   - Real-time tracking
   - Webhook updates

## Webhook Configuration

### Webhook URL
```
https://your-backend.com/api/shiprocket/webhook
```

### Webhook Secret
Stored in database: `shiprocket_config.webhook_secret`

### Handled Events
- Order status updates
- Tracking updates
- Delivery confirmation
- Return initiation
- Courier assignment

## Testing

### Test Pincode Serviceability
```bash
./shiprocket pincode 324008  # Tiraya, Rajasthan
./shiprocket pincode 110001  # Delhi
./shiprocket pincode 400001  # Mumbai
```

### Test Tracking
```bash
./shiprocket track <AWB_NUMBER>
```

Replace `<AWB_NUMBER>` with actual tracking number from your orders.

## Troubleshooting

### 403 Forbidden
- Usually means 2FA is enabled
- Solution: Use `admin@glycogrit.com` account

### SSL Certificate Error
- CLI automatically disables SSL verification
- Common with corporate proxies

### Token Expired
- CLI auto-refreshes tokens
- Manual refresh: `./shiprocket test`

### Invalid Pickup Location
- Ensure "Home" location is configured in Shiprocket dashboard
- Verify address matches database config

## Future Enhancements

- [ ] Add order creation via CLI
- [ ] Bulk shipment operations
- [ ] Webhook log viewer
- [ ] Label PDF download
- [ ] Manifest generation
- [ ] Return order handling
- [ ] Courier rate comparison

## Support

For Shiprocket API issues:
- Email: support@shiprocket.in
- Phone: 1800-419-4455
- Portal: https://support.shiprocket.in/

For CLI issues:
- Check logs in `~/.shiprocket/`
- Run: `./shiprocket test`
- Review [DEMO.md](DEMO.md) and [README.md](README.md)
