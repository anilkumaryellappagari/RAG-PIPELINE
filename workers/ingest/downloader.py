"""Download documents from MinIO."""

import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

load_dotenv()

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = os.getenv("MINIO_PORT", "9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "rag-raw")

minio_client = Minio(
    f"{MINIO_HOST}:{MINIO_PORT}",
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=False,
)


def download_document(s3_key: str, output_path: str) -> str:
    """Download a PDF from MinIO to a local path."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    minio_client.fget_object(
        MINIO_BUCKET,
        s3_key,
        str(output),
    )

    return str(output)
