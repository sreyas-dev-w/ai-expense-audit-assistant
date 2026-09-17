"""Audit Agent graph assembly.

Thin aggregator over the production wiring in ``app/services/audit_service.py``
and the injectable graph builder in ``app/agents/audit_agent.py``. Kept as its
own module so callers import from one place regardless of the wiring they need:

- ``build_default_audit_graph`` — production services/tools + deterministic aggregation.
- ``run_audit`` — run the default graph for a claim and return its result.
"""
from app.agents.audit_agent import build_audit_agent, run_audit_agent
from app.services.audit_service import (
    AuditService,
    aggregate_audit_result,
    build_default_audit_graph,
)

__all__ = [
    "AuditService",
    "aggregate_audit_result",
    "build_audit_agent",
    "build_default_audit_graph",
    "run_audit_agent",
]


async def run_audit(claim_id: int):
    """Convenience one-shot runner using the default production graph."""
    return await AuditService().run_audit(claim_id)