import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

settings = {
    "AZURE_STORAGE_CONNECTION_STRING": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    "AZURE_STORAGE_CONTAINER": os.getenv("AZURE_STORAGE_CONTAINER"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "GEMINI_EMBEDDING_MODEL": os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
    "GEMINI_GENERATION_MODEL": os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-flash"),
    "EMBEDDING_DIMENSIONS": int(os.getenv("EMBEDDING_DIMENSIONS", "3072")),
}