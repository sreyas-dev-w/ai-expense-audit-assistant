from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType
from app.models.enums import (
    ClaimPriority,
    ClaimStatus,
    Currency,
    ExpenseCategory,
)


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    business_purpose: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    merchant_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"),
        nullable=False,
        index=True,
    )
    category_data: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auditer_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auditer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    claim_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency"),
        nullable=False,
        default=Currency.INR,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status"),
        nullable=False,
        default=ClaimStatus.DRAFT,
        index=True,
    )
    priority: Mapped[ClaimPriority] = mapped_column(
        Enum(ClaimPriority, name="claim_priority"),
        nullable=False,
        default=ClaimPriority.MEDIUM,
    )
    receipt_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    claim_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    claim_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    receipt_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="claims", foreign_keys=[employee_id]
    )
    auditer: Mapped["Employee | None"] = relationship(
        back_populates="audited_claims", foreign_keys=[auditer_id]
    )
    agent_responses: Mapped[list["AgentResponse"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="AgentResponse.id",
    )