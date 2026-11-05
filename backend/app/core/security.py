import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from app.core.config import settings
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()


ALGORITHM = "HS256"

SECRET_KEY = settings["SECRET_KEY"]

if not SECRET_KEY or SECRET_KEY.startswith("replace-with"):
    raise RuntimeError("SECRET_KEY must be configured with a random value")

ACCESS_TOKEN_EXPIRE_MINUTES = settings["ACCESS_TOKEN_EXPIRE_MINUTES"]

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its hash."""

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(user_id: int) -> str:
    """Create a signed JWT access token."""

    expires_at = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }
    if settings["JWT_ISSUER"]:
        payload["iss"] = settings["JWT_ISSUER"]
    if settings["JWT_AUDIENCE"]:
        payload["aud"] = settings["JWT_AUDIENCE"]

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token() -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(
        days=settings["REFRESH_TOKEN_EXPIRE_DAYS"]
    )
    return raw_token, token_hash, expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
