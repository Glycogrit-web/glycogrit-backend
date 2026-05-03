import sys
sys.path.insert(0, '/Users/ygahlot/mac-one-Personal-projects/runnersParadise/glycogrit-backend')

from app.models.user_reward import UserReward
from app.core.database import get_db

db = next(get_db())
rewards = db.query(UserReward).filter(UserReward.event_id == 27).all()

for reward in rewards:
    print(f"\n{'='*60}")
    print(f"Reward ID: {reward.id}")
    print(f"User: {reward.user_id}, Event: {reward.event_id}")
    print(f"Reward: {reward.reward_name}")
    print(f"Status: {reward.status.value if reward.status else None}")
    print(f"Is Unlocked: {reward.is_unlocked}")
    print(f"Tracking Number: {reward.tracking_number}")
    print(f"Courier Partner: {reward.courier_partner}")
    print(f"Tracking URL: {reward.tracking_url}")
    print(f"\nto_dict() output:")
    d = reward.to_dict()
    print(f"  - tracking_number: {d.get('tracking_number')}")
    print(f"  - courier_partner: {d.get('courier_partner')}")
    print(f"  - tracking_url: {d.get('tracking_url')}")

db.close()
