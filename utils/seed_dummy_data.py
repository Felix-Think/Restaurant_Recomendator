"""Seed MongoDB with dummy users and interaction logs."""

from __future__ import annotations

import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Sequence

import pandas as pd
try:
    from utils.db import get_db
except ImportError:
    # Allow running as script
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    from utils.db import get_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_users(db, count: int = 30) -> List[Dict]:
    users = []
    for i in range(1, count + 1):
        uid = f"u{i}"
        user = {"user_id": uid, "username": f"user{i}", "password": "pass123"}
        db.users.update_one({"user_id": uid}, {"$set": user}, upsert=True)
        users.append(user)
    return users


def load_restaurant_ids(csv_path: Path | str = "data/foody_page1.csv", limit: int | None = None) -> List[str]:
    """Load restaurant_id list from Foody CSV; fallback to synthetic if missing."""
    csv_path = Path(csv_path)
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        ids = [str(r) for r in df["restaurant_id"].dropna().unique().tolist() if str(r).strip()]
        if limit:
            ids = ids[:limit]
        if ids:
            return ids
    # Fallback synthetic ids if CSV unavailable/empty
    return [str(10000 + i) for i in range(1, 201)]


def seed_logs(db, users: List[Dict], restaurants: Sequence[str], likes: int = 150, total: int = 200):
    docs = []
    for user in users:
        uid = user["user_id"]
        # 150 likes with reward 1.0
        for _ in range(likes):
            docs.append(
                {
                    "user_id": uid,
                    "restaurant_id": random.choice(restaurants),
                    "timestamp": _now_iso(),
                    "action": "like",
                    "reward": 1.0,
                    "lat": None,
                    "lng": None,
                    "intent": None,
                    "cuisine": None,
                    "price_min": None,
                    "price_max": None,
                }
            )
        # Remaining logs as clicks with reward 0.1
        for _ in range(max(total - likes, 0)):
            docs.append(
                {
                    "user_id": uid,
                    "restaurant_id": random.choice(restaurants),
                    "timestamp": _now_iso(),
                    "action": "click",
                    "reward": 0.1,
                    "lat": None,
                    "lng": None,
                    "intent": None,
                    "cuisine": None,
                    "price_min": None,
                    "price_max": None,
                }
            )
    # Insert in batches to avoid huge payloads
    batch_size = 1000
    for i in range(0, len(docs), batch_size):
        db.interactions.insert_many(docs[i : i + batch_size])


def main():
    random.seed(42)
    db = get_db()
    # Pull restaurant ids from foody CSV so CF aligns with retrieval
    restaurants = load_restaurant_ids(csv_path="data/foody_page1.csv", limit=400)
    users = seed_users(db, count=30)
    seed_logs(db, users, restaurants, likes=150, total=200)
    print(f"Seeded {len(users)} users and {len(users) * 200} interaction logs.")


if __name__ == "__main__":
    main()
