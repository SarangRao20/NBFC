"""FastAPI configuration — settings and dependency injection."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    APP_NAME: str = "NBFC Loan Processing API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # File storage
    UPLOAD_DIR: str = "data/uploads"
    SANCTION_DIR: str = "data/sanctions"

    # Underwriting thresholds
    MIN_CREDIT_SCORE: int = 700
    MAX_DTI_RATIO: float = 0.50
    MAX_EXPOSURE_MULTIPLIER: float = 2.0

    # Persuasion loop
    MAX_NEGOTIATION_ROUNDS: int = 3

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Ensure directories exist
settings = get_settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.SANCTION_DIR, exist_ok=True)
