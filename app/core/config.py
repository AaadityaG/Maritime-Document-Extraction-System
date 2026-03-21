import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # LLM Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_API_KEY: str = ""
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = True
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"image/jpeg", "image/png", "application/pdf"}
    UPLOAD_DIR: str = "./uploads"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Job Processing
    JOB_TIMEOUT: int = 30  # seconds
    ASYNC_THRESHOLD: int = 5 * 1024 * 1024  # 5MB
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./smde.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
