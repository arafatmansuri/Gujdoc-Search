import uuid

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_connection
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


@router.post("/register", status_code=201)
def register_user(request: RegisterRequest):
    """Register a new user."""

    email = str(request.email).lower()

    hashed_password = hash_password(request.password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    email,
                    hashed_password
                )
                VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id, email
                """,
                (email, hashed_password),
            )

            user = cur.fetchone()

        conn.commit()

    if user is None:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    return {
        "id": user[0],
        "email": user[1],
        "message": "User registered successfully",
    }


@router.post("/login")
def login_user(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate user and return JWT."""

    enforce_rate_limit(request, "login", settings["RATE_LIMIT_LOGIN"])
    email = form.username.lower()

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, email, hashed_password
                FROM users
                WHERE email = %s
                AND is_active = TRUE
                """,
            (email,),
        )

        user = cur.fetchone()

    if user is None or not verify_password(
        form.password,
        user[2],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user[0])
    refresh_token, token_hash, expires_at = create_refresh_token()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (uuid.uuid4(), user[0], token_hash, expires_at),
            )
        conn.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_access_token(request: RefreshRequest):
    token_hash = hash_refresh_token(request.refresh_token)
    new_refresh, new_hash, new_expiry = create_refresh_token()
    replacement_id = uuid.uuid4()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id
                FROM refresh_tokens
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                FOR UPDATE
                """,
                (token_hash,),
            )
            token = cur.fetchone()
            if token is None:
                conn.rollback()
                raise HTTPException(status_code=401, detail="Invalid refresh token")

            cur.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = CURRENT_TIMESTAMP, replaced_by = %s
                WHERE id = %s
                """,
                (replacement_id, token[0]),
            )
            cur.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (replacement_id, token[1], new_hash, new_expiry),
            )
        conn.commit()

    return {
        "access_token": create_access_token(token[1]),
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=204)
def logout(request: RefreshRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP)
                WHERE token_hash = %s
                """,
                (hash_refresh_token(request.refresh_token),),
            )
        conn.commit()


@router.get("/me")
def get_me(
    current_user: dict = Depends(get_current_user),
):
    return current_user
