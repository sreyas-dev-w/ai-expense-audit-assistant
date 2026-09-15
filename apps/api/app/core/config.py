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

    embedding_dimension: int = 768

    gemini_api_key: str = ""

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()