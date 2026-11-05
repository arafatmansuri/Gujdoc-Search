import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables from .env file
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.admin import router as admin_router
from app.core.config import settings

app = FastAPI(
    title="Gujdoc API",
    description=("Gujarati Government Document Digitisation and Semantic Search"),
    version="1.0.0",
)

logger = logging.getLogger("gujdoc")

if not settings["CORS_ORIGINS"]:
    raise RuntimeError("CORS_ORIGINS must contain at least one trusted origin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["CORS_ORIGINS"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error", extra={"request_id": request_id})
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    documents_router,
    prefix="/api/v1",
)
app.include_router(
    admin_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "gujdoc-api",
    }
