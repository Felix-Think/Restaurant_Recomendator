"""Chain for the Restaurant Retrieval Agent."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import unicodedata

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    load_dotenv = None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute haversine distance in km."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _normalize_list_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    return [v.strip().lower() for v in str(value).split(",") if v.strip()]


def _normalize_text(value: str) -> str:
    """Lowercase and remove diacritics for fuzzy contains checks."""
    if not isinstance(value, str):
        value = str(value or "")
    value = value.lower()
    nfkd = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


_CUISINE_ALIASES = {
    "fried chicken": ["ga ran", "fried chicken", "chicken"],
    "chicken": ["ga", "ga ran", "chicken"],
    "korean": ["han quoc", "korean"],
    "bbq": ["barbecue", "nuong", "bbq"],
}


def _expand_requested(requested: Iterable[str]) -> List[str]:
    expanded: List[str] = []
    for item in requested:
        expanded.append(item)
        expanded.extend(_CUISINE_ALIASES.get(item.lower(), []))
    return expanded


def _passes_cuisine_filter(meta: Dict[str, Any], requested: List[str]) -> bool:
    if not requested:
        return True
    cuisine_fields = _normalize_list_field(meta.get("cuisines")) + _normalize_list_field(
        meta.get("categories")
    )
    # also include name/branch for dish keywords
    name_fields = [meta.get("name") or "", meta.get("branch_name") or ""]
    normalized_fields = [_normalize_text(f) for f in cuisine_fields + name_fields]
    requested_tokens = [_normalize_text(c) for c in _expand_requested(requested)]
    return any(any(token in field for field in normalized_fields) for token in requested_tokens)


def _passes_rating(meta: Dict[str, Any], rating_min: Optional[float]) -> bool:
    if rating_min is None:
        return True
    try:
        rating = float(meta.get("avg_rating"))
    except (TypeError, ValueError):
        return True
    return rating >= rating_min


def _passes_distance(meta: Dict[str, Any], distance_limit: Optional[float], user_loc: Dict[str, Any]) -> bool:
    if distance_limit is None:
        return True
    lat = meta.get("latitude")
    lng = meta.get("longitude")
    if lat in (None, "") or lng in (None, ""):
        return True
    if user_loc.get("lat") is None or user_loc.get("lng") is None:
        return True
    try:
        dist = _haversine_km(float(user_loc["lat"]), float(user_loc["lng"]), float(lat), float(lng))
    except (TypeError, ValueError):
        return True
    return dist <= distance_limit


def _best_effort_special(meta: Dict[str, Any], requirements: List[str]) -> bool:
    # Dataset lacks explicit flags; pass-through for now.
    return True if requirements is None else True


def _build_output_item(meta: Dict[str, Any], distance_km: Optional[float]) -> Dict[str, Any]:
    return {
        "name": meta.get("name") or meta.get("branch_name") or "",
        "address": meta.get("address") or "",
        "lat": float(meta["latitude"]) if meta.get("latitude") not in (None, "") else 0.0,
        "lng": float(meta["longitude"]) if meta.get("longitude") not in (None, "") else 0.0,
        "rating": float(meta["avg_rating"]) if meta.get("avg_rating") not in (None, "") else 0.0,
        "price_range": "",
        "cuisine": _normalize_list_field(meta.get("cuisines")),
        "distance_km": distance_km if distance_km is not None else 0.0,
        "url": meta.get("detail_url") or meta.get("delivery_url") or "",
    }


def retrieve_restaurants(
    query: Dict[str, Any],
    persist_dir: Path | str = "chroma/foody",
    collection_name: str = "foody_restaurants",
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieve restaurants from Chroma that satisfy the parsed query.

    Args:
        query: JSON dict from Input Parser Agent.
        persist_dir: Path where Chroma was persisted.
        collection_name: Collection name used in ingestion.

    Returns:
        {"restaurants": [ ... ]} matching the required schema.
    """
    persist_dir = Path(persist_dir)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
        collection_name=collection_name,
    )

    data = store.get(include=["metadatas"])
    metadatas = data.get("metadatas", []) or []

    user_loc = query.get("user_location") or {"lat": None, "lng": None}
    distance_limit = query.get("distance_limit_km")
    rating_min = query.get("rating_min")
    requested_cuisine = query.get("cuisine") or []
    special_req = query.get("special_requirements") or []

    results: List[Dict[str, Any]] = []
    for meta in metadatas:
        if not _passes_cuisine_filter(meta, requested_cuisine):
            continue
        if not _passes_rating(meta, rating_min):
            continue
        if not _passes_distance(meta, distance_limit, user_loc):
            continue
        if not _best_effort_special(meta, special_req):
            continue

        dist = None
        if user_loc.get("lat") is not None and user_loc.get("lng") is not None:
            try:
                dist = _haversine_km(
                    float(user_loc["lat"]),
                    float(user_loc["lng"]),
                    float(meta.get("latitude")),
                    float(meta.get("longitude")),
                )
            except (TypeError, ValueError):
                dist = None

        results.append(_build_output_item(meta, dist))

    return {"restaurants": results}


def build_retrieval_chain(
    persist_dir: Path | str = "chroma/foody",
    collection_name: str = "foody_restaurants",
):
    """
    Build a retrieval chain that closes over Chroma persistence config.

    Returns a callable: chain.invoke(query_dict) -> {"restaurants": [...]}
    """

    def _invoke(query: Dict[str, Any]) -> Dict[str, Any]:
        return retrieve_restaurants(query, persist_dir=persist_dir, collection_name=collection_name)

    class _Chain:
        def invoke(self, inp: Dict[str, Any]) -> Dict[str, Any]:
            return _invoke(inp)

    return _Chain()


def run_retrieval(
    query: Dict[str, Any],
    persist_dir: Path | str = "chroma/foody",
    collection_name: str = "foody_restaurants",
) -> Dict[str, Any]:
    """Convenience function to run retrieval once."""
    chain = build_retrieval_chain(persist_dir=persist_dir, collection_name=collection_name)
    return chain.invoke(query)
