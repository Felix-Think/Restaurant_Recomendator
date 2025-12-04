"""Node wrapper for the Input Parser Agent chain."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent.chains.input_parser import build_input_parser_chain, parse_user_request

# Build a default chain once for reuse.
_DEFAULT_CHAIN = build_input_parser_chain()


def run(
    user_message: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    chain=None,
) -> Dict[str, Any]:
    """
    Execute the input parser node.

    Args:
        user_message: Raw user utterance.
        lat: Latitude if available.
        lng: Longitude if available.
        chain: Optional pre-built chain; otherwise uses the shared default chain.

    Returns:
        Parsed JSON dict following the required schema.
    """
    active_chain = chain or _DEFAULT_CHAIN
    return parse_user_request(user_message=user_message, lat=lat, lng=lng, chain=active_chain)
