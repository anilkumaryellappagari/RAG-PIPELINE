"""Text chunking for the RAG ingestion pipeline."""

from typing import Any


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict[str, Any]]:
    """Split page text into overlapping chunks while preserving page metadata."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be >= 0 and smaller than chunk_size"
        )

    chunks = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"].strip()

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "chunk_id": len(chunks),
                        "page_number": page_number,
                        "text": chunk_text,
                    }
                )

            if end >= len(text):
                break

            start = end - chunk_overlap

    return chunks
