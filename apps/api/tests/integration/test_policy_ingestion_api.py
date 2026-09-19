"""Integration tests: policy ingestion + search API against the real DB.

The Gemini key is unavailable in CI/dev, so the retrieval service is wired to
a deterministic fake embedding provider. Everything else (route handling,
filesystem dump, PDF extraction, chunking, pgvector persistence and
similarity search) exercises the real stack.
"""
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from app.db.session import async_session_factory
from app.main import app
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument
from app.services.policy_document_service import PolicyDocumentService
from app.services.rag_service import PolicyRagService

from tests.conftest import FakeEmbedder

SEED_PDF = Path(__file__).resolve().parents[4] / "data" / "seed" / "expense_policy_v1.pdf"


@pytest.fixture
async def seeded_policy_ids() -> set[int]:
    """policy_ids that existed *before* the test, so cleanup never touches them.

    These tests run against the real (shared) database. Ingestion de-dupes by
    file hash, so ``ingest_pdf`` may return the id of a document we did not
    create here. Cleanup must only delete documents the test itself created;
    deleting a pre-existing policy would destroy data we do not own.
    """
    async with async_session_factory() as session:
        ids = (await session.execute(select(PolicyDocument.policy_id))).scalars().all()
    return set(ids)


async def _delete_if_created(
    policy_id: int | None,
    seeded_policy_ids: set[int],
    policy_service: PolicyDocumentService,
) -> None:
    if policy_id is not None and policy_id not in seeded_policy_ids:
        await policy_service.delete_document(policy_id)


@pytest.fixture
def policy_service() -> PolicyDocumentService:
    return PolicyDocumentService(embedding_provider=FakeEmbedder())


@pytest.fixture
def rag_service() -> PolicyRagService:
    return PolicyRagService(embedding_provider=FakeEmbedder())


@pytest.fixture
async def client(policy_service, rag_service):
    app.dependency_overrides.clear()
    from app.core.dependencies import (
        get_policy_document_service,
        get_policy_rag_service,
    )

    app.dependency_overrides[get_policy_document_service] = lambda: policy_service
    app.dependency_overrides[get_policy_rag_service] = lambda: rag_service
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _chunk_contents(policy_id: int) -> list[tuple[int, str]]:
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(PolicyChunk)
                .where(PolicyChunk.policy_id == policy_id)
                .order_by(PolicyChunk.id)
            )
        ).scalars().all()
        return [(row.id, row.content) for row in rows]


async def test_ingest_upload_and_list_documents(client, policy_service, seeded_policy_ids):
    policy_id = None
    try:
        response = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, SEED_PDF.read_bytes(), "application/pdf")},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["chunk_count"] > 0
        assert body["reingested"] is False
        policy_id = body["policy_id"]

        listed = await client.get("/api/v1/policies/documents")
        assert listed.status_code == 200
        docs = listed.json()
        assert any(doc["policy_id"] == policy_id and doc["policy_version"] == "EXPENSE-POLICY-V1" for doc in docs)

        detail = await client.get(f"/api/v1/policies/documents/{policy_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
    finally:
        await _delete_if_created(policy_id, seeded_policy_ids, policy_service)


async def test_ingest_rejects_non_pdf(client):
    response = await client.post(
        "/api/v1/policies/documents",
        files={"file": ("note.txt", b"this is not a pdf", "text/plain")},
    )
    assert response.status_code == 400


async def test_dedupe_and_force_reingest(client, policy_service, seeded_policy_ids):
    content = SEED_PDF.read_bytes()
    policy_id = None
    try:
        first = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, content, "application/pdf")},
        )
        assert first.status_code == 201
        policy_id = first.json()["policy_id"]

        dup = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, content, "application/pdf")},
        )
        assert dup.status_code == 201
        assert dup.json()["policy_id"] == policy_id
        assert dup.json()["reingested"] is False

        forced = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, content, "application/pdf")},
            data={"force": "true"},
        )
        assert forced.status_code == 201
        assert forced.json()["policy_id"] == policy_id
        assert forced.json()["reingested"] is True
        assert forced.json()["chunk_count"] == first.json()["chunk_count"]
    finally:
        await _delete_if_created(policy_id, seeded_policy_ids, policy_service)


async def test_search_returns_exact_match_first(client, policy_service, seeded_policy_ids):
    policy_id = None
    try:
        ingest = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, SEED_PDF.read_bytes(), "application/pdf")},
        )
        assert ingest.status_code == 201
        policy_id = ingest.json()["policy_id"]

        chunk_id, chunk_text = (await _chunk_contents(policy_id))[0]

        response = await client.post(
            "/api/v1/policies/search",
            json={"query": chunk_text, "top_k": 5, "policy_id": policy_id},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["count"] >= 1
        top = body["results"][0]
        assert top["chunk_id"] == chunk_id
        assert top["similarity_score"] > 0.99
        # the policy document filename is joined in from policy_documents
        assert top["policy_filename"] == SEED_PDF.name
    finally:
        await _delete_if_created(policy_id, seeded_policy_ids, policy_service)


async def test_search_respects_threshold_and_policy_filter(client, policy_service, seeded_policy_ids):
    policy_id = None
    try:
        ingest = await client.post(
            "/api/v1/policies/documents",
            files={"file": (SEED_PDF.name, SEED_PDF.read_bytes(), "application/pdf")},
        )
        policy_id = ingest.json()["policy_id"]
        _, chunk_text = (await _chunk_contents(policy_id))[0]

        crisp = await client.post(
            "/api/v1/policies/search",
            json={"query": chunk_text, "policy_id": policy_id, "similarity_threshold": 0.99},
        )
        assert crisp.json()["count"] == 1

        impossible = await client.post(
            "/api/v1/policies/search",
            json={"query": chunk_text, "policy_id": policy_id, "similarity_threshold": 1.5},
        )
        assert impossible.status_code == 422  # pydantic bounds

        wrong_policy = await client.post(
            "/api/v1/policies/search",
            json={"query": chunk_text, "policy_id": 999999},
        )
        assert wrong_policy.json()["count"] == 0
    finally:
        await _delete_if_created(policy_id, seeded_policy_ids, policy_service)


async def test_get_and_delete(client, policy_service, seeded_policy_ids):
    if seeded_policy_ids:
        pytest.skip(
            "Policy documents already exist; ingest would re-use a pre-existing "
            "document and this test deletes it, so it is skipped against live data"
        )
    ingest = await client.post(
        "/api/v1/policies/documents",
        files={"file": (SEED_PDF.name, SEED_PDF.read_bytes(), "application/pdf")},
    )
    policy_id = ingest.json()["policy_id"]

    deleted = await client.delete(f"/api/v1/policies/documents/{policy_id}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/policies/documents/{policy_id}")
    assert missing.status_code == 404