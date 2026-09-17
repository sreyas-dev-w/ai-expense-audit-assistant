"""Shared test doubles for policy ingestion, retrieval and agent tests."""
import hashlib

import pytest
from decimal import Decimal
from datetime import date

from app.models.enums import ExpenseCategory
from app.schemas.expense import FoodMealsData, LineItem
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
            line_items=[
                {"item_header": "Dinner", "item_amount": Decimal("2000.00")}
            ],
        ),
    )


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def food_meals_request() -> FoodMealsPolicyEvaluation:
    return sample_food_meals_request()


# ---------------------------------------------------------------------------
# Audit Agent test doubles
# ---------------------------------------------------------------------------


class FakeOcrAgent:
    """Deterministic stand-in for ``OCRAgent``; returns a canned Extraction."""

    def __init__(self, extraction=None, error=None, label="validate_structured"):
        self._extraction = extraction or sample_food_extraction()
        self._error = error
        self.last_kwargs = None

    async def process(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._extraction


class FakePolicyRunner:
    """Stand-in for the Policy RAG agent's ``run_policy_agent``."""

    def __init__(self, result=None, error=None):
        self._result = result if result is not None else make_policy_result()
        self._error = error
        self.last_request = None

    async def __call__(self, request):
        self.last_request = request
        if self._error is not None:
            raise self._error
        return self._result


class FakeValidationRunner:
    """Stand-in for the (future) Validation Agent runner."""

    def __init__(self, result=None):
        self._result = result
        self.called = False

    async def __call__(self, request):
        self.called = True
        return self._result


class FakeSession:
    """In-memory ``AsyncSession`` double keyed by (table name, primary key)."""

    def __init__(self, store: dict, next_ids: dict):
        self._store = store
        self._next_ids = next_ids
        self._added: list = []

    async def get(self, model, pk):
        return self._store.get((model.__tablename__, pk))

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        while self._added:
            obj = self._added.pop(0)
            table = obj.__tablename__
            for column_key in ("id", "claim_id"):
                if getattr(obj, column_key, None) is None and column_key != "claim_id":
                    obj.id = self._next_id(table)
                    break
            self._store[(table, obj.id)] = obj

    async def commit(self):
        await self.flush()

    async def rollback(self):
        pass

    async def close(self):
        pass

    def _next_id(self, table: str) -> int:
        next_id = self._next_ids.setdefault(table, 1)
        self._next_ids[table] = next_id + 1
        return next_id


def make_fake_session_factory(store: dict, next_ids: dict | None = None):
    """Return a callable factory producing ``FakeSession`` instances over a store.

    The returned factory/callable mirrors ``async_session_factory``'s call
    signature (``session_factory()`` → session).
    """

    def factory():
        return FakeSession(store, next_ids or {})

    return factory


FOOD_CATEGORY_DATA = {
    "meal_type": "Dinner",
    "merchant_name": "Zulu Bistro",
    "number_of_people": 2,
    "line_items": [
        {"item_header": "Dinner", "item_amount": "2000.00"}
    ],
}


def make_food_claim_row(
    claim_id: int = 101,
    *,
    category_data: dict | None = None,
    status="submitted",
    ai_run_status="pending",
    receipt_url: str | None = None,
):
    from app.models.claims import Claim
    from app.models.enums import AIRunStatus, ClaimPriority, ClaimStatus, Currency

    return Claim(
        claim_id=claim_id,
        business_purpose="Client dinner",
        merchant_name="Zulu Bistro",
        category=ExpenseCategory.FOOD_MEALS,
        category_data=category_data if category_data is not None else dict(FOOD_CATEGORY_DATA),
        employee_id="EMP-001",
        project_code="PROJ-1",
        claim_amount=Decimal("2000.00"),
        tax_amount=Decimal("0.00"),
        currency=Currency.INR,
        status=ClaimStatus(status),
        priority=ClaimPriority.MEDIUM,
        ai_run_status=AIRunStatus(ai_run_status),
        ai_decision=None,
        receipt_url=receipt_url,
        claim_created_at=None,
        claim_updated_at=None,
    )


def make_employee_row(
    employee_id: str = "EMP-001", job_level="L2"
):
    from app.models.employees import Employee
    from app.models.enums import JobLevel

    return Employee(
        employee_id=employee_id,
        employee_name="Ada Lovelace",
        job_level=JobLevel(job_level),
        is_manager=False,
    )


def sample_food_extraction():
    from datetime import date

    from app.schemas.extraction import FoodMealsExtraction, LineItem as ExtractionLineItem

    return FoodMealsExtraction(
        is_receipt=True,
        receipt_no="RCP-1001",
        merchant_name="Zulu Bistro",
        expense_date=date(2026, 3, 1).isoformat(),
        claim_amount=2000.0,
        tax_amount=0.0,
        line_items=[
            ExtractionLineItem(description="Dinner", amount=2000.0),
        ],
        currency="INR",
        payment_status="paid",
        meal_type="NON_VEG",
        number_of_people=2,
    )


def make_food_audit_context(claim_id: int = 101, *, receipt_url: str | None = None):
    from app.schemas.audit import ClaimAuditContext
    from app.models.enums import Currency

    return ClaimAuditContext(
        claim_id=claim_id,
        category=ExpenseCategory.FOOD_MEALS,
        category_data=dict(FOOD_CATEGORY_DATA),
        receipt_url=receipt_url,
        merchant_name="Zulu Bistro",
        claim_amount=Decimal("2000.00"),
        tax_amount=Decimal("0.00"),
        currency=Currency.INR,
        business_purpose="Client dinner",
        project_code="PROJ-1",
        employee_id="EMP-001",
        employee_job_level="L2",
        priority=None,
    )


def make_policy_result(decision=PolicyDecision.FLAG_FOR_REVIEW, *, warnings=None):
    from app.schemas.policy import (
        PolicyAgentResult,
        PolicyAgentStatus,
        PolicyReference,
    )

    return PolicyAgentResult(
        status=PolicyAgentStatus.SUCCESS,
        output=PolicyAgentOutput(
            decision=decision,
            confidence=0.85,
            violations=[
                PolicyViolation(
                    policy_reference="Section 3 - Meal Reimbursement",
                    severity=PolicySeverity.WARNING,
                    description="Dinner at 2,000 INR exceeds the 1,500 INR limit.",
                )
            ],
            checks=[
                PolicyCheck(
                    check_name="Per-meal limit",
                    status=PolicyCheckStatus.FAILED,
                    policy_reference="Section 3",
                )
            ],
            reasons=["Dinner exceeds the per-meal limit."],
            warnings=list(warnings or []),
            references=[
                PolicyReference(
                    chunk_id=1,
                    policy_id=1,
                    content="Meal reimbursement policy.",
                    similarity_score=0.9,
                )
            ],
            summary="Dinner claim exceeds the per-meal limit.",
        ),
    )


def build_audit_tools_for(store: dict, next_ids: dict | None = None):
    """Build the real audit tools wired to a FakeSession store."""
    from app.tools import build_audit_tools

    factory = make_fake_session_factory(store, next_ids)
    return build_audit_tools(session_factory=factory)