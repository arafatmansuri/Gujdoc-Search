import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

results = {}


def check(name, fn):
    """Run an independent connection check."""
    try:
        message = fn()
        results[name] = ("PASS", message)
    except Exception as exc:
        results[name] = ("FAIL", str(exc))


# --------------------------------------------------
# PostgreSQL + pgvector
# --------------------------------------------------

def check_postgres():
    import psycopg

    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is missing")

    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]

            cur.execute(
                "SELECT EXISTS "
                "(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            vector_enabled = cur.fetchone()[0]

    if not vector_enabled:
        raise RuntimeError(
            "Connected, but pgvector extension is not enabled"
        )

    return f"Connected; pgvector enabled; {version.split(',')[0]}"


# --------------------------------------------------
# Redis
# --------------------------------------------------

def check_redis():
    import redis

    url = os.getenv("REDIS_URL")
    if not url:
        raise ValueError("REDIS_URL is missing")

    client = redis.Redis.from_url(
        url,
        socket_connect_timeout=10,
        socket_timeout=10,
        decode_responses=True,
    )

    try:
        if client.ping():
            return "Redis PING successful"
        raise RuntimeError("Redis PING returned False")
    finally:
        client.close()


# --------------------------------------------------
# Azure Blob Storage
# --------------------------------------------------

def check_azure():
    from azure.storage.blob import BlobServiceClient

    connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING"
    )
    container_name = os.getenv("AZURE_STORAGE_CONTAINER")

    if not connection_string:
        raise ValueError(
            "AZURE_STORAGE_CONNECTION_STRING is missing"
        )

    if not container_name:
        raise ValueError("AZURE_STORAGE_CONTAINER is missing")

    service = BlobServiceClient.from_connection_string(
        connection_string
    )

    container = service.get_container_client(container_name)

    # Verify container access
    container.get_container_properties()

    # Verify upload and delete permissions
    blob_name = f"connection-check/{os.urandom(8).hex()}.txt"
    blob = container.get_blob_client(blob_name)

    try:
        blob.upload_blob(
            b"Gujdoc connection check",
            overwrite=False,
        )
    finally:
        try:
            blob.delete_blob()
        except Exception:
            pass

    return f"Container '{container_name}' accessible"


# --------------------------------------------------
# Google Gemini
# --------------------------------------------------

def check_gemini():
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv(
        "GEMINI_EMBEDDING_MODEL",
        "gemini-embedding-001",
    )
    expected_dimensions = int(
        os.getenv("EMBEDDING_DIMENSIONS", "3072")
    )

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.embed_content(
            model=model,
            contents="Gujdoc connection test",
            config=types.EmbedContentConfig(
                output_dimensionality=expected_dimensions,
            ),
        )

        embedding = response.embeddings[0].values
        actual_dimensions = len(embedding)

        if actual_dimensions != expected_dimensions:
            raise RuntimeError(
                f"Expected {expected_dimensions} dimensions, "
                f"received {actual_dimensions}"
            )

        return (
            f"Embedding successful; "
            f"{actual_dimensions} dimensions"
        )
    finally:
        client.close()


# --------------------------------------------------
# Tesseract OCR
# --------------------------------------------------

def check_tesseract_old():
    import pytesseract
    from PIL import Image, ImageDraw

    tesseract_cmd = os.getenv("TESSERACT_CMD")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = (
            tesseract_cmd
        )

    # Verify executable
    version = pytesseract.get_tesseract_version()

    # Verify Gujarati and English language data
    languages = pytesseract.get_languages(config="")

    required = {"guj", "eng"}
    missing = required - set(languages)

    if missing:
        raise RuntimeError(
            f"Missing language data: {', '.join(missing)}"
        )

    # Generate a simple test image
    image = Image.new("RGB", (500, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 30), "GUJDOC OCR TEST 123", fill="black")

    extracted_text = pytesseract.image_to_string(
        image,
        lang="eng",
    )

    if "GUJDOC" not in extracted_text.upper():
        raise RuntimeError(
            "Tesseract ran, but failed to recognize test text"
        )

    return f"OCR working; Tesseract {version}"

def check_tesseract():
    import pytesseract
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    tesseract_cmd = os.getenv("TESSERACT_CMD")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # Check Tesseract executable
    version = pytesseract.get_tesseract_version()

    # Check installed language data
    languages = pytesseract.get_languages(config="")

    required = {"guj", "eng"}
    missing = required - set(languages)

    if missing:
        raise RuntimeError(
            f"Missing language data: {', '.join(missing)}"
        )

    # Create a high-resolution test image
    image = Image.new("RGB", (1200, 250), "white")
    draw = ImageDraw.Draw(image)

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    font = None

    for font_path in font_paths:
        if Path(font_path).exists():
            font = ImageFont.truetype(font_path, 72)
            break

    if font is None:
        font = ImageFont.load_default()

    draw.text(
        (40, 60),
        "GUJDOC OCR TEST 123",
        fill="black",
        font=font,
    )

    # Preprocess image
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)

    # OCR with English language
    extracted_text = pytesseract.image_to_string(
        image,
        lang="eng",
        config="--psm 6",
    )

    normalized = extracted_text.upper().replace(" ", "")

    if "GUJDOC" not in normalized:
        raise RuntimeError(
            f"OCR recognition failed. Extracted: {extracted_text!r}"
        )

    return (
        f"OCR working; Tesseract {version}; "
        f"Gujarati and English language data available"
    )



# --------------------------------------------------
# Run all checks
# --------------------------------------------------

if __name__ == "__main__":
    print("\nGUJDOC BACKEND CONNECTION CHECK")
    print("=" * 45)

    # check("PostgreSQL + pgvector", check_postgres)
    # check("Redis", check_redis)
    # check("Azure Blob Storage", check_azure)
    # check("Google Gemini", check_gemini)
    check("Tesseract OCR", check_tesseract)

    print()

    for service, (status, message) in results.items():
        print(f"[{status}] {service}")
        print(f"       {message}\n")

    passed = sum(
        status == "PASS"
        for status, _ in results.values()
    )

    total = len(results)

    print("=" * 45)
    print(f"RESULT: {passed}/{total} services ready")

    sys.exit(0 if passed == total else 1)
