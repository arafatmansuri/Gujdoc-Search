import os

import pymupdf  # PyMuPDF
import pytesseract
from PIL import Image


def extract_pdf_text(
    pdf_path: str,
    ocr_languages: str | None = None,
) -> list[dict]:
    """
    Extract text from a PDF.

    Digital PDFs:
        Extract text directly using PyMuPDF.

    Scanned PDFs:
        Render pages as images and extract text using Tesseract.

    Returns:
        [
            {
                "page_number": 1,
                "text": "Extracted text..."
            }
        ]
    """

    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    ocr_languages = ocr_languages or os.getenv(
        "OCR_LANGUAGES",
        "guj+eng",
    )

    extracted_pages = []

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            # Attempt direct text extraction
            text = page.get_text("text").strip()

            # Use OCR if the page has little or no text
            if len(text) < 30:
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(300 / 72, 300 / 72),
                    alpha=False,
                )

                image = Image.frombytes(
                    "RGB",
                    [pix.width, pix.height],
                    pix.samples,
                )

                text = pytesseract.image_to_string(
                    image,
                    lang=ocr_languages,
                    config="--psm 3",
                ).strip()

            extracted_pages.append(
                {
                    "page_number": page_index + 1,
                    "text": text,
                }
            )

    return extracted_pages
