# reranker_extension_rag

## Reference sources

- https://github.com/deepset-ai/haystack
- Common reranker pipeline patterns.

## Scanner signals

- `requirements.txt` contains `sentence-transformers`.
- `config.yaml` contains a `cross-encoder` reranker model.
- `src/rerank.py` contains reranker extension evidence.

## Safety notes

- This fixture does not require network or model downloads.
- This fixture does not include real secrets.
- The reranker is an extension signal, not a baseline required slot.
