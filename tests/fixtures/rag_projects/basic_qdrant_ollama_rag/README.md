# basic_qdrant_ollama_rag

## Reference sources

- https://github.com/AllAboutAI-YT/easy-local-rag
- https://github.com/qdrant/examples
- https://github.com/Mintplex-Labs/anything-llm

## Scanner signals

- `docker-compose.yml` contains `qdrant/qdrant` and `ollama/ollama` services.
- `requirements.txt` contains `qdrant-client`, `ollama`, and `fastapi`.
- `.env.example` contains local provider settings and fake values.
- `src/retriever.py` contains Qdrant vector retrieval and Ollama embedding signals.
- `src/app.py` contains a FastAPI query route.

## Safety notes

- This fixture does not require network, Docker, Ollama, or Qdrant to run.
- This fixture does not include real secrets.
- This fixture is project-owned synthetic code, not a vendored external repo.
