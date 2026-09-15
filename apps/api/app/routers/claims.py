import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Claim, ClaimStatus, Employee
from app.schemas import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ClaimResponse,
    ClaimSubmitRequest,
    SubmitResponse,
    TeamClaimResponse,
)
from app.workflow.graph import compiled_graph
from app.workflow.state import ClaimAuditState

router = APIRouter(prefix="/claims", tags=["claims"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
ALLOWED_SUFFIX = {".png", ".jpg", ".jpeg", ".pdf", ".webp", "application/pdf"}

db_session = Annotated[AsyncSession, Depends(get_db)]


def _validate_upload(file: UploadFile) -> None:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
            "Accepted: PNG, JPEG, WebP, PDF.",
        )


async def _save_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".pdf", ".webp"}:
        suffix = ".bin"
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    destination.write_bytes(content)
    return str(destination)


@router.post("/submit", response_model=SubmitResponse)
async def submit_claim(
    session: db_session,
    employee_id: Annotated[str, Form()],
    claim_name: Annotated[str, Form()],
    estimated_amount: Annotated[float, Form()],
    document: Annotated[UploadFile, File()],
) -> SubmitResponse:
    """Submit a claim with a receipt asset and run the LangGraph audit workflow."""
    _validate_upload(document)

    employee = (
        await session.execute(
            select(Employee).where(Employee.employee_id == employee_id)
        )
    ).scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    document_path = await _save_upload(document)

    claim = Claim(
        employee_id=employee_id,
        claim_name=claim_name,
        estimated_amount=estimated_amount,
        status=ClaimStatus.DRAFT,
        document_path=document_path,
        requires_human_review=False,
    )
    session.add(claim)
    await session.commit()
    await session.refresh(claim)

    initial_state: ClaimAuditState = {
        "claim_id": claim.claim_id,
        "employee_id": employee_id,
        "claim_name": claim_name,
        "claim_amount": estimated_amount,
        "document_path": document_path,
        "ocr_text": {},
        "is_valid": True,
        "is_compliant": True,
        "violations": [],
        "requires_human_review": False,
        "final_status": None,
        "audit_trail": [],
    }

    result = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"session": session}},
    )

    await session.commit()
    await session.refresh(claim)

    violations = result.get("violations", []) or []
    final_status = result.get("final_status") or claim.status

    return SubmitResponse(
        claim_id=claim.claim_id,
        status=final_status,
        violations=violations,
        requires_human_review=claim.requires_human_review,
        ocr_text=result.get("ocr_text", {}),
        message=(
            "Claim submitted and queued for manager approval."
            if final_status == ClaimStatus.UNDER_REVIEW
            else "Claim failed automated validation."
        ),
    )


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    session: db_session,
    employee_id: str,
    status: str | None = None,
) -> list[ClaimResponse]:
    import json

    query = select(Claim).where(Claim.employee_id == employee_id)
    if status:
        query = query.where(Claim.status == status)
    query = query.order_by(Claim.created_at.desc())
    claims = (await session.execute(query)).scalars().all()
    return [
        ClaimResponse(
            claim_id=c.claim_id,
            employee_id=c.employee_id,
            claim_name=c.claim_name,
            estimated_amount=c.estimated_amount,
            status=c.status,
            violations=c.violations,
            requires_human_review=c.requires_human_review,
            document_path=c.document_path,
            ocr_text=json.loads(c.ocr_text) if c.ocr_text else None,
            created_at=c.created_at,
        )
        for c in claims
    ]


@router.get("/team", response_model=list[TeamClaimResponse])
async def list_team_approvals(
    session: db_session,
    manager_id: str,
) -> list[TeamClaimResponse]:
    """Approval inbox: 'Under Review' claims submitted by the manager's direct reports."""
    reportee_ids = (
        await session.execute(
            select(Employee.employee_id).where(Employee.manager_id == manager_id)
        )
    ).scalars().all()

    if not reportee_ids:
        return []

    rows = (
        await session.execute(
            select(Claim, Employee)
            .join(Employee, Employee.employee_id == Claim.employee_id)
            .where(
                Claim.employee_id.in_(reportee_ids),
                Claim.status == ClaimStatus.UNDER_REVIEW,
            )
            .order_by(Claim.created_at.asc())
        )
    ).all()

    import json

    return [
        TeamClaimResponse(
            claim_id=claim.claim_id,
            claim_name=claim.claim_name,
            estimated_amount=claim.estimated_amount,
            status=claim.status,
            violations=claim.violations,
            requires_human_review=claim.requires_human_review,
            document_path=claim.document_path,
            ocr_text=json.loads(claim.ocr_text) if claim.ocr_text else None,
            created_at=claim.created_at,
            employee_id=employee.employee_id,
            employee_name=employee.employee_name,
            job_level=employee.job_level,
        )
        for claim, employee in rows
    ]


@router.patch("/{claim_id}/approve", response_model=ApprovalActionResponse)
async def approve_claim(
    claim_id: int,
    request: ApprovalActionRequest,
    session: db_session,
) -> ApprovalActionResponse:
    claim = (
        await session.execute(select(Claim).where(Claim.claim_id == claim_id))
    ).scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    manager = (
        await session.execute(
            select(Employee).where(Employee.employee_id == request.manager_id)
        )
    ).scalar_one_or_none()
    if manager is None:
        raise HTTPException(status_code=404, detail="Manager not found")

    claim.status = ClaimStatus.APPROVED
    claim.requires_human_review = False
    await session.commit()

    return ApprovalActionResponse(
        claim_id=claim_id,
        status=ClaimStatus.APPROVED,
        message=f"Claim {claim_id} approved.",
    )


@router.patch("/{claim_id}/reject", response_model=ApprovalActionResponse)
async def reject_claim(
    claim_id: int,
    request: ApprovalActionRequest,
    session: db_session,
) -> ApprovalActionResponse:
    claim = (
        await session.execute(select(Claim).where(Claim.claim_id == claim_id))
    ).scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    note = request.note or "Rejected by manager"
    existing = f"{claim.violations}; " if claim.violations else ""
    claim.status = ClaimStatus.FAILED
    claim.violations = f"{existing}Rejected by manager: {note}"
    claim.requires_human_review = False
    await session.commit()

    return ApprovalActionResponse(
        claim_id=claim_id,
        status=ClaimStatus.FAILED,
        message=f"Claim {claim_id} rejected.",
    )