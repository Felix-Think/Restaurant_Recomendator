"""Mongo-backed logger for interactions."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from utils.db import get_db

DEFAULT_ACTION_REWARD = {
    "impression": 0.0,
    "view": 0.0,
    "click": 0.1,
    "like": 1.0,
    "dislike": -0.5,
}


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
    except Exception:
        return None
    if s in ("", "None", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def log_interaction(
    user_id: str,
    restaurant_id: str,
    action: str,
    context: Dict[str, Any],
    reward: float = 0.0,
):
    """
    Persist an interaction event to Mongo.
    Fields: user_id, restaurant_id, timestamp, action, reward, lat, lng, intent, cuisine, price_min, price_max.
    """
    # Ghi thời gian theo múi giờ VN (UTC+7) để dễ đọc log địa phương
    ts = datetime.now(timezone(timedelta(hours=7))).isoformat()
    lat = _to_float(context.get("lat"))
    lng = _to_float(context.get("lng"))
    intent = (context.get("intent") or "").strip() or None
    cuisine = context.get("cuisine")
    if isinstance(cuisine, list):
        cuisine = ", ".join([c for c in cuisine if c])
    price_range = context.get("price_range") or {}
    price_min = _to_float(price_range.get("min"))
    price_max = _to_float(price_range.get("max"))

    action_norm = (action or "impression").strip().lower()
    reward_val = _to_float(reward)
    if reward_val is None or reward_val == 0:
        reward_val = DEFAULT_ACTION_REWARD.get(action_norm, 0.0)

    row = {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "timestamp": ts,
        "action": action_norm,
        "reward": reward_val,
        "lat": lat,
        "lng": lng,
        "intent": intent,
        "cuisine": cuisine,
        "price_min": price_min,
        "price_max": price_max,
    }

    db = get_db()
    db.interactions.insert_one(row)


__all__ = ["log_interaction"]
