"""LangGraph state for the Audit Agent parent workflow."""
from typing import TypedDict

from app.schemas.audit import (
    AuditAgentError,
    AuditAgentResult,
    AuditContext,
    AuditRequest,
)
from app.schemas.extraction import OCRResponse
from app.schemas.policy import PolicyAgentResult
from app.schemas.validation import ValidationAgentResult


class AuditGraphState(TypedDict, total=False):
    request: AuditRequest
    receipt_bytes: bytes | None
    mime_type: str | None
    context: AuditContext
    extraction: OCRResponse | None
    validation: ValidationAgentResult | None
    policy: PolicyAgentResult | None
    result: AuditAgentResult | None
    agent_response_id: int | None
    error: AuditAgentError | None
    persist_warnings: list[str]
