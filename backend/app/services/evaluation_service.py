import json
import re

from app.core.database import get_connection


def save_evaluation_case(user_id: int, document_id: int, case: dict) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM documents WHERE id = %s AND user_id = %s AND status <> 'deleted'",
            (document_id, user_id),
        )
        if cur.fetchone() is None:
            raise LookupError("Document not found")
        cur.execute(
            """
            INSERT INTO evaluation_cases
                (document_id, user_id, page_number, expected_text,
                 expected_document_number, expected_date, expected_subject,
                 expected_issuing_office, expected_region)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (document_id, page_number) DO UPDATE SET
                expected_text = EXCLUDED.expected_text,
                expected_document_number = EXCLUDED.expected_document_number,
                expected_date = EXCLUDED.expected_date,
                expected_subject = EXCLUDED.expected_subject,
                expected_issuing_office = EXCLUDED.expected_issuing_office,
                expected_region = EXCLUDED.expected_region
            RETURNING id
            """,
            (
                document_id, user_id, case["page_number"], case["expected_text"],
                case.get("expected_document_number"), case.get("expected_date"),
                case.get("expected_subject"), case.get("expected_issuing_office"),
                json.dumps(case.get("expected_region")),
            ),
        )
        case_id = cur.fetchone()[0]
        conn.commit()
    return {"id": case_id, "document_id": document_id, "page_number": case["page_number"]}


def get_evaluation_metrics(user_id: int) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.expected_text, COALESCE(string_agg(r.text, ' ' ORDER BY r.id), ''),
                   c.expected_document_number, d.document_number,
                   c.expected_subject, d.subject,
                   c.expected_issuing_office, d.issuing_office,
                   c.expected_region, r.x0, r.y0, r.x1, r.y1
            FROM evaluation_cases c
            JOIN documents d ON d.id = c.document_id
            LEFT JOIN document_regions r
              ON r.document_id = c.document_id AND r.page_number = c.page_number
            WHERE c.user_id = %s
            GROUP BY c.id, d.document_number, d.subject, d.issuing_office,
                     r.x0, r.y0, r.x1, r.y1
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    def norm(value: str | None) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().casefold())

    def edit_distance(left: str, right: str) -> int:
        previous = list(range(len(right) + 1))
        for i, char in enumerate(left, 1):
            current = [i]
            for j, other in enumerate(right, 1):
                current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (char != other)))
            previous = current
        return previous[-1]

    cer_values = []
    metadata_hits = metadata_total = 0
    region_hits = region_total = 0
    for row in rows:
        expected, actual = norm(row[0]), norm(row[1])
        cer_values.append(edit_distance(expected, actual) / max(len(expected), 1))
        for expected_value, actual_value in ((row[2], row[3]), (row[4], row[5]), (row[6], row[7])):
            if expected_value:
                metadata_total += 1
                metadata_hits += norm(str(expected_value)) == norm(str(actual_value))
        if row[8] and all(value is not None for value in row[9:13]):
            region_total += 1
            expected_region = row[8]
            region_hits += all(
                abs(float(expected_region[key]) - float(value)) <= 5
                for key, value in zip(("x0", "y0", "x1", "y1"), row[9:13])
            )
    return {
        "evaluation_cases": len(rows),
        "ocr_character_error_rate": sum(cer_values) / len(cer_values) if cer_values else None,
        "metadata_precision_recall": metadata_hits / metadata_total if metadata_total else None,
        "source_region_accuracy": region_hits / region_total if region_total else None,
    }
