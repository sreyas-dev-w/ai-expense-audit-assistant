"""Unit tests for claim submission's ``agent_response`` row creation.

Submitting a claim must also create its ``agent_response`` row in the same
transaction (empty stage outputs) so a persisted claim always has one row that
the agents progressively fill in.
"""
from decimal import Decimal

from app.schemas.claim import FoodMealsClaimCreate
from app.schemas.expense import FoodMealsData, LineItem
from app.services.claim_service import ClaimSubmissionService
from tests.conftest import make_employee_row, make_fake_session_factory


def _food_claim_create() -> FoodMealsClaimCreate:
    return FoodMealsClaimCreate(
        employee_id="EMP-001",
        category="FOOD_MEALS",
        business_purpose="Client dinner",
        merchant_name="Zulu Bistro",
        project_code="PROJ-1",
        claim_amount=Decimal("2000.00"),
        category_data=FoodMealsData(
            meal_type="Dinner",
            merchant_name="Zulu Bistro",
            number_of_people=2,
            line_items=[
                LineItem(item_header="Dinner", item_amount=Decimal("2000.00"))
            ],
        ),
    )


async def test_submit_claim_creates_agent_response_row(monkeypatch):
    store = {("employees", "EMP-001"): make_employee_row()}
    next_ids = {}
    factory = make_fake_session_factory(store, next_ids)
    monkeypatch.setattr(
        "app.services.claim_service.store_receipt",
        lambda *_args, **_kwargs: "/tmp/fake-receipt.jpg",
    )

    service = ClaimSubmissionService(session_factory=factory)
    response = await service.submit_claim(
        claim=_food_claim_create(),
        receipt_filename="receipt.jpg",
        receipt_content=b"fake-jpeg",
        receipt_mime_type="image/jpeg",
    )

    assert response.claim_id == 1
    agent_response_rows = [row for (name, _), row in store.items() if name == "agent_response"]
    assert len(agent_response_rows) == 1
    row = agent_response_rows[0]
    assert row.claim_id == response.claim_id
    assert row.validation_response is None
    assert row.policy_response is None
    assert row.notes is None
    assert row.confidence_score is None