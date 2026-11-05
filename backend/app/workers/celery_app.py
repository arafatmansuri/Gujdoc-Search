import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise ValueError("REDIS_URL is missing")

broker_url = os.getenv("CELERY_BROKER_URL") or REDIS_URL
result_backend = os.getenv("CELERY_RESULT_BACKEND") or REDIS_URL

# Docker env files do not expand shell-style references such as
# CELERY_BROKER_URL=${REDIS_URL}.
if broker_url == "${REDIS_URL}":
    broker_url = REDIS_URL
if result_backend == "${REDIS_URL}":
    result_backend = REDIS_URL

celery_app = Celery(
    "gujdoc",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
)
