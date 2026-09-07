"""Command-line interface for inspecting query-router decisions."""

import argparse

from dlmm_position_lab.router import route_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify a DLMM Position Lab question")
    parser.add_argument("question", help="Question to classify")
    args = parser.parse_args()

    result = route_question(args.question)
    print(f"Question type: {result.decision.question_type}")
    print(f"Use RAG: {result.decision.use_rag}")
    print(f"Tools: {', '.join(result.decision.tools) or 'none'}")
    print(f"Why: {result.decision.explanation}")
    print(f"Latency: {result.latency_ms:.0f} ms")


if __name__ == "__main__":
    main()
