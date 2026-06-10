#!/usr/bin/env python3
"""
Test Shiprocket order creation with verify=False
"""

import asyncio
import httpx

# Shiprocket token (from database)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEwMzk5NTU1LCJzb3VyY2UiOiJzci1hdXRoLWludCIsImV4cCI6MTc4MTkxOTk2NSwianRpIjoiTTJjWWdxS0VXSW9NQzdIUiIsImlhdCI6MTc4MTA1NTk2NSwiaXNzIjoiaHR0cHM6Ly9zci1hdXRoLnNoaXByb2NrZXQuaW4vYXV0aG9yaXplL3VzZXIiLCJuYmYiOjE3ODEwNTU5NjUsImNpZCI6MTAxMjI2MjQsInRjIjozNjAsInZlcmJvc2UiOmZhbHNlLCJ2ZW5kb3JfaWQiOjAsInZlbmRvcl9jb2RlIjoiIn0.I3sbjd9GQDLwuMXfgB3u6zXJcm06VSObhW16mmSoE2I"

# Test order payload
payload = {
    "order_id": "TEST-ORDER-2026-06-10-001",
    "order_date": "2026-06-10 10:00:00",
    "pickup_location": "Home",
    "billing_customer_name": "Test Customer",
    "billing_first_name": "Test",
    "billing_last_name": "Customer",
    "billing_address": "123 Test Street",
    "billing_address_2": "",
    "billing_city": "Mumbai",
    "billing_pincode": "400001",
    "billing_state": "Maharashtra",
    "billing_country": "India",
    "billing_email": "test@example.com",
    "billing_phone": "9876543210",
    "shipping_is_billing": True,
    "order_items": [
        {
            "name": "Test Medal",
            "sku": "TEST-MEDAL-001",
            "units": 1,
            "selling_price": "0",
            "discount": "0",
            "tax": "0",
            "hsn": "",
        }
    ],
    "payment_method": "Prepaid",
    "sub_total": 0,
    "length": 15.0,
    "breadth": 10.0,
    "height": 5.0,
    "weight": 0.5,
}


async def test_order_creation():
    """Test order creation with verify=False"""

    print("=" * 70)
    print("Testing Shiprocket Order Creation")
    print("=" * 70)
    print()
    print("Configuration:")
    print(f"  Endpoint: https://apiv2.shiprocket.in/v1/external/orders/create/adhoc")
    print(f"  verify=False: YES (bypassing SSL verification)")
    print(f"  Token: {TOKEN[:30]}...")
    print()
    print("Test Payload:")
    print(f"  Order ID: {payload['order_id']}")
    print(f"  Customer: {payload['billing_customer_name']}")
    print(f"  City: {payload['billing_city']}, {payload['billing_state']}")
    print(f"  Pincode: {payload['billing_pincode']}")
    print()

    try:
        print("🔗 Sending request to Shiprocket...")
        print()

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                "https://apiv2.shiprocket.in/v1/external/orders/create/adhoc",
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
            )

            print(f"📡 Response Status: {response.status_code}")
            print()

            if response.status_code == 200:
                print("✅ SUCCESS - Order created!")
                print()
                data = response.json()
                print("Response data:")
                print(f"  Order ID: {data.get('order_id')}")
                print(f"  Shipment ID: {data.get('shipment_id')}")
                print(f"  Status Code: {data.get('status_code')}")
                print()
                print("Full response:")
                import json
                print(json.dumps(data, indent=2))

            elif response.status_code == 403:
                print("❌ 403 FORBIDDEN")
                print()

                # Check if it's HTML (Cloudflare/WAF)
                response_text = response.text[:500]
                is_html = response_text.strip().startswith("<html") or response_text.strip().startswith("<!DOCTYPE")

                if is_html:
                    print("⚠️  This is an HTML response (Cloudflare/WAF blocking)")
                    print("   Railway's IP is blocked by Shiprocket's firewall")
                    print("   verify=False does NOT bypass IP blocking")
                    print()
                    print("First 500 chars of response:")
                    print(response_text)
                else:
                    print("This is a JSON/API error response:")
                    print(response.text[:500])

            elif response.status_code == 401:
                print("❌ 401 UNAUTHORIZED")
                print("   Token is invalid or expired")
                print()
                print("Response:")
                print(response.text[:500])

            else:
                print(f"❌ ERROR {response.status_code}")
                print()
                print("Response:")
                print(response.text[:500])

    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        print()
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_order_creation())
