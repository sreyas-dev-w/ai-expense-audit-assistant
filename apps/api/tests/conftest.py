"""Shared test doubles for policy ingestion, retrieval and agent tests."""
import asyncio
import hashlib
import os
import sys
from decimal import Decimal
from datetime import date

import pytest

# Importing app.main constructs OCRAgent, which requires a Gemini key.
os.environ.setdefault("GEMINI_API_KEY", "test-placeholder")

# psycopg async cannot run on Windows ProactorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.models.enums import ExpenseCategory
from app.schemas.expense import FoodMealsData
from app.schemas.policy import (
    FoodMealsPolicyEvaluation,
    PolicyClaimContext,
    PolicyAgentOutput,
    PolicyDecision,
    PolicySeverity,
    PolicyViolation,
    PolicyCheck,
    PolicyCheckStatus,
    RetrievedPolicyChunk,
)
from app.services.embedding_service import EmbeddingProvider

EMBEDDING_DIM = 1536


class FakeEmbedder(EmbeddingProvider):
    """Deterministic, hash-based embeddings.

    Identical text always yields the identical vector, so exact-match queries
    score ~1.0 which lets integration tests assert on retrieval ordering.
    """

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [((digest[i % len(digest)]) / 255.0) * 2 - 1 for i in range(EMBEDDING_DIM)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class StubRagService:
    def __init__(self, chunks: list[RetrievedPolicyChunk] | None = None, error=None):
        self._chunks = chunks or []
        self._error = error

    async def search(self, **kwargs) -> list[RetrievedPolicyChunk]:
        if self._error is not None:
            raise self._error
        return self._chunks


class StubLLMClient:
    """Returns a canned structured payload; inject a callable to control it."""

    def __init__(self, payload=None, error=None):
        self._payload = payload or default_llm_payload()
        self._error = error
        self.last_contents = None

    def generate_structured(self, *, system_instruction, contents, response_schema):
        if self._error is not None:
            raise self._error
        self.last_contents = contents
        return dict(self._payload)


def default_llm_payload() -> dict:
    return {
        "decision": "FLAG_FOR_REVIEW",
        "confidence": 0.85,
        "violations": [
            {
                "policy_reference": "Section 3 - Meal Reimbursement",
                "severity": "warning",
                "description": "Dinner at 2,000 INR exceeds the 1,500 INR limit.",
                "related_chunk_ids": [1],
            }
        ],
        "checks": [
            {
                "check_name": "Per-meal limit",
                "status": "failed",
                "policy_reference": "Section 3",
                "related_chunk_ids": [1],
            }
        ],
        "reasons": ["Dinner exceeds the per-meal limit."],
        "warnings": [],
        "references": [],
        "summary": "Dinner claim exceeds the per-meal limit.",
    }


SAMPLE_CHUNK = RetrievedPolicyChunk(
    chunk_id=1,
    policy_id=1,
    content=(
        "3. MEAL REIMBURSEMENT Meal reimbursement is provided for business "
        "meals. Dinner has a per-meal limit of 1,500 INR. Alcohol is not "
        "reimbursable."
    ),
    similarity_score=0.9,
)


def sample_food_meals_request() -> FoodMealsPolicyEvaluation:
    return FoodMealsPolicyEvaluation(
        category=ExpenseCategory.FOOD_MEALS,
        claim=PolicyClaimContext(
            claim_id=101,
            employee_id="EMP-001",
            employee_job_level="L2",
            merchant_name="Zulu Bistro",
            business_purpose="Client dinner",
            project_code="PROJ-1",
            claim_amount=Decimal("2000.00"),
            expense_date=date(2026, 3, 1),
        ),
        category_data=FoodMealsData(
            meal_type="Dinner",
            merchant_name="Zulu Bistro",
            number_of_people=2,
        ),
    )


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def food_meals_request() -> FoodMealsPolicyEvaluation:
    return sample_food_meals_request()