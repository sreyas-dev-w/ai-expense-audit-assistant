from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClaimStatus:
    DRAFT = "Draft"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    FAILED = "Failed"


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    account_name: Mapped[str] = mapped_column(String)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    budget_allocated: Mapped[float] = mapped_column(Float)
    spent_amount: Mapped[float] = mapped_column(Float)
    remaining_budget: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    account_hr_id: Mapped[str] = mapped_column(String)

    projects: Mapped[list["Project"]] = relationship(back_populates="account")


class Project(Base):
    __tablename__ = "projects"

    project_code: Mapped[str] = mapped_column(String, primary_key=True)
    project_name: Mapped[str] = mapped_column(String)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"))
    project_lead_id: Mapped[str] = mapped_column(String)

    account: Mapped["Account"] = relationship(back_populates="projects")
    employees: Mapped[list["Employee"]] = relationship(back_populates="project")


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_name: Mapped[str] = mapped_column(String)
    job_level: Mapped[str] = mapped_column(String)
    manager_id: Mapped[str | None] = mapped_column(String, nullable=True)
    project_code: Mapped[str] = mapped_column(ForeignKey("projects.project_code"))

    project: Mapped["Project"] = relationship(back_populates="employees")
    claims: Mapped[list["Claim"]] = relationship(back_populates="employee")


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    claim_name: Mapped[str] = mapped_column(String)
    estimated_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default=ClaimStatus.DRAFT)
    violations: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    document_path: Mapped[str | None] = mapped_column(String, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    employee: Mapped["Employee"] = relationship(back_populates="claims")