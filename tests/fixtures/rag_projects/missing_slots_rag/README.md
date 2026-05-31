# missing_slots_rag

## Reference sources

- Project-owned fixture based on `rag-core-v1` missing slot behavior.

## Scanner signals

- `requirements.txt` includes a minimal FastAPI app only.
- `src/app.py` exposes a query route but has no vector store, retriever, citation, guardrails, or observability evidence.

## Safety notes

- This fixture does not require network or runtime services.
- This fixture does not include real secrets.
- Missing RAG slots are intentional.
