"""Policy document ingestion orchestration.

Pipeline (see ``docs/backend/rag-pipeline.md``):

    PDF upload → validate → store dump → extract text → chunk
    → embed (external, outside any DB transaction)
    → persist document + chunks in one short transaction

Embedding happens *before* the write transaction is opened so no long-lived
transaction is held across potentially slow LLM calls.
"""
import asyncio
from pathlib import Path

from app.core.config import settings
from app.db.session import async_session_factory
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import PolicyIngestResult
from app.services.chunking_service import chunk_policy_text, extract_policy_version
from app.services.embedding_service import EmbeddingProvider, EmbeddingProviderError
from app.services.file_service import store_pdf
from app.services.pdf_extraction_service import PdfExtractionError, extract_pdf_text
from app.utils.file_hash import sha256_hex


class InvalidPdfError(Exception):
    """Uploaded bytes are not a PDF."""


class PolicyDocumentIngestionError(Exception):
    def __init__(self, message: str, *, code: str = "policy_ingestion_error"):
        super().__init__(message)
        self.code = code


class PolicyDocumentService:
    def __init__(
        self,
        *,
        session_factory=async_session_factory,
        embedding_provider: EmbeddingProvider,
        chunk_size: int = settings.policy_chunk_size,
        chunk_overlap: int = settings.policy_chunk_overlap,
        embedding_timeout_seconds: int = settings.embedding_timeout_seconds,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_provider = embedding_provider
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embedding_timeout_seconds = embedding_timeout_seconds

    async def ingest_pdf(
        self, *, filename: str, content: bytes, force: bool = False
    ) -> PolicyIngestResult:
        if not content.startswith(b"%PDF"):
            raise InvalidPdfError(
                "Only PDF files are supported; upload must start with the %PDF signature"
            )

        doc_hash = sha256_hex(content)
        existing = await self._find_by_hash(doc_hash)
        if existing is not None and not force:
            return PolicyIngestResult(
                policy_id=existing.policy_id,
                filename=existing.filename,
                doc_hash=doc_hash,
                chunk_count=existing.chunk_count,
                reingested=False,
            )

        stored_path = store_pdf(filename, content)
        previous_stored_path = existing.stored_path if existing is not None else None
        try:
            chunks, policy_version = self._chunk_policy(stored_path)
            vectors = await self._embed(chunks)
            return await self._persist(
                existing_policy_id=existing.policy_id if existing is not None else None,
                force=force,
                filename=filename,
                stored_path=str(stored_path),
                previous_stored_path=previous_stored_path,
                doc_hash=doc_hash,
                policies_version=policy_version,
                chunks=chunks,
                vectors=vectors,
            )
        except PdfExtractionError as exc:
            stored_path.unlink(missing_ok=True)
            raise PolicyDocumentIngestionError(
                str(exc), code=exc.code
            ) from exc
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

    async def _find_by_hash(self, doc_hash: str):
        async with self._session_factory() as session:
            return await PolicyRepository(session).get_document_by_hash(doc_hash)

    async def get_document(self, policy_id: int):
        async with self._session_factory() as session:
            return await PolicyRepository(session).get_document(policy_id)

    async def list_documents(
        self, *, limit: int = 100, offset: int = 0
    ) -> list:
        async with self._session_factory() as session:
            return await PolicyRepository(session).list_documents(
                limit=limit, offset=offset
            )

    async def delete_document(self, policy_id: int) -> bool:
        async with self._session_factory() as session:
            repository = PolicyRepository(session)
            try:
                document = await repository.get_document(policy_id)
                deleted = await repository.delete_document(policy_id)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        if deleted and document is not None:
            self._remove_stored_file(document.stored_path)
        return deleted

    @staticmethod
    def _remove_stored_file(stored_path: str) -> None:
        try:
            Path(stored_path).unlink(missing_ok=True)
        except OSError:
            pass

    def _chunk_policy(self, stored_path):
        pages = extract_pdf_text(stored_path)
        full_text = "\n\n".join(pages)
        if not full_text.strip():
            raise PdfExtractionError(
                f"PDF at {stored_path} contains no extractable text"
            )
        chunks = chunk_policy_text(
            full_text, chunk_size=self._chunk_size, overlap=self._chunk_overlap
        )
        return chunks, extract_policy_version(full_text)

    async def _embed(self, chunks):
        texts = [chunk.text for chunk in chunks]
        try:
            vectors = await asyncio.wait_for(
                asyncio.to_thread(
                    self._embedding_provider.embed_documents, texts
                ),
                timeout=self._embedding_timeout_seconds,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise PolicyDocumentIngestionError(
                "Timed out while embedding policy chunks",
                code="embedding_timeout",
            ) from exc
        except EmbeddingProviderError as exc:
            raise PolicyDocumentIngestionError(
                str(exc), code=exc.code
            ) from exc
        if len(vectors) != len(chunks):
            raise PolicyDocumentIngestionError(
                "Embedding provider returned a different number of vectors "
                f"({len(vectors)}) than chunks ({len(chunks)})",
                code="embedding_count_mismatch",
            )
        return vectors

    async def _persist(
        self,
        *,
        existing_policy_id: int | None,
        force: bool,
        filename: str,
        stored_path: str,
        previous_stored_path: str | None,
        doc_hash: str,
        policies_version: str | None,
        chunks,
        vectors,
    ) -> PolicyIngestResult:
        async with self._session_factory() as session:
            repository = PolicyRepository(session)
            try:
                if existing_policy_id is not None and force:
                    await repository.delete_chunks(existing_policy_id)
                    document = await repository.get_document(existing_policy_id)
                    document.filename = filename
                    document.stored_path = stored_path
                    document.policy_version = policies_version
                    document.status = "completed"
                    document.error = None
                    policy_id = existing_policy_id
                else:
                    document = await repository.create_document(
                        filename=filename,
                        stored_path=stored_path,
                        doc_hash=doc_hash,
                        policy_version=policies_version,
                    )
                    await session.flush()
                    policy_id = document.policy_id

                items = [
                    (chunk.text, chunk.metadata, embedding)
                    for chunk, embedding in zip(chunks, vectors)
                ]
                await repository.add_chunks(policy_id=policy_id, items=items)
                document.chunk_count = len(items)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        if previous_stored_path is not None and previous_stored_path != stored_path:
            self._remove_stored_file(previous_stored_path)
        return PolicyIngestResult(
            policy_id=policy_id,
            filename=filename,
            doc_hash=doc_hash,
            chunk_count=len(items),
            reingested=bool(existing_policy_id is not None and force),
        )