from fastapi import FastAPI

app = FastAPI()


@app.post("/query")
def query(payload: dict[str, str]) -> dict[str, str]:
    return {"answer": f"No retrieval configured for {payload['question']}"}
