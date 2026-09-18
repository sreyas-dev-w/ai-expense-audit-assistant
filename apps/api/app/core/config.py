from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI Expense Audit Assistant API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://expense_audit:expense_audit@localhost:5432/expense_audit"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # RAG / embedding
    embedding_model: str = "gemini-embedding-2"
    # Must match the pgvector column width in policy_chunking (1536) for
    # gemini-embedding-2 unless truncated elsewhere on purpose.
    embedding_dimension: int = 1536
    embedding_batch_size: int = 64
    embedding_timeout_seconds: int = 60

    # Policy document storage (relative to apps/api/)
    policy_storage_dir: Path = Path("storage_dump/policies")
    policy_chunk_size: int = 800
    policy_chunk_overlap: int = 80
    policy_search_default_top_k: int = 5
    policy_search_max_top_k: int = 20
    policy_search_similarity_threshold: float = 0.0

    # Claim receipt storage (relative to apps/api/)
    receipt_storage_dir: Path = Path("storage_dump/receipts")

    # LLM
    gemini_api_key: str = ""
    gemini_llm_model: str = "gemini-3.5-flash-lite"
    gemini_llm_timeout_seconds: int = 60
    gemini_max_retries: int = 2

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()