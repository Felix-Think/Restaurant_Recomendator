"""Quick smoke test for the input parser node."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.nodes.input_parser import run


def main():
    result = run(
        "tôi muốn ăn mì quảng hoặc bún bò,  tôi không ăn được hành và không thích chỗ đông người, ăn lúc 10h sáng",
        lat=16.0471,
        lng=108.2062,
    )
    print(result)


if __name__ == "__main__":
    main()
