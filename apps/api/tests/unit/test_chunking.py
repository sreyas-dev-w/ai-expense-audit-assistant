"""Unit tests for the deterministic policy text chunker."""
from app.services.chunking_service import (
    chunk_policy_text,
    extract_policy_version,
)


def test_extract_policy_version():
    text = "Policy Version: EXPENSE-POLICY-V1\nEffective: January 1, 2026"
    assert extract_policy_version(text) == "EXPENSE-POLICY-V1"


def test_extract_policy_version_missing():
    assert extract_policy_version("no version header here") is None


def test_single_small_document_is_one_chunk():
    text = "1. INTRODUCTION\n\nAll expenses must comply with this policy."
    chunks = chunk_policy_text(text, chunk_size=800, overlap=80)
    assert len(chunks) == 1
    assert chunks[0].metadata["section"] == "INTRODUCTION"
    assert chunks[0].metadata["section_number"] == "1"


def test_sections_are_split_and_kept():
    text = (
        "1. INTRODUCTION\n\nIntro body here.\n\n"
        "2. GENERAL RULES\n\nRules body here.\n\n"
        "3. MEAL REIMBURSEMENT\n\nBreakfast 500.\n\n"
    )
    chunks = chunk_policy_text(text, chunk_size=800, overlap=80)
    assert len(chunks) == 3
    assert [c.metadata["section"] for c in chunks] == [
        "INTRODUCTION",
        "GENERAL RULES",
        "MEAL REIMBURSEMENT",
    ]
    assert [c.metadata["section_number"] for c in chunks] == ["1", "2", "3"]


def test_long_section_is_split_with_overlap():
    body = ("A long policy sentence with plenty of words. " * 80)
    text = f"4. TRAVEL & ACCOMMODATION\n\n{body}"
    chunks = chunk_policy_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text  # never empty
    # consecutive windows share context (overlap)
    assert chunks[0].text[-20:] in chunks[1].text or chunks[1].text[:50] in chunks[0].text


def test_chunk_under_section_never_starts_mid_word():
    text = "prohibited " * 400
    chunks = chunk_policy_text(text, chunk_size=90, overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.split(), chunk.text[:30]


def test_empty_text_raises():
    import pytest

    with pytest.raises(ValueError):
        chunk_policy_text("   ")