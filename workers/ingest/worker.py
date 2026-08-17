"""Redis-based document ingestion worker."""

import os
import tempfile

import psycopg
import redis
from dotenv import load_dotenv

from workers.ingest.downloader import download_document
from workers.ingest.processor import DocumentProcessor


load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ragdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "raguser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ragdevpass")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
)


def get_db_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def update_document(
    document_id: str,
    status: str,
    *,
    page_count=None,
    chunk_count=None,
    entity_count=None,
    error=None,
):
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE documents
            SET
                status = %s,
                page_count = COALESCE(%s, page_count),
                chunk_count = COALESCE(%s, chunk_count),
                entity_count = COALESCE(%s, entity_count),
                error = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                status,
                page_count,
                chunk_count,
                entity_count,
                error,
                document_id,
            ),
        )
        conn.commit()


def get_document(document_id: str):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, filename, s3_key
            FROM documents
            WHERE id = %s
            """,
            (document_id,),
        ).fetchone()

    return row


def process_job(document_id: str):
    print(f"[worker] Processing document: {document_id}")

    row = get_document(document_id)

    if row is None:
        print(f"[worker] Document not found: {document_id}")
        return

    _, filename, s3_key = row

    try:
        update_document(document_id, "processing")

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, filename)

            print(f"[worker] Downloading: {s3_key}")

            download_document(
                s3_key=s3_key,
                output_path=pdf_path,
            )

            print("[worker] Processing PDF...")

            processor = DocumentProcessor()

            result = processor.process(
                pdf_path=pdf_path,
                document_id=document_id,
                filename=filename,
            )

        update_document(
            document_id,
            "done",
            page_count=result["page_count"],
            chunk_count=result["chunk_count"],
            entity_count=result["entity_count"],
            error=None,
        )

        print(
            f"[worker] DONE: {document_id} | "
            f"pages={result['page_count']} | "
            f"chunks={result['chunk_count']}"
        )

    except Exception as exc:
        print(f"[worker] FAILED: {document_id}: {exc}")

        update_document(
            document_id,
            "failed",
            error=str(exc),
        )


def main():
    print("[worker] RAG ingestion worker started")
    print("[worker] Waiting for jobs on Redis queue: rag:jobs")

    while True:
        job = redis_client.blpop("rag:jobs", timeout=0)

        if job is None:
            continue

        _, document_id = job

        process_job(document_id)


if __name__ == "__main__":
    main()
