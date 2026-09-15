"""Compiled LangGraph state machine for the claim-audit workflow.

Node sequence:
    1. OCR agent      -> extracts mock metadata from the uploaded asset
    2. Validation agent -> checks the OCR total against the account budget
    3. Policy agent   -> placeholder compliance gate

Conditional routing:
    - Any violation OR is_valid=False routes to the FAILED terminator.
    - Otherwise the state routes to the UNDER_REVIEW terminator.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    Claim,
    ClaimStatus,
    Employee,
    Project,
)
from app.workflow.state import ClaimAuditState


# ---------------------------------------------------------------------------
# Node 1: OCR agent
# ---------------------------------------------------------------------------
async def ocr_agent(state: ClaimAuditState) -> dict[str, Any]:
    """Simulate OCR extraction of merchant / date / total_amount from the asset."""
    extracted: dict[str, Any] = {
        "merchant": f"Vendor-{uuid4().hex[:6].upper()}",
        "date": date.today().isoformat(),
        "total_amount": round(state.get("claim_amount", 0.0), 2),
    }
    return {
        "ocr_text": extracted,
        "audit_trail": ["ocr_agent: extracted document metadata"],
    }


# ---------------------------------------------------------------------------
# Node 2: Validation agent
# ---------------------------------------------------------------------------
async def validation_agent(
    state: ClaimAuditState, config: RunnableConfig
) -> dict[str, Any]:
    """Resolve employee -> project -> account and compare against remaining budget."""
    session: AsyncSession = config["configurable"]["session"]
    employee = (
        await session.execute(
            select(Employee).where(Employee.employee_id == state["employee_id"])
        )
    ).scalar_one_or_none()

    violations: list[str] = []
    is_valid: bool = True
    requires_human_review: bool = False

    if employee is None:
        violations.append(f"Employee {state['employee_id']} not found")
        is_valid = False
    else:
        project = (
            await session.execute(
                select(Project).where(Project.project_code == employee.project_code)
            )
        ).scalar_one_or_none()

        if project is None:
            violations.append(
                f"Project {employee.project_code} not found for employee"
            )
            is_valid = False
        else:
            account = (
                await session.execute(
                    select(Account).where(Account.account_id == project.account_id)
                )
            ).scalar_one_or_none()

            if account is None:
                violations.append(
                    f"Account {project.account_id} not found for project"
                )
                is_valid = False
            else:
                requested = float(state.get("ocr_text", {}).get("total_amount", 0.0))
                available = float(account.remaining_budget)

                if requested > available:
                    violations.append(
                        f"Budget Exceeded. Available: {available:,.2f}, "
                        f"Requested: {requested:,.2f}"
                    )
                    is_valid = False
                    requires_human_review = True

    return {
        "is_valid": is_valid,
        "violations": violations,
        "requires_human_review": requires_human_review or state.get(
            "requires_human_review", False
        ),
        "audit_trail": ["validation_agent: budget bounds verified"],
    }


# ---------------------------------------------------------------------------
# Node 3: Policy agent
# ---------------------------------------------------------------------------
async def policy_agent(state: ClaimAuditState) -> dict[str, Any]:
    """Placeholder compliance checker against corporate policy guidelines."""
    is_compliant = True
    violations: list[str] = []
    return {
        "is_compliant": is_compliant,
        "violations": violations,
        "audit_trail": ["policy_agent: corporate policy scan complete"],
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------
def route_after_policy(state: ClaimAuditState) -> str:
    if not state.get("is_valid", True) or state.get("violations"):
        return "terminate_failed"
    return "terminate_under_review"


# ---------------------------------------------------------------------------
# Terminator nodes
# ---------------------------------------------------------------------------
async def terminate_failed(
    state: ClaimAuditState, config: RunnableConfig
) -> dict[str, Any]:
    """Flush error strings into the claim schema and mark the claim as Failed."""
    session: AsyncSession = config["configurable"]["session"]
    violations = state.get("violations", [])
    violation_text = "; ".join(violations) if violations else None

    claim = (
        await session.execute(
            select(Claim).where(Claim.claim_id == state["claim_id"])
        )
    ).scalar_one_or_none()

    if claim is not None:
        claim.status = ClaimStatus.FAILED
        claim.violations = violation_text or "Workflow terminated with violations"
        claim.requires_human_review = True

    return {
        "final_status": ClaimStatus.FAILED,
        "audit_trail": ["terminate_failed: claim marked as Failed"],
    }


async def terminate_under_review(
    state: ClaimAuditState, config: RunnableConfig
) -> dict[str, Any]:
    """Mark the claim as Under Review so it lands in the manager's queue."""
    session: AsyncSession = config["configurable"]["session"]
    claim = (
        await session.execute(
            select(Claim).where(Claim.claim_id == state["claim_id"])
        )
    ).scalar_one_or_none()

    if claim is not None:
        claim.status = ClaimStatus.UNDER_REVIEW
        claim.violations = None
        claim.requires_human_review = True
        claim.ocr_text = json.dumps(state.get("ocr_text", {}))

    return {
        "final_status": ClaimStatus.UNDER_REVIEW,
        "audit_trail": ["terminate_under_review: claim queued for approval"],
    }


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------
def build_claim_audit_graph():
    workflow = StateGraph(ClaimAuditState)

    workflow.add_node("ocr_agent", ocr_agent)
    workflow.add_node("validation_agent", validation_agent)
    workflow.add_node("policy_agent", policy_agent)
    workflow.add_node("terminate_failed", terminate_failed)
    workflow.add_node("terminate_under_review", terminate_under_review)

    workflow.add_edge(START, "ocr_agent")
    workflow.add_edge("ocr_agent", "validation_agent")
    workflow.add_edge("validation_agent", "policy_agent")
    workflow.add_conditional_edges(
        "policy_agent",
        route_after_policy,
        {
            "terminate_failed": "terminate_failed",
            "terminate_under_review": "terminate_under_review",
        },
    )
    workflow.add_edge("terminate_failed", END)
    workflow.add_edge("terminate_under_review", END)

    return workflow.compile()


compiled_graph = build_claim_audit_graph()