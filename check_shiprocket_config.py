#!/usr/bin/env python3
"""Check Shiprocket configuration in database"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

database_url = os.getenv("DATABASE_URL")
engine = create_engine(database_url)
session = Session(engine)

result = session.execute(
    text("SELECT id, email, default_pickup_location, is_active, access_token IS NOT NULL as has_token, token_expires_at FROM shiprocket_config")
)

print("Shiprocket Configuration:")
print("=" * 80)
for row in result:
    print(f"\nConfig ID: {row.id}")
    print(f"Email: {row.email}")
    print(f"Pickup Location: {row.default_pickup_location}")
    print(f"Active: {row.is_active}")
    print(f"Has Token: {row.has_token}")
    print(f"Token Expires: {row.token_expires_at}")
    print("-" * 80)

session.close()
