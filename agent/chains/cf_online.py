"""Lightweight memory-based CF scorer using interaction logs.

Uses implicit feedback (reward > 0) to build user-item sets and item popularity.
Scoring: Jaccard similarity between target user and other users' item sets,
         score = sum(similarity * reward) for each candidate;
         fallback to popularity if no similarity.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple

from utils.db import get_db


class OnlineCF:
    def __init__(self):
        self.user_items: Dict[str, Set[str]] = defaultdict(set)
        self.item_popularity: Dict[str, float] = defaultdict(float)
        self.user_item_reward: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._load()

    def _load(self):
        try:
            db = get_db()
            cursor = db.interactions.find({"reward": {"$gt": 0}}, {"user_id": 1, "restaurant_id": 1, "reward": 1})
        except Exception:
            cursor = []

        for row in cursor:
            user = str(row.get("user_id", "")).strip()
            item = str(row.get("restaurant_id", "")).strip()
            if not user or not item:
                continue
            try:
                reward = float(row.get("reward", 0) or 0)
            except Exception:
                reward = 0.0
            if reward <= 0:
                continue
            self.user_items[user].add(item)
            self.item_popularity[item] += reward
            self.user_item_reward[user][item] = reward

    @staticmethod
    def _jaccard(a: Set[str], b: Set[str]) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    def score_candidates(self, user_id: str, candidates: Iterable[Dict], top_k: int = 3) -> List[Tuple[Dict, float]]:
        candidates = list(candidates)
        cand_ids = [str(c.get("restaurant_id") or c.get("url") or i) for i, c in enumerate(candidates)]
        user_set = self.user_items.get(user_id, set())

        sims: Dict[str, float] = {}
        for other, items in self.user_items.items():
            if other == user_id:
                continue
            sim = self._jaccard(user_set, items)
            if sim > 0:
                sims[other] = sim

        scores: Dict[str, float] = defaultdict(float)
        for cid in cand_ids:
            for other, sim in sims.items():
                r = self.user_item_reward[other].get(cid, 0)
                if r > 0:
                    scores[cid] += sim * r
            if scores[cid] == 0 and cid in self.item_popularity:
                scores[cid] += 0.1 * self.item_popularity[cid]

        ranked: List[Tuple[Dict, float]] = []
        id_to_candidate = {cid: c for cid, c in zip(cand_ids, candidates)}
        for cid, score in sorted(scores.items(), key=lambda t: t[1], reverse=True):
            ranked.append((id_to_candidate[cid], score))
        # If some candidates missing in scores (no signal), append them with score 0
        for cid, cand in id_to_candidate.items():
            if cid not in scores:
                ranked.append((cand, 0.0))
        return ranked[:top_k]


def cf_rerank(candidates: Iterable[Dict], user_id: str, top_k: int = 3) -> List[Dict]:
    """Return candidates sorted by CF score and attach cf_score field."""
    model = OnlineCF()
    ranked = model.score_candidates(user_id, candidates, top_k=top_k)
    out: List[Dict] = []
    for cand, score in ranked:
        cand = dict(cand)
        cand["cf_score"] = score
        out.append(cand)
    return out


__all__ = ["OnlineCF", "cf_rerank"]
