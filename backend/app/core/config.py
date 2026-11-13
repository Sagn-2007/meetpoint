"""Application configuration using Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MeetPoint configuration settings."""

    PROJECT_NAME: str = "MeetPoint Geospatial Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # "development", "test", "production"

    # CORS configuration
    CORS_ORIGINS: str = ""  # Comma-separated list of origins, e.g., "https://meetpoint.example.com,https://app.meetpoint.example.com"

    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = True
    TRUSTED_PROXIES: str = "127.0.0.1,::1"  # Comma-separated trusted upstream proxy IPs/CIDRs
    RATE_LIMIT_SESSION_CREATE: int = 15      # Max requests per minute per IP
    RATE_LIMIT_SESSION_GET: int = 60         # Max requests per minute per IP
    RATE_LIMIT_INVITATION_LOOKUP: int = 60   # Alias for session lookup
    RATE_LIMIT_SESSION_JOIN: int = 30        # Max requests per minute per IP
    RATE_LIMIT_JOIN: int = 30                # Alias for session join
    RATE_LIMIT_OPTIMIZE: int = 10            # Max requests per minute per IP
    RATE_LIMIT_SUBMIT_LOCATION: int = 60     # Max requests per minute per IP
    RATE_LIMIT_LOCATION: int = 60            # Alias for submit location

    # Cache settings
    CACHE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "cache" / "osm_graphs"
    ENABLE_DISK_CACHE: bool = True
    MAX_IN_MEMORY_GRAPHS: int = 8  # Bounded LRU memory cache for parsed NetworkX graphs

    # Geospatial and network parameters
    DEFAULT_NETWORK_TYPE: str = "walk"
    DEFAULT_BBOX_PADDING_RATIO: float = 0.20
    MIN_BBOX_PADDING_DEG: float = 0.015   # ~1.65 km minimum padding
    MAX_SNAP_DISTANCE_M: float = 10000.0   # 10 km max distance from node
    MAX_BBOX_DIAMETER_KM: float = 80.0    # 80 km max bounding box diagonal limit
    MAX_PARTICIPANT_PAIRWISE_DISTANCE_KM: float = 75.0  # Max spread between any two participants

    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://meetpoint:meetpoint@localhost:5432/meetpoint"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://meetpoint:meetpoint@localhost:5432/meetpoint"
    DATABASE_SSL: str = ""  # e.g., "require" for Neon or managed clouds

    # Collaborative Session parameters
    SESSION_EXPIRATION_HOURS: int = 24
    SESSION_CLEANUP_INTERVAL_MINUTES: int = 15
    SESSION_RETENTION_HOURS: int = 48  # Hard purge age after creation/expiration
    INVITATION_CODE_LENGTH: int = 8
    WS_AUTH_TIMEOUT_SECONDS: float = 5.0  # Max seconds to wait for first-message auth handshake

    # Optimization parameters
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    # OSMnx Overpass query timeout in seconds
    OVERPASS_TIMEOUT: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="MEETPOINT_",
        case_sensitive=False,
    )

    def get_cors_origins(self) -> List[str]:
        """
        Parse and return validated CORS origins.
        In development/test mode without explicit CORS_ORIGINS, returns localhost defaults.
        In production, requires explicit domains and strictly rejects wildcards with credentials.
        """
        raw_origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

        if self.ENVIRONMENT == "production":
            if not raw_origins:
                raise ValueError(
                    "MEETPOINT_CORS_ORIGINS must be explicitly configured in production. "
                    "Cannot start with empty or undefined CORS origins."
                )
            if "*" in raw_origins:
                raise ValueError(
                    "Wildcard '*' in MEETPOINT_CORS_ORIGINS is forbidden in production "
                    "because credentialed access is enabled."
                )
            return raw_origins

        # Development / test mode fallback
        if raw_origins:
            return raw_origins

        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def validate_production_safety(self) -> None:
        """Enforce production security constraints on database credentials and secrets."""
        if self.ENVIRONMENT == "production":
            self.get_cors_origins()
            default_signatures = [
                "meetpoint:meetpoint@localhost",
                "meetpoint:meetpoint@127.0.0.1",
            ]
            for sig in default_signatures:
                if sig in self.DATABASE_URL or sig in self.SYNC_DATABASE_URL:
                    raise ValueError(
                        f"Refusing to start in production environment: DATABASE_URL contains default "
                        f"development credentials ('{sig}'). Configure secure production database credentials."
                    )


settings = Settings()
# Ensure cache directory exists
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
