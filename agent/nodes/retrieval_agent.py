"""Node wrapper for the Restaurant Retrieval Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from agent.chains.retrieval_agent import build_retrieval_chain, run_retrieval

# Build a shared default chain
_DEFAULT_CHAIN = build_retrieval_chain()


def run(
    query: Dict[str, Any],
    persist_dir: Path | str = "chroma/foody",
    collection_name: str = "foody_restaurants",
    top_k: int = 3,
    chain=None,
) -> Dict[str, Any]:
    """
    Execute the retrieval node with the parsed query.
    Returns {"restaurants": [...]}
    """
    if chain is None:
        chain = _DEFAULT_CHAIN
    enriched_query = query | {"persist_dir": persist_dir, "collection_name": collection_name, "top_k": top_k}
    return chain.invoke(enriched_query)


__all__ = ["run", "build_retrieval_chain", "run_retrieval"]
