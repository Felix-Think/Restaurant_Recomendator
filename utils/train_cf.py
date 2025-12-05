"""Train a matrix-factorization CF model (ALS) using implicit feedback from MongoDB.

Requirements:
- implicit (pip install implicit)
- scipy, numpy, pandas

Input: Mongo collection `interactions` (reward > 0)
Output: data/cf_model.pkl with factors + user/item index mapping
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares
from scipy import sparse

DEFAULT_OUT = Path("data/cf_model.pkl")


def _load_interactions_df() -> pd.DataFrame:
    """Load interactions from Mongo only."""
    try:
        try:
            from utils.db import get_db
        except ImportError:
            # Allow running as script: add project root to sys.path
            ROOT = Path(__file__).resolve().parent.parent
            if str(ROOT) not in sys.path:
                sys.path.append(str(ROOT))
            from utils.db import get_db

        db = get_db()
        docs = list(
            db.interactions.find(
                {},
                {
                    "user_id": 1,
                    "restaurant_id": 1,
                    "timestamp": 1,
                    "action": 1,
                    "reward": 1,
                    "lat": 1,
                    "lng": 1,
                    "intent": 1,
                    "cuisine": 1,
                    "price_min": 1,
                    "price_max": 1,
                },
            )
        )
        if docs:
            for d in docs:
                d.pop("_id", None)
            return pd.DataFrame(docs)
    except Exception as e:
        raise RuntimeError(f"Failed to load interactions from Mongo: {e}") from e

    raise ValueError("No interactions found in Mongo to train CF model.")


def train(
    out_path: Path = DEFAULT_OUT,
    factors: int = 64,
    reg: float = 0.08,
    iterations: int = 20,
):
    df = _load_interactions_df()

    # Aggregate per user-item
    agg = {}
    for _, row in df.iterrows():
        u = str(row["user_id"]).strip()
        it = str(row["restaurant_id"]).strip()
        act = str(row.get("action", "")).lower()
        try:
            r = float(row.get("reward", 0) or 0)
        except Exception:
            r = 0.0
        key = (u, it)
        cur = agg.get(key, 0.0)
        if act == "dislike":
            cur = min(cur, -0.5)
        elif act == "like":
            cur = max(cur, 1.0)
        elif act == "click":
            cur = min(cur + 0.1, 1.0)
        elif r > 0:
            cur = max(cur, r)
        agg[key] = cur

    aggregated = [(u, it, r) for (u, it), r in agg.items() if r > 0]
    print(f"Training with {len(aggregated)} positive user-item pairs from {len(df)} raw logs")
    if not aggregated:
        raise ValueError("No positive aggregated rewards to train CF model.")

    users = {u: idx for idx, u in enumerate(sorted({u for u, _, _ in aggregated}))}
    items = {i: idx for idx, i in enumerate(sorted({it for _, it, _ in aggregated}))}

    rows = np.array([users[u] for u, _, _ in aggregated], dtype=np.int64)
    cols = np.array([items[it] for _, it, _ in aggregated], dtype=np.int64)
    data = np.array([r for _, _, r in aggregated], dtype=np.float32)

    mat = sparse.coo_matrix((data, (rows, cols)), shape=(len(users), len(items))).tocsr()

    model = AlternatingLeastSquares(
        factors=factors,
        regularization=reg,
        iterations=iterations,
        calculate_training_loss=False,
    )
    # implicit expects item-user matrix
    model.fit(mat.T)

    payload = {
        "user_factors": model.user_factors,
        "item_factors": model.item_factors,
        "user_index": users,
        "item_index": items,
        "factors": factors,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        pickle.dump(payload, f)
    print(f"Trained ALS: users={len(users)}, items={len(items)}, factors={factors} -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CF ALS model from interaction logs.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output model path")
    parser.add_argument("--factors", type=int, default=64)
    parser.add_argument("--reg", type=float, default=0.08)
    parser.add_argument("--iters", type=int, default=20)
    args = parser.parse_args()
    train(
        Path(args.out),
        factors=args.factors,
        reg=args.reg,
        iterations=args.iters,
    )
