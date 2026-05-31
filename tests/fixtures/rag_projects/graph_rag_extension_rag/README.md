# graph_rag_extension_rag

## Reference sources

- https://github.com/microsoft/graphrag
- https://github.com/HKUDS/LightRAG
- https://github.com/neo4j/neo4j-graphrag-python

## Scanner signals

- `requirements.txt` contains `graphrag`, `neo4j`, and `networkx`.
- `config.yaml` contains `knowledge_graph`, `graph_store`, and `graph_retriever` settings.
- `src/graph_retriever.py` contains entity extraction, graph traversal, and hybrid graph/vector retrieval signals.

## Safety notes

- This fixture does not require network, Neo4j, or GraphRAG runtime.
- This fixture does not include real secrets.
- No graph database dump, embeddings, or model artifacts are checked in.
- This fixture is a project-owned synthetic GraphRAG extension sample.
