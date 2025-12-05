"""CF scorer that loads pre-trained matrix factorization from data/cf_model.pkl.

Also provides a lightweight trigger to retrain ALS in background when log grows.
"""

from __future__ import annotations

import pickle
import threading
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

MODEL_PATH = Path("data/cf_model.pkl")
LOG_PATH = Path("data/interactions_log.csv")
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


def _count_positive(log_path: Path = LOG_PATH) -> int:
    if not log_path.exists():
        return 0
    count = 0
    with log_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        if not rows:
            return 0
        # Check header presence
        start_idx = 1 if rows[0] and rows[0][0] == "user_id" else 0
        for row in rows[start_idx:]:
            try:
                reward = float(row[4]) if len(row) > 4 else 0.0
            except Exception:
                reward = 0.0
            if reward > 0:
                count += 1
    return count


def _train_background(log_path: Path, model_path: Path, meta_path: Path, pos_count: int):
    global _TRAINING
    try:
        from utils.train_cf import train
        train(log_path, model_path)
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
    pos = _count_positive(LOG_PATH)
    last = _load_meta(META_PATH)
    if pos - last < threshold:
        return
    with _TRAIN_LOCK:
        if _TRAINING:
            return
        _TRAINING = True
    print(f"[CF] Trigger retrain in background: positives {pos} (last {last})")
    t = threading.Thread(target=_train_background, args=(LOG_PATH, MODEL_PATH, META_PATH, pos), daemon=True)
    t.start()


__all__ = ["CFModel", "MODEL_PATH", "trigger_retrain_if_needed"]
