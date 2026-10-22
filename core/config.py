"""Configuration module for AegisGate Core using pydantic-settings.

Enforces zero-hardcoding policy as specified in python_clean_code.md.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration parameters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General System
    APP_NAME: str = "AegisGate Core"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server Network
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    MCP_PORT: int = 8001

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'aegisgate.db'}"
    KNOWLEDGE_DOCS_DIR: Path = BASE_DIR / "data" / "knowledge_docs"
    PLUGINS_DIR: Path = BASE_DIR / "plugins"

    # Execution Timeout Guards (Strict limits per plan.md & tech.md)
    READ_TIMEOUT_SECONDS: float = 15.0
    WRITE_TIMEOUT_SECONDS: float = 30.0
    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    # Auto Approval Mode Default
    AUTO_APPROVAL_DEFAULT: bool = False

    # SSE Heartbeat
    SSE_HEARTBEAT_INTERVAL_SECONDS: float = 2.0


settings = Settings()

