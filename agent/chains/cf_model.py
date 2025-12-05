"""CF scorer that loads pre-trained matrix factorization from data/cf_model.pkl.

Also provides a lightweight trigger to retrain ALS in background when Mongo logs grow.
"""

from __future__ import annotations

import json
import pickle
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

MODEL_PATH = Path("data/cf_model.pkl")
META_PATH = Path("data/cf_model_meta.json")

_TRAINING = False
_TRAIN_LOCK = threading.Lock()


class CFModel:
    def __init__(self, model_path: Path | str = MODEL_PATH):
        self.model_path = Path(model_path)
        self.user_factors: List[List[float]] = []
        self.item_factors: List[List[float]] = []
        self.user_index: Dict[str, int] = {}
        self.item_index: Dict[str, int] = {}
        self.factors = 0
        self._loaded = False
        self._mtime = None
        self._load()

    def _load(self):
        if not self.model_path.exists():
            return
        with self.model_path.open("rb") as f:
            data = pickle.load(f)
        self.user_factors = data.get("user_factors", [])
        self.item_factors = data.get("item_factors", [])
        self.user_index = data.get("user_index", {})
        self.item_index = data.get("item_index", {})
        self.factors = data.get("factors", 0)
        self._loaded = True
        self._mtime = self.model_path.stat().st_mtime

    def _ensure_fresh(self):
        """Reload model if file changed."""
        try:
            mtime = self.model_path.stat().st_mtime
        except FileNotFoundError:
            return
        if not self._loaded or self._mtime != mtime:
            self._load()

    def available(self) -> bool:
        return self._loaded

    def has_user(self, user_id: str) -> bool:
        """Check if user_id exists in trained model."""
        self._ensure_fresh()
        return user_id in self.user_index

    def score(self, user_id: str, item_id: str) -> float:
        self._ensure_fresh()
        if not self._loaded:
            return 0.0
        uidx = self.user_index.get(user_id)
        iidx = self.item_index.get(item_id)
        if uidx is None or iidx is None:
            return 0.0
        # Defensive bounds check in case stored factors are misaligned with indices
        if uidx >= len(self.user_factors) or iidx >= len(self.item_factors):
            return 0.0
        uvec = self.user_factors[uidx]
        ivec = self.item_factors[iidx]
        return sum(u * v for u, v in zip(uvec, ivec))

    def rerank(self, user_id: str, candidates: Iterable[Dict], top_k: int = 3) -> List[Dict]:
        self._ensure_fresh()
        scored: List[Tuple[float, Dict]] = []
        for c in candidates:
            cid = str(c.get("restaurant_id") or c.get("url") or "")
            s = self.score(user_id, cid)
            c = dict(c)
            c["cf_score"] = s
            scored.append((s, c))
        scored.sort(key=lambda t: t[0], reverse=True)
        ranked = [c for _, c in scored]
        return ranked[:top_k]


def _load_meta(meta_path: Path = META_PATH) -> int:
    if not meta_path.exists():
        return 0
    try:
        with meta_path.open() as f:
            data = json.load(f)
            return int(data.get("trained_pos_count", 0))
    except Exception:
        return 0


def _save_meta(count: int, meta_path: Path = META_PATH):
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w") as f:
        json.dump({"trained_pos_count": count}, f)


def _count_positive() -> int:
    """Count positive interactions from Mongo."""
    try:
        from utils.db import get_db

        db = get_db()
        return db.interactions.count_documents({"reward": {"$gt": 0}})
    except Exception:
        return 0


def _train_background(model_path: Path, meta_path: Path, pos_count: int):
    global _TRAINING
    try:
        from utils.train_cf import train
        train(out_path=model_path)
        _save_meta(pos_count, meta_path)
        print(f"[CF] Retrain done: positives={pos_count}, model={model_path}")
    except Exception:
        # Swallow errors to avoid impacting request path
        pass
    finally:
        with _TRAIN_LOCK:
            _TRAINING = False


def trigger_retrain_if_needed(threshold: int = 10):
    """If new positive interactions exceed threshold, retrain ALS in background."""
    global _TRAINING
    pos = _count_positive()
    last = _load_meta(META_PATH)
    # If meta count is stale (larger than actual positives), force retrain on next threshold
    if pos < last:
        last = 0
    if pos - last < threshold:
        return
    with _TRAIN_LOCK:
        if _TRAINING:
            return
        _TRAINING = True
    print(f"[CF] Trigger retrain in background: positives {pos} (last {last})")
    t = threading.Thread(target=_train_background, args=(MODEL_PATH, META_PATH, pos), daemon=True)
    t.start()


__all__ = ["CFModel", "MODEL_PATH", "trigger_retrain_if_needed"]
