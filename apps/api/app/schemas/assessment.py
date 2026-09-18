"""Contracts for the Audit Agent's LLM assessment step.

The ``AuditAssessment`` is the structured payload the LLM returns when it
summarises the stage outputs (OCR extraction, Policy RAG result, Validation
result). It is the single contract that drives the persisted decision-support
values: the note shown to the auditor (``summary``), the AI recommendation
(``ai_decision``), the triage priority and the confidence.

It deliberately carries no free-form fields and only the values that are
persisted: ``summary`` -> ``agent_response.notes``, ``confidence`` ->
``agent_response.confidence_score``, and ``ai_decision`` / ``priority`` onto
the ``claims`` row via the finish node. It never writes to the existing
``policy_response`` / ``validation_response`` JSONB columns.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AIDecision, ClaimPriority


class AuditAssessment(BaseModel):
    """LLM output schema for the audit assessment step.

    LLM output is untrusted until Pydantic-validated; ``extra="forbid"``
    rejects hallucinated fields.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    ai_decision: AIDecision
    priority: ClaimPriority
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("summary")
    @classmethod
    def _summary_not_blank(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("summary must not be empty")
        return value

    @field_validator("ai_decision", "priority", mode="before")
    @classmethod
    def _coerce_enum_case(cls, value):
        """Tolerate uppercase LLM output while persisting the canonical enum."""
        if isinstance(value, str):
            return value.lower()
        return value