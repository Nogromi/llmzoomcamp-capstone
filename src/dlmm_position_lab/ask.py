"""Command-line interface for grounded Meteora documentation answers."""

import argparse

from dlmm_position_lab.rag import answer_documentation_question


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask a grounded question about Meteora DLMM documentation"
    )
    parser.add_argument("question", help="Documentation question")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = answer_documentation_question(args.question)
    print(result.answer)
    print("\nSources:")
    for number, source in enumerate(result.sources, start=1):
        print(f"[{number}] {source.title} — {source.section}")
        print(f"    {source.url}")
    print(f"\nLatency: {result.latency_ms:.0f} ms")


if __name__ == "__main__":
    main()
