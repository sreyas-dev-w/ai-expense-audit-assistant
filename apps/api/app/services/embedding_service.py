"""Vector embedding generation for the policy store.

A single, strict **Gemini-only** provider. A missing API key fails explicitly
at construction time so misconfiguration surfaces loudly instead of producing
silently-broken retrieval.

Timeouts are enforced by the calling async services (``asyncio.wait_for``)
since these methods are synchronous I/O calls run via ``asyncio.to_thread``.
"""
from abc import ABC, abstractmethod

from google import genai
from google.genai import types

from app.core.config import settings


class EmbeddingProviderError(Exception):
    def __init__(self, message: str, *, code: str = "embedding_error"):
        super().__init__(message)
        self.code = code


class MissingApiKeyError(EmbeddingProviderError):
    def __init__(self, provider: str):
        super().__init__(
            f"{provider} requires GEMINI_API_KEY to be configured",
            code="missing_api_key",
        )


class EmbeddingProvider(ABC):
    """Produces vector embeddings for documents and queries."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed chunk texts for storage (RETRIEVAL_DOCUMENT task)."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (RETRIEVAL_QUERY task)."""


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        api_key: str = settings.gemini_api_key,
        model: str = settings.embedding_model,
        dimensions: int = settings.embedding_dimension,
        batch_size: int = settings.embedding_batch_size,
    ) -> None:
        if not api_key:
            raise MissingApiKeyError("GeminiEmbeddingProvider")
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._client = genai.Client(api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            batch = texts[offset : offset + self.batch_size]
            response = self._client.models.embed_content(
                model=self.model,
                contents=[self._content(text) for text in batch],
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.dimensions,
                ),
            )
            vectors.extend(self._values(embedding) for embedding in response.embeddings)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = self._client.models.embed_content(
            model=self.model,
            contents=[self._content(text)],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.dimensions,
            ),
        )
        return self._values(response.embeddings[0])

    @staticmethod
    def _content(text: str) -> types.Content:
        """A bare ``list[str]`` is coalesced by the SDK into a single Content
        (hence a single embedding); wrap each string in its own Content."""
        return types.Content(parts=[types.Part(text=text)])

    def _values(self, embedding: types.ContentEmbedding) -> list[float]:
        values = [float(v) for v in embedding.values]
        if len(values) != self.dimensions:
            raise EmbeddingProviderError(
                f"Embedding dimension mismatch: expected {self.dimensions}, "
                f"got {len(values)}",
                code="embedding_dimension_mismatch",
            )
        return values