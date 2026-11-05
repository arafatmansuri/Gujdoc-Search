from app.core.database import get_connection
from psycopg.errors import UniqueViolation


class DuplicateDocumentError(Exception):
    """Raised when a user uploads the same content more than once."""


def save_document(
    filename: str,
    blob_name: str | None,
    user_id: int,
    content_hash: str,
) -> int:
    """Create a document record owned by a user."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                INSERT INTO documents (
                    filename,
                    blob_name,
                    user_id,
                    content_hash
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                    (filename, blob_name, user_id, content_hash),
                )
            except UniqueViolation as exc:
                conn.rollback()
                raise DuplicateDocumentError from exc

            document_id = cur.fetchone()[0]

        conn.commit()

    return document_id


def save_chunks(
    document_id: int,
    chunks: list[dict],
) -> None:
    """Save chunks and their embeddings."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        page_number,
                        chunk_index,
                        content,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, chunk_index)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        document_id,
                        chunk["page_number"],
                        chunk["chunk_index"],
                        chunk["content"],
                        chunk["embedding"],
                    ),
                )

        conn.commit()


def update_document_status(
    document_id: int,
    status: str,
) -> None:
    """Update processing status."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET status = %s
                WHERE id = %s
                  AND status <> 'deleted'
                """,
                (status, document_id),
            )

        conn.commit()


def get_document_for_processing(document_id: int, blob_name: str) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, blob_name, status
                FROM documents
                WHERE id = %s AND blob_name = %s AND status <> 'deleted'
                """,
            (document_id, blob_name),
        )
        row = cur.fetchone()
    return {"id": row[0], "blob_name": row[1], "status": row[2]} if row else None


def clear_chunks(document_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM document_chunks WHERE document_id = %s", (document_id,)
            )
        conn.commit()


def search_documents(
    query_embedding: list[float],
    user_id: int,
    limit: int = 5,
) -> list[dict]:
    """Search only documents belonging to the user."""

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    d.filename,
                    c.document_id,
                    c.page_number,
                    c.content,
                    1 - (c.embedding <=> %s::vector)
                        AS similarity
                FROM document_chunks c
                JOIN documents d
                    ON d.id = c.document_id
                WHERE
                    c.embedding IS NOT NULL
                    AND d.user_id = %s
                    AND d.status = 'completed'
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
            (
                query_embedding,
                user_id,
                query_embedding,
                limit,
            ),
        )

        rows = cur.fetchall()

    return [
        {
            "filename": row[0],
            "document_id": row[1],
            "page_number": row[2],
            "content": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]
