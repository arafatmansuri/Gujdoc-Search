import logging
import os
import tempfile

from azure.storage.blob import BlobServiceClient

from app.services.embedding_service import generate_embedding
from app.services.pdf_extractor import extract_pdf_text
from app.services.search_service import (
    save_chunks,
    update_document_status,
)
from app.services.text_chunker import chunk_text
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=3,
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
        update_document_status(
            document_id,
            "processing",
        )

        connection_string = os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING"
        )

        container_name = os.getenv(
            "AZURE_STORAGE_CONTAINER"
        )

        if not connection_string or not container_name:
            raise ValueError(
                "Azure configuration is missing"
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

            chunks_to_save = []
            chunk_index = 0

            # Process each page
            for page in pages:

                page_chunks = chunk_text(
                    page["text"]
                )

                for content in page_chunks:

                    embedding = generate_embedding(
                        content
                    )

                    chunks_to_save.append(
                        {
                            "page_number": page[
                                "page_number"
                            ],
                            "chunk_index": chunk_index,
                            "content": content,
                            "embedding": embedding,
                        }
                    )

                    chunk_index += 1

            # Store chunks and embeddings
            save_chunks(
                document_id,
                chunks_to_save,
            )

            update_document_status(
                document_id,
                "completed",
            )

            return {
                "document_id": document_id,
                "total_pages": len(pages),
                "total_chunks": len(chunks_to_save),
                "status": "completed",
            }

        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    except Exception as exc:
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
                countdown=30,
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
