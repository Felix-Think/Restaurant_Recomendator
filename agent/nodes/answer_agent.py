"""Node wrapper for the answer formatter."""

from __future__ import annotations

from typing import Any, Dict, List

from agent.chains.answer_agent import format_answer


def run(restaurants: List[Dict[str, Any]], query: Dict[str, Any]) -> str:
    return format_answer(restaurants, query)


__all__ = ["run"]
