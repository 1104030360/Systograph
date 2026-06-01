import faiss
from sentence_transformers import SentenceTransformer


def retrieve(question: str) -> list[int]:
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    vector = model.encode([question])
    index = faiss.IndexFlatL2(384)
    _distances, ids = index.search(vector, 3)
    return ids[0].tolist()
