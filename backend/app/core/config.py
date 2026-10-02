import os
from typing import List
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # type: ignore

class Settings(BaseSettings):
    PROJECT_NAME: str = "FraudShield AI Backend"
    API_V1_STR: str = ""
    JWT_SECRET: str = "super-secret-key-change-in-production-12345"
    ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fraudshield.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    MODEL_FOR_SCORING: str = os.getenv("MODEL_FOR_SCORING", "xgboost")
    MODEL_FOR_EXPLANATION: str = os.getenv("MODEL_FOR_EXPLANATION", "xgboost")
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
