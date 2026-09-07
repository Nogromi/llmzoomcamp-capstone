"""Prefect flow for running the two reproducible evaluation scripts."""

import runpy

from prefect import flow, task


@task(name="evaluate-retrieval")
def evaluate_retrieval() -> None:
    """Compare BM25, vector, and hybrid retrieval."""
    runpy.run_path("evaluation/retrieval.py", run_name="__main__")


@task(name="evaluate-rag-and-router")
def evaluate_quality() -> None:
    """Run simple RAG validation and router accuracy checks."""
    runpy.run_path("evaluation/quality.py", run_name="__main__")


@flow(name="dlmm-position-lab-evaluation", log_prints=True)
def evaluate_project() -> None:
    """Run evaluation tasks with Prefect visibility."""
    evaluate_retrieval()
    evaluate_quality()


if __name__ == "__main__":
    evaluate_project()
