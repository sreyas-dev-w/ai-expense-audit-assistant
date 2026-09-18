"""Unit tests for the ``AgentResponse`` row lifecycle per claim.

A claim gets exactly one ``agent_response`` row, created eagerly at submission
time with empty stage fields, then populated progressively as the policy and
validation agents respond and the final AI note is generated.
"""
from decimal import Decimal

from app.models.agent_response import AgentResponse
from app.repositories.agent_response_repository import AgentResponseRepository
from tests.conftest import make_fake_session_factory

CLAIM_ID = 101


async def test_create_for_claim_inserts_empty_row():
    store, next_ids = {}, {}
    factory = make_fake_session_factory(store, next_ids)
    session = factory()

    repository = AgentResponseRepository(session)
    row = await repository.create_for_claim(claim_id=CLAIM_ID)

    assert row.id == 1
    assert row.claim_id == CLAIM_ID
    assert row.validation_response is None
    assert row.policy_response is None
    assert row.notes is None
    assert row.confidence_score is None


async def test_get_for_claim_returns_none_when_missing():
    session = make_fake_session_factory({})()
    repository = AgentResponseRepository(session)

    assert await repository.get_for_claim(CLAIM_ID) is None


async def test_get_for_claim_returns_latest_row():
    store = {
        ("agent_response", 1): AgentResponse(id=1, claim_id=CLAIM_ID, notes="old"),
        ("agent_response", 2): AgentResponse(id=2, claim_id=CLAIM_ID, notes="new"),
    }
    session = make_fake_session_factory(store)()
    repository = AgentResponseRepository(session)

    row = await repository.get_for_claim(CLAIM_ID)

    assert row is not None
    assert row.id == 2
    assert row.notes == "new"


async def test_get_or_create_for_claim_creates_when_missing():
    store, next_ids = {}, {}
    session = make_fake_session_factory(store, next_ids)()
    repository = AgentResponseRepository(session)

    row = await repository.get_or_create_for_claim(CLAIM_ID)

    assert row.id == 1
    assert store[("agent_response", 1)].claim_id == CLAIM_ID
    assert store[("agent_response", 1)].notes is None


async def test_update_validation_response_populates_row():
    store, next_ids = {}, {}
    session = make_fake_session_factory(store, next_ids)()
    repository = AgentResponseRepository(session)

    await repository.update_validation_response(
        claim_id=CLAIM_ID,
        validation_response={"verdict": "ok"},
        confidence_score=Decimal("0.90"),
        notes="Validation summary.",
    )

    row = store[("agent_response", 1)]
    assert row.validation_response == {"verdict": "ok"}
    assert row.confidence_score == Decimal("0.90")
    assert row.notes == "Validation summary."
    assert row.policy_response is None


async def test_update_responses_sets_policy_and_validation():
    store, next_ids = {}, {}
    session = make_fake_session_factory(store, next_ids)()
    repository = AgentResponseRepository(session)

    await repository.update_responses(
        claim_id=CLAIM_ID,
        policy_response={"decision": "FLAG_FOR_REVIEW"},
        validation_response={"verdict": "ok"},
        confidence_score=Decimal("0.85"),
    )

    row = store[("agent_response", 1)]
    assert row.policy_response == {"decision": "FLAG_FOR_REVIEW"}
    assert row.validation_response == {"verdict": "ok"}
    assert row.confidence_score == Decimal("0.85")
    assert row.notes is None


async def test_update_responses_skips_none_payloads():
    store, next_ids = {}, {}
    session = make_fake_session_factory(store, next_ids)()
    repository = AgentResponseRepository(session)

    await repository.update_responses(
        claim_id=CLAIM_ID,
        policy_response={"decision": "APPROVE"},
        validation_response=None,
    )

    row = store[("agent_response", 1)]
    assert row.policy_response == {"decision": "APPROVE"}
    assert row.validation_response is None


async def test_update_responses_does_not_clobber_existing_with_none():
    store = {
        ("agent_response", 1): AgentResponse(
            id=1, claim_id=CLAIM_ID, validation_response={"verdict": "ok"}
        )
    }
    session = make_fake_session_factory(store)()
    repository = AgentResponseRepository(session)

    await repository.update_responses(
        claim_id=CLAIM_ID, policy_response={"decision": "REJECT"}
    )

    row = store[("agent_response", 1)]
    assert row.validation_response == {"verdict": "ok"}
    assert row.policy_response == {"decision": "REJECT"}


async def test_update_notes_fills_the_existing_row():
    store = {
        ("agent_response", 1): AgentResponse(id=1, claim_id=CLAIM_ID),
        ("claims", CLAIM_ID): object(),
    }
    session = make_fake_session_factory(store)()
    repository = AgentResponseRepository(session)

    await repository.update_notes(claim_id=CLAIM_ID, notes="AI recommendation.")

    row = store[("agent_response", 1)]
    assert row.notes == "AI recommendation."
    assert len([k for k in store if k[0] == "agent_response"]) == 1


async def test_update_assessment_writes_only_note_and_confidence():
    store = {
        ("agent_response", 1): AgentResponse(
            id=1,
            claim_id=CLAIM_ID,
            validation_response={"verdict": "ok"},
            policy_response={"decision": "FLAG_FOR_REVIEW"},
        )
    }
    session = make_fake_session_factory(store)()
    repository = AgentResponseRepository(session)

    await repository.update_assessment(
        claim_id=CLAIM_ID,
        notes="The claim is compliant.",
        confidence_score=Decimal("0.95"),
    )

    row = store[("agent_response", 1)]
    assert row.notes == "The claim is compliant."
    assert row.confidence_score == Decimal("0.95")
    # Existing envelope columns are never touched by the assessment stage.
    assert row.validation_response == {"verdict": "ok"}
    assert row.policy_response == {"decision": "FLAG_FOR_REVIEW"}