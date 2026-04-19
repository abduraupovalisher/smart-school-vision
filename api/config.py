import os


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins if origins else ["*"]


class Settings:
    """Application settings loaded from environment variables."""

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./school.db")
    snapshot_dir: str = os.getenv("SNAPSHOT_DIR", "data/snapshots")
    dedup_ttl_seconds: int = int(os.getenv("DEDUP_TTL_SECONDS", "30"))
    cors_origins: list[str] = _parse_cors_origins()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    diagnostics_enabled: bool = os.getenv("DIAGNOSTICS_ENABLED", "0").lower() in ("1", "true", "yes")
    diagnostics_buffer_size: int = int(os.getenv("DIAGNOSTICS_BUFFER_SIZE", "100"))


settings = Settings()
