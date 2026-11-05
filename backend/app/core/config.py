import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

settings = {
    "APP_ENV": os.getenv("APP_ENV", "development"),
    "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
    "SECRET_KEY": os.getenv("SECRET_KEY"),
    "JWT_ISSUER": os.getenv("JWT_ISSUER"),
    "JWT_AUDIENCE": os.getenv("JWT_AUDIENCE"),
    "ACCESS_TOKEN_EXPIRE_MINUTES": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
    "REFRESH_TOKEN_EXPIRE_DAYS": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")),
    "CORS_ORIGINS": [
        x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()
    ],
    "AZURE_STORAGE_CONNECTION_STRING": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    "AZURE_STORAGE_CONTAINER": os.getenv("AZURE_STORAGE_CONTAINER"),
    "DATABASE_URL": os.getenv("DATABASE_URL"),
    "REDIS_URL": os.getenv("REDIS_URL"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "GEMINI_EMBEDDING_MODEL": os.getenv(
        "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
    ),
    "GEMINI_GENERATION_MODEL": os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-flash"),
    "EMBEDDING_DIMENSIONS": int(os.getenv("EMBEDDING_DIMENSIONS", "3072")),
    "MAX_UPLOAD_SIZE_BYTES": int(
        os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024))
    ),
    "RATE_LIMIT_LOGIN": int(os.getenv("RATE_LIMIT_LOGIN", "10")),
    "RATE_LIMIT_EXPENSIVE": int(os.getenv("RATE_LIMIT_EXPENSIVE", "30")),
    "RATE_LIMIT_WINDOW_SECONDS": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
}
