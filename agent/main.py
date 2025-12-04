"""Simple entrypoint to run the full agent pipeline on a sample input."""


from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.nodes.orchestrator import run as run_orchestrator


def main():
    user_message = "mình muốn ăn gà rán, càng gần cầu rồng càng tốt, giá tầm 50.000"
    lat, lng = 16.065, 108.229

    result = run_orchestrator(user_message=user_message, lat=lat, lng=lng, top_k=3)

    print("Parsed:")
    print(result["parsed"])
    print("\nAnswer:")
    print(result["answer"])
    print("\nRestaurants:")
    for r in result["restaurants"]:
        print(r)


if __name__ == "__main__":
    main()
