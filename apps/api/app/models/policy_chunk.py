from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSONType, Base

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 1536


class PolicyChunk(Base):
    __tablename__ = "policy_chunking"
    __table_args__ = (
        Index(
            "ix_policy_chunking_embeddings",
            "embeddings",
            postgresql_using="hnsw",
            postgresql_ops={"embeddings": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONType, nullable=True
    )
    embeddings: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )