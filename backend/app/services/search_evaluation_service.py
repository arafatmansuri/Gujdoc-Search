import json

from app.core.database import get_connection


def create_search_case(user_id: int, query: str, expected_document_ids: list[int]) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO search_evaluation_cases (user_id, query, expected_document_ids)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id
            """,
            (user_id, query.strip(), json.dumps(expected_document_ids)),
        )
        case_id = cur.fetchone()[0]
        conn.commit()
    return {"id": case_id, "query": query, "expected_document_ids": expected_document_ids}


def record_search_result(case_id: int, user_id: int, success: bool) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE search_evaluation_cases
            SET last_success = %s, last_run_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (success, case_id, user_id),
        )
        conn.commit()


def get_search_metrics(user_id: int) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*), COUNT(*) FILTER (WHERE last_success IS TRUE)
            FROM search_evaluation_cases
            WHERE user_id = %s
            """,
            (user_id,),
        )
        total, successful = cur.fetchone()
    return {
        "search_evaluation_cases": total,
        "search_success_rate": successful / total if total else None,
    }
