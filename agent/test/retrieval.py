"""Batch run retrieval against predefined test cases.

Reads test cases from agent/test/testcase/testcases.py and writes results
into agent/test/testcase/tested/<id>.txt for easy review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.nodes.input_parser import run as run_parser
from agent.nodes.retrieval_agent import run as run_retrieval_agent
from agent.test.testcase.testcases import TEST_CASES


def run_test_cases():
    testcase_dir = Path(__file__).parent / "testcase"
    tested_dir = testcase_dir / "tested"
    tested_dir.mkdir(parents=True, exist_ok=True)

    for case in TEST_CASES:
        case_id = case["id"]
        user_input = case["user_input"]
        lat = case.get("lat")
        lng = case.get("lng")

        parsed = run_parser(user_input, lat=lat, lng=lng)
        retrieved = run_retrieval_agent(
            query=parsed,
            persist_dir="chroma/foody",
            collection_name="foody_restaurants",
        )

        output_path = tested_dir / f"{case_id}.txt"
        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"TestCase: {case_id}\n")
            f.write("Parsed:\n")
            f.write(json.dumps(parsed, ensure_ascii=False) + "\n")
            f.write("Retrieved:\n")
            f.write(json.dumps(retrieved, ensure_ascii=False) + "\n")

        print(f"Wrote result for {case_id} -> {output_path}")


if __name__ == "__main__":
    run_test_cases()
