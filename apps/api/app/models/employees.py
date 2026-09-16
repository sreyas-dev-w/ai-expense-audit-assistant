from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobLevel


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_level: Mapped[JobLevel] = mapped_column(
        Enum(JobLevel, name="job_level"),
        nullable=False,
    )
    is_manager: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    manager_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_code: Mapped[str | None] = mapped_column(
        ForeignKey("projects.project_code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True,
    )
    password: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )

    manager: Mapped["Employee | None"] = relationship(
        remote_side=[employee_id], back_populates="reports"
    )
    reports: Mapped[list["Employee"]] = relationship(back_populates="manager")
    project: Mapped["Project | None"] = relationship(
        back_populates="employees",
        foreign_keys=[project_code],
    )
    led_projects: Mapped[list["Project"]] = relationship(
        back_populates="project_lead",
        foreign_keys="Project.project_lead_id",
    )
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="employee", foreign_keys="Claim.employee_id"
    )
    audited_claims: Mapped[list["Claim"]] = relationship(
        back_populates="auditer", foreign_keys="Claim.auditer_id"
    )