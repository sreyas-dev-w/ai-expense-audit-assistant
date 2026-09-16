"""Tests for store_validation_result insert behaviour."""
from decimal import Decimal

from app.schemas.validation import (
    ValidationAgentError,
    ValidationAgentOutput,
    ValidationAgentResult,
    ValidationAgentStatus,
    ValidationVerdict,
)
from app.services.validation_service import ClaimNotFoundError, ValidationService


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSessionFactory:
    def __init__(self, session: FakeSession):
        self.session = session

    def __call__(self):
        return self.session


def _success_result() -> ValidationAgentResult:
    return ValidationAgentResult(
        status=ValidationAgentStatus.SUCCESS,
        output=ValidationAgentOutput(
            verdict=ValidationVerdict.FAIL,
            confidence=0.9,
            findings=[],
            summary="1 blocking validation issue(s). Claimed spend amount does not match the receipt total.",
        ),
    )


def _error_result() -> ValidationAgentResult:
    return ValidationAgentResult(
        status=ValidationAgentStatus.ERROR,
        error=ValidationAgentError(code="malformed_input", message="bad"),
    )


async def test_store_validation_result_inserts_jsonb_payload(monkeypatch):
    inserted: dict = {}

    class FakeClaimRepo:
        def __init__(self, session):
            self.session = session

        async def get_claim(self, claim_id):
            return object()

    class FakeAgentRepo:
        def __init__(self, session):
            self.session = session

        async def insert_validation_response(self, **kwargs):
            inserted.update(kwargs)

            class Row:
                id = 17

            return Row()

    monkeypatch.setattr(
        "app.services.validation_service.ClaimRepository", FakeClaimRepo
    )
    monkeypatch.setattr(
        "app.services.validation_service.AgentResponseRepository", FakeAgentRepo
    )

    session = FakeSession()
    service = ValidationService(
        llm_client=object(),
        session_factory=FakeSessionFactory(session),
    )
    stored_id = await service.store_validation_result(
        claim_id=3, result=_success_result()
    )
    assert stored_id == 17
    assert session.committed is True
    assert inserted["claim_id"] == 3
    assert inserted["validation_response"]["verdict"] == "FAIL"
    assert inserted["confidence_score"] == Decimal("0.90")


async def test_store_validation_result_skips_error_envelopes(monkeypatch):
    class Boom:
        def __init__(self, session):
            raise AssertionError("should not open repositories for ERROR results")

    monkeypatch.setattr("app.services.validation_service.ClaimRepository", Boom)
    service = ValidationService(llm_client=object())
    assert await service.store_validation_result(claim_id=3, result=_error_result()) is None


async def test_store_validation_result_rejects_unknown_claim(monkeypatch):
    class FakeClaimRepo:
        def __init__(self, session):
            self.session = session

        async def get_claim(self, claim_id):
            return None

    monkeypatch.setattr(
        "app.services.validation_service.ClaimRepository", FakeClaimRepo
    )
    session = FakeSession()
    service = ValidationService(
        llm_client=object(),
        session_factory=FakeSessionFactory(session),
    )
    try:
        await service.store_validation_result(claim_id=99, result=_success_result())
        assert False, "expected ClaimNotFoundError"
    except ClaimNotFoundError as exc:
        assert exc.claim_id == 99
        assert session.committed is False
