"""Node wrapper for reranker."""

from __future__ import annotations

from typing import Any, Dict, List

from agent.chains.reranker import rerank_restaurants


def run(restaurants: List[Dict[str, Any]], query: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
    return rerank_restaurants(restaurants, query, top_k=top_k)


__all__ = ["run"]
