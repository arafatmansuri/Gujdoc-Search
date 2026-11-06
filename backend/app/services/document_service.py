import json
from datetime import UTC, datetime

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
                    created_at,
                    page_count,
                    searchable_blob_name,
                    document_number,
                    document_date,
                    subject,
                    issuing_office,
                    referenced_documents,
                    metadata_confidence,
                    metadata_status
                    ,ocr_confidence
                    ,uncertain_regions
                    ,layout_features
                    ,processing_started_at
                    ,processing_completed_at
                    ,processing_error
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
                "page_count": row[4],
                "has_searchable_pdf": row[5] is not None,
                "document_number": row[6],
                "document_date": row[7],
                "subject": row[8],
                "issuing_office": row[9],
                "referenced_documents": row[10],
                "metadata_confidence": float(row[11]) if row[11] is not None else None,
                "metadata_status": row[12],
                "ocr_confidence": float(row[13]) if row[13] is not None else None,
                "uncertain_regions": row[14],
                "layout_features": row[15] or {},
                "processing_started_at": row[16],
                "processing_completed_at": row[17],
                "processing_error": row[18],
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
                    created_at,
                    page_count,
                    searchable_blob_name,
                    document_number,
                    document_date,
                    subject,
                    issuing_office,
                    referenced_documents,
                    metadata_confidence,
                    metadata_status
                    ,ocr_confidence
                    ,uncertain_regions
                    ,layout_features
                    ,processing_started_at
                    ,processing_completed_at
                    ,processing_error
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
        "page_count": row[5],
        "searchable_blob_name": row[6],
        "document_number": row[7],
        "document_date": row[8],
        "subject": row[9],
        "issuing_office": row[10],
        "referenced_documents": row[11],
        "metadata_confidence": float(row[12]) if row[12] is not None else None,
        "metadata_status": row[13],
        "ocr_confidence": float(row[14]) if row[14] is not None else None,
        "uncertain_regions": row[15],
        "layout_features": row[16] or {},
        "processing_started_at": row[17],
        "processing_completed_at": row[18],
        "processing_error": row[19],
    }


def update_ocr_quality(
    document_id: int,
    confidence: float | None,
    uncertain_regions: int,
    layout_features: dict,
) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET ocr_confidence = %s, uncertain_regions = %s, layout_features = %s::jsonb
            WHERE id = %s
            """,
            (confidence, uncertain_regions, json.dumps(layout_features), document_id),
        )
        conn.commit()


def mark_processing_started(document_id: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET processing_started_at = %s, processing_completed_at = NULL,
                processing_error = NULL
            WHERE id = %s
            """,
            (datetime.now(UTC), document_id),
        )
        conn.commit()


def mark_processing_completed(document_id: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET processing_completed_at = %s WHERE id = %s",
            (datetime.now(UTC), document_id),
        )
        conn.commit()


def mark_processing_error(document_id: int, error: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET processing_error = %s WHERE id = %s",
            (error[:1000], document_id),
        )
        conn.commit()


def set_searchable_blob(document_id: int, blob_name: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET searchable_blob_name = %s WHERE id = %s",
            (blob_name, document_id),
        )
        conn.commit()


def update_document_metadata(document_id: int, metadata: dict) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET document_number = %s,
                document_date = %s,
                subject = %s,
                issuing_office = %s,
                referenced_documents = %s::jsonb,
                metadata_confidence = %s,
                metadata_status = %s
            WHERE id = %s AND status <> 'deleted'
            """,
            (
                metadata["document_number"],
                metadata["document_date"],
                metadata["subject"],
                metadata["issuing_office"],
                json.dumps(metadata["referenced_documents"]),
                metadata["confidence"],
                metadata["status"],
                document_id,
            ),
        )
        conn.commit()


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


def get_processing_metrics(user_id: int) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'completed'),
                COUNT(*) FILTER (WHERE status = 'failed'),
                COUNT(*) FILTER (WHERE metadata_status = 'verified'),
                COALESCE(AVG(ocr_confidence), 0),
                COALESCE(SUM(uncertain_regions), 0),
                COALESCE(AVG(EXTRACT(EPOCH FROM (processing_completed_at - processing_started_at))), 0)
            FROM documents
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return {
        "completed_documents": row[0],
        "failed_documents": row[1],
        "verified_metadata_documents": row[2],
        "average_ocr_confidence": float(row[3]),
        "uncertain_regions": row[4],
        "average_processing_seconds": float(row[5]),
    }
