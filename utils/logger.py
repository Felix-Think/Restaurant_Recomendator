"""Simple CSV logger for interactions."""

from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_LOG = Path("data/interactions_log.csv")

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
    log_path: Path | str = DEFAULT_LOG,
):
    """
    Append an interaction row to CSV.
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

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()

    with log_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)


__all__ = ["log_interaction", "DEFAULT_LOG"]
