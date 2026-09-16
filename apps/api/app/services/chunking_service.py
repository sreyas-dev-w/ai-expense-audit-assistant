"""Deterministic, section-aware chunking of policy text.

The policy PDF is organized in numbered sections (e.g. "3. MEAL
REIMBURSEMENT"). Chunking keeps section headings attached to their content so
each chunk carries enough policy context for grounded retrieval. Sections
longer than ``chunk_size`` are split into overlapping word-safe windows with
the section title repeated as a prefix.
"""
import re
from dataclasses import dataclass, field
from typing import Any

SECTION_RE = re.compile(
    r"^(?P<num>\d{1,2})\.\s+(?P<title>[A-Z][A-Z0-9 &'()+.,-]+)$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PolicyTextChunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def extract_policy_version(text: str) -> str | None:
    """Extract the ``Policy Version`` header value, e.g. EXPENSE-POLICY-V1."""
    match = re.search(r"Policy Version:\s*([A-Za-z0-9\-_]+)", text)
    return match.group(1) if match else None


def chunk_policy_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 80,
) -> list[PolicyTextChunk]:
    if not text or not text.strip():
        raise ValueError("cannot chunk empty policy text")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    sections = _split_sections(text)
    chunks: list[PolicyTextChunk] = []
    index = 0
    for section_number, title, body in sections:
        section_text = f"{title}\n\n{body}".strip()
        for piece in _window(section_text, chunk_size, overlap):
            chunks.append(
                PolicyTextChunk(
                    text=piece,
                    metadata={
                        "section": title,
                        "section_number": section_number,
                        "chunk_index": index,
                    },
                )
            )
            index += 1
    return chunks


def _split_sections(
    text: str,
) -> list[tuple[str | None, str, str]]:
    """Split text into (section_number, title, body) tuples."""
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return [(None, "Policy Document", text)]

    sections: list[tuple[str | None, str, str]] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(
            (match.group("num"), match.group("title").strip(), text[match.end() : end])
        )

    preamble_end = matches[0].start()
    if preamble_end > 0 and text[:preamble_end].strip():
        sections.insert(0, (None, "Policy Document", text[:preamble_end].strip()))
    return sections


def _window(text: str, size: int, overlap: int) -> list[str]:
    """Overlapping, word-safe windows of ``text``.

    Windows break on word boundaries and the overlap preserves surrounding
    context between consecutive chunks.
    """
    text = " ".join(text.split())
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + max(size // 2, 1), end)
            if boundary != -1:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks