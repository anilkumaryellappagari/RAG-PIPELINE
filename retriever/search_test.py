from retriever.embeddings import Embedder
from retriever.qdrant_store import QdrantStore


query = "What agents are included in this project?"

embedder = Embedder()
query_vector = embedder.embed_query(query)

store = QdrantStore()
results = store.search(query_vector, limit=5)

print()
print("=" * 80)
print(f"QUERY: {query}")
print(f"RESULTS: {len(results)}")
print("=" * 80)

for i, result in enumerate(results, start=1):
    payload = result.payload

    print()
    print("-" * 80)
    print(f"RESULT {i}")
    print(f"Score     : {result.score:.4f}")
    print(f"Document  : {payload.get('filename')}")
    print(f"Page      : {payload.get('page_number')}")
    print(f"Chunk     : {payload.get('chunk_id')}")
    print("-" * 80)
    print(payload.get("text", "")[:1000])

print()
