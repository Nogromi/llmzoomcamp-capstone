"""Visible, testable prompts used by the documentation RAG flow."""

from dlmm_position_lab.models import SearchResult

DOCUMENTATION_SYSTEM_PROMPT = """You are an educational assistant for Meteora DLMM.

Answer using only the supplied documentation context.
If the context does not contain enough information, say that the available documentation is insufficient.
Do not provide financial advice or recommendations.
Cite supporting context inline using its bracketed source number, for example [1].
Do not cite a source that does not support the statement."""


def build_documentation_context(results: list[SearchResult]) -> str:
    """Format retrieved chunks with stable citation numbers."""
    return "\n\n".join(
        (
            f"[{number}] {result.title} — {result.section}\n"
            f"URL: {result.url}\n"
            f"{result.text}"
        )
        for number, result in enumerate(results, start=1)
    )


def build_documentation_prompt(question: str, results: list[SearchResult]) -> str:
    """Build the user message containing the question and retrieved context."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be empty")
    context = build_documentation_context(results)
    return f"""Question:
{normalized_question}

Documentation context:
{context or "No documentation was retrieved."}

Give a concise educational answer with inline source citations."""
