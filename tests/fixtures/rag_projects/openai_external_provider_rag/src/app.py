from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()


@app.post("/ask")
def ask(payload: dict[str, str]) -> dict[str, str]:
    client = OpenAI(base_url="https://api.openai.example/v1")
    client.embeddings.create(
        model="text-embedding-3-small",
        input=payload["question"],
    )
    return {"answer": "synthetic external provider answer"}
