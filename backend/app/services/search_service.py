from psycopg.errors import UniqueViolation

from app.core.database import get_connection


class DuplicateDocumentError(Exception):
    """Raised when a user uploads the same content more than once."""


def save_document(
    filename: str,
    blob_name: str | None,
    user_id: int,
    content_hash: str,
    page_count: int,
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
                    page_count,
                    user_id,
                    content_hash
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                    (filename, blob_name, page_count, user_id, content_hash),
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
            cur.execute(
                "DELETE FROM document_regions WHERE document_id = %s", (document_id,)
            )
        conn.commit()


def save_regions(document_id: int, pages: list[dict]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for page in pages:
            for region in page.get("regions", []):
                cur.execute(
                    """
                    INSERT INTO document_regions
                        (document_id, page_number, text, x0, y0, x1, y1, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        page["page_number"],
                        region["text"],
                        region["x0"],
                        region["y0"],
                        region["x1"],
                        region["y1"],
                        region["confidence"],
                    ),
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
                    r.x0,
                    r.y0,
                    r.x1,
                    r.y1,
                    1 - (c.embedding <=> %s::vector)
                        AS similarity
                FROM document_chunks c
                JOIN documents d
                    ON d.id = c.document_id
                LEFT JOIN LATERAL (
                    SELECT x0, y0, x1, y1
                    FROM document_regions
                    WHERE document_id = c.document_id
                      AND page_number = c.page_number
                    ORDER BY id
                    LIMIT 1
                ) r ON TRUE
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
            "similarity": float(row[8]),
            "region": {"x0": row[4], "y0": row[5], "x1": row[6], "y1": row[7]},
        }
        for row in rows
    ]


def search_record_metadata(
    user_id: int,
    query: str = "",
    document_number: str | None = None,
    issuing_office: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    terms = [part for part in query.split() if part]
    with get_connection() as conn, conn.cursor() as cur:
        clauses = ["d.user_id = %s", "d.status = 'completed'"]
        params: list[object] = [user_id]
        for term in terms:
            clauses.append(
                "(d.filename ILIKE %s OR d.document_number ILIKE %s OR "
                "d.subject ILIKE %s OR d.issuing_office ILIKE %s)"
            )
            value = f"%{term}%"
            params.extend([value, value, value, value])
        if document_number:
            clauses.append("d.document_number ILIKE %s")
            params.append(f"%{document_number}%")
        if issuing_office:
            clauses.append("d.issuing_office ILIKE %s")
            params.append(f"%{issuing_office}%")
        if date_from:
            clauses.append("d.document_date >= %s")
            params.append(date_from)
        if date_to:
            clauses.append("d.document_date <= %s")
            params.append(date_to)
        where = " AND ".join(clauses)
        cur.execute(
            f"""
            SELECT d.id, d.filename, d.document_number, d.document_date,
                   d.subject, d.issuing_office, d.referenced_documents,
                   d.metadata_confidence, d.metadata_status, d.created_at
            FROM documents d
            WHERE {where}
            ORDER BY d.document_date DESC NULLS LAST, d.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (*params, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) FROM documents d WHERE {where}", params)
        total = cur.fetchone()[0]
    return {
        "items": [
            {
                "id": row[0],
                "filename": row[1],
                "document_number": row[2],
                "document_date": row[3],
                "subject": row[4],
                "issuing_office": row[5],
                "referenced_documents": row[6] or [],
                "metadata_confidence": float(row[7]) if row[7] is not None else None,
                "metadata_status": row[8],
                "created_at": row[9],
            }
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_document_regions(document_id: int, user_id: int, page_number: int | None = None) -> list[dict] | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, r.page_number, r.text, r.x0, r.y0, r.x1, r.y1, r.confidence
            FROM document_regions r
            JOIN documents d ON d.id = r.document_id
            WHERE r.document_id = %s AND d.user_id = %s
              AND (%s::integer IS NULL OR r.page_number = %s::integer)
            ORDER BY r.page_number, r.id
            """,
            (document_id, user_id, page_number, page_number),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    return [
        {
            "id": row[0],
            "page_number": row[1],
            "text": row[2],
            "x0": row[3],
            "y0": row[4],
            "x1": row[5],
            "y1": row[6],
            "confidence": float(row[7]) if row[7] is not None else None,
        }
        for row in rows
    ]
