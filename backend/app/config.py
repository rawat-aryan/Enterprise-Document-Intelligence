from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Enterprise Document Intelligence"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-secrets-manager"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google Cloud
    GOOGLE_PROJECT_ID: str = "my-gcp-project"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_EMBEDDING_MODEL: str = "models/embedding-001"

    # GCS
    GCS_BUCKET_NAME: str = "enterprise-documents"
    GCS_PROCESSED_PREFIX: str = "processed/"
    GCS_RAW_PREFIX: str = "raw/"

    # Pub/Sub
    PUBSUB_TOPIC: str = "document-processing"
    PUBSUB_SUBSCRIPTION: str = "document-processing-sub"

    # BigQuery
    BIGQUERY_DATASET: str = "document_intelligence"
    BIGQUERY_LOCATION: str = "US"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8501", "http://localhost:3000"]

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    PDF_DPI: int = 300

    # Secret Manager
    SECRET_MANAGER_PREFIX: str = "enterprise-doc-intel"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
