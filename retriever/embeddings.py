"""Local text embeddings using FastEmbed."""

from fastembed import TextEmbedding


MODEL_NAME = "BAAI/bge-small-en-v1.5"


class Embedder:
    def __init__(self) -> None:
        self.model = TextEmbedding(model_name=MODEL_NAME)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate one embedding vector for each text."""
        return [vector.tolist() for vector in self.model.embed(texts)]

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a search query."""
        return next(self.model.embed([query])).tolist()
