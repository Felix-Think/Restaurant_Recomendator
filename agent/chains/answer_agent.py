"""Simple answer formatter for restaurant results."""

from __future__ import annotations

from typing import Any, Dict, List


def format_answer(restaurants: List[Dict[str, Any]], query: Dict[str, Any]) -> str:
    """Create a human-readable answer from retrieval results."""
    if not restaurants:
        return "Không tìm thấy quán phù hợp."

    lines = []
    lines.append("Gợi ý quán:")
    for r in restaurants:
        parts = [
            f"- {r.get('name', '')}",
            r.get("address", ""),
        ]
        extra = []
        if r.get("distance_km") is not None:
            extra.append(f"{r['distance_km']:.2f} km")
        if r.get("rating"):
            extra.append(f"rating {r['rating']}")
        if r.get("price_range"):
            extra.append(f"giá {r['price_range']}")
        if r.get("opening_hours"):
            extra.append(f"giờ {r['opening_hours']}")
        if extra:
            parts.append(f"({'; '.join(extra)})")
        lines.append(" | ".join(p for p in parts if p))
        if r.get("url"):
            lines.append(f"  {r['url']}")
    return "\n".join(lines)


__all__ = ["format_answer"]
