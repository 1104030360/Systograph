from fastapi import FastAPI
from retriever import retrieve_context

app = FastAPI()


@app.post("/query")
def query(payload: dict[str, str]) -> dict[str, object]:
    question = payload["question"]
    documents = retrieve_context(question)
    return {"answer": "synthetic local answer", "documents": documents}
