from app.services.metadata_extractor import extract_metadata


def test_extracts_mixed_language_metadata():
    metadata = extract_metadata(
        [
            {
                "page_number": 1,
                "text": (
                    "No: GAD/2026/041\n"
                    "Date: 05/11/2026\n"
                    "Subject: Digitisation of records\n"
                    "કચેરી: General Administration Department\n"
                    "Ref: IT/12/2025"
                ),
            }
        ]
    )

    assert metadata["document_number"] == "GAD/2026/041"
    assert metadata["document_date"] == "2026-11-05"
    assert metadata["subject"] == "Digitisation of records"
    assert metadata["issuing_office"] == "General Administration Department"
    assert "IT/12/2025" in metadata["referenced_documents"]
    assert metadata["status"] == "needs_review"
