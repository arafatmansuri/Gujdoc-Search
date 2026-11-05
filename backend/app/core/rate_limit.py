import logging

from app.core.config import settings
from fastapi import HTTPException, Request
from redis import Redis

logger = logging.getLogger(__name__)


def enforce_rate_limit(
    request: Request, scope: str, limit: int, identity: str | None = None
) -> None:
    """Apply a Redis-backed fixed-window limit without trusting forwarded headers."""

    redis_url = settings["REDIS_URL"]
    if not redis_url:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"gujdoc:rate:{scope}:{identity or client_ip}"
    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, settings["RATE_LIMIT_WINDOW_SECONDS"])
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(settings["RATE_LIMIT_WINDOW_SECONDS"])},
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "Rate limiter unavailable", extra={"scope": scope}, exc_info=True
        )
