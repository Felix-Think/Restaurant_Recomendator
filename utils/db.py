"""MongoDB connection helper."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from pymongo import MongoClient


@lru_cache(maxsize=1)
def _get_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return MongoClient(uri)


def get_db() -> Any:
    """Return Mongo database handle."""
    name = os.getenv("MONGODB_DB", "restaurant_recommendation")
    return _get_client()[name]


__all__ = ["get_db"]
