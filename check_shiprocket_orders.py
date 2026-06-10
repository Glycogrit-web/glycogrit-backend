#!/usr/bin/env python3
"""Check if any Shiprocket orders exist in database"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

database_url = os.getenv("DATABASE_URL")
engine = create_engine(database_url)
session = Session(engine)

# Check ShiprocketOrder table
print("=== Shiprocket Orders ===")
result = session.execute(
    text("SELECT COUNT(*) as count FROM shiprocket_orders")
)
count = result.scalar()
print(f"Total orders: {count}")

if count > 0:
    result = session.execute(
        text("""
            SELECT 
                id, 
                order_reference, 
                shiprocket_order_id, 
                status, 
                order_sent_at,
                created_at
            FROM shiprocket_orders 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    )
    print("\nMost recent orders:")
    for row in result:
        print(f"  {row.order_reference} | Status: {row.status} | Created: {row.created_at}")

# Check UserRewards with tracking numbers
print("\n=== User Rewards with Tracking ===")
result = session.execute(
    text("SELECT COUNT(*) as count FROM user_rewards WHERE tracking_number IS NOT NULL")
)
count = result.scalar()
print(f"Rewards with tracking: {count}")

if count > 0:
    result = session.execute(
        text("""
            SELECT 
                id,
                reward_id,
                tracking_number,
                courier_partner,
                status,
                updated_at
            FROM user_rewards 
            WHERE tracking_number IS NOT NULL
            ORDER BY updated_at DESC 
            LIMIT 10
        """)
    )
    print("\nMost recent tracked rewards:")
    for row in result:
        print(f"  {row.reward_id} | AWB: {row.tracking_number} | Courier: {row.courier_partner} | Status: {row.status}")

session.close()
