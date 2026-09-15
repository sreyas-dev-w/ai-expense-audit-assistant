import operator
from typing import Annotated, TypedDict


class ClaimAuditState(TypedDict):
    """State schema tracked across the LangGraph claim-audit workflow."""

    claim_id: int
    employee_id: str
    claim_name: str
    claim_amount: float
    document_path: str | None
    ocr_text: dict
    is_valid: bool
    is_compliant: bool
    violations: Annotated[list[str], operator.add]
    requires_human_review: bool
    final_status: str | None
    audit_trail: Annotated[list[str], operator.add]