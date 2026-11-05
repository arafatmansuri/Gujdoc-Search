import fitz  # PyMuPDF
import pytesseract

from PIL import Image


def extract_pdf_text(
    pdf_path: str,
    ocr_languages: str = "guj+eng",
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

    extracted_pages = []

    with fitz.open(pdf_path) as document:

        for page_index, page in enumerate(document):

            # Attempt direct text extraction
            text = page.get_text("text").strip()

            # Use OCR if the page has little or no text
            if len(text) < 30:

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(300 / 72, 300 / 72),
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


def test_pdf_extraction():
    pdf_path = "tests/sample_doc.pdf"

    pages = extract_pdf_text(pdf_path)

    assert len(pages) > 0

    for page in pages:
        assert "page_number" in page
        assert "text" in page

    print(f"Extracted {len(pages)} pages")

    for page in pages:
        print(f"\nPage {page['page_number']}")
        print(page["text"][:500])


if __name__ == "__main__":
    test_pdf_extraction()
