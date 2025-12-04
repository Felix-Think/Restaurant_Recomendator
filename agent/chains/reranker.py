"""Simple reranker for restaurant results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _parse_price_range(value: str) -> tuple[Optional[float], Optional[float]]:
    if not value:
        return None, None
    parts = value.split("-")
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None, None
    try:
        v = float(parts[0])
        return v, v
    except Exception:
        return None, None


def _price_fits(user_range: Dict[str, Any], item_range: str) -> bool:
    umin, umax = user_range.get("min"), user_range.get("max")
    imin, imax = _parse_price_range(item_range)
    if imin is None and imax is None:
        return True  # no data, do not block
    if umin is not None and imax is not None and imax < umin:
        return False
    if umax is not None and imin is not None and imin > umax:
        return False
    return True


def rerank_restaurants(
    restaurants: List[Dict[str, Any]],
    query: Dict[str, Any],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Score and rerank results by distance, rating, and price fit."""
    user_price = query.get("price_range") or {}
    rating_min = query.get("rating_min")

    scored: List[tuple[float, Dict[str, Any]]] = []
    for r in restaurants:
        score = 0.0

        # Rating
        score += float(r.get("rating", 0.0)) * 1.5
        if rating_min and r.get("rating") and r["rating"] < rating_min:
            score -= 2.0

        # Distance (closer is better)
        dist = r.get("distance_km")
        if dist is not None:
            score += max(0, 5 - dist)  # simple decay

        # Price fit
        if user_price and (user_price.get("min") is not None or user_price.get("max") is not None):
            if _price_fits(user_price, r.get("price_range", "")):
                score += 2.0
            else:
                score -= 3.0

        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]


__all__ = ["rerank_restaurants"]
