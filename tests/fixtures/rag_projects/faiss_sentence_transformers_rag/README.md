# faiss_sentence_transformers_rag

## Reference sources

- https://github.com/zylon-ai/private-gpt
- https://github.com/deepset-ai/haystack

## Scanner signals

- `requirements.txt` contains `faiss-cpu` and `sentence-transformers`.
- `config.yaml` contains a local FAISS index path and BGE embedding model.
- `src/retriever.py` contains `faiss.IndexFlatL2` and local embedding signals.

## Safety notes

- This fixture does not require network or model downloads.
- This fixture does not include real secrets.
- No FAISS index binary or model weights are checked in.
