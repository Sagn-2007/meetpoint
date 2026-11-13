"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MeetPoint configuration settings."""

    PROJECT_NAME: str = "MeetPoint Geospatial Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Cache settings
    CACHE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "cache" / "osm_graphs"
    ENABLE_DISK_CACHE: bool = True
    
    # Geospatial and network parameters
    DEFAULT_NETWORK_TYPE: str = "walk"
    DEFAULT_BBOX_PADDING_RATIO: float = 0.20
    MIN_BBOX_PADDING_DEG: float = 0.015  # ~1.65 km minimum padding
    MAX_SNAP_DISTANCE_M: float = 10000.0  # 10 km max distance from node
    
    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://meetpoint:meetpoint@localhost:5432/meetpoint"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://meetpoint:meetpoint@localhost:5432/meetpoint"

    # Collaborative Session parameters
    SESSION_EXPIRATION_HOURS: int = 24
    INVITATION_CODE_LENGTH: int = 8

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


settings = Settings()
# Ensure cache directory exists
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
