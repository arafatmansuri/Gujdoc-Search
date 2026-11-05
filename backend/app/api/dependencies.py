import os

import jwt
from app.core.database import get_connection
from app.core.security import ALGORITHM, SECRET_KEY
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    """Validate JWT and return the authenticated user."""

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=os.getenv("JWT_ISSUER") or None,
            audience=os.getenv("JWT_AUDIENCE") or None,
            options={"require": ["sub", "exp", "iat", "type"]},
        )

        user_id = payload.get("sub")

        if not user_id or payload.get("type") != "access":
            raise credentials_exception

        user_id = int(user_id)

    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
    ):
        raise credentials_exception

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, email, is_active
                FROM users
                WHERE id = %s
                """,
            (user_id,),
        )

        user = cur.fetchone()

    if user is None or not user[2]:
        raise credentials_exception

    return {
        "id": user[0],
        "email": user[1],
    }
