import hashlib
import logging
import re
import uuid
from pathlib import Path

import pymupdf
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_connection
from app.core.rate_limit import enforce_rate_limit
from app.services.document_service import (
    delete_document_record,
    get_document,
    list_documents,
)
from app.services.embedding_service import (
    generate_embedding,
)
from app.services.rag_service import answer_question
from app.services.search_service import (
    DuplicateDocumentError,
    save_document,
    search_documents,
)
from app.workers.tasks import process_document
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
from pydantic import BaseModel, Field

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
            if pdf.page_count == 0:
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
        )

        # Queue background processing
        task = process_document.delay(
            document_id=document_id,
            blob_name=blob_name,
        )

        return {
            "document_id": document_id,
            "filename": safe_filename[:255],
            "status": "pending",
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
                    created_at
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
    }


# --------------------------------------------------
# Semantic search
# --------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )


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
        settings.AZURE_STORAGE_CONNECTION_STRING
    )

    blob_client = blob_service.get_blob_client(
        container=settings.AZURE_STORAGE_CONTAINER,
        blob=blob_name,
    )

    try:
        blob_client.delete_blob(delete_snapshots="include")
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

    return {
        "message": "Document processing has been queued.",
        "document_id": document_id,
        "status": "queued",
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
