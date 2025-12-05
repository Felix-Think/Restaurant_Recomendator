"""Node wrapper for the full flow."""

from __future__ import annotations

from typing import Any

from agent.chains.orchestrator import run_flow


def run(
    user_message: str,
    lat: float | None = None,
    lng: float | None = None,
    user_id: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    return run_flow(user_message=user_message, lat=lat, lng=lng, user_id=user_id, top_k=top_k)


__all__ = ["run"]
