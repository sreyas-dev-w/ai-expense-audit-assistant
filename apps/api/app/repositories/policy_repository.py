"""Data access for policy documents and their vector chunks.

Persistence-only: services own session lifecycle and transaction boundaries
(see ``docs/backend/reliability.md``).
"""
from typing import Any, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- documents ---------------------------------------------------------

    async def get_document(self, policy_id: int) -> PolicyDocument | None:
        return await self._session.get(PolicyDocument, policy_id)

    async def get_document_by_hash(self, doc_hash: str) -> PolicyDocument | None:
        stmt = select(PolicyDocument).where(PolicyDocument.doc_hash == doc_hash)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_documents(
        self, *, limit: int = 100, offset: int = 0
    ) -> list[PolicyDocument]:
        stmt = (
            select(PolicyDocument)
            .order_by(PolicyDocument.policy_id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_document(
        self,
        *,
        filename: str,
        stored_path: str,
        doc_hash: str,
        policy_version: str | None = None,
        status: str = "completed",
        error: str | None = None,
    ) -> PolicyDocument:
        document = PolicyDocument(
            filename=filename,
            stored_path=stored_path,
            doc_hash=doc_hash,
            policy_version=policy_version,
            status=status,
            error=error,
        )
        self._session.add(document)
        return document

    async def delete_document(self, policy_id: int) -> bool:
        document = await self.get_document(policy_id)
        if document is None:
            return False
        await self._session.delete(document)
        return True

    # -- chunks ------------------------------------------------------------

    async def add_chunks(
        self,
        *,
        policy_id: int,
        items: Sequence[tuple[str, dict[str, Any] | None, list[float] | None]],
    ) -> int:
        """Bulk-insert chunks as (content, metadata, embeddings) tuples."""
        for content, metadata_, embeddings in items:
            self._session.add(
                PolicyChunk(
                    policy_id=policy_id,
                    content=content,
                    metadata_=metadata_,
                    embeddings=embeddings,
                )
            )
        return len(items)

    async def delete_chunks(self, policy_id: int) -> int:
        result = await self._session.execute(
            delete(PolicyChunk).where(PolicyChunk.policy_id == policy_id)
        )
        return result.rowcount or 0

    async def count_chunks(self, policy_id: int) -> int:
        stmt = select(func.count(PolicyChunk.id)).where(
            PolicyChunk.policy_id == policy_id
        )
        return (await self._session.execute(stmt)).scalar_one()

    # -- vector search -----------------------------------------------------

    async def search_chunks(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        policy_id: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[tuple[PolicyChunk, float]]:
        """Return (chunk, similarity) pairs ordered most-similar first.

        Cosine distance ascending == most similar first; similarity is
        ``1 - cosine_distance``. RESULTS may contain fewer than ``top_k`` rows
        when a threshold filters low-similarity matches out.
        """
        distance = PolicyChunk.embeddings.cosine_distance(query_vector)
        stmt = select(PolicyChunk, (1 - distance).label("similarity")).where(
            PolicyChunk.embeddings.is_not(None)
        )
        if policy_id is not None:
            stmt = stmt.where(PolicyChunk.policy_id == policy_id)
        stmt = stmt.order_by(distance.asc()).limit(top_k)

        rows = (await self._session.execute(stmt)).all()
        results: list[tuple[PolicyChunk, float]] = []
        for chunk, similarity in rows:
            score = float(similarity)
            if similarity_threshold is None or score >= similarity_threshold:
                results.append((chunk, score))
        return results