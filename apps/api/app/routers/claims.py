from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import current_user
from app.schemas.api import (
    ClaimCreate,
    ClaimCreateResponse,
    ClaimDetailResponse,
    documented_errors,
)
from app.services.api_store import USERS, claims, documents, identifier, claim_numbers, policies, now

router = APIRouter(prefix="/claims", tags=["Claims"])


def _policy_for_version(version: str) -> dict | None:
    return next(
        (policy for policy in policies.values() if policy["policy_version"] == version),
        None,
    )


def _user_record(user_id: str) -> dict | None:
    return next((record for record in USERS.values() if record["user_id"] == user_id), None)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClaimCreateResponse,
    responses=documented_errors(401, 403, 404, 422),
)
def create_claim(payload: ClaimCreate, user: dict = Depends(current_user)):
    policy = _policy_for_version(payload.policy_version)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy version does not exist")
    employee = _user_record(user["sub"])
    if not employee:
        raise HTTPException(status_code=403, detail="Token user does not exist")
    if not policy.get("active") or policy.get("indexing_status") != "READY":
        raise HTTPException(status_code=422, detail="Policy is not active and ready")
    if policy["country"].casefold() != employee["country"].casefold():
        raise HTTPException(
            status_code=422,
            detail="Policy is not applicable to the employee country",
        )
    policy_start = date.fromisoformat(policy["effective_from"])
    if any(line.expense_date < policy_start for line in payload.expense_lines):
        raise HTTPException(
            status_code=422,
            detail="Policy was not active on one or more expense dates",
        )
    document_ids = [line.receipt_document_id for line in payload.expense_lines]
    if payload.reimbursement_form_document_id:
        document_ids.append(payload.reimbursement_form_document_id)
    for document_id in document_ids:
        document = documents.get(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} does not exist")
        if user["role"] == "EMPLOYEE" and document["owner_id"] != user["sub"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Document {document_id} belongs to another user")
    currencies = {line.currency.upper() for line in payload.expense_lines}
    if len(currencies) != 1:
        raise HTTPException(status_code=422, detail="All expense lines must use one currency")
    claim_id = identifier("CLM", claim_numbers)
    total = sum((line.claimed_amount for line in payload.expense_lines), Decimal("0"))
    lines = []
    for index, line in enumerate(payload.expense_lines, start=1):
        values = line.model_dump(mode="json")
        values["line_id"] = f"LINE-{claim_id.split('-')[1]}-{index:03d}"
        values["claimed_amount"] = f"{line.claimed_amount:.2f}"
        values["currency"] = line.currency.upper()
        lines.append(values)
    claims[claim_id] = {"claim_id": claim_id, "owner_id": user["sub"], "employee_id": user.get("employee_id"), "purpose": payload.purpose, "project_code": payload.project_code, "policy_version": payload.policy_version, "status": "DRAFT", "total_claimed_amount": f"{total:.2f}", "currency": currencies.pop(), "expense_lines": lines, "reimbursement_form_document_id": payload.reimbursement_form_document_id, "created_at": now()}
    claim = claims[claim_id]
    return {key: claim[key] for key in ("claim_id", "status", "employee_id", "total_claimed_amount", "currency", "created_at")}


@router.get(
    "/{claim_id}",
    response_model=ClaimDetailResponse,
    responses=documented_errors(401, 403, 404),
)
def get_claim(claim_id: str, user: dict = Depends(current_user)):
    claim = claims.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if user["role"] == "EMPLOYEE" and claim["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="You can only view your own claims")
    employee = next((item for item in USERS.values() if item["employee_id"] == claim["employee_id"]), None)
    document_ids = [line["receipt_document_id"] for line in claim["expense_lines"]]
    if claim["reimbursement_form_document_id"]:
        document_ids.append(claim["reimbursement_form_document_id"])
    linked_documents = [{key: documents[item][key] for key in ("document_id", "document_type", "original_filename")} for item in document_ids]
    return {**{key: claim[key] for key in ("claim_id", "purpose", "project_code", "policy_version", "status", "total_claimed_amount", "currency", "expense_lines")}, "employee": {"employee_id": claim["employee_id"], "name": employee["name"] if employee else "Unknown", "department": employee["department"] if employee else "Unknown"}, "documents": linked_documents}
