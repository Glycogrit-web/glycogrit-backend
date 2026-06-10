#!/usr/bin/env python3
"""Check actual shipping_details structure in database"""

import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

database_url = os.getenv("DATABASE_URL")
engine = create_engine(database_url)
session = Session(engine)

result = session.execute(
    text("SELECT id, reward_id, shipping_details FROM user_rewards WHERE shipping_details IS NOT NULL LIMIT 5")
)

print("Current shipping_details in database:")
print("=" * 80)
for row in result:
    print(f"\nReward ID: {row.id}")
    print(f"Business ID: {row.reward_id}")
    print(f"Shipping Details: {json.dumps(row.shipping_details, indent=2)}")
    print("-" * 80)

session.close()
