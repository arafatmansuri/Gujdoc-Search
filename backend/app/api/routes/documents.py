import hashlib
import logging
import re
import uuid
from io import BytesIO
from pathlib import Path

import pymupdf
from azure.storage.blob import BlobServiceClient
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_connection
from app.core.rate_limit import enforce_rate_limit
from app.services.document_service import (
    delete_document_record,
    get_processing_metrics,
    get_document,
    list_documents,
)
from app.services.embedding_service import (
    generate_embedding,
)
from app.services.metadata_review_service import (
    get_document_audit_events,
    save_metadata_correction,
    save_region_correction,
)
from app.services.evaluation_service import get_evaluation_metrics, save_evaluation_case
from app.services.search_evaluation_service import (
    create_search_case,
    get_search_metrics,
    record_search_result,
)
from app.services.rag_service import answer_question
from app.services.search_service import (
    DuplicateDocumentError,
    get_document_regions,
    save_document,
    search_documents,
    search_record_metadata,
)
from app.workers.tasks import process_document

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

logger = logging.getLogger(__name__)
MAX_UPLOAD_SIZE = settings["MAX_UPLOAD_SIZE_BYTES"]


# --------------------------------------------------
# Upload document
# --------------------------------------------------


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a PDF to Azure Blob Storage
    and queue background processing.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    safe_filename = Path(file.filename).name
    safe_filename = re.sub(r"[\x00-\x1f\x7f]", "", safe_filename).strip()
    if not safe_filename or Path(safe_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    if file.content_type not in (None, "application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read(MAX_UPLOAD_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty file",
        )

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds maximum upload size",
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400, detail="The uploaded file is not a valid PDF"
        )
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            page_count = pdf.page_count
            if page_count == 0:
                raise HTTPException(status_code=400, detail="The PDF contains no pages")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="The uploaded PDF is malformed"
        ) from exc

    content_hash = hashlib.sha256(content).hexdigest()

    connection_string = settings["AZURE_STORAGE_CONNECTION_STRING"]

    container_name = settings["AZURE_STORAGE_CONTAINER"]

    if not connection_string or not container_name:
        raise HTTPException(
            status_code=500,
            detail="Azure configuration missing",
        )

    blob_name = f"documents/{uuid.uuid4().hex}.pdf"

    blob_service = BlobServiceClient.from_connection_string(connection_string)

    blob_client = blob_service.get_container_client(container_name).get_blob_client(
        blob_name
    )

    document_id = None

    try:
        # Upload PDF to Azure
        blob_client.upload_blob(
            content,
            overwrite=False,
            content_settings=None,
        )

        # Create document record
        document_id = save_document(
            filename=safe_filename[:255],
            blob_name=blob_name,
            user_id=current_user["id"],
            content_hash=content_hash,
            page_count=page_count,
        )

        # Queue background processing
        task = process_document.delay(
            document_id=document_id,
            blob_name=blob_name,
        )

        document = get_document(document_id, current_user["id"])
        if document is None:
            raise HTTPException(status_code=500, detail="Uploaded document could not be loaded")
        document.pop("blob_name", None)
        document.pop("searchable_blob_name", None)
        return {
            **document,
            "task_id": task.id,
            "message": "Document queued for processing",
        }

    except DuplicateDocumentError as exc:
        try:
            blob_client.delete_blob()
        except Exception:
            logger.warning("Could not remove duplicate upload blob", exc_info=True)
        raise HTTPException(
            status_code=409,
            detail="This document has already been uploaded.",
        ) from exc
    except Exception as exc:
        # Remove uploaded blob if database/task setup fails
        try:
            blob_client.delete_blob()
        except Exception:
            logger.warning("Could not remove failed upload blob", exc_info=True)

        if document_id is not None:
            try:
                from app.services.search_service import (
                    update_document_status,
                )

                update_document_status(
                    document_id,
                    "failed",
                )
            except Exception:
                logger.warning("Could not mark failed upload", exc_info=True)

        raise HTTPException(
            status_code=500,
            detail="Document upload or queueing failed",
        ) from exc

    finally:
        await file.close()


# --------------------------------------------------
# Document processing status
# --------------------------------------------------


@router.get("/{document_id}/status")
def get_document_status(
    document_id: int, current_user: dict = Depends(get_current_user)
):
    """Retrieve document processing status."""

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    id,
                    filename,
                    status,
                    created_at,
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
                """,
            (document_id, current_user["id"]),
        )

        row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "document_id": row[0],
        "filename": row[1],
        "status": row[2],
        "created_at": row[3],
        "document_number": row[4],
        "document_date": row[5],
        "subject": row[6],
        "issuing_office": row[7],
        "referenced_documents": row[8],
        "metadata_confidence": float(row[9]) if row[9] is not None else None,
        "metadata_status": row[10],
        "ocr_confidence": float(row[11]) if row[11] is not None else None,
        "uncertain_regions": row[12],
        "layout_features": row[13] or {},
        "processing_started_at": row[14],
        "processing_completed_at": row[15],
        "processing_error": row[16],
    }


# --------------------------------------------------
# Semantic search
# --------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000,
    )
    limit: int = Field(default=5, ge=1, le=20)


class RecordSearchRequest(BaseModel):
    query: str = Field(default="", max_length=2000)
    document_number: str | None = Field(default=None, max_length=255)
    issuing_office: str | None = Field(default=None, max_length=1000)
    date_from: str | None = Field(default=None, max_length=10)
    date_to: str | None = Field(default=None, max_length=10)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MetadataCorrectionRequest(BaseModel):
    document_number: str | None = Field(default=None, max_length=255)
    document_date: str | None = Field(default=None, max_length=10)
    subject: str | None = Field(default=None, max_length=2000)
    issuing_office: str | None = Field(default=None, max_length=1000)
    referenced_documents: list[str] = Field(default_factory=list, max_length=100)


class RegionCorrectionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class EvaluationCaseRequest(BaseModel):
    page_number: int = Field(ge=1)
    expected_text: str = Field(min_length=1, max_length=200000)
    expected_document_number: str | None = Field(default=None, max_length=255)
    expected_date: str | None = Field(default=None, max_length=10)
    expected_subject: str | None = Field(default=None, max_length=2000)
    expected_issuing_office: str | None = Field(default=None, max_length=1000)
    expected_region: dict[str, float] | None = None


class SearchEvaluationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    expected_document_ids: list[int] = Field(min_length=1, max_length=50)


class SearchEvaluationRunRequest(BaseModel):
    case_id: int


@router.patch("/{document_id}/metadata")
def correct_document_metadata(
    document_id: int,
    request: MetadataCorrectionRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required")
    try:
        save_metadata_correction(
            document_id=document_id,
            user_id=current_user["id"],
            metadata=request.model_dump(),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    updated = get_document(document_id, current_user["id"])
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found")
    updated.pop("blob_name", None)
    updated.pop("searchable_blob_name", None)
    return {
        **updated,
        "message": "Metadata correction saved.",
    }


@router.patch("/regions/{region_id}")
def correct_ocr_region(
    region_id: int,
    request: RegionCorrectionRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required")
    try:
        return save_region_correction(region_id, current_user["id"], request.text.strip())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/records/search")
def search_records(
    request: RecordSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    return search_record_metadata(
        user_id=current_user["id"],
        query=request.query.strip(),
        document_number=request.document_number,
        issuing_office=request.issuing_office,
        date_from=request.date_from,
        date_to=request.date_to,
        limit=request.limit,
        offset=request.offset,
    )


@router.get("/{document_id}/regions")
def document_regions(
    document_id: int,
    page_number: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
):
    regions = get_document_regions(document_id, current_user["id"], page_number)
    if regions is None:
        raise HTTPException(status_code=404, detail="Document regions not found")
    return {"document_id": document_id, "regions": regions}


@router.get("/{document_id}/audit")
def document_audit(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    events = get_document_audit_events(document_id, current_user["id"])
    if events is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": document_id, "events": events}


@router.post("/{document_id}/evaluation")
def add_evaluation_case(
    document_id: int,
    request: EvaluationCaseRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required")
    try:
        return save_evaluation_case(current_user["id"], document_id, request.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evaluation/search-case")
def add_search_evaluation_case(
    request: SearchEvaluationRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required")
    return create_search_case(
        current_user["id"],
        request.query,
        request.expected_document_ids,
    )


@router.post("/evaluation/search-run")
def run_search_evaluation(
    request: SearchEvaluationRunRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT query, expected_document_ids
            FROM search_evaluation_cases
            WHERE id = %s AND user_id = %s
            """,
            (request.case_id, current_user["id"]),
        )
        case = cur.fetchone()
    if case is None:
        raise HTTPException(status_code=404, detail="Search evaluation case not found")
    enforce_rate_limit(http_request, "search", settings["RATE_LIMIT_EXPENSIVE"], str(current_user["id"]))
    results = search_documents(
        generate_embedding(case[0]),
        current_user["id"],
        limit=10,
    )
    expected = set(case[1] or [])
    success = any(result["document_id"] in expected for result in results)
    record_search_result(request.case_id, current_user["id"], success)
    return {"case_id": request.case_id, "success": success, "result_count": len(results)}


@router.get("/{document_id}/searchable-pdf")
def download_searchable_pdf(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    document = get_document(document_id, current_user["id"])
    if not document or not document.get("searchable_blob_name"):
        raise HTTPException(status_code=404, detail="Searchable PDF is not ready")
    blob = BlobServiceClient.from_connection_string(
        settings["AZURE_STORAGE_CONNECTION_STRING"]
    ).get_blob_client(
        container=settings["AZURE_STORAGE_CONTAINER"],
        blob=document["searchable_blob_name"],
    ).download_blob().readall()
    return StreamingResponse(
        BytesIO(blob),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document["filename"]}"'
        },
    )


@router.get("/{document_id}/preview")
def preview_document_page(
    document_id: int,
    page_number: int = Query(default=1, ge=1),
    current_user: dict = Depends(get_current_user),
):
    document = get_document(document_id, current_user["id"])
    if not document or not document.get("blob_name"):
        raise HTTPException(status_code=404, detail="Document not found")
    blob = BlobServiceClient.from_connection_string(
        settings["AZURE_STORAGE_CONNECTION_STRING"]
    ).get_blob_client(
        container=settings["AZURE_STORAGE_CONTAINER"],
        blob=document["blob_name"],
    ).download_blob().readall()
    try:
        with pymupdf.open(stream=blob, filetype="pdf") as pdf:
            if page_number > pdf.page_count:
                raise HTTPException(status_code=404, detail="Page not found")
            pixmap = pdf[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            image = pixmap.tobytes("png")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not render document page") from exc
    return StreamingResponse(BytesIO(image), media_type="image/png")


@router.post("/search")
def semantic_search(
    request: SearchRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Search document chunks using Gemini embeddings."""

    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    try:
        enforce_rate_limit(
            http_request,
            "search",
            settings["RATE_LIMIT_EXPENSIVE"],
            str(current_user["id"]),
        )
        query_embedding = generate_embedding(query)

        results = search_documents(
            query_embedding=query_embedding,
            user_id=current_user["id"],
            limit=request.limit,
        )

        return {
            "query": query,
            "total_results": len(results),
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Semantic search failed",
        ) from exc


@router.get("/evaluation/metrics")
def evaluation_metrics(current_user: dict = Depends(get_current_user)):
    return {
        **get_evaluation_metrics(current_user["id"]),
        **get_search_metrics(current_user["id"]),
    }


@router.get("")
def get_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    return list_documents(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
    )


@router.get("/metrics/summary")
def get_metrics_summary(current_user: dict = Depends(get_current_user)):
    return get_processing_metrics(current_user["id"])


@router.get("/{document_id}")
def get_document_details(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    document = get_document(
        document_id=document_id,
        user_id=current_user["id"],
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Avoid exposing the internal Azure blob name.
    document.pop("blob_name", None)
    document.pop("searchable_blob_name", None)

    return document


@router.delete("/{document_id}")
def delete_user_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    document = get_document(
        document_id=document_id,
        user_id=current_user["id"],
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    blob_name = document["blob_name"]

    # Delete the Azure blob first.
    blob_service = BlobServiceClient.from_connection_string(
        settings["AZURE_STORAGE_CONNECTION_STRING"]
    )

    blob_client = blob_service.get_blob_client(
        container=settings["AZURE_STORAGE_CONTAINER"],
        blob=blob_name,
    )

    try:
        blob_client.delete_blob(delete_snapshots="include")
        if document.get("searchable_blob_name"):
            BlobServiceClient.from_connection_string(
                settings["AZURE_STORAGE_CONNECTION_STRING"]
            ).get_blob_client(
                container=settings["AZURE_STORAGE_CONTAINER"],
                blob=document["searchable_blob_name"],
            ).delete_blob(delete_snapshots="include")
    except Exception as exc:
        logger.exception(
            "Document blob deletion failed", extra={"document_id": document_id}
        )
        raise HTTPException(
            status_code=503,
            detail="Document cleanup is temporarily unavailable.",
        ) from exc

    # Delete database records only after blob deletion succeeds.
    delete_document_record(
        document_id=document_id,
        user_id=current_user["id"],
    )

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
    }


@router.post("/{document_id}/retry")
def retry_document_processing(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    document = get_document(
        document_id=document_id,
        user_id=current_user["id"],
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail="Only failed documents can be retried.",
        )

    process_document.delay(
        document_id,
        document["blob_name"],
    )

    updated = get_document(document_id, current_user["id"])
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found")
    updated.pop("blob_name", None)
    updated.pop("searchable_blob_name", None)
    return {
        **updated,
        "message": "Document processing has been queued.",
    }


class AskRequest(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )


@router.post("/ask")
def ask_documents(
    request: AskRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    try:
        enforce_rate_limit(
            http_request,
            "ask",
            settings["RATE_LIMIT_EXPENSIVE"],
            str(current_user["id"]),
        )
        return answer_question(
            question=request.question,
            user_id=current_user["id"],
            limit=request.limit,
        )
    except Exception as exc:
        logger.exception(
            "Failed to answer the question",
            extra={"exception":exc},
        )
        # Replace with your project's logger/error handler as it is added.
        raise HTTPException(
            status_code=500,
            detail="Failed to answer the question.",
        ) from exc

@router.post("/ask/{document_id}")
def ask_documents(
    document_id: int,
    request: AskRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    try:
        enforce_rate_limit(
            http_request,
            "ask",
            settings["RATE_LIMIT_EXPENSIVE"],
            str(current_user["id"]),
        )
        return answer_question(
            question=request.question,
            user_id=current_user["id"],
            limit=request.limit,
            document_id=document_id,
        )
    except Exception as exc:
        logger.exception(
            "Failed to answer the question",
            extra={"exception":exc},
        )
        # Replace with your project's logger/error handler as it is added.
        raise HTTPException(
            status_code=500,
            detail="Failed to answer the question.",
        ) from exc
