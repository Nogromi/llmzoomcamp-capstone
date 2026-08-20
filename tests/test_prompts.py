import pytest

from dlmm_position_lab.models import SearchResult
from dlmm_position_lab.prompts import (
    build_documentation_context,
    build_documentation_prompt,
)


def result(identifier: str) -> SearchResult:
    return SearchResult(
        id=identifier,
        title=f"Title {identifier}",
        section=f"Section {identifier}",
        url=f"https://example.test/{identifier}",
        text=f"Evidence for {identifier}.",
        score=1.0,
    )


def test_context_numbers_chunks_and_preserves_metadata() -> None:
    context = build_documentation_context([result("one"), result("two")])

    assert "[1] Title one — Section one" in context
    assert "URL: https://example.test/one" in context
    assert "[2] Title two — Section two" in context
    assert "Evidence for two." in context


def test_prompt_contains_question_and_empty_context_fallback() -> None:
    prompt = build_documentation_prompt("  What is a bin?  ", [])

    assert "What is a bin?" in prompt
    assert "No documentation was retrieved." in prompt


def test_prompt_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="question must not be empty"):
        build_documentation_prompt("  ", [])
