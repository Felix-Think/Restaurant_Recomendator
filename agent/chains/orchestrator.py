"""Orchestrator: parse -> retrieval -> rerank -> answer."""

from __future__ import annotations

from typing import Any, Dict, List

from agent.nodes.input_parser import run as parse_input
from agent.nodes.retrieval_agent import run as run_retrieval
from agent.chains.answer_agent import format_answer
from agent.chains.bandit import bandit_rerank, SimpleLinUCB
from agent.chains.cf_online import cf_rerank
from agent.chains.cf_model import CFModel, trigger_retrain_if_needed
cf_model = CFModel()
def run_flow(
    user_message: str,
    lat: float | None = None,
    lng: float | None = None,
    user_id: str | None = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Execute full pipeline and return structured output plus formatted answer."""
    parsed = parse_input(user_message, lat=lat, lng=lng)
    # trigger background CF retrain if log grew enough
    trigger_retrain_if_needed() # neu du  n samples
    retrieved = run_retrieval(parsed, top_k=top_k)
    restaurants: List[Dict[str, Any]] = retrieved.get("restaurants", [])
    # CF rerank: prefer trained model if available, else fallback to online CF
    if user_id:
        if cf_model.available():
            restaurants = cf_model.rerank(user_id, restaurants, top_k=top_k)
        else:
            restaurants = cf_rerank(restaurants, user_id=user_id, top_k=top_k)
    # Bandit rerank (placeholder model) using cf_score feature
    bandit_ranked, _ = bandit_rerank(restaurants, parsed, top_k=top_k, model=SimpleLinUCB())
    answer = format_answer(bandit_ranked, parsed)
    return {"parsed": parsed, "restaurants": bandit_ranked, "answer": answer}


__all__ = ["run_flow"]
