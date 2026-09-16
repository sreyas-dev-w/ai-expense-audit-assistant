from decimal import Decimal

from sqlalchemy import Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Currency


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    budget_allocated: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    remaining_budget: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency"),
        nullable=False,
        default=Currency.INR,
    )

    projects: Mapped[list["Project"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )