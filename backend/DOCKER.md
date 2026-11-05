# Backend Docker deployment

The backend image includes Python, FastAPI, the Celery worker, and Tesseract
with Gujarati and English language data. PostgreSQL, Redis, Azure Blob Storage,
and Gemini remain external services and are configured with environment
variables.

## Build

From the `backend` directory:

```bash
docker build -t gujdoc-backend .
```

## Run on an Ubuntu VM

Copy a production `.env` file to the VM (do not commit it), then run:

```bash
docker run -d \
  --name gujdoc-backend \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  gujdoc-backend
```

The API is available at `http://<vm-address>:8000`. The container starts both
the API and one Celery worker process. Set `CELERY_WORKER_CONCURRENCY` in the
environment to adjust worker concurrency.

The container sets these Linux OCR defaults:

```text
TESSERACT_CMD=/usr/bin/tesseract
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
OCR_LANGUAGES=guj+eng
```

`REDIS_URL`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, cloud credentials,
and `GEMINI_API_KEY` must be supplied in the `.env` file. Use a Redis URL
reachable from the VM, including `rediss://` when TLS is required.

## Verify

```bash
docker logs -f gujdoc-backend
curl http://127.0.0.1:8000/health
docker exec gujdoc-backend tesseract --list-langs
```

The language list should include `eng` and `guj`.
