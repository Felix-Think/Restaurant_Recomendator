"""Orchestrator: parse -> retrieval -> rerank -> answer."""

from __future__ import annotations

from typing import Any, Dict, List

from agent.nodes.input_parser import run as parse_input
from agent.nodes.retrieval_agent import run as run_retrieval
from agent.chains.reranker import rerank_restaurants
from agent.chains.answer_agent import format_answer
from agent.chains.bandit import bandit_rerank, SimpleLinUCB


def run_flow(
    user_message: str,
    lat: float | None = None,
    lng: float | None = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """Execute full pipeline and return structured output plus formatted answer."""
    parsed = parse_input(user_message, lat=lat, lng=lng)
    retrieved = run_retrieval(parsed, top_k=top_k)
    restaurants: List[Dict[str, Any]] = retrieved.get("restaurants", [])
    # First pass rerank (static weights)
    #reranked = rerank_restaurants(restaurants, parsed, top_k=top_k)
    # Bandit rerank (placeholder model)
    bandit_ranked, _ = bandit_rerank(restaurants, parsed, top_k=top_k, model=SimpleLinUCB())
    answer = format_answer(bandit_ranked, parsed)
    return {"parsed": parsed, "restaurants": bandit_ranked, "answer": answer}


__all__ = ["run_flow"]
