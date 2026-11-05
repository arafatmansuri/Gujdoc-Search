from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path
# Load environment variables from .env file
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

from app.api.routes.documents import router as documents_router


app = FastAPI(
    title="Gujdoc API",
    description=(
        "Gujarati Government Document Digitisation "
        "and Semantic Search"
    ),
    version="1.0.0",
)

app.include_router(
    documents_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "gujdoc-api",
    }
