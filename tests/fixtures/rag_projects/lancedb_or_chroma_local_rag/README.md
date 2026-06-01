# lancedb_or_chroma_local_rag

## Reference sources

- https://github.com/Mintplex-Labs/anything-llm
- https://github.com/open-webui/open-webui
- https://github.com/QuivrHQ/quivr

## Scanner signals

- `requirements.txt` contains `lancedb`.
- `config.yaml` contains workspace, knowledge base, local DB path, and local embedding provider settings.
- `src/workspace.py` contains LanceDB table and workspace retrieval signals.

## Safety notes

- This fixture does not require network or local DB runtime.
- This fixture does not include real secrets.
- No LanceDB data directory is checked in.
