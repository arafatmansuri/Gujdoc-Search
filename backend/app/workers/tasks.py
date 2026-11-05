import logging
import os
import tempfile
import uuid

from azure.storage.blob import BlobServiceClient, ContentSettings

from app.services.document_service import (
    mark_processing_completed,
    mark_processing_error,
    mark_processing_started,
    set_searchable_blob,
    update_document_metadata,
    update_ocr_quality,
)
from app.services.embedding_service import generate_embedding
from app.services.metadata_extractor import extract_metadata
from app.services.pdf_extractor import create_searchable_pdf, extract_pdf_text
from app.services.search_service import (
    clear_chunks,
    get_document_for_processing,
    save_chunks,
    save_regions,
    update_document_status,
)
from app.services.text_chunker import chunk_text
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=3,
    default_retry_delay=30,
)
def process_document(
    self,
    document_id: int,
    blob_name: str,
):
    """
    Process an uploaded PDF from Azure Blob Storage.
    """

    try:
        document = get_document_for_processing(document_id, blob_name)
        if document is None:
            logger.warning(
                "Skipping stale document task",
                extra={"document_id": document_id},
            )
            return {"document_id": document_id, "status": "stale"}

        update_document_status(
            document_id,
            "processing",
        )
        mark_processing_started(document_id)

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        container_name = os.getenv("AZURE_STORAGE_CONTAINER")

        if not connection_string or not container_name:
            raise ValueError("Azure configuration is missing")

        blob_service = BlobServiceClient.from_connection_string(connection_string)

        blob_client = blob_service.get_container_client(container_name).get_blob_client(
            blob_name
        )

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temp_file:
            pdf_path = temp_file.name

        try:
            # Download PDF
            with open(pdf_path, "wb") as file:
                download = blob_client.download_blob()
                file.write(download.readall())

            # Extract text
            pages = extract_pdf_text(pdf_path)
            update_document_metadata(document_id, extract_metadata(pages))
            quality_pages = [page for page in pages if page["ocr_confidence"] is not None]
            update_ocr_quality(
                document_id,
                (
                    sum(page["ocr_confidence"] for page in quality_pages)
                    / len(quality_pages)
                    if quality_pages
                    else None
                ),
                sum(page["uncertain_regions"] for page in pages),
                {
                    **{
                        feature: sum(
                            page["layout_features"].get(feature, 0) for page in pages
                        )
                        for feature in ("tables", "stamp_like_regions")
                    },
                    "annotations": [
                        {
                            **annotation,
                            "page_number": page["page_number"],
                        }
                        for page in pages
                        for annotation in page["layout_features"].get("annotations", [])
                    ],
                },
            )
            searchable_path = f"{pdf_path}.searchable.pdf"
            create_searchable_pdf(pdf_path, searchable_path, pages)
            searchable_blob_name = f"searchable/{uuid.uuid4().hex}.pdf"
            with open(searchable_path, "rb") as searchable_file:
                blob_service.get_container_client(container_name).get_blob_client(
                    searchable_blob_name
                ).upload_blob(
                    searchable_file,
                    overwrite=False,
                    content_settings=ContentSettings(content_type="application/pdf"),
                )
            set_searchable_blob(document_id, searchable_blob_name)

            chunks_to_save = []
            chunk_index = 0

            # Process each page
            for page in pages:
                page_chunks = chunk_text(page["text"])

                for content in page_chunks:
                    embedding = generate_embedding(content)

                    chunks_to_save.append(
                        {
                            "page_number": page["page_number"],
                            "chunk_index": chunk_index,
                            "content": content,
                            "embedding": embedding,
                        }
                    )

                    chunk_index += 1

            # Rebuild chunks so retries cannot leave stale embeddings behind.
            clear_chunks(document_id)
            save_regions(document_id, pages)
            save_chunks(
                document_id,
                chunks_to_save,
            )

            update_document_status(
                document_id,
                "completed",
            )
            mark_processing_completed(document_id)

            return {
                "document_id": document_id,
                "total_pages": len(pages),
                "total_chunks": len(chunks_to_save),
                "status": "completed",
            }

        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            searchable_path = f"{pdf_path}.searchable.pdf"
            if os.path.exists(searchable_path):
                os.remove(searchable_path)

    except Exception as exc:
        try:
            mark_processing_error(document_id, str(exc))
        except Exception:
            logger.exception("Could not save processing error", extra={"document_id": document_id})
        # Keep the document visible as processing while Celery retries. The
        # API uses this status for polling, so marking it failed here makes a
        # transient failure look permanent before the retry is attempted.
        if self.request.retries < self.max_retries:
            logger.warning(
                "Document processing failed; retrying",
                extra={
                    "document_id": document_id,
                    "blob_name": blob_name,
                    "retry": self.request.retries + 1,
                    "max_retries": self.max_retries,
                },
                exc_info=True,
            )
            raise self.retry(
                exc=exc,
                countdown=min(300, 30 * (2**self.request.retries)),
            )

        try:
            update_document_status(
                document_id,
                "failed",
            )
        except Exception:
            logger.exception(
                "Could not mark document processing as failed",
                extra={"document_id": document_id},
            )

        logger.exception(
            "Document processing failed permanently",
            extra={
                "document_id": document_id,
                "blob_name": blob_name,
            },
        )
        raise
