import os
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
)
from pydantic import BaseModel, Field

from azure.storage.blob import BlobServiceClient

from app.core.database import get_connection
from app.services.search_service import (
    save_document,
    search_documents,
)
from app.services.embedding_service import (
    generate_embedding,
)
from app.workers.tasks import process_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

MAX_UPLOAD_SIZE = int(
    os.getenv("MAX_UPLOAD_SIZE_BYTES", "52428800")
)


# --------------------------------------------------
# Upload document
# --------------------------------------------------

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
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

    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

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

    connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING"
    )

    container_name = os.getenv(
        "AZURE_STORAGE_CONTAINER"
    )

    if not connection_string or not container_name:
        raise HTTPException(
            status_code=500,
            detail="Azure configuration missing",
        )

    blob_name = (
        f"documents/{uuid.uuid4().hex}.pdf"
    )

    blob_service = (
        BlobServiceClient.from_connection_string(
            connection_string
        )
    )

    blob_client = (
        blob_service
        .get_container_client(container_name)
        .get_blob_client(blob_name)
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
            filename=file.filename,
            blob_name=blob_name,
        )

        # Queue background processing
        task = process_document.delay(
            document_id=document_id,
            blob_name=blob_name,
        )

        return {
            "document_id": document_id,
            "filename": file.filename,
            "status": "pending",
            "task_id": task.id,
            "message": "Document queued for processing",
        }

    except Exception as exc:

        # Remove uploaded blob if database/task setup fails
        try:
            blob_client.delete_blob()
        except Exception:
            pass

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
                pass

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
    document_id: int,
):
    """Retrieve document processing status."""

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    filename,
                    status,
                    created_at
                FROM documents
                WHERE id = %s
                """,
                (document_id,),
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
):
    """Search document chunks using Gemini embeddings."""

    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    try:
        query_embedding = generate_embedding(query)

        results = search_documents(
            query_embedding=query_embedding,
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
