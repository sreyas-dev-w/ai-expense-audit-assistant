from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSONType, Base


class AgentResponse(Base):
    __tablename__ = "agent_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validation_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )
    policy_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    claim: Mapped["Claim"] = relationship(back_populates="agent_responses")