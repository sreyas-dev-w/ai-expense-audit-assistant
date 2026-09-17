"""Shared object factories (FastAPI dependencies + agent wiring).

``GeminiEmbeddingProvider`` and ``GeminiClient`` wrap an HTTP client and are
stateless per request, so they are cached for the process lifetime. Policy
services are cheap to build and hold no mutable request state.
"""
from functools import lru_cache

from app.services.embedding_service import EmbeddingProvider, GeminiEmbeddingProvider
from app.services.audit_service import AuditService
from app.services.gemini_client import GeminiClient
from app.services.policy_document_service import PolicyDocumentService
from app.services.rag_service import PolicyRagService


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()


@lru_cache(maxsize=1)
def get_llm_client() -> GeminiClient:
    return GeminiClient()


def get_policy_rag_service() -> PolicyRagService:
    return PolicyRagService(embedding_provider=get_embedding_provider())


def get_policy_document_service() -> PolicyDocumentService:
    return PolicyDocumentService(embedding_provider=get_embedding_provider())


def get_audit_service() -> AuditService:
    return AuditService()