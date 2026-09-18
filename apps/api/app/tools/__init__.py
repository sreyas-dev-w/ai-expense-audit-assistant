"""Tool registry for the Audit Agent.

Returns the narrow, least-privilege tools the orchestration nodes use
(``docs/agents/agent-tools.md``). Each tool owns its own short-lived DB
transaction via an injected ``session_factory`` and commits before returning.
"""
from app.tools.base import AuditTool
from app.tools.claim_tools import (
    GetClaimTool,
    UpdateAuditRunStatusTool,
    UpdateClaimResultTool,
)
from app.tools.receipt_tools import FetchReceiptTool
from app.tools.response_tools import (
    GetAgentResponseTool,
    StoreAgentResponseTool,
    StoreAssessmentTool,
    StoreExtractionTool,
)


def build_audit_tools(*, session_factory=None) -> dict[str, AuditTool]:
    """Build the audit workflow tool set keyed by tool name."""
    if session_factory is None:
        from app.db.session import async_session_factory

        session_factory = async_session_factory

    tools = [
        GetClaimTool(session_factory=session_factory),
        UpdateAuditRunStatusTool(session_factory=session_factory),
        FetchReceiptTool(),
        StoreExtractionTool(session_factory=session_factory),
        StoreAgentResponseTool(session_factory=session_factory),
        GetAgentResponseTool(session_factory=session_factory),
        StoreAssessmentTool(session_factory=session_factory),
        UpdateClaimResultTool(session_factory=session_factory),
    ]
    return {tool.name: tool for tool in tools}


__all__ = [
    "AuditTool",
    "AuditToolError",
    "build_audit_tools",
    "GetClaimTool",
    "UpdateAuditRunStatusTool",
    "UpdateClaimResultTool",
    "FetchReceiptTool",
    "StoreExtractionTool",
    "StoreAgentResponseTool",
    "GetAgentResponseTool",
    "StoreAssessmentTool",
]