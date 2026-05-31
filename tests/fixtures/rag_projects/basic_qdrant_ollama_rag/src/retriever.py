import ollama
from qdrant_client import QdrantClient

COLLECTION = "health_notes"


def embed_query(question: str) -> list[float]:
    response = ollama.embeddings(model="nomic-embed-text", prompt=question)
    return response["embedding"]


def retrieve_context(question: str) -> list[str]:
    client = QdrantClient(url="http://localhost:6333")
    vector = embed_query(question)
    results = client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=3,
    )
    return [hit.payload["text"] for hit in results]
