"""Shared object factories (FastAPI dependencies + agent wiring).

``GeminiEmbeddingProvider`` and ``GeminiClient`` wrap an HTTP client and are
stateless per request, so they are cached for the process lifetime. Policy
services are cheap to build and hold no mutable request state.
"""
from functools import lru_cache

from app.services.embedding_service import EmbeddingProvider, GeminiEmbeddingProvider
from app.services.audit_service import AuditService
from app.services.claim_service import ClaimSubmissionService
from app.services.gemini_client import GeminiClient
from app.services.policy_document_service import PolicyDocumentService
from app.services.rag_service import PolicyRagService
from app.services.validation_context_service import ValidationContextService
from app.services.validation_service import ValidationService


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


def get_claim_submission_service() -> ClaimSubmissionService:
    return ClaimSubmissionService()

def get_validation_context_service() -> ValidationContextService:
    return ValidationContextService()


def get_validation_service() -> ValidationService:
    return ValidationService(
        llm_client=get_llm_client(),
        context_service=get_validation_context_service(),
    )

