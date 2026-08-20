"""Command-line interface for inspecting BM25 retrieval results."""

import argparse

from dlmm_position_lab.hybrid_search import hybrid_search
from dlmm_position_lab.retrieval import DEFAULT_SEARCH_LIMIT, bm25_search, vector_search


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search Meteora DLMM documentation")
    parser.add_argument("query", help="Natural-language documentation question")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SEARCH_LIMIT,
        help=f"Number of results to return (default: {DEFAULT_SEARCH_LIMIT})",
    )
    parser.add_argument(
        "--method",
        choices=("bm25", "vector", "hybrid"),
        default="bm25",
        help="Retrieval method (default: bm25)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    methods = {
        "bm25": bm25_search,
        "vector": vector_search,
        "hybrid": hybrid_search,
    }
    search = methods[args.method]
    results = search(args.query, args.limit)
    if not results:
        print("No matching documentation found.")
        return

    for rank, result in enumerate(results, start=1):
        excerpt = result.text[:300]
        if len(result.text) > len(excerpt):
            excerpt += "..."
        print(f"{rank}. {result.title} — {result.section}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Source: {result.url}")
        print(f"   {excerpt}\n")


if __name__ == "__main__":
    main()
