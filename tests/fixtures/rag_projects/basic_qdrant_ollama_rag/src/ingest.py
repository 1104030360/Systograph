from qdrant_client import QdrantClient

COLLECTION = "health_notes"


def ingest_documents(chunks: list[str]) -> None:
    client = QdrantClient(url="http://localhost:6333")
    points = [
        {"id": index, "vector": [0.0, 0.1], "payload": {"text": text}}
        for index, text in enumerate(chunks)
    ]
    client.upsert(collection_name=COLLECTION, points=points)
