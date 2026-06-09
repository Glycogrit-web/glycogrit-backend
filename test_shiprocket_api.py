import asyncio
import httpx
import os

async def test_shiprocket_serviceability():
    """Test Shiprocket API directly"""
    
    # Get token from database
    import psycopg2
    conn = psycopg2.connect(
        host="nozomi.proxy.rlwy.net",
        port=29493,
        database="railway",
        user="postgres",
        password="AXAVbrPvtStBmpObpiyoQufpkPtAvmeI"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM shiprocket_config WHERE is_active = true LIMIT 1")
    token = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    print(f"Token (first 20 chars): {token[:20]}...")
    
    # Test pincodes
    test_pincodes = ["500081", "311021", "400001", "110001"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for pincode in test_pincodes:
            print(f"\n{'='*50}")
            print(f"Testing pincode: {pincode}")
            print(f"{'='*50}")
            
            response = await client.get(
                "https://apiv2.shiprocket.in/v1/external/courier/serviceability/",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                params={
                    "delivery_postcode": pincode,
                    "pickup_pincode": "500081",  # Your pickup location
                    "weight": 0.5,
                    "length": 15,
                    "breadth": 10,
                    "height": 5,
                    "cod": 0
                }
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {data}")
                
                service_data = data.get("data", {})
                print(f"\nCity: {service_data.get('city')}")
                print(f"State: {service_data.get('state')}")
                print(f"Serviceable: {service_data.get('is_serviceable')}")
                print(f"Available Couriers: {len(service_data.get('available_courier_companies', []))}")
            else:
                print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_shiprocket_serviceability())
