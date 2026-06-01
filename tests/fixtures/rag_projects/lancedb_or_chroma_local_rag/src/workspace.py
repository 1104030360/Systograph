import lancedb
import ollama


def workspace_search(question: str) -> list[dict[str, object]]:
    embedding = ollama.embeddings(model="nomic-embed-text", prompt=question)
    db = lancedb.connect("storage/lancedb")
    table = db.open_table("local_health_docs")
    return table.search(embedding["embedding"]).limit(3).to_list()
