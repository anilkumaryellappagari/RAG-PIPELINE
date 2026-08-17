"""Phase 0, Spec items 2-3: FastAPI document upload and PostgreSQL/Redis job management."""

import os
import uuid
from contextlib import asynccontextmanager

import psycopg
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from minio import Minio

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ragdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "raguser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ragdevpass")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = os.getenv("MINIO_PORT", "9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "rag-raw")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
)

minio_client = Minio(
    f"{MINIO_HOST}:{MINIO_PORT}",
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=False,
)


def get_db_connection():
    """Create a PostgreSQL connection."""
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify required infrastructure when the API starts."""
    try:
        redis_client.ping()
        print("Redis connection: OK")
    except Exception as exc:
        print(f"Redis connection warning: {exc}")

    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        print("PostgreSQL connection: OK")
    except Exception as exc:
        print(f"PostgreSQL connection warning: {exc}")

    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
        print(f"MinIO bucket '{MINIO_BUCKET}': OK")
    except Exception as exc:
        print(f"MinIO connection warning: {exc}")

    yield


app = FastAPI(
    title="Local RAG Pipeline API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Return the basic API health status."""
    return {
        "status": "ok",
        "service": "rag-api",
    }


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF to MinIO and enqueue its document-processing job."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    document_id = uuid.uuid4()
    safe_filename = os.path.basename(file.filename)
    object_key = f"{document_id}/{safe_filename}"

    try:
        file_data = await file.read()

        if not file_data:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is empty",
            )

        # Store PDF in MinIO.
        from io import BytesIO

        minio_client.put_object(
            MINIO_BUCKET,
            object_key,
            BytesIO(file_data),
            length=len(file_data),
            content_type="application/pdf",
        )

        # Create the document job in PostgreSQL.
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents
                    (id, filename, s3_key, status)
                VALUES
                    (%s, %s, %s, 'queued')
                """,
                (
                    document_id,
                    safe_filename,
                    object_key,
                ),
            )
            conn.commit()

        # Send job to Redis.
        redis_client.rpush(
            "rag:jobs",
            str(document_id),
        )

        return {
            "doc_id": str(document_id),
            "filename": safe_filename,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {exc}",
        ) from exc



@app.get("/documents")
def list_documents():
    """Return all uploaded documents and their processing status."""

    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    filename,
                    s3_key,
                    status,
                    error,
                    page_count,
                    chunk_count,
                    entity_count,
                    created_at,
                    updated_at
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()

        columns = [
            "id",
            "filename",
            "s3_key",
            "status",
            "error",
            "page_count",
            "chunk_count",
            "entity_count",
            "created_at",
            "updated_at",
        ]

        documents = []

        for row in rows:
            document = dict(zip(columns, row))
            document["id"] = str(document["id"])
            documents.append(document)

        return {
            "count": len(documents),
            "documents": documents,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc


@app.get("/documents/{document_id}")
def get_document(document_id: str):
    """Return the complete processing state for one document."""

    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document UUID",
        ) from exc

    try:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    filename,
                    s3_key,
                    status,
                    error,
                    page_count,
                    chunk_count,
                    entity_count,
                    created_at,
                    updated_at
                FROM documents
                WHERE id = %s
                """,
                (parsed_id,),
            ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        columns = [
            "id",
            "filename",
            "s3_key",
            "status",
            "error",
            "page_count",
            "chunk_count",
            "entity_count",
            "created_at",
            "updated_at",
        ]

        result = dict(zip(columns, row))
        result["id"] = str(result["id"])

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

from pydantic import BaseModel
from retriever.rag import RAGPipeline


class QueryRequest(BaseModel):
    question: str
    limit: int = 5
    document_id: str | None = None


@app.post("/query")
def query_rag(request: QueryRequest):
    """Answer a question using retrieved document context."""

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    if request.limit < 1 or request.limit > 20:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 20",
        )

    try:
        rag = RAGPipeline()

        result = rag.answer(
            question=request.question,
            limit=request.limit,
            document_id=request.document_id,
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {exc}",
        ) from exc
