import os
import re

import pymupdf  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pytesseract import Output


def _preprocess_scan(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    grayscale = ImageOps.grayscale(image)
    if grayscale.width < 1800:
        scale = 1800 / grayscale.width
        grayscale = grayscale.resize(
            (1800, round(grayscale.height * scale)),
            Image.Resampling.LANCZOS,
        )
    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(1.25)
    return grayscale.filter(ImageFilter.MedianFilter(size=3))


def _correct_orientation(image: Image.Image) -> Image.Image:
    try:
        osd = pytesseract.image_to_osd(image, output_type=Output.STRING)
        match = re.search(r"Rotate:\s*(\d+)", osd)
        rotation = int(match.group(1)) if match else 0
        return image.rotate(-rotation, expand=True) if rotation else image
    except (pytesseract.TesseractError, ValueError):
        return image


def _detect_layout_features(page: pymupdf.Page, image: Image.Image | None) -> dict:
    drawings = page.get_drawings()
    line_rects = [drawing.get("rect") for drawing in drawings if drawing.get("rect")]
    horizontal_lines = sum(
        1
        for drawing in drawings
        for item in drawing.get("items", [])
        if item[0] == "l" and abs(item[1].y - item[2].y) < 3
    )
    vertical_lines = sum(
        1
        for drawing in drawings
        for item in drawing.get("items", [])
        if item[0] == "l" and abs(item[1].x - item[2].x) < 3
    )
    tables = 1 if horizontal_lines >= 3 and vertical_lines >= 2 else 0
    annotations = []
    if tables and line_rects:
        rect = line_rects[0]
        annotations.append(
            {
                "type": "table",
                "x0": rect.x0,
                "y0": rect.y0,
                "x1": rect.x1,
                "y1": rect.y1,
            }
        )
    colored_pixels = 0
    if image is not None and image.mode != "L":
        rgb = image.convert("RGB")
        sample = list(rgb.resize((min(120, rgb.width), min(120, rgb.height))).getdata())
        colored_pixels = sum(
            max(pixel) - min(pixel) > 35 and max(pixel) > 80 for pixel in sample
        )
    stamp_like = 1 if colored_pixels > 30 else 0
    if stamp_like and image is not None:
        annotations.append(
            {
                "type": "stamp",
                "x0": page.rect.width * 0.65,
                "y0": page.rect.height * 0.55,
                "x1": page.rect.width * 0.95,
                "y1": page.rect.height * 0.9,
            }
        )
    return {
        "tables": tables,
        "stamp_like_regions": stamp_like,
        "annotations": annotations,
    }


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
            regions = []
            scan_image = None

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
                scan_image = image
                image = _correct_orientation(_preprocess_scan(image))

                ocr = pytesseract.image_to_data(
                    image,
                    lang=ocr_languages,
                    config=os.getenv("OCR_CONFIG", "--psm 3"),
                    output_type=Output.DICT,
                )
                words = []
                for index, value in enumerate(ocr["text"]):
                    value = value.strip()
                    if not value:
                        continue
                    words.append(value)
                    regions.append(
                        {
                            "text": value,
                            "x0": ocr["left"][index] * 72 / 300,
                            "y0": ocr["top"][index] * 72 / 300,
                            "x1": (ocr["left"][index] + ocr["width"][index]) * 72 / 300,
                            "y1": (ocr["top"][index] + ocr["height"][index]) * 72 / 300,
                            "confidence": max(0, float(ocr["conf"][index])) / 100,
                        }
                    )
                text = " ".join(words)
            else:
                for block in page.get_text("blocks"):
                    if len(block) >= 5 and block[4].strip():
                        regions.append(
                            {
                                "text": block[4].strip(),
                                "x0": block[0],
                                "y0": block[1],
                                "x1": block[2],
                                "y1": block[3],
                                "confidence": 1,
                            }
                        )

            extracted_pages.append(
                {
                    "page_number": page_index + 1,
                    "text": text,
                    "regions": regions,
                    "ocr_confidence": (
                        sum(region["confidence"] for region in regions) / len(regions)
                        if regions else None
                    ),
                    "uncertain_regions": sum(
                        region["confidence"] < 0.65 for region in regions
                    ),
                    "layout_features": _detect_layout_features(page, scan_image),
                }
            )

    return extracted_pages


def create_searchable_pdf(
    source_path: str,
    output_path: str,
    pages: list[dict],
) -> None:
    """Add an invisible OCR text layer while preserving the original page artwork."""
    with pymupdf.open(source_path) as document:
        for page_data, page in zip(pages, document):
            if not page_data.get("regions"):
                continue
            for region in page_data["regions"]:
                rect = pymupdf.Rect(
                    region["x0"],
                    region["y0"],
                    region["x1"],
                    region["y1"],
                )
                page.insert_textbox(
                    rect,
                    region["text"],
                    fontsize=max(5, min(18, rect.height * 0.8)),
                    fontname="helv",
                    render_mode=3,
                    overlay=True,
                )
        document.save(output_path, garbage=4, deflate=True)
