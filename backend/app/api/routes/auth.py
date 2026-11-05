from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from app.api.dependencies import get_current_user

from app.core.database import get_connection
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

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

@router.post("/register", status_code=201)
def register_user(request: RegisterRequest):
    """Register a new user."""

    email = str(request.email).lower()

    hashed_password = hash_password(
        request.password
    )

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
    form: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate user and return JWT."""

    email = form.username.lower()

    with get_connection() as conn:
        with conn.cursor() as cur:

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

    if (
        user is None
        or not verify_password(
            form.password,
            user[2],
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = create_access_token(user[0])

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.get("/me")
def get_me(
    current_user: dict = Depends(get_current_user),
):
    return current_user