#!/usr/bin/env bash
set -Eeuo pipefail

worker_concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
worker_log_level="${CELERY_LOG_LEVEL:-INFO}"
api_host="${API_HOST:-0.0.0.0}"
api_port="${API_PORT:-8000}"

cleanup() {
    local exit_code=$?
    trap - TERM INT EXIT
    kill "${celery_pid:-}" "${api_pid:-}" 2>/dev/null || true
    wait "${celery_pid:-}" "${api_pid:-}" 2>/dev/null || true
    exit "$exit_code"
}

trap cleanup TERM INT EXIT

celery \
    -A app.workers.celery_app:celery_app worker \
    --loglevel="$worker_log_level" \
    --concurrency="$worker_concurrency" &
celery_pid=$!

uvicorn app.main:app \
    --host="$api_host" \
    --port="$api_port" &
api_pid=$!

# Keep the container alive while both services run, and stop the other service
# if either one exits unexpectedly.
wait -n "$celery_pid" "$api_pid"
