# 公開參考 Repositories

這些 repositories 適合拿來研究 KAI-Mind 的 input layer。它們展示了 scanner 未來會遇到的檔案、config、ports、services 與 RAG 結構。

## Open WebUI

- URL: https://github.com/open-webui/open-webui
- 為什麼重要：大型 self-hosted AI platform，支援 Ollama / OpenAI-compatible API、Local RAG、多種 vector database、Docker files、`.env.example` 與 Web UI configuration。
- KAI-Mind 可學習：
  - Docker Compose scanning。
  - `.env` 與 provider config scanning。
  - RAG / vector DB configuration patterns。
  - Local Web UI exposure 與 port patterns。

## AnythingLLM

- URL: https://github.com/Mintplex-Labs/anything-llm
- 為什麼重要：privacy-first local AI app，包含 documents、agents、vector DB integrations、providers、workspace settings 與 local/desktop deployment concerns。
- KAI-Mind 可學習：
  - Document ingestion configuration。
  - Agent 與 tool configuration。
  - Provider 與 vector database settings。
  - Privacy 與 telemetry 相關 configuration surfaces。

## PrivateGPT

- URL: https://github.com/zylon-ai/private-gpt
- 為什麼重要：private document assistant，包含多個 `settings-*.yaml`、Dockerfile variants、`docker-compose.yaml`、Ollama settings 與 Qdrant setup。
- KAI-Mind 可學習：
  - 多 settings profile scanning。
  - Qdrant / vector store readiness。
  - Local vs cloud provider mode detection。
  - RAG settings normalization。

## local-rag-engine

- URL: https://github.com/noorjotk/local-rag-engine
- 為什麼重要：小型且容易閱讀的 local RAG 範例，使用 FastAPI、Streamlit、Qdrant、Ollama、Docker Compose 與常見 ports。
- KAI-Mind 可學習：
  - 作為 sample project candidate。
  - System Map Builder smoke test。
  - End-to-end RAG stack detection。
  - Qdrant 與 Ollama service mapping。

## local-ai-packaged

- URL: https://github.com/coleam00/local-ai-packaged
- 為什麼重要：Docker Compose local AI stack，包含 Ollama、Open WebUI、n8n、Supabase 與 Qdrant，也記錄 Mac 上 `host.docker.internal` 對 local Ollama 的處理方式。
- KAI-Mind 可學習：
  - Multi-service Docker Compose scanning。
  - macOS local runtime detection。
  - Qdrant URL 與 API key config patterns。
  - n8n file / command nodes 等 agent/workflow tool risk surfaces。

## ollama-docker

- URL: https://github.com/wolffaxn/ollama-docker
- 為什麼重要：LlamaIndex + Ollama + Qdrant + Open WebUI stack，包含 ingestion 與 query scripts。
- KAI-Mind 可學習：
  - RAG pipeline input/output flow。
  - Ingestion script detection。
  - Open WebUI connection settings。
  - Qdrant 與 Ollama service topology。

## RAGFlow

- URL: https://github.com/infiniflow/ragflow
- 為什麼重要：成熟的 RAG 與 agent system，包含 self-hosting、document parsing、chunking、citation、agent 與 Docker architecture。
- KAI-Mind 可學習：
  - 成熟 RAG architecture vocabulary。
  - Citation 與 chunk traceability。
  - Large repo scanning considerations。
  - RAG workflow 與 release readiness checks 的邊界。

## 如何使用這些參考 Repo

不要直接複製它們的架構。建議拿來建立 scanner fixtures 與測試案例：

- `docker-compose.yml` examples。
- `.env.example` 與 config examples。
- Qdrant / vector DB settings。
- Ollama endpoint settings。
- App/API port exposure examples。
- Agent tool 或 workflow config examples。
