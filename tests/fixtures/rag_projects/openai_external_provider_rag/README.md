# openai_external_provider_rag

## Reference sources

- https://github.com/run-llama/llama_index
- https://github.com/langchain-ai/langchain

## Scanner signals

- `.env.example` contains fake `OPENAI_API_KEY=sk-test-example`.
- `requirements.txt` contains OpenAI and LlamaIndex dependencies.
- `config.yaml` contains external embedding and LLM provider settings.
- `src/app.py` contains an external provider query route.

## Safety notes

- This fixture does not require network or OpenAI API access.
- This fixture does not include real secrets.
- The fake key is intentionally non-sensitive test data.
