# Bulk Shipping Workflow with Shiprocket

## Overview

This document describes the Excel-based bulk shipping workflow for physical rewards. This is a **two-step process** similar to certificate generation, designed to bypass Railway IP blocking issues.

## Why This Approach?

- ✅ **No proxy needed** - No need to run local servers or ngrok
- ✅ **No IP blocking** - You upload to Shiprocket directly from your browser
- ✅ **Batch processing** - Handle hundreds of shipments at once
- ✅ **Manual review** - Review all details before creating orders
- ✅ **Reliable** - Uses Shiprocket's official bulk upload feature

## Workflow Steps

### Step 1: Export Pending Shipments

**Admin Action**: Download Excel file with all pending shipments

**API Endpoint**:
```
GET /api/admin/rewards/export-pending-shipments
Query Parameters:
  - event_id (optional): Filter by specific event
```

**What You Get**:
- Excel file with all rewards in "Ready to Ship" status
- Pre-filled with customer details, addresses, product info
- Includes package dimensions and weight
- Empty columns for AWB, Tracking Number, Courier Name

**Excel Columns**:
| Column | Description | Example |
|--------|-------------|---------|
| Internal ID | Our reward UUID | `550e8400-e29b-41d4-a716-446655440000` |
| Order Reference | Unique order ID for Shiprocket | `RNR-EVT-123-USR-456-RWD-ABC12345` |
| Full Name | Customer name | `Yashvin Gujjar` |
| Address Line 1 | Street address | `Gahlot bhawan` |
| Address Line 2 | Apartment/suite | `` |
| City | City name | `Kota` |
| State | State name | `Rajasthan` |
| Pincode | Postal code | `324008` |
| Phone | Phone number | `7765098807` |
| Email | Email address | `gyash2558@gmail.com` |
| Product Name | Reward name | `Finisher Medal - Marathon 2026` |
| Product SKU | Item SKU | `MEDAL-2026-FN` |
| Weight (kg) | Package weight | `0.5` |
| Length (cm) | Package length | `15` |
| Breadth (cm) | Package breadth | `10` |
| Height (cm) | Package height | `5` |
| **AWB Code** | **Empty - filled by Shiprocket** | `` |
| **Tracking Number** | **Empty - filled by Shiprocket** | `` |
| **Courier Name** | **Empty - filled by Shiprocket** | `` |

### Step 2: Bulk Upload to Shiprocket

**Admin Action**: Upload Excel to Shiprocket portal

1. **Login to Shiprocket**:
   - Go to https://app.shiprocket.in/
   - Login with: `admin@glycogrit.com`

2. **Navigate to Bulk Upload**:
   - Click "Orders" in sidebar
   - Click "Bulk Upload" or "Upload Orders"

3. **Upload Your Excel File**:
   - Click "Choose File" and select the exported Excel
   - Shiprocket will validate the data
   - Review any errors and fix them

4. **Configure Bulk Settings**:
   - Pickup Location: Select "Home" (default)
   - Courier Selection: Choose "Auto-select cheapest"
   - Payment Method: "Prepaid" (since rewards are free)

5. **Create Orders**:
   - Click "Create Orders"
   - Shiprocket will process all orders
   - This may take a few minutes for large batches

6. **Download Order Report**:
   - After processing, download the order report
   - This Excel will have AWB codes, tracking numbers, and courier names filled in
   - **This is the file you'll upload back to our system**

### Step 3: Import Tracking Data

**Admin Action**: Upload Shiprocket's Excel back to our system

**API Endpoint**:
```
POST /api/admin/rewards/import-shipment-tracking
Content-Type: multipart/form-data
Body: Excel file from Shiprocket
```

**What Happens**:
- System reads the Excel file
- Matches orders using Internal ID or Order Reference
- Updates each reward with:
  - `tracking_number` = AWB Code
  - `courier_partner` = Courier Name
  - `status` = "shipped"
  - `shipped_at` = current timestamp
- Returns summary of successful/failed updates

**Response Example**:
```json
{
  "total_rows": 50,
  "successful_updates": 48,
  "failed_updates": 2,
  "errors": [
    "Row 5: Reward ID RNR-EVT-123-USR-456-RWD-789 not found",
    "Row 12: Missing AWB code"
  ]
}
```

## Frontend Integration

### Export Button

Add to admin dashboard (where "Ready to Ship" button currently is):

```typescript
// Button to export pending shipments
<Button
  onClick={() => exportPendingShipments(eventId)}
  variant="outline"
>
  Export for Shiprocket
</Button>

// API call
async function exportPendingShipments(eventId?: number) {
  const params = eventId ? `?event_id=${eventId}` : '';
  const response = await fetch(
    `/api/admin/rewards/export-pending-shipments${params}`,
    {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  // Download file
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'pending_shipments.xlsx';
  a.click();
}
```

### Import Button

Add file upload UI:

```typescript
// File input for uploading Shiprocket Excel
<input
  type="file"
  accept=".xlsx,.xls"
  onChange={(e) => importShipmentTracking(e.target.files[0])}
/>

// API call
async function importShipmentTracking(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    '/api/admin/rewards/import-shipment-tracking',
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    }
  );

  const result = await response.json();

  // Show results
  alert(`Success: ${result.successful_updates}/${result.total_rows} orders updated`);

  if (result.errors.length > 0) {
    console.error('Errors:', result.errors);
  }
}
```

## Excel Column Mapping (Flexible)

The import endpoint is flexible with column names. It will recognize:

| Our System | Shiprocket Variations |
|------------|----------------------|
| Internal ID | Internal ID, Internal Id, internal_id |
| Order Reference | Order Reference, Order Ref, Order ID, order_reference |
| AWB Code | AWB Code, AWB, Tracking Number, tracking_number |
| Courier Name | Courier Name, Courier Partner, courier_name |

**Column matching is case-insensitive and flexible.**

## Error Handling

Common errors and solutions:

### Export Errors
- **No pending shipments**: Users haven't provided shipping details yet
- **Missing event_id**: Make sure event exists

### Import Errors
- **"Excel must contain 'Internal ID' or 'Order Reference' column"**:
  - Make sure you're uploading Shiprocket's output file, not the original export
  - Check column headers match expected names

- **"Row X: Missing AWB code"**:
  - Shiprocket didn't create order for that row
  - Check Shiprocket portal for failed orders
  - You can remove those rows and upload the rest

- **"Row X: Reward not found"**:
  - Order reference doesn't match any reward in database
  - Verify the Internal ID or Order Reference is correct
  - May have been deleted or modified

## Advantages Over Direct API Integration

1. **No Infrastructure Issues**: No proxy servers, ngrok tunnels, or IP whitelisting needed
2. **Manual Review**: Admin can review all shipments before creating orders
3. **Batch Processing**: Handle hundreds of orders at once
4. **Error Recovery**: If some orders fail, you can fix and re-upload just those
5. **Shiprocket Features**: Use Shiprocket's bulk upload features like auto-courier selection
6. **Reliable**: Uses Shiprocket's official workflow, not reverse-engineered API

## Complete Example

```bash
# 1. Export pending shipments
curl -X GET 'https://api.glycogrit.com/api/admin/rewards/export-pending-shipments?event_id=123' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -o pending_shipments.xlsx

# 2. Upload to Shiprocket portal (manual step in browser)
# 3. Download order report from Shiprocket

# 4. Import tracking data
curl -X POST 'https://api.glycogrit.com/api/admin/rewards/import-shipment-tracking' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'file=@shiprocket_orders.xlsx'
```

## Future Enhancements

Possible improvements:
- **Auto-sync**: Periodically check Shiprocket for status updates via API
- **Webhook integration**: Receive delivery updates automatically
- **Template download**: Provide empty template for manual order entry
- **Validation**: Pre-validate addresses before export (pincode serviceability)
- **Scheduling**: Schedule bulk uploads for specific times

## Support

If you encounter issues:
1. Check Railway logs for detailed error messages
2. Verify Excel file format matches expected structure
3. Ensure all required columns are present
4. Contact Shiprocket support if orders fail to create

## Technical Details

**Database Changes**:
- Rewards updated with tracking info maintain their UUID
- Status changed from `pending_shipment` to `shipped`
- `status_history` tracks bulk import timestamp and source

**Performance**:
- Export handles 1000+ rewards in ~5 seconds
- Import processes 100 rows in ~10 seconds
- No timeout issues with large batches

**Security**:
- Both endpoints are admin-only protected
- File upload size limited to 10MB
- Only Excel formats accepted (.xlsx, .xls)
