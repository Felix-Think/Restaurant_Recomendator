"""Minimal contextual bandit skeleton (LinUCB-style) for reranking candidates.

This is a lightweight placeholder to enable scoring with context; weights are kept
in-memory and can be updated with observed rewards.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple


def _feature_vector(candidate: Dict, query: Dict) -> List[float]:
    """Build a simple feature vector from candidate metadata and user query."""
    dist = candidate.get("distance_km") or 0.0
    rating = candidate.get("rating") or 0.0
    cf = candidate.get("cf_score") or 0.0
    price_range = candidate.get("price_range") or ""
    price_min, price_max = 0.0, 0.0
    if "-" in price_range:
        parts = price_range.split("-")
        try:
            price_min = float(parts[0])
            price_max = float(parts[1])
        except Exception:
            price_min = price_max = 0.0

    user_price = query.get("price_range") or {}
    up_min, up_max = user_price.get("min") or 0.0, user_price.get("max") or 0.0
    price_fit = 0.0
    if up_min or up_max:
        if up_min and price_max and price_max < up_min:
            price_fit = -1.0
        elif up_max and price_min and price_min > up_max:
            price_fit = -1.0
        else:
            price_fit = 1.0

    # Features: [1 (bias), rating, -distance, price_fit, cf_score]
    return [1.0, rating, -dist, price_fit, cf]


class SimpleLinUCB:
    """Very small LinUCB-style scorer (shared theta, diagonal covariance)."""

    def __init__(self, alpha: float = 1.0, dim: int = 5):
        self.alpha = alpha
        self.dim = dim
        self.A_diag = [1.0] * dim  # diagonal of A matrix
        self.b = [0.0] * dim

    def _theta(self) -> List[float]:
        return [self.b[i] / self.A_diag[i] for i in range(self.dim)]

    def score(self, x: List[float]) -> float:
        theta = self._theta()
        p = sum(theta[i] * x[i] for i in range(self.dim))
        # confidence term using diagonal approx
        conf = self.alpha * math.sqrt(sum((x[i] ** 2) / self.A_diag[i] for i in range(self.dim)))
        return p + conf

    def update(self, x: List[float], reward: float):
        for i in range(self.dim):
            self.A_diag[i] += x[i] ** 2
            self.b[i] += x[i] * reward


def bandit_rerank(
    candidates: Iterable[Dict],
    query: Dict,
    model: SimpleLinUCB | None = None,
    top_k: int = 3,
) -> Tuple[List[Dict], SimpleLinUCB]:
    """Score and rerank candidates with a shared SimpleLinUCB model."""
    model = model or SimpleLinUCB()
    scored: List[Tuple[float, Dict, List[float]]] = []
    for c in candidates:
        x = _feature_vector(c, query)
        s = model.score(x)
        scored.append((s, c, x))
    scored.sort(key=lambda t: t[0], reverse=True)
    ranked = [c for _, c, _ in scored[:top_k]]
    return ranked, model


__all__ = ["SimpleLinUCB", "bandit_rerank"]
