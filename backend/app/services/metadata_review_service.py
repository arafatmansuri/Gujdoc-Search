import json

from app.core.database import get_connection


def get_document_audit_events(document_id: int, user_id: int) -> list[dict] | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id
            FROM documents d
            WHERE d.id = %s AND d.user_id = %s AND d.status <> 'deleted'
            """,
            (document_id, user_id),
        )
        if cur.fetchone() is None:
            return None
        cur.execute(
            """
            SELECT e.id, e.action, e.details, e.created_at, u.email
            FROM document_audit_events e
            JOIN users u ON u.id = e.user_id
            WHERE e.document_id = %s
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT 200
            """,
            (document_id,),
        )
        return [
            {
                "id": row[0],
                "action": row[1],
                "details": row[2] or {},
                "created_at": row[3],
                "user_email": row[4],
            }
            for row in cur.fetchall()
        ]


def save_metadata_correction(
    document_id: int,
    user_id: int,
    metadata: dict,
) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT document_number, document_date, subject, issuing_office,
                   referenced_documents, metadata_status
            FROM documents
            WHERE id = %s AND user_id = %s AND status <> 'deleted'
            FOR UPDATE
            """,
            (document_id, user_id),
        )
        previous = cur.fetchone()
        if previous is None:
            raise LookupError("Document not found")

        cur.execute(
            """
            INSERT INTO document_metadata_corrections
                (document_id, user_id, previous_values, corrected_values)
            VALUES (%s, %s, %s::jsonb, %s::jsonb)
            """,
            (
                document_id,
                user_id,
                json.dumps(
                    {
                        "document_number": previous[0],
                        "document_date": previous[1].isoformat() if previous[1] else None,
                        "subject": previous[2],
                        "issuing_office": previous[3],
                        "referenced_documents": previous[4] or [],
                        "metadata_status": previous[5],
                    }
                ),
                json.dumps(metadata),
            ),
        )
        cur.execute(
            """
            UPDATE documents
            SET document_number = %s,
                document_date = %s,
                subject = %s,
                issuing_office = %s,
                referenced_documents = %s::jsonb,
                metadata_confidence = 1,
                metadata_status = 'verified'
            WHERE id = %s AND user_id = %s
            """,
            (
                metadata["document_number"],
                metadata["document_date"],
                metadata["subject"],
                metadata["issuing_office"],
                json.dumps(metadata["referenced_documents"]),
                document_id,
                user_id,
            ),
        )
        cur.execute(
            """
            INSERT INTO document_audit_events (document_id, user_id, action, details)
            VALUES (%s, %s, 'metadata_corrected', %s::jsonb)
            """,
            (
                document_id,
                user_id,
                json.dumps(
                    {
                        "previous_values": {
                            "document_number": previous[0],
                            "document_date": previous[1].isoformat() if previous[1] else None,
                            "subject": previous[2],
                            "issuing_office": previous[3],
                        },
                        "corrected_values": metadata,
                    }
                ),
            ),
        )
        conn.commit()


def save_region_correction(
    region_id: int,
    user_id: int,
    text: str,
) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.document_id, r.text, d.user_id
            FROM document_regions r
            JOIN documents d ON d.id = r.document_id
            WHERE r.id = %s AND d.user_id = %s
            FOR UPDATE
            """,
            (region_id, user_id),
        )
        row = cur.fetchone()
        if row is None:
            raise LookupError("OCR region not found")
        cur.execute(
            "UPDATE document_regions SET text = %s, confidence = 1 WHERE id = %s",
            (text, region_id),
        )
        cur.execute(
            """
            INSERT INTO document_audit_events (document_id, user_id, action, details)
            VALUES (%s, %s, 'ocr_region_corrected', %s::jsonb)
            """,
            (
                row[0],
                user_id,
                json.dumps({"region_id": region_id, "previous_text": row[1], "text": text}),
            ),
        )
        conn.commit()
    return {"region_id": region_id, "text": text, "confidence": 1}
