# Public Reference Repositories

These repositories are useful input-layer references for KAI-Mind. They show the kinds of files, configs, ports, services, and RAG structures the scanner should eventually understand.

## Open WebUI

- URL: https://github.com/open-webui/open-webui
- Why it matters: Large self-hosted AI platform with Ollama/OpenAI-compatible API support, Local RAG, many vector database options, Docker files, `.env.example`, and web UI configuration.
- KAI-Mind learning target:
  - Docker Compose scanning.
  - `.env` and provider config scanning.
  - RAG/vector DB configuration patterns.
  - Local Web UI exposure and port patterns.

## AnythingLLM

- URL: https://github.com/Mintplex-Labs/anything-llm
- Why it matters: Privacy-first local AI app with documents, agents, vector DB integrations, providers, workspace settings, and local/desktop deployment concerns.
- KAI-Mind learning target:
  - Document ingestion configuration.
  - Agent and tool configuration.
  - Provider and vector database settings.
  - Privacy and telemetry-related configuration surfaces.

## PrivateGPT

- URL: https://github.com/zylon-ai/private-gpt
- Why it matters: Private document assistant with multiple `settings-*.yaml` files, Dockerfile variants, `docker-compose.yaml`, Ollama settings, and Qdrant-related setup.
- KAI-Mind learning target:
  - Multiple settings profile scanning.
  - Qdrant / vector store readiness.
  - Local vs cloud provider mode detection.
  - RAG settings normalization.

## local-rag-engine

- URL: https://github.com/noorjotk/local-rag-engine
- Why it matters: Small and readable local RAG example using FastAPI, Streamlit, Qdrant, Ollama, Docker Compose, and common ports.
- KAI-Mind learning target:
  - Good sample project candidate.
  - System Map Builder smoke test.
  - End-to-end RAG stack detection.
  - Qdrant and Ollama service mapping.

## local-ai-packaged

- URL: https://github.com/coleam00/local-ai-packaged
- Why it matters: Docker Compose local AI stack containing Ollama, Open WebUI, n8n, Supabase, and Qdrant. It also documents Mac-specific `host.docker.internal` handling for local Ollama.
- KAI-Mind learning target:
  - Multi-service Docker Compose scanning.
  - macOS local runtime detection.
  - Qdrant URL and API key config patterns.
  - Agent/workflow tool risk surfaces such as n8n file and command nodes.

## ollama-docker

- URL: https://github.com/wolffaxn/ollama-docker
- Why it matters: LlamaIndex + Ollama + Qdrant + Open WebUI stack with ingestion and query scripts.
- KAI-Mind learning target:
  - RAG pipeline input/output flow.
  - Ingestion script detection.
  - Open WebUI connection settings.
  - Qdrant and Ollama service topology.

## RAGFlow

- URL: https://github.com/infiniflow/ragflow
- Why it matters: Mature RAG and agent system with self-hosting, document parsing, chunking, citation, agent, and Docker architecture.
- KAI-Mind learning target:
  - Mature RAG architecture vocabulary.
  - Citation and chunk traceability.
  - Large repo scanning considerations.
  - Separation between RAG workflow and release readiness checks.

## How to Use These References

Do not copy architecture wholesale. Use them to build scanner fixtures and test cases:

- `docker-compose.yml` examples.
- `.env.example` and config examples.
- Qdrant / vector DB settings.
- Ollama endpoint settings.
- App/API port exposure examples.
- Agent tool or workflow config examples.
