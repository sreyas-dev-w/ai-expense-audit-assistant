from collections import Counter
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.core.security import require_roles
from app.schemas.api import DashboardSummaryResponse, documented_errors
from app.services.api_store import USERS, audits, claims

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    responses=documented_errors(401, 403, 422),
)
def dashboard_summary(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    department: str | None = Query(None),
    _: dict = Depends(require_roles("AUDITOR", "ADMIN")),
):
    selected = list(claims.values())
    if from_date or to_date:
        selected = [claim for claim in selected if (not from_date or date.fromisoformat(claim["created_at"][:10]) >= from_date) and (not to_date or date.fromisoformat(claim["created_at"][:10]) <= to_date)]
    if department:
        employee_ids = {item["employee_id"] for item in USERS.values() if item["department"].lower() == department.lower()}
        selected = [claim for claim in selected if claim["employee_id"] in employee_ids]
    statuses = Counter(claim["status"] for claim in selected)
    selected_ids = {claim["claim_id"] for claim in selected}
    selected_audits = [audit for audit in audits.values() if audit["claim_id"] in selected_ids]
    categories = Counter(line["expense_category"] for claim in selected for line in claim["expense_lines"])
    total = sum((Decimal(claim["total_claimed_amount"]) for claim in selected), Decimal("0"))
    findings = [finding for audit in selected_audits for finding in audit.get("findings", [])]
    risk = Counter("LOW" if audit.get("risk_score", 0) < 30 else "MEDIUM" if audit.get("risk_score", 0) < 70 else "HIGH" for audit in selected_audits if audit.get("audit_status") == "COMPLETED")
    return {
        "filters": {"from_date": str(from_date) if from_date else None, "to_date": str(to_date) if to_date else None, "department": department},
        "summary": {"total_claims": len(selected), "draft_claims": statuses["DRAFT"], "processing_claims": statuses["PROCESSING"], "approved_claims": statuses["APPROVED"], "rejected_claims": statuses["REJECTED"], "needs_clarification_claims": statuses["NEEDS_CLARIFICATION"], "duplicate_cases": sum(finding.get("finding_type") == "POSSIBLE_DUPLICATE" for finding in findings), "policy_violations": sum(finding.get("finding_type") == "POLICY_VIOLATION" for finding in findings), "total_claimed_amount": f"{total:.2f}", "flagged_amount": "0.00", "currency": "INR"},
        "violations_by_category": [{"expense_category": category, "count": amount} for category, amount in categories.items()],
        "risk_distribution": [{"risk_level": level, "count": amount} for level, amount in risk.items()],
    }
