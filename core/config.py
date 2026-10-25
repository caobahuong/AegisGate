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

    # If a plugin dry-run crashes: True = reject the query (fail-closed, recommended).
    # False = continue but never auto-execute; the query is forced into manual review.
    FAIL_CLOSED_ON_DRY_RUN_ERROR: bool = True

    # Plugin installer limits (ZIP / Git). Git hosts must be HTTPS and in this allow-list.
    PLUGIN_GIT_ALLOWED_HOSTS: list[str] = ["github.com", "gitlab.com", "bitbucket.org"]
    PLUGIN_MAX_ZIP_BYTES: int = 50 * 1024 * 1024
    PLUGIN_MAX_UNZIPPED_BYTES: int = 200 * 1024 * 1024
    PLUGIN_MAX_ZIP_ENTRIES: int = 5000
    PLUGIN_GIT_CLONE_TIMEOUT_SECONDS: float = 60.0

    # Max size of a single JSON-RPC message from a persistent plugin worker (result sets).
    PLUGIN_MAX_MESSAGE_BYTES: int = 64 * 1024 * 1024

    # Auto Approval Mode Default
    AUTO_APPROVAL_DEFAULT: bool = False

    # SSE Heartbeat
    SSE_HEARTBEAT_INTERVAL_SECONDS: float = 2.0


settings = Settings()
