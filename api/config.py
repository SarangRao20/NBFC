"""FastAPI configuration — settings and dependency injection."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    APP_NAME: str = "NBFC Loan Processing API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = True

    # File storage
    UPLOAD_DIR: str = "data/uploads"
    SANCTION_DIR: str = "data/sanctions"

    # MongoDB Configuration
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/nbfc")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@finserve-nbfc.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "FinServe NBFC")
    
    # AI API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Development Settings
    DISABLE_OTP: bool = os.getenv("DISABLE_OTP", "false").lower() == "true"
    DEV_OTP: str = os.getenv("DEV_OTP", "123456")  # Default OTP for development
    
    # Feature Flags
    USE_DTI_SCORE: bool = os.getenv("USE_DTI_SCORE", "false").lower() == "true"

    # Underwriting thresholds
    MIN_CREDIT_SCORE: int = int(os.getenv("MIN_CREDIT_SCORE", "700"))
    MAX_DTI_RATIO: float = float(os.getenv("MAX_DTI_RATIO", "0.50"))  # 50% maximum DTI
    MAX_EXPOSURE_MULTIPLIER: float = float(os.getenv("MAX_EXPOSURE_MULTIPLIER", "2.0"))  # Allow up to 2× pre-approved by default
    
    # Persuasion loop
    MAX_NEGOTIATION_ROUNDS: int = int(os.getenv("MAX_NEGOTIATION_ROUNDS", "3"))
    
    # Profile completeness
    REQUIRED_PROFILE_FIELDS: list = [
        "name", "phone", "email", "city", "salary", "credit_score", "existing_emi_total"
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
