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

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_TTL: int = 3600  # 1 hour

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@finserve-nbfc.com"
    EMAIL_FROM_NAME: str = "FinServe NBFC"

    # Development Settings
    DISABLE_OTP: bool = False  # Toggle for development/testing
    DEV_OTP: str = "123456"  # Default OTP for development

    # Underwriting thresholds
    MIN_CREDIT_SCORE: int = 700
    MAX_DTI_RATIO: float = 0.50
    MAX_EXPOSURE_MULTIPLIER: float = 2.0

    # Persuasion loop
    MAX_NEGOTIATION_ROUNDS: int = 3

    # Profile completeness
    REQUIRED_PROFILE_FIELDS: list = [
        "name", "phone", "email", "city", "salary", 
        "credit_score", "existing_emi_total"
    ]

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
