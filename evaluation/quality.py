"""Run reproducible deterministic RAG and router quality evaluation."""

import json
from pathlib import Path

from dlmm_position_lab.quality_evaluation import (
    RagCaseResult,
    RagEvaluationCase,
    RouterEvaluationCase,
    evaluate_router,
    summarize_rag,
    validate_rag_answer,
)
from dlmm_position_lab.rag import answer_documentation_question
from dlmm_position_lab.router import route_question

PROJECT_ROOT = Path(__file__).parents[1]
RAG_QUESTION_PATH = PROJECT_ROOT / "evaluation/rag_questions.json"
ROUTER_QUESTION_PATH = PROJECT_ROOT / "evaluation/router_questions.json"
RESULT_PATH = PROJECT_ROOT / "evaluation/quality_results.json"


def load_records(path: Path, model: type) -> list:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [model.model_validate(record) for record in records]


def main() -> None:
    rag_cases = load_records(RAG_QUESTION_PATH, RagEvaluationCase)
    rag_results: list[RagCaseResult] = []
    for case in rag_cases:
        answer = answer_documentation_question(case.question)
        rag_results.append(
            RagCaseResult(
                question=case.question,
                answer=answer,
                validation=validate_rag_answer(case, answer),
            )
        )
    rag_metrics = summarize_rag([item.validation for item in rag_results])

    router_cases = load_records(ROUTER_QUESTION_PATH, RouterEvaluationCase)
    router_metrics, router_results = evaluate_router(router_cases, route_question)

    output = {
        "rag_metrics": rag_metrics.model_dump(mode="json"),
        "rag_cases": [item.model_dump(mode="json") for item in rag_results],
        "router_metrics": router_metrics.model_dump(mode="json"),
        "router_cases": [item.model_dump(mode="json") for item in router_results],
    }
    RESULT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print("RAG validation")
    print(f"Pass rate:               {rag_metrics.pass_rate:.3f}")
    print(f"Answer rate:             {rag_metrics.answer_rate:.3f}")
    print(f"Source rate:             {rag_metrics.source_rate:.3f}")
    print(f"Citation rate:           {rag_metrics.citation_rate:.3f}")
    print(f"Expected document rate:  {rag_metrics.expected_document_rate:.3f}")
    print("\nRouter evaluation")
    print(
        f"Classification accuracy:      "
        f"{router_metrics.classification_accuracy:.3f}"
    )
    print(
        f"RAG selection accuracy:       "
        f"{router_metrics.rag_selection_accuracy:.3f}"
    )
    print(
        f"Tool selection accuracy:      "
        f"{router_metrics.tool_selection_accuracy:.3f}"
    )
    print(
        f"Unnecessary tool-call rate:   "
        f"{router_metrics.unnecessary_tool_call_rate:.3f}"
    )
    print(f"Failure rate:                 {router_metrics.failure_rate:.3f}")
    print(f"\nSaved: {RESULT_PATH}")


if __name__ == "__main__":
    main()
