"""Qdrant vector storage for the RAG pipeline."""

import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION_NAME = "rag_documents"
VECTOR_SIZE = 384


class QdrantStore:
    def __init__(self) -> None:
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
        )

    def create_collection(self) -> None:
        collections = self.client.get_collections().collections
        existing = {collection.name for collection in collections}

        if COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def _point_id(self, document_id: str, chunk_id: int) -> str:
        """Create a deterministic UUID for each document chunk."""

        raw_id = f"{document_id}:{chunk_id}"

        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                raw_id,
            )
        )

    def upsert_chunks(
        self,
        vectors: list[list[float]],
        chunks: list[dict[str, Any]],
        document_id: str,
        filename: str,
    ) -> None:
        points = []

        for vector, chunk in zip(vectors, chunks):
            chunk_id = chunk["chunk_id"]

            point_id = self._point_id(
                document_id,
                chunk_id,
            )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_id": chunk_id,
                        "page_number": chunk["page_number"],
                        "text": chunk["text"],
                    },
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        document_id: str | None = None,
    ):
        query_filter = None

        if document_id:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

        return self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        ).points
