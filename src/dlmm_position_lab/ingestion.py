"""Deterministic Meteora documentation parsing and chunking utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag

DOCUMENTATION_INDEX_URL = "https://docs.meteora.ag/llms.txt"
DOCUMENTATION_INDEX_HEADING = "Docs"
DLMM_PATH_PREFIX = "https://docs.meteora.ag/core-products/dlmm/"
HTTP_TIMEOUT_SECONDS = 30.0
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_WORDS = 20
BOILERPLATE_TEXT = {
    "was this page helpful?",
    "copy page",
    "ask ai",
    "on this page",
    "previous",
    "next",
}


@dataclass(frozen=True)
class DocumentationSection:
    """A heading and its cleaned body text."""

    title: str
    text: str


@dataclass(frozen=True)
class DocumentationPage:
    """Parsed content from one source page."""

    title: str
    url: str
    sections: tuple[DocumentationSection, ...]


@dataclass(frozen=True)
class DocumentationChunk:
    """A JSON-serializable retrieval unit."""

    id: str
    title: str
    section: str
    url: str
    text: str


def documentation_urls_from_env() -> list[str]:
    """Read optional comma-separated source URLs from ``METEORA_DOC_URLS``."""
    raw_urls = os.getenv("METEORA_DOC_URLS", "")
    return [url.strip() for url in raw_urls.split(",") if url.strip()]


def discover_documentation_urls(
    index_text: str,
    heading: str = DOCUMENTATION_INDEX_HEADING,
    path_prefix: str = DLMM_PATH_PREFIX,
) -> list[str]:
    """Extract DLMM documentation links from one Markdown index section.

    The Markdown representations are preferred over rendered HTML because they
    contain the documentation content without navigation and feedback widgets.
    """
    heading_pattern = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
    link_pattern = re.compile(r"\[[^]]+\]\((https://docs\.meteora\.ag/[^)]+)\)")
    target_level: int | None = None
    in_target_section = False
    urls: list[str] = []

    for line in index_text.splitlines():
        heading_match = heading_pattern.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            name = clean_text(heading_match.group(2))
            if in_target_section and target_level is not None and level <= target_level:
                break
            if name.casefold() == heading.casefold():
                in_target_section = True
                target_level = level
            continue

        if not in_target_section:
            continue
        for url in link_pattern.findall(line):
            if not url.startswith(path_prefix):
                continue
            if url not in urls:
                urls.append(url)

    if not urls:
        raise ValueError(
            f"No documentation links with prefix {path_prefix!r} "
            f"found under heading {heading!r}"
        )
    return urls


def download_page(url: str, timeout: float = HTTP_TIMEOUT_SECONDS) -> str:
    """Download a documentation resource and reject unsuccessful responses."""
    headers = {"User-Agent": "DLMM-Position-Lab/0.1 (educational capstone)"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def clean_text(text: str) -> str:
    """Remove invisible format characters and normalize repeated whitespace."""
    text = "".join(
        " " if character == "\xa0" else character
        for character in text
        if unicodedata.category(character) != "Cf"
    )
    return re.sub(r"\s+", " ", text).strip()


def is_meaningful_text(text: str) -> bool:
    """Reject empty and known website-interface text."""
    normalized = clean_text(text).casefold().rstrip(".! ")
    boilerplate = {value.casefold().rstrip(".! ") for value in BOILERPLATE_TEXT}
    return bool(normalized) and normalized not in boilerplate


def _clean_markdown_text(text: str) -> str:
    """Convert common Markdown markup to compact retrieval-friendly text."""
    text = re.sub(r"!\[[^]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b(?:math|text)\s+theme=\{[\"']system[\"']\}\s*", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)
    text = text.replace("```", " ").replace("`", "")
    return clean_text(text)


def parse_markdown_page(markdown: str, url: str) -> DocumentationPage:
    """Parse an official Markdown page into meaningful heading-based sections."""
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
    lines = markdown.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                lines = lines[index + 1 :]
                break

    title = ""
    current_section = ""
    section_parts: list[str] = []
    sections: list[DocumentationSection] = []

    def flush_section() -> None:
        text = _clean_markdown_text("\n".join(section_parts))
        if current_section and is_meaningful_text(text):
            sections.append(DocumentationSection(current_section, text))
        section_parts.clear()

    for line in lines:
        heading_match = heading_pattern.match(line)
        if heading_match:
            flush_section()
            heading_text = _clean_markdown_text(heading_match.group(2))
            if not title and len(heading_match.group(1)) == 1:
                title = heading_text
            current_section = heading_text
        else:
            section_parts.append(line)
    flush_section()

    source_url = url.removesuffix(".md")
    if not title:
        title = sections[0].title if sections else source_url
    if not sections:
        raise ValueError(f"No documentation sections found at {url}")
    return DocumentationPage(title=title, url=source_url, sections=tuple(sections))


def parse_document(content: str, url: str) -> DocumentationPage:
    """Parse Markdown sources preferentially, with HTML kept for overrides."""
    if url.endswith(".md") or not re.search(r"<(?:html|main|article|body)\b", content):
        return parse_markdown_page(content, url)
    return parse_page(content, url)


def parse_page(html: str, url: str) -> DocumentationPage:
    """Extract title and heading-based sections from the page's main content."""
    soup = BeautifulSoup(html, "html.parser")
    for unwanted in soup.select("script, style, nav, footer, aside, noscript, svg"):
        unwanted.decompose()

    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        raise ValueError(f"No readable content found at {url}")

    title_tag = main.find("h1") or soup.find("h1") or soup.find("title")
    title = clean_text(title_tag.get_text(" ", strip=True)) if title_tag else url
    current_section = title
    section_parts: list[str] = []
    sections: list[DocumentationSection] = []

    def flush_section() -> None:
        text = clean_text(" ".join(section_parts))
        if is_meaningful_text(text):
            sections.append(DocumentationSection(current_section, text))
        section_parts.clear()

    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre"]):
        if not isinstance(element, Tag):
            continue
        text = clean_text(element.get_text(" ", strip=True))
        if not text:
            continue
        if element.name in {"h1", "h2", "h3", "h4"}:
            if element is title_tag and text == title:
                continue
            flush_section()
            current_section = text
        elif element.name == "li" and element.find_parent("li") is not None:
            continue
        else:
            section_parts.append(text)

    flush_section()
    if not sections:
        raise ValueError(f"No documentation sections found at {url}")
    return DocumentationPage(title=title, url=url, sections=tuple(sections))


def _split_text(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative")

    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words):
            added = len(words[end]) + (1 if end > start else 0)
            if end > start and length + added > max_chars:
                break
            length += added
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        next_start = max(start + 1, end - overlap_words)
        start = next_start
    return chunks


def stable_chunk_id(
    url: str, section: str, section_number: int, chunk_number: int
) -> str:
    """Build a stable ID from a chunk's deterministic source location."""
    value = f"{url}\n{section_number}\n{section}\n{chunk_number}".encode()
    return hashlib.sha256(value).hexdigest()[:24]


def chunk_sections(
    page: DocumentationPage,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[DocumentationChunk]:
    """Split every page section and attach retrieval metadata."""
    chunks: list[DocumentationChunk] = []
    for section_number, section in enumerate(page.sections):
        for chunk_number, text in enumerate(
            _split_text(section.text, max_chars, overlap_words)
        ):
            if not is_meaningful_text(text):
                continue
            chunks.append(
                DocumentationChunk(
                    id=stable_chunk_id(
                        page.url, section.title, section_number, chunk_number
                    ),
                    title=page.title,
                    section=section.title,
                    url=page.url,
                    text=text,
                )
            )
    return chunks


def save_documents(chunks: list[DocumentationChunk], output_path: Path) -> None:
    """Atomically replace the generated JSON document file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps([asdict(chunk) for chunk in chunks], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
