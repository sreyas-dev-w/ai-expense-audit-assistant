from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentResponseDetails(BaseModel):
    id: int
    claim_id: int
    validation_response: dict[str, Any] | None
    policy_response: dict[str, Any] | None
    notes: str | None
    confidence_score: Decimal | None

    model_config = ConfigDict(from_attributes=True)