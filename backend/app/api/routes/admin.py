from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.database import get_connection

router = APIRouter(prefix="/admin", tags=["Administration"])


class RoleRequest(BaseModel):
    role: str


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:  # noqa: B008
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required")
    return current_user


@router.get("/users")
def list_users(_: dict = Depends(require_admin)):  # noqa: B008
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            """
        )
        return [
            {
                "id": row[0],
                "email": row[1],
                "role": row[2],
                "is_active": row[3],
                "created_at": row[4],
            }
            for row in cur.fetchall()
        ]


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    request: RoleRequest,
    current_user: dict = Depends(require_admin),  # noqa: B008
):
    if request.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=400, detail="Role must be reviewer or admin")
    if user_id == current_user["id"] and request.role != "admin":
        raise HTTPException(status_code=400, detail="An administrator cannot remove their own access")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET role = %s WHERE id = %s RETURNING id, email, role",
            (request.role, user_id),
        )
        user = cur.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    return {"id": user[0], "email": user[1], "role": user[2]}
