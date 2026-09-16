from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    project_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_lead_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    account: Mapped["Account"] = relationship(back_populates="projects")
    project_lead: Mapped["Employee | None"] = relationship(
        foreign_keys=[project_lead_id], back_populates="led_projects"
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="project",
        foreign_keys="Employee.project_code",
    )