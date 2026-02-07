"""
Application Configuration
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file"""
    
    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "CertifyHub"
    APP_URL: str = "http://localhost:8000"
    SECRET_KEY: str = "temp-secret-key-change-later"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./certifyhub.db"  # Temporary SQLite for now
    
    # JWT
    JWT_SECRET_KEY: str = "temp-jwt-secret-change-later"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@certifyhub.com"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 5242880  # 5MB
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/jpg"
    
    # Storage (Supabase)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    STORAGE_BUCKET: str = "certifyhub"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()