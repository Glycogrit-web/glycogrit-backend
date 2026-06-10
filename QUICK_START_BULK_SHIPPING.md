# Quick Start: Bulk Shipping with Shiprocket

## TL;DR - 3 Simple Steps

1. **Export** → Download Excel from admin dashboard
2. **Upload to Shiprocket** → Use their bulk upload feature
3. **Import** → Upload Shiprocket's result back to admin dashboard

**No proxy, no ngrok, no infrastructure setup needed!**

---

## Step-by-Step Instructions

### 1️⃣ Export Pending Shipments (2 minutes)

**In Admin Dashboard:**
```
Click: "Export for Shiprocket" button
↓
Downloads: pending_shipments.xlsx
```

**Or via API:**
```bash
curl -X GET 'https://your-api.railway.app/api/admin/rewards/export-pending-shipments' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -o pending_shipments.xlsx
```

**What's in the file:**
- All rewards with "Ready to Ship" status
- Customer names, addresses, phone numbers
- Product details and dimensions
- Empty AWB/tracking columns (to be filled by Shiprocket)

---

### 2️⃣ Upload to Shiprocket Portal (5 minutes)

**Login:**
- Go to: https://app.shiprocket.in/
- Email: `admin@glycogrit.com`
- Password: `nL$QBA7In^h0F!3jD7tldjQPwtwMzRU5`

**Upload Orders:**
1. Click **"Orders"** in sidebar
2. Click **"Bulk Upload"** or **"Upload Orders"**
3. Choose file: `pending_shipments.xlsx`
4. Review validation results
5. Set:
   - Pickup Location: **"Home"**
   - Courier: **"Auto-select cheapest"**
   - Payment: **"Prepaid"**
6. Click **"Create Orders"**
7. Wait for processing (may take a few minutes)
8. **Download order report** (this has AWB codes!)

**Important**: Save the downloaded report - you'll need it for Step 3!

---

### 3️⃣ Import Tracking Data (1 minute)

**In Admin Dashboard:**
```
Click: "Import Tracking Data" button
↓
Upload: shiprocket_order_report.xlsx (from Step 2)
↓
Shows: "48/50 orders updated successfully"
```

**Or via API:**
```bash
curl -X POST 'https://your-api.railway.app/api/admin/rewards/import-shipment-tracking' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'file=@shiprocket_order_report.xlsx'
```

**What happens:**
- System matches orders using Internal ID
- Updates tracking numbers and courier names
- Changes status to "shipped"
- Shows you success/failure summary

---

## That's It! 🎉

Your rewards are now shipped and tracking info is visible to users.

---

## Troubleshooting

### Export shows 0 rewards
- Users need to provide shipping details first
- Check reward status is "Ready to Ship"

### Shiprocket upload fails
- Check pincode is valid (6 digits)
- Check address fields are filled
- Check phone number format

### Import shows errors
- Make sure you uploaded **Shiprocket's output file**, not the original export
- Check the file has AWB codes filled in
- Verify column headers match (they should if downloaded from Shiprocket)

### Some orders failed to import
- Check error messages in response
- Fix issues and re-upload just those rows
- Common: Reward not found (was deleted), Missing AWB (Shiprocket didn't create order)

---

## Need Frontend Integration?

See [BULK_SHIPPING_WORKFLOW.md](./BULK_SHIPPING_WORKFLOW.md) for complete code examples.

---

## Advantages Over API Integration

✅ No proxy server needed
✅ No ngrok tunnel needed
✅ No IP whitelisting needed
✅ No Railway infrastructure issues
✅ Manual review before shipping
✅ Batch process hundreds of orders
✅ Uses Shiprocket's official workflow

---

## Questions?

Check the detailed guide: [BULK_SHIPPING_WORKFLOW.md](./BULK_SHIPPING_WORKFLOW.md)
