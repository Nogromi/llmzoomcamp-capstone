import json

import pytest

from dlmm_position_lab.ingestion import (
    DocumentationPage,
    DocumentationSection,
    chunk_sections,
    clean_text,
    discover_documentation_urls,
    is_meaningful_text,
    parse_document,
    parse_markdown_page,
    parse_page,
    save_documents,
)

SAMPLE_HTML = """
<html>
  <head><title>Ignored browser title</title><style>.hidden {}</style></head>
  <body>
    <nav>Navigation noise</nav>
    <main>
      <h1>What is DLMM?</h1>
      <p>Introductory&nbsp; text   about DLMM.</p>
      <h2>Price bins</h2>
      <p>Liquidity is distributed across discrete bins.</p>
      <ul><li>Only the active bin trades.</li><li>Bins have fixed prices.</li></ul>
      <h3>Bin step</h3>
      <p>The bin step controls the price increment.</p>
    </main>
    <footer>Footer noise</footer>
  </body>
</html>
"""


def test_clean_text_normalizes_whitespace() -> None:
    assert clean_text("  active\xa0\n  \u200bbin  ") == "active bin"


def test_boilerplate_is_not_meaningful() -> None:
    assert not is_meaningful_text("Was this page helpful?")
    assert is_meaningful_text("The active bin contains liquidity for swaps.")


def test_discover_documentation_urls_uses_docs_heading_and_dlmm_links() -> None:
    index = """# Meteora Documentation
## Docs
- [Intro](https://docs.meteora.ag/get-started/index.md)
- [What is DLMM?](https://docs.meteora.ag/core-products/dlmm/what-is-dlmm.md)
- [Formulas](https://docs.meteora.ag/core-products/dlmm/formulas.md)
- [Formulas duplicate](https://docs.meteora.ag/core-products/dlmm/formulas.md)
## API
- [Not in Docs](https://docs.meteora.ag/core-products/dlmm/not-in-docs.md)
"""

    assert discover_documentation_urls(index) == [
        "https://docs.meteora.ag/core-products/dlmm/what-is-dlmm.md",
        "https://docs.meteora.ag/core-products/dlmm/formulas.md",
    ]


def test_discover_documentation_urls_requires_matching_links() -> None:
    with pytest.raises(ValueError, match="No documentation links"):
        discover_documentation_urls("# Index\n## Docs\n- no links")


def test_parse_page_extracts_title_sections_and_clean_text() -> None:
    page = parse_page(SAMPLE_HTML, "https://example.test/dlmm")

    assert page.title == "What is DLMM?"
    assert [section.title for section in page.sections] == [
        "What is DLMM?",
        "Price bins",
        "Bin step",
    ]
    assert page.sections[0].text == "Introductory text about DLMM."
    assert "Only the active bin trades." in page.sections[1].text
    assert "Navigation noise" not in " ".join(s.text for s in page.sections)


def test_parse_markdown_extracts_meaningful_sections_and_cleans_markup() -> None:
    markdown = """---
description: A page
---
# DLMM Formulas

Intro with [a source](https://example.test).

## \u200bPrice Impact Guard

math theme={"system"} The guard limits excessive price movement during a swap.

## Empty widget

Was this page helpful?
"""

    page = parse_markdown_page(
        markdown, "https://docs.meteora.ag/core-products/dlmm/formulas.md"
    )

    assert page.url.endswith("/formulas")
    assert page.title == "DLMM Formulas"
    assert [section.title for section in page.sections] == [
        "DLMM Formulas",
        "Price Impact Guard",
    ]
    assert page.sections[0].text == "Intro with a source."
    assert all("helpful" not in section.text for section in page.sections)
    assert "theme=" not in page.sections[1].text


def test_parse_document_selects_markdown_for_markdown_url() -> None:
    page = parse_document("# DLMM\n\nMeaningful documentation text.", "docs.md")
    assert page.title == "DLMM"


def test_chunking_is_bounded_and_ids_are_stable() -> None:
    page = DocumentationPage(
        title="DLMM",
        url="https://example.test/dlmm",
        sections=(
            DocumentationSection(
                title="Bins",
                text="one two three four five six seven eight nine ten",
            ),
        ),
    )

    first = chunk_sections(page, max_chars=18, overlap_words=1)
    second = chunk_sections(page, max_chars=18, overlap_words=1)

    assert first == second
    assert len(first) > 1
    assert all(len(chunk.text) <= 18 for chunk in first)
    assert len({chunk.id for chunk in first}) == len(first)
    assert all(chunk.url == page.url for chunk in first)


def test_chunk_id_stays_stable_when_source_text_is_edited() -> None:
    before = DocumentationPage(
        title="DLMM",
        url="https://example.test/dlmm",
        sections=(DocumentationSection(title="Bins", text="Original useful text."),),
    )
    after = DocumentationPage(
        title="DLMM",
        url="https://example.test/dlmm",
        sections=(DocumentationSection(title="Bins", text="Updated useful text."),),
    )

    assert chunk_sections(before)[0].id == chunk_sections(after)[0].id


def test_save_documents_creates_expected_json(tmp_path) -> None:
    page = parse_page(SAMPLE_HTML, "https://example.test/dlmm")
    chunks = chunk_sections(page)
    output = tmp_path / "nested" / "documents.json"

    save_documents(chunks, output)

    payload = json.loads(output.read_text())
    assert set(payload[0]) == {"id", "title", "section", "url", "text"}
    assert payload[0]["title"] == "What is DLMM?"


def test_parse_page_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="No documentation sections"):
        parse_page("<html><body><main><h1>Empty</h1></main></body></html>", "x")
