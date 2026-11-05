import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        ".env",
    )
)

MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

DIMENSIONS = int(
    os.getenv("EMBEDDING_DIMENSIONS", "3072")
)

client: genai.Client | None = None


def _get_client() -> genai.Client:
    global client

    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
        client = genai.Client(api_key=api_key)

    return client


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding for a single text."""

    if not text.strip():
        raise ValueError("Cannot embed empty text")

    response = _get_client().models.embed_content(
        model=MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=DIMENSIONS,
        ),
    )

    embedding = response.embeddings[0].values

    if len(embedding) != DIMENSIONS:
        raise ValueError(
            f"Expected {DIMENSIONS} dimensions, "
            f"received {len(embedding)}"
        )

    return embedding


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """Generate embeddings for multiple chunks."""

    return [
        generate_embedding(text)
        for text in texts
    ]
