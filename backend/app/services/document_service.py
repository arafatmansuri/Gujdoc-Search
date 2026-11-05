from app.core.database import get_connection


def list_documents(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    id,
                    filename,
                    status,
                    created_at
                FROM documents
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
            (user_id, limit, offset),
        )

        rows = cur.fetchall()

        cur.execute(
            """
                SELECT COUNT(*)
                FROM documents
                WHERE user_id = %s
                """,
            (user_id,),
        )

        total = cur.fetchone()[0]

    return {
        "items": [
            {
                "id": row[0],
                "filename": row[1],
                "status": row[2],
                "created_at": row[3],
            }
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_document(
    document_id: int,
    user_id: int,
) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    id,
                    filename,
                    blob_name,
                    status,
                    created_at
                FROM documents
                WHERE id = %s
                  AND user_id = %s
                  AND status <> 'deleted'
                """,
            (document_id, user_id),
        )

        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "blob_name": row[2],
        "status": row[3],
        "created_at": row[4],
    }


def delete_document_record(
    document_id: int,
    user_id: int,
) -> str | None:
    """
    Delete chunks and document record.
    Returns blob_name if the document exists and belongs to the user.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT blob_name
                FROM documents
                WHERE id = %s
                  AND user_id = %s
                """,
                (document_id, user_id),
            )

            row = cur.fetchone()

            if not row:
                return None

            blob_name = row[0]

            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )

            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s
                  AND user_id = %s
                """,
                (document_id, user_id),
            )
        conn.commit()

    return blob_name
