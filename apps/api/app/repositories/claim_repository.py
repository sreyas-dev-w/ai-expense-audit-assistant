"""Data access for claims used by the Audit Agent tools.

Persistence-only: the tool layer owns session lifecycle and transaction
boundaries so no session is ever held across an LLM/agent call
(``docs/backend/reliability.md``). Methods are deliberately narrow — they use
``session.get`` and direct field updates only.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest import result

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims import Claim
from app.models.employees import Employee
from app.models.enums import (
    AIDecision,
    AIRunStatus,
    ClaimPriority,
    ClaimStatus,
    Currency,
    ExpenseCategory,
)
from app.rules.constants import EMPLOYEE_CLAIM_SCAN_LIMIT


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, claim_id: int) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def get_employee(self, employee_id: str) -> Employee | None:
        return await self._session.get(Employee, employee_id)

    
    async def update_audit_fields(
        self,
        claim_id: int,
        *,
        status: ClaimStatus,
        priority: ClaimPriority,
        auditer_id: str,
        auditer_notes: str | None = None,
    ) -> Claim | None:
        """
        Update manager/auditor-controlled fields for a claim.

        Only the following claim fields are modified:
        - status
        - priority
        - auditer_id
        - auditer_notes

        claim_updated_at is also updated automatically.
        """
        claim = await self._session.get(Claim, claim_id)

        if claim is None:
            return None

        claim.status = status
        claim.priority = priority
        claim.auditer_id = auditer_id
        claim.auditer_notes = auditer_notes
        claim.claim_updated_at = _now()

        await self._session.flush()

        return claim


    async def get_claims_by_manager_id(
        self,
        manager_id: str,
    ) -> list[Claim]:

        result = await self._session.execute(
            select(Claim)
            .join(
                Employee,
                Claim.employee_id == Employee.employee_id,
            )
            .where(
                Employee.manager_id == manager_id
            )
        )

        return list(result.scalars().all())


    async def create(
        self,
        *,
        employee_id: str,
        category: ExpenseCategory,
        category_data: dict[str, Any],
        claim_amount: Decimal,
        currency: Currency = Currency.INR,
        business_purpose: str | None = None,
        merchant_name: str | None = None,
        project_code: str | None = None,
        receipt_url: str | None = None,
        status: ClaimStatus = ClaimStatus.SUBMITTED,
        priority: ClaimPriority = ClaimPriority.MEDIUM,
    ) -> Claim:
        """Insert a submitted claim and flush so ``claim_id`` is populated."""
        now = _now()
        claim = Claim(
            employee_id=employee_id,
            category=category,
            category_data=category_data,
            claim_amount=claim_amount,
            currency=currency,
            business_purpose=business_purpose,
            merchant_name=merchant_name,
            project_code=project_code,
            receipt_url=receipt_url,
            status=status,
            priority=priority,
            ai_run_status=AIRunStatus.PENDING,
            claim_created_at=now,
            claim_updated_at=now,
        )
        self._session.add(claim)
        await self._session.flush()
        return claim

    async def update_run_status(
        self,
        claim_id: int,
        *,
        claim_status: ClaimStatus,
        ai_run_status: AIRunStatus,
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.status = claim_status
        claim.ai_run_status = ai_run_status
        claim.claim_updated_at = _now()
        return claim

    async def update_category_data(
        self, claim_id: int, category_data: dict
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.category_data = category_data
        claim.claim_updated_at = _now()
        return claim

    async def update_result(
        self,
        claim_id: int,
        *,
        ai_decision: AIDecision,
        priority: ClaimPriority,
        ai_run_status: AIRunStatus = AIRunStatus.COMPLETED,
    ) -> Claim | None:
        claim = await self._session.get(Claim, claim_id)
        if claim is None:
            return None
        claim.ai_decision = ai_decision
        claim.priority = priority
        claim.ai_run_status = ai_run_status
        claim.claim_updated_at = _now()
        return claim

    async def get_claim(self, claim_id: int) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def list_employee_claims(
        self,
        employee_id: str,
        *,
        exclude_claim_id: int | None = None,
        limit: int = EMPLOYEE_CLAIM_SCAN_LIMIT,
    ) -> list[dict[str, Any]]:
        stmt = select(Claim).where(Claim.employee_id == employee_id)

        if exclude_claim_id is not None:
            stmt = stmt.where(Claim.claim_id != exclude_claim_id)

        stmt = stmt.order_by(Claim.claim_id.desc()).limit(limit)

        rows = list(
            (await self._session.execute(stmt)).scalars().all()
        )

        return [_claim_row(claim) for claim in rows]

    # ============================================================
    # GET ALL CLAIM DETAILS FOR AN EMPLOYEE
    # ============================================================

    async def get_claims_by_employee_id(
        self,
        employee_id: str,
    ) -> list[dict[str, Any]]:
        """
        Fetch all claims belonging to an employee.

        The employee_id in claims.employee_id is used to
        identify the employee who submitted the claim.
        """

        query = (
            select(Claim)
            .where(Claim.employee_id == employee_id)
            .order_by(Claim.claim_created_at.desc())
        )

        result = await self._session.execute(query)
        claims = result.scalars().all()

        return [
            {
                "claim_id": claim.claim_id,
                "business_purpose": claim.business_purpose,
                "merchant_name": claim.merchant_name,
                "category": claim.category.value,
                "category_data": claim.category_data,
                "employee_id": claim.employee_id,
                "auditer_id": claim.auditer_id,
                "auditer_notes": claim.auditer_notes,
                "project_code": claim.project_code,
                "claim_amount": claim.claim_amount,
                "tax_amount": claim.tax_amount,
                "currency": claim.currency.value,
                "status": claim.status.value,
                "priority": claim.priority.value,
                "ai_run_status": claim.ai_run_status.value,
                "ai_decision": (
                    claim.ai_decision.value
                    if claim.ai_decision is not None
                    else None
                ),
                "receipt_url": claim.receipt_url,
                "claim_created_at": claim.claim_created_at,
                "claim_updated_at": claim.claim_updated_at,
                "receipt_created_at": claim.receipt_created_at,
            }
            for claim in claims
        ]


def _claim_row(claim: Claim) -> dict[str, Any]:
    amount = claim.claim_amount

    if amount is not None and not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    return {
        "claim_id": claim.claim_id,
        "employee_id": claim.employee_id,
        "merchant_name": claim.merchant_name,
        "claim_amount": amount,
        "category_data": claim.category_data or {},
        "claim_created_at": claim.claim_created_at,
    }

