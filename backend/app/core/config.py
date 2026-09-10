from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Document Intelligence"

    database_url: str = "sqlite:///./document_intelligence.db"

    # ============================================================
    # LLM CONFIGURATION
    # ============================================================

    llm_provider: str = "kimi"

    # We keep a generic internal name so the rest of the application
    # does not care which LLM provider is being used.
    llm_api_key: str = ""

    llm_model: str = "kimi-k3"

    llm_base_url: str = "https://api.moonshot.ai/v1"

    # ============================================================
    # OCR
    # ============================================================

    ocr_provider: str = "tesseract"

    # ============================================================
    # DOCUMENT VALIDATION
    # ============================================================

    max_file_size_mb: int = 10
    max_pages: int = 3

    # ============================================================
    # API
    # ============================================================

    api_prefix: str = "/api/v1"

    cors_origins: str = "*"

    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()