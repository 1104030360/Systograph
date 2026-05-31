# pgvector_openai_rag

## Reference sources

- https://github.com/open-webui/open-webui
- https://github.com/langgenius/dify

## Scanner signals

- `docker-compose.yml` contains PostgreSQL with pgvector.
- `.env.example` contains fake `DATABASE_URL` and `OPENAI_API_KEY=sk-test-example`.
- `requirements.txt` contains `pgvector`, `psycopg`, and `openai`.
- `src/retriever.py` contains SQL-backed vector retrieval.

## Safety notes

- This fixture does not require network, Docker, Postgres, or OpenAI to run.
- This fixture does not include real secrets.
- The database URL uses fake local credentials.
