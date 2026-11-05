import os

import psycopg
from pgvector.psycopg import register_vector


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Create a PostgreSQL connection."""

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing")

    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)

    return conn


def initialize_database():
    """Create the required tables."""

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;

                CREATE TABLE IF NOT EXISTS documents (
                    id BIGSERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    blob_name TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMPTZ
                        DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    document_id BIGINT NOT NULL
                        REFERENCES documents(id)
                        ON DELETE CASCADE,
                    page_number INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(3072),
                    created_at TIMESTAMPTZ
                        DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(document_id, chunk_index)
                );
                
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS user_id BIGINT
                REFERENCES users(id)
                ON DELETE SET NULL;

            """)

        conn.commit()
