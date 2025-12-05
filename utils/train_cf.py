"""Train a matrix-factorization CF model (ALS) using implicit feedback.

Requirements:
- implicit (pip install implicit)
- scipy, numpy, pandas

Input: data/interactions_log.csv (reward > 0)
Output: data/cf_model.pkl with factors + user/item index mapping
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares
from scipy import sparse

DEFAULT_LOG = Path("data/interactions_log.csv")
DEFAULT_OUT = Path("data/cf_model.pkl")


def train(
    log_path: Path = DEFAULT_LOG,
    out_path: Path = DEFAULT_OUT,
    factors: int = 64,
    reg: float = 0.08,
    iterations: int = 20,
):
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    df = pd.read_csv(log_path)
    if "reward" not in df.columns:
        df = pd.read_csv(
            log_path,
            header=None,
            names=[
                "user_id",
                "restaurant_id",
                "timestamp",
                "action",
                "reward",
                "lat",
                "lng",
                "intent",
                "cuisine",
                "price_min",
                "price_max",
            ],
        )

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
    parser.add_argument("--log", default=str(DEFAULT_LOG), help="Path to interactions_log.csv")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output model path")
    parser.add_argument("--factors", type=int, default=64)
    parser.add_argument("--reg", type=float, default=0.08)
    parser.add_argument("--iters", type=int, default=20)
    args = parser.parse_args()
    train(Path(args.log), Path(args.out), factors=args.factors, reg=args.reg, iterations=args.iters)
