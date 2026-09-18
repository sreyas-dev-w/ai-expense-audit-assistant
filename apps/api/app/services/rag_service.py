"""Semantic retrieval against the policy vector store.

Shared by the search API route and the Policy RAG Agent. Retrieval is
embedding + pgvector search in a short read-only transaction; reasoning over
the retrieved context happens in the agent, never here.
"""
import asyncio

from app.core.config import settings
from app.db.session import async_session_factory
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import RetrievedPolicyChunk
from app.services.embedding_service import EmbeddingProvider, EmbeddingProviderError


class PolicyRetrievalError(Exception):
    def __init__(self, message: str, *, code: str = "policy_retrieval_error"):
        super().__init__(message)
        self.code = code


class PolicyRagService:
    def __init__(
        self,
        *,
        session_factory=async_session_factory,
        embedding_provider: EmbeddingProvider,
        default_top_k: int = settings.policy_search_default_top_k,
        max_top_k: int = settings.policy_search_max_top_k,
        default_threshold: float = settings.policy_search_similarity_threshold,
        embedding_timeout_seconds: int = settings.embedding_timeout_seconds,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_provider = embedding_provider
        self._default_top_k = default_top_k
        self._max_top_k = max_top_k
        self._default_threshold = default_threshold
        self._embedding_timeout_seconds = embedding_timeout_seconds

    async def search(
        self,
        *,
        query: str,
        top_k: int | None = None,
        policy_id: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedPolicyChunk]:
        k = min(top_k or self._default_top_k, self._max_top_k)
        threshold = (
            self._default_threshold
            if similarity_threshold is None
            else similarity_threshold
        )

        try:
            vector = await asyncio.wait_for(
                asyncio.to_thread(self._embedding_provider.embed_query, query),
                timeout=self._embedding_timeout_seconds,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise PolicyRetrievalError(
                "Timed out while embedding the search query",
                code="embedding_timeout",
            ) from exc
        except EmbeddingProviderError as exc:
            raise PolicyRetrievalError(str(exc), code=exc.code) from exc

        async with self._session_factory() as session:
            repository = PolicyRepository(session)
            rows = await repository.search_chunks(
                query_vector=vector,
                top_k=k,
                policy_id=policy_id,
                similarity_threshold=threshold,
            )

        return [
            RetrievedPolicyChunk(
                chunk_id=chunk.id,
                policy_id=chunk.policy_id,
                policy_filename=filename,
                content=chunk.content,
                metadata=chunk.metadata_,
                similarity_score=similarity,
            )
            for chunk, similarity, filename in rows
        ]