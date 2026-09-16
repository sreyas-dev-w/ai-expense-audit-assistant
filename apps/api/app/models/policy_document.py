from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PolicyDocument(Base):
    """Registry of policy PDFs ingested into the vector store.

    ``policy_chunking.policy_id`` references ``policy_documents.policy_id``.
    """

    __tablename__ = "policy_documents"

    policy_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    doc_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    policy_version: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed"
    )
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["PolicyChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )