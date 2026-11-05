import re
from datetime import datetime


_REFERENCE_PATTERNS = (
    r"\b(?:No\.?| નંબર|क्रमांक|ક્રમાંક)\s*[:./-]?\s*([A-Z0-9અ-હઆ-ઔ./-]{3,})",
    r"\b(?:Ref(?:erence)?\.?)\s*[:./-]?\s*([A-Z0-9અ-હઆ-ઔ./-]{3,})",
)
_DATE_PATTERNS = (
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
)
_LABELS = {
    "subject": ("subject", "વિષય", "વિષયઃ"),
    "issuing_office": (
        "issuing office",
        "office",
        "from",
        "કાર્યાલય",
        "કચેરી",
    ),
}


def _label_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?im)^\s*(?:{label_pattern})\s*[:.-]\s*(.+?)\s*$",
        text,
    )
    return match.group(1).strip() if match else None


def _normalise_date(value: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_metadata(pages: list[dict]) -> dict:
    """Extract conservative metadata candidates from the first pages of a document.

    Values are candidates only; the review workflow must verify them before they
    are treated as authoritative metadata.
    """

    text = "\n".join(str(page.get("text", "")) for page in pages[:3])
    document_number = None
    for pattern in _REFERENCE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            document_number = match.group(1).strip(" .:-")
            break

    document_date = None
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            document_date = _normalise_date(match.group(1))
            if document_date:
                break

    subject = _label_value(text, _LABELS["subject"])
    issuing_office = _label_value(text, _LABELS["issuing_office"])

    references = []
    for pattern in _REFERENCE_PATTERNS:
        references.extend(match.group(1).strip(" .:-") for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    references = list(dict.fromkeys(references))

    values = {
        "document_number": document_number,
        "document_date": document_date,
        "subject": subject,
        "issuing_office": issuing_office,
        "referenced_documents": references,
    }
    populated = sum(value is not None and value != [] for value in values.values())
    values["confidence"] = round(populated / 5, 2)
    values["status"] = "needs_review" if populated else "unavailable"
    return values
