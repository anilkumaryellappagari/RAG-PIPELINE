"""Document processing pipeline."""

from retriever.embeddings import Embedder
from retriever.qdrant_store import QdrantStore

from workers.ingest.chunker import chunk_pages
from workers.ingest.parser import extract_pdf


class DocumentProcessor:
    def __init__(self) -> None:
        self.embedder = Embedder()
        self.qdrant = QdrantStore()
        self.qdrant.create_collection()

    def process(
        self,
        pdf_path: str,
        document_id: str,
        filename: str,
    ) -> dict:
        """Extract, chunk, embed and store a document."""

        extracted = extract_pdf(pdf_path)

        chunks = chunk_pages(extracted["pages"])

        if not chunks:
            raise ValueError("No text could be extracted from the PDF")

        texts = [chunk["text"] for chunk in chunks]

        vectors = self.embedder.embed_texts(texts)

        self.qdrant.upsert_chunks(
            vectors=vectors,
            chunks=chunks,
            document_id=document_id,
            filename=filename,
        )

        return {
            "page_count": extracted["page_count"],
            "chunk_count": len(chunks),
            "entity_count": 0,
        }
