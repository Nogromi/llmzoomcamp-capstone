"""Compare retrieval methods, then check RAG citations and native tool calls."""

import argparse
import json
import re
from pathlib import Path

from openai import OpenAI

from dlmm_position_lab.rag import answer_question, start_answer
from dlmm_position_lab.retrieval import fuse_results, search

EVALUATION_DIR = Path(__file__).parent


def load_cases(filename: str) -> list[dict]:
    return json.loads((EVALUATION_DIR / filename).read_text(encoding="utf-8"))


def evaluate_retrieval() -> list[dict]:
    questions = load_cases("questions.json")
    scores = {name: [] for name in ("bm25", "vector", "hybrid")}
    for case in questions:
        print(case["question"])
        bm25 = search(case["question"], "bm25", 10)
        vector = search(case["question"], "vector", 10)
        rankings = {
            "bm25": bm25,
            "vector": vector,
            "hybrid": fuse_results([bm25, vector]),
        }
        for name, documents in rankings.items():
            rank = next(
                (
                    i
                    for i, doc in enumerate(documents[:5], 1)
                    if doc["id"] in case["expected_document_ids"]
                ),
                0,
            )
            scores[name].append(1 / rank if rank else 0)
    return [
        {
            "retriever": name,
            "questions": len(values),
            "hit_rate_at_5": sum(value > 0 for value in values) / len(values),
            "mrr": sum(values) / len(values),
        }
        for name, values in scores.items()
    ]


def evaluate_quality() -> dict:
    rag_results = []
    for case in load_cases("rag_questions.json"):
        print(f"RAG: {case['question']}")
        response = answer_question(case["question"])
        citations = [
            int(number) for number in re.findall(r"\[(\d+)\]", response["answer"])
        ]
        checks = {
            "has_answer": bool(response["answer"].strip()),
            "has_sources": bool(response["sources"]),
            "valid_citations": bool(citations)
            and all(1 <= n <= len(response["sources"]) for n in citations),
            "expected_document_retrieved": bool(
                set(case["expected_document_ids"])
                & {doc["id"] for doc in response["sources"]}
            ),
        }
        rag_results.append(
            {
                "question": case["question"],
                "answer": response["answer"],
                "checks": checks,
                "passed": all(checks.values()),
            }
        )
    tool_results = []
    with OpenAI() as client:
        for case in load_cases("tool_questions.json"):
            print(f"Tool selection: {case['question']}")
            response = start_answer(
                client, case["question"], [], case.get("pool_address", "")
            )
            actual = [
                {"name": item.name, "arguments": json.loads(item.arguments)}
                for item in response.output
                if item.type == "function_call"
            ]
            expected = (
                [
                    {
                        "name": "get_pool",
                        "arguments": {"address": case["expected_address"]},
                    }
                ]
                if case["expected_address"]
                else []
            )
            tool_results.append(
                {**case, "actual": actual, "passed": actual == expected}
            )
    return {
        "rag_pass_rate": sum(row["passed"] for row in rag_results) / len(rag_results),
        "tool_call_accuracy": sum(row["passed"] for row in tool_results)
        / len(tool_results),
        "rag_cases": rag_results,
        "tool_cases": tool_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quality",
        action="store_true",
        help="Also call the LLM for RAG and native tool selection checks.",
    )
    args = parser.parse_args()
    result = {"retrieval": evaluate_retrieval()}
    if args.quality:
        result["quality"] = evaluate_quality()
    output = EVALUATION_DIR / "results.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
