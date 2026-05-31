# Task 4: Build Test Fixtures and Contract Baseline

## 目標
建立 Epic 1 scanner 測試用 sample projects 與 contract test baseline。這些 fixtures 會支撐後續每個 provider、service、CLI、viewer projection 的驗收。

## 為什麼要先做這個
AGENTS.md 明確指出 scanner 行為缺少測試時視為 P1。設計文件也要求 scanner tests 使用 sample projects / fixtures；先建立 fixtures 可以讓新手每完成一個 provider 就有具體測試場景。

## 前置需求
- Task 1 已完成測試框架。
- Task 2 已完成 schema 與 core models。
- Task 3 已完成 `rag-core-v1` template。
- 已完成 RAG repo 參考條件整理：`docs/work/Timmy/schedule/explain/rag-repo-reference-criteria.md`。
- 已完成 GitHub RAG repo research 初版報告：`test-input/rag_github_repo_research.md`。

## 外部 RAG repo 參考策略
Task 4 可以參考公開 RAG sample repo 的架構與常見 patterns，但不可整包 vendoring 外部 repo，也不可直接複製大型真實專案。正確做法是：

```text
公開 RAG sample repo
        ↓
參考架構與常見 patterns
        ↓
抽出 scanner 測試需要的 deterministic signals
        ↓
轉寫成 project-owned minimal fixtures
        ↓
放進 tests/fixtures/rag_projects/
```

這樣做的理由：

- 保留真實 RAG repo 的架構參考價值。
- 避免外部 repo 改版造成測試不穩。
- 避免授權、secret、大型資料、外部服務依賴風險。
- 讓 fixtures 小型、可讀、跨平台、可重現。
- 讓後續 provider tests 可以精準測單一 scanner signal。

不可做：

- 不直接 clone / copy 整包外部 repo 到 `tests/fixtures/`。
- 不放入真實 `.env`、API key、token、password、cloud credential。
- 不放入大型 dataset、model weights、binary artifacts。
- 不讓 fixture 測試需要網路、Docker daemon、OpenAI API、Ollama server 或 vector DB server 真正啟動。
- 不用外部 repo 的授權不明程式碼作為 checked-in fixture 原始碼。

## RAG repo 參考條件
選入參考 repo 時，必須依照 `docs/work/Timmy/schedule/explain/rag-repo-reference-criteria.md` 的條件判斷。Task 4 實作時至少檢查：

| 條件 | Task 4 使用方式 |
|---|---|
| RAG 流程清楚 | 能看出 loader、chunking、embedding、vector store、retriever、prompt、LLM 中至少幾個明確訊號 |
| 檔案小、結構簡單 | 只抽小型 fixture，不建立大型真實 repo |
| dependency 明確 | 優先參考 `requirements.txt`、`pyproject.toml`、`package.json` 裡的 deterministic signals |
| config / docker / env 明確 | 優先抽 `docker-compose.yml`、`.env.example`、`config.yaml` 的 scanner signals |
| 沒有真 secret | 只能使用 fake/example values，例如 `OPENAI_API_KEY=sk-test-example` |
| 不需要真的跑起來 | fixtures 只提供靜態掃描訊號，不要求外部服務可用 |
| 授權清楚 | 優先 MIT、Apache-2.0、BSD；授權不明 repo 只能作概念參考 |
| 可轉寫成 minimal fixture | 參考 pattern，使用本專案自己寫的小型檔案 |

## GitHub RAG Repo Research Baseline
已依照本機規則與 GitHub metadata 搜尋，完整報告儲存在：

```text
test-input/rag_github_repo_research.md
```

Task 4 實作時優先參考下列 repos，但只抽概念與 scanner signals，不直接複製整包 repo。

### 高優先參考

| Repo | 類型 | 參考價值 |
|---|---|---|
| [`AllAboutAI-YT/easy-local-rag`](https://github.com/AllAboutAI-YT/easy-local-rag) | Local RAG | 小型 local RAG + Ollama，最接近 local fixture 需求 |
| [`Mintplex-Labs/anything-llm`](https://github.com/Mintplex-Labs/anything-llm) | Local / self-hosted RAG app | 完整 local/private RAG app，適合參考 workspace、document ingestion、vector DB、Ollama/local LLM、agent/MCP integration 邊界 |
| [`open-webui/open-webui`](https://github.com/open-webui/open-webui) | Self-hosted AI UI + RAG | 適合參考 Ollama / OpenAI-compatible provider、offline/self-hosted、knowledge/RAG、vector DB、embedding config 訊號 |
| [`infiniflow/ragflow`](https://github.com/infiniflow/ragflow) | RAG engine + agent | 完整 RAG engine，適合參考 document parsing、retrieval、agentic retrieval、context layer 邊界 |
| [`arc53/DocsGPT`](https://github.com/arc53/DocsGPT) | Private docs QA / enterprise search | 適合參考 docs ingestion、semantic search、RAG answer、private deployment 訊號 |
| [`qdrant/examples`](https://github.com/qdrant/examples) | Vector DB examples | 適合抽 Qdrant vector store、collection、embedding、similarity search 訊號 |
| [`weaviate/Verba`](https://github.com/weaviate/Verba) | Vector DB RAG app | 適合參考 ingestion + vector DB + chatbot RAG 結構 |
| [`NVIDIA-AI-Blueprints/rag`](https://github.com/NVIDIA-AI-Blueprints/rag) | Production-ready RAG blueprint | 適合參考 production RAG pipeline 邊界 |
| [`microsoft/graphrag`](https://github.com/microsoft/graphrag) | Graph RAG | GraphRAG 代表性高，適合 graph extension fixture 參考 |
| [`zylon-ai/private-gpt`](https://github.com/zylon-ai/private-gpt) | Local/private RAG | 貼近 local/private document QA 與 no data leak 定位 |

### 中優先參考

| Repo | 類型 | 參考價值 |
|---|---|---|
| [`run-llama/llama_index`](https://github.com/run-llama/llama_index) | RAG framework | 適合參考 ingestion、index、retriever、query engine pattern |
| [`langgenius/dify`](https://github.com/langgenius/dify) | LLM app platform / RAG pipeline | 適合參考 Docker Compose、`.env`、RAG pipeline template/export、workflow、agent、vector store config |
| [`FlowiseAI/Flowise`](https://github.com/FlowiseAI/Flowise) | Low-code RAG / agent builder | 適合參考 visual flow、LangChain、vector DB、agent workflow 訊號 |
| [`QuivrHQ/quivr`](https://github.com/QuivrHQ/quivr) | Opinionated RAG app | 適合參考 any LLM / any vector store / file ingestion 的 productized RAG 訊號 |
| [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj) | Self-hosted personal AI / second brain | 適合參考 local docs、web docs、offline LLM、personal knowledge base 訊號 |
| [`ragapp/ragapp`](https://github.com/ragapp/ragapp) | Agentic RAG | 適合參考 app + agentic RAG integration |
| [`HKUDS/LightRAG`](https://github.com/HKUDS/LightRAG) | Graph / lightweight RAG | 適合參考 graph + vector hybrid signals |
| [`deepset-ai/haystack`](https://github.com/deepset-ai/haystack) | Pipeline framework | 適合參考 retriever / ranker / generator pipeline 邊界 |
| [`neo4j/neo4j-graphrag-python`](https://github.com/neo4j/neo4j-graphrag-python) | Graph DB RAG | 適合 graph database integration；license metadata 需人工確認 |
| [`souvikmajumder26/Multi-Agent-Medical-Assistant`](https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant) | Healthcare agentic RAG | 適合醫療 + agentic + RAG 概念參考，但 fixture 必須轉寫成 fake medical data |

### 低優先或延伸參考

| Repo | 類型 | 原因 |
|---|---|---|
| [`langchain-ai/langchain`](https://github.com/langchain-ai/langchain) | RAG / agent framework | 太大，適合理解 pattern，不適合直接 fixture |
| [`danny-avila/LibreChat`](https://github.com/danny-avila/LibreChat) | Self-hosted chat UI | self-hosted chat/agent UI 很強，但 RAG 不是最核心訊號，適合延伸參考 |
| [`lobehub/lobehub`](https://github.com/lobehub/lobehub) | Agent / knowledge-base UI | 有 knowledge-base 訊號，但更偏 agent operation，不作 Task 4 主 fixture 來源 |
| [`HKUDS/RAG-Anything`](https://github.com/HKUDS/RAG-Anything) | Multimodal RAG | 多模態重要，但 Task 4 初版可先不做 |
| [`apecloud/ApeRAG`](https://github.com/apecloud/ApeRAG) | Production GraphRAG | production 訊號多，但系統複雜 |
| [`dmis-lab/RAG2`](https://github.com/dmis-lab/RAG2) | Medical RAG research | medical QA 有價值，但 license 未確認、偏研究 |
| [`vibrantlabsai/ragas`](https://github.com/vibrantlabsai/ragas) | RAG evaluation | 適合後續 evaluation design，不是 Task 4 fixture 來源 |

## Fixture 覆蓋策略：不要只測 Qdrant + Ollama
`basic_qdrant_ollama_rag/` 只應該是最小 happy path，不應該代表 scanner 只支援 Qdrant 或 Ollama。從 AI backend / architecture 角度，Task 4 的 fixture baseline 必須刻意覆蓋「同一個 RAG 階段可由不同 provider 實作」這件事。

### Epic 1 design 對 fixture 選擇的決策

已讀取 Epic 1 design：

- `docs/work/Timmy/design/epic1-backend-design.md`
- `docs/work/Timmy/design/epic1-scan-pipeline-research.md`

設計文件對 Task 4 的重點不是「建立能真正跑起來的 RAG app」，而是建立可以穩定驗證 scanner contract 的 sample projects：

- provider 必須 deterministic parse config / Docker / dependency / code pattern。
- raw facts 必須有 evidence。
- detected component 不可沒有 evidence。
- malformed config 不可讓整體 scan crash。
- secret-like value 必須 mask。
- unmapped / custom component 不可硬塞進 standard slot。
- `ai_system_map.json` 必須通過 `ai-system-map/v1` schema validation。

因此第一個 fixture 的主參考應選：

| 角色 | Repo | 使用方式 |
|---|---|---|
| 第一個 fixture 的主要形狀參考 | [`AllAboutAI-YT/easy-local-rag`](https://github.com/AllAboutAI-YT/easy-local-rag) | 參考小型 local RAG 專案形狀：app entry、ingest、retriever、local model provider；只抽 pattern，不複製整包 |
| 第一個 fixture 的 Qdrant evidence 參考 | [`qdrant/examples`](https://github.com/qdrant/examples) | 參考 Qdrant client、collection、similarity search、Docker image / port 等 deterministic scanner signals |
| 第一個 fixture 的 product boundary 參考 | [`Mintplex-Labs/anything-llm`](https://github.com/Mintplex-Labs/anything-llm) | 只參考 local/private RAG app 邊界，例如 workspace、document ingestion、vector DB、local provider config，不作為第一個 fixture 的完整形狀 |

不建議第一個 fixture 直接以 AnythingLLM / Open WebUI / Dify / RAGFlow 為主，原因是：

- 它們是 product/platform 等級，檔案量與架構邊界太大。
- Task 4 需要的是 scanner signal，不是 product behavior。
- 大型 repo 的 fixture 容易引入不必要的 frontend、auth、DB migration、background job、plugin 系統訊號。
- Epic 1 design 要先保護 JSON contract 和 deterministic provider，而不是模擬完整 SaaS。

決策：

```text
第一個要做：basic_qdrant_ollama_rag/
主參考：easy-local-rag 的小型 local RAG shape
輔助參考：qdrant/examples 的 Qdrant scanner signals
概念參考：AnythingLLM 的 local/private RAG app boundary
```

這個 fixture 應該能先驗證：

```text
DockerComposeProvider     -> qdrant / ollama service facts
DependencyManifestProvider -> qdrant-client / ollama / fastapi facts
ConfigParseProvider       -> fake env / provider config facts
CodePatternProvider       -> ingest / retriever / query route patterns
ComponentDetectionService -> vector_store / embedding_model / llm / retriever slots
SystemMapValidation       -> detected components all have evidence
```

### Fixture 數量決策：一個 canonical fixture + 少量 variation fixtures

不應該只做一個 fixture，也不應該一開始做很多大型 fixture。最穩定的做法是：

```text
1 canonical happy path fixture
        +
3 provider variation fixtures
        +
3 behavior / contract fixtures
        +
optional advanced fixtures
```

原因：

- 只做一個 fixture：scanner 容易只會辨識 Qdrant + Ollama，對 pgvector、FAISS、OpenAI embedding、sentence-transformers、custom router 看不出來。
- 一開始做太多 fixture：Task 4 會變成維護假專案大全，拖慢 core scanner / schema / contract test。
- 少量 variation fixtures：可以精準測「同一個 RAG slot 有不同 provider」，又不會讓測試變重。

建議順序：

| 順序 | Fixture | 目的 |
|---:|---|---|
| 1 | `basic_qdrant_ollama_rag/` | canonical happy path，先打通 Docker / dependency / config / code pattern / slot mapping |
| 2 | `openai_external_provider_rag/` | 測 external provider、fake secret masking、external endpoint / risk hint |
| 3 | `pgvector_openai_rag/` | 測 SQL-backed vector store，不讓 scanner 只懂 Qdrant |
| 4 | `faiss_sentence_transformers_rag/` | 測 file-based local vector index 與 HuggingFace embedding |
| 5 | `malformed_config_rag/` | 測 parse error 產生 partial map，不 crash |
| 6 | `missing_slots_rag/` | 測缺少 evidence 的 slot 不可標成 detected |
| 7 | `custom_router_rag/` / `reranker_extension_rag/` | 測 extension / unmapped，不硬塞 standard slot |

這樣符合 Epic 1 design 的 testing strategy：先用 sample projects 驗證完整 map build，再用 contract tests 保護 JSON schema、evidence、secret masking、path normalization 和 unmapped behavior。

### 少量 provider variation fixtures 應先覆蓋哪些 RAG 階段

少量 provider variation fixtures 不需要一開始覆蓋所有 RAG 階段。Task 4 初版應優先覆蓋「最常換 provider，而且最容易讓 scanner 誤判」的階段。

優先階段：

```text
1. Embedding
2. Vector Store
3. Retriever
4. LLM Provider
5. Orchestration / App Route
```

| RAG 階段 | 為什麼要測 variation | Task 4 建議 fixture |
|---|---|---|
| Embedding | 不一定使用 Ollama；常見可能是 OpenAI、HuggingFace、BGE、sentence-transformers | `openai_external_provider_rag/`、`faiss_sentence_transformers_rag/` |
| Vector Store | 不一定使用 Qdrant；常見可能是 pgvector、FAISS、Chroma、LanceDB | `pgvector_openai_rag/`、`faiss_sentence_transformers_rag/`、`lancedb_or_chroma_local_rag/` |
| Retriever | 有些使用 `.as_retriever()`，有些是自寫 similarity search，有些是 hybrid search | `basic_qdrant_ollama_rag/`、`custom_router_rag/` |
| LLM Provider | 有 local Ollama，也有 OpenAI-compatible、Azure OpenAI、其他 hosted provider | `basic_qdrant_ollama_rag/`、`openai_external_provider_rag/` |
| Orchestration / App Route | 有些是 FastAPI route，有些是 CLI，有些是 workflow / agent router | `basic_qdrant_ollama_rag/`、`custom_router_rag/` |

第一版可以先延後的階段：

```text
document_loader
chunking
reranker
citation
guardrails
observability
graph retrieval
multimodal ingestion
```

白話決策：

```text
先測 scanner 會不會認錯核心 RAG 組件。
再測 RAG 流程是不是完整。
最後才測 reranker、citation、guardrails、observability、graph、multimodal 這些進階功能。
```

正確設計方向：

```text
RAG stage
  ingestion      -> local files / web docs / uploaded docs
  chunking       -> recursive splitter / token splitter / custom splitter
  embedding      -> Ollama / OpenAI / HuggingFace sentence-transformers / BGE
  vector store   -> Qdrant / pgvector / FAISS / LanceDB / Chroma / Weaviate
  retrieval      -> similarity search / hybrid search / graph retrieval
  rerank         -> cross-encoder / Cohere-style rerank / custom reranker
  generation     -> Ollama / OpenAI-compatible / Azure OpenAI / local llama.cpp
  orchestration  -> simple route / LangChain / LlamaIndex / custom router / workflow
```

因此 scanner contract 不應寫死成：

```text
if qdrant-client exists -> this is RAG
```

而應該掃描並輸出更通用的 evidence：

```text
component.kind = vector_store
component.provider = qdrant | pgvector | faiss | lancedb | chroma | weaviate | unknown
component.evidence = dependency / docker image / config key / import path / code pattern
```

同樣地，embedding 也不能只看 `ollama`：

```text
component.kind = embedding_model
component.provider = ollama | openai | huggingface | sentence_transformers | bge | unknown
component.evidence = env key / package / model name / import path / config field
```

### Provider coverage matrix

Task 4 至少要讓 fixtures 覆蓋下列差異，避免後續 scanner 只會辨識單一路徑：

| RAG 階段 | 最小必測 provider / pattern | 主要 evidence 來源 |
|---|---|---|
| Vector store | Qdrant | `docker-compose.yml` image、`qdrant-client` dependency、`QDRANT_URL` config |
| Vector store | pgvector / PostgreSQL | `postgres` / `pgvector` image、`pgvector` / `psycopg` dependency、`DATABASE_URL`、SQL extension hint |
| Vector store | FAISS | `faiss-cpu` dependency、local index path、`FAISS.from_documents` / `faiss.IndexFlatL2` style import |
| Vector store | LanceDB / Chroma（至少一個） | `lancedb` / `chromadb` dependency、local DB path、AnythingLLM / Open WebUI 類型 config |
| Embedding | Ollama local embedding | `ollama` dependency、`OLLAMA_BASE_URL`、`nomic-embed-text` / local embedding model name |
| Embedding | OpenAI embedding | fake `OPENAI_API_KEY`、`text-embedding-3-small` / OpenAI embedding config |
| Embedding | HuggingFace / sentence-transformers | `sentence-transformers` dependency、`all-MiniLM` / `bge-*` model name |
| LLM provider | Ollama / local model | `OLLAMA_BASE_URL`、`llama3` / local model config |
| LLM provider | OpenAI-compatible external provider | fake API key、base URL、model name；不得放真 secret |
| Pipeline | Reranker / router / agentic flow | `reranker` dependency、custom router code、workflow config、agent route |

這個 matrix 的目的不是要求 Task 4 建一堆能跑的 RAG，而是讓 scanner 有足夠靜態樣本可以驗證「同一個 slot 有不同 provider」。

## Fixture 設計對應建議
Task 4 fixtures 應從上述 research baseline 轉寫成下列小型樣本：

| Fixture | 主要參考 repo | 應保留的 scanner signals |
|---|---|---|
| `basic_qdrant_ollama_rag/` | `qdrant/examples`、`AllAboutAI-YT/easy-local-rag`、`Mintplex-Labs/anything-llm` | 最小 happy path；`docker-compose.yml` 中的 Qdrant/Ollama images、published ports、`requirements.txt` 中的 `qdrant-client` / `ollama`、`src/app.py` query route、`src/retriever.py` vector retriever pattern；不可作為唯一 provider 覆蓋 |
| `pgvector_openai_rag/` | `open-webui/open-webui`、`langgenius/dify`、common pgvector RAG patterns | PostgreSQL / pgvector vector store、fake `DATABASE_URL`、fake `OPENAI_API_KEY`、OpenAI embedding model name、外部 LLM provider config；用來測 scanner 不只辨識 Qdrant |
| `faiss_sentence_transformers_rag/` | `zylon-ai/private-gpt`、`deepset-ai/haystack`、common FAISS local RAG patterns | `faiss-cpu`、`sentence-transformers`、local index path、HuggingFace / BGE / MiniLM embedding model name；用來測 local file-based vector index |
| `lancedb_or_chroma_local_rag/` | `Mintplex-Labs/anything-llm`、`open-webui/open-webui`、`QuivrHQ/quivr` | LanceDB 或 Chroma local vector DB、workspace / knowledge base config、local embedding provider；用來覆蓋 self-hosted RAG app 常見 local DB 訊號 |
| `openai_external_provider_rag/` | `run-llama/llama_index`、`langchain-ai/langchain` common patterns | `.env.example` fake `OPENAI_API_KEY`、OpenAI embedding / LLM dependency、external provider config，但不可放真 secret |
| `malformed_config_rag/` | 不需外部 repo | 故意壞掉的 YAML / Compose，用來測 parse error 不 crash |
| `missing_slots_rag/` | 本專案 `rag-core-v1` template | 缺少 citation、guardrails、observability 等 evidence，用來支援後續 missing / not_configured status 測試 |
| `custom_router_rag/` | `ragapp/ragapp`、LangGraph/LangChain agentic patterns | custom query router / agent router 訊號，用來測不要硬塞進標準 slot |
| `reranker_extension_rag/` | Haystack / common reranker pipeline patterns | reranker dependency / code pattern，用來測 extension / unmapped component |
| `graph_rag_extension_rag/` | `microsoft/graphrag`、`HKUDS/LightRAG`、`neo4j/neo4j-graphrag-python` | graph retriever / graph store / knowledge graph 訊號，用來支援 GraphRAG extension 測試 |
| `healthcare_rag_minimal/` | `souvikmajumder26/Multi-Agent-Medical-Assistant`、`dmis-lab/RAG2` | fake medical documents、medical QA route、citation、guardrail hint；不可放真病患資料 |

## 實作範圍
- 建立 `tests/fixtures/rag_projects/`。
- 建立 basic Qdrant/Ollama fixture。
- 建立 pgvector + OpenAI embedding/provider fixture。
- 建立 FAISS + sentence-transformers / HuggingFace embedding fixture。
- 建立 LanceDB 或 Chroma local vector DB fixture。
- 建立 malformed config/compose fixture。
- 建立 OpenAI external provider fixture，值必須是 fake secret。
- 建立 missing slots fixture。
- 建立 custom router / reranker extension fixture。
- 建立 graph RAG extension fixture。
- 建立 healthcare RAG minimal fixture。
- 建立 contract test helpers。

## 不包含範圍
- 不需要所有 provider 一次通過完整 map。
- 不建立大型真實 repo。
- 不放入任何真實 secret。
- 不建立 GUI 測試。
- 不直接 vendoring 外部 GitHub repo。
- 不讓 fixture 依賴網路、Docker daemon、真 LLM provider 或真 vector DB runtime。

## 建議實作步驟
1. 閱讀 `docs/work/Timmy/schedule/explain/rag-repo-reference-criteria.md` 與 `test-input/rag_github_repo_research.md`，確認 Task 4 只參考外部 repo pattern，不直接複製整包 repo。
2. 建立 `tests/fixtures/rag_projects/basic_qdrant_ollama_rag/`。
3. 參考 `qdrant/examples` 與 `AllAboutAI-YT/easy-local-rag`，轉寫小型 `docker-compose.yml`、`requirements.txt`、`src/app.py`、`src/ingest.py`、`src/retriever.py`、`README.md`。
4. 建立 `pgvector_openai_rag/`，放小型 Postgres / pgvector Compose、fake `DATABASE_URL`、fake OpenAI embedding config，用來驗證 scanner 可辨識 SQL-backed vector store。
5. 建立 `faiss_sentence_transformers_rag/`，放 `faiss-cpu`、`sentence-transformers`、local index path 與 fake embedding model config，用來驗證 scanner 可辨識 file-based local vector index。
6. 建立 `lancedb_or_chroma_local_rag/`，參考 AnythingLLM / Open WebUI / Quivr 類型 self-hosted app 訊號，只保留 workspace、local DB path、embedding provider config。
7. 建立 `openai_external_provider_rag/`，參考 LlamaIndex / LangChain 常見 external provider pattern，使用 fake `OPENAI_API_KEY=sk-test-example` 或同等假值。
8. 建立 `malformed_config_rag/`，放一個故意壞掉的 YAML 或 Compose，測試後續 parser 必須產生 parse issue / evidence 而不是 crash。
9. 建立 `missing_slots_rag/`，保留最少 app / retriever 訊號，但刻意缺少 citation、guardrails、observability。
10. 建立 `custom_router_rag/`，放小型 custom query router / agent router pattern，用來測後續不確定 component 不應硬塞標準 slot。
11. 建立 `reranker_extension_rag/`，放小型 reranker dependency / code pattern，用來測 extension / unmapped component。
12. 建立 `graph_rag_extension_rag/`，參考 Microsoft GraphRAG / LightRAG / Neo4j GraphRAG，只放 graph retriever / graph store 的最小 scanner signals。
13. 建立 `healthcare_rag_minimal/`，參考 healthcare RAG research，只使用 fake medical documents，不放真病患資料，並保留 citation / guardrails / PHI policy scanner signals。
14. 每個 fixture 的 `README.md` 記錄：參考來源 repo URL、抽取的 pattern 類型、沒有複製真 secret / 大型資料 / runtime assets、fixture 不需要網路。
15. 建立 `tests/helpers/fixtures.py` 提供 fixture path helper。
16. 建立初始 contract tests，只檢查 fixtures 存在、檔案小型、路徑跨平台、沒有真實 secret pattern、README 有 reference / safety notes。

## 預期輸出
- `tests/fixtures/rag_projects/basic_qdrant_ollama_rag/`
- `tests/fixtures/rag_projects/pgvector_openai_rag/`
- `tests/fixtures/rag_projects/faiss_sentence_transformers_rag/`
- `tests/fixtures/rag_projects/lancedb_or_chroma_local_rag/`
- `tests/fixtures/rag_projects/openai_external_provider_rag/`
- `tests/fixtures/rag_projects/malformed_config_rag/`
- `tests/fixtures/rag_projects/missing_slots_rag/`
- `tests/fixtures/rag_projects/custom_router_rag/`
- `tests/fixtures/rag_projects/reranker_extension_rag/`
- `tests/fixtures/rag_projects/graph_rag_extension_rag/`
- `tests/fixtures/rag_projects/healthcare_rag_minimal/`
- `tests/helpers/fixtures.py`
- `tests/fixtures/rag_projects/*/README.md`

## 驗收標準
- pytest 可找到所有 fixtures。
- fixtures 小型、可讀、跨平台，不依賴 absolute path。
- fake secret 不會被誤認為真實 credential。
- 後續 tasks 可直接引用 fixture path helper。
- 每個 fixture 都有 README 記錄參考來源與轉寫原因。
- 每個 fixture 都明確標示不需要網路、Docker daemon、真 LLM provider 或真 vector DB runtime。
- contract baseline 至少覆蓋 Qdrant、pgvector、FAISS、LanceDB 或 Chroma 其中一個 local DB pattern。
- contract baseline 至少覆蓋 Ollama、OpenAI、HuggingFace / sentence-transformers 三種 embedding/provider 訊號。
- contract baseline 的 assertions 必須以 generic component kind + provider + evidence 為主，不可以只測 `qdrant-client` 或 `ollama` 單一路徑。
- contract tests 會掃描 fixtures，確認沒有真 secret-like values 被 checked in。
- contract tests 會確認外部 repo 只作參考，不存在整包 vendored third-party source tree。

## 可能風險與注意事項
- 不要把本機 `.env` 或真實 API key 複製進 fixtures。
- 測試 fixture 應該足夠小，不要引入真實依賴安裝。
- 不要把外部 repo 整包 vendoring 進本專案；授權允許也只參考 pattern。
- 如果參考 repo license 未確認，只能用作概念參考，不可複製程式碼。
- healthcare fixture 必須使用 fake / synthetic medical text，不可放真病患資料。
- multimodal fixtures 可以先做 optional，避免 Task 4 一次變成大型資料集工程。
- 不要讓 `basic_qdrant_ollama_rag/` 變成唯一成功樣本；它只能證明 happy path，不能證明 scanner 對 RAG provider 變體有足夠覆蓋。
- 若 scanner output schema 需要新增 provider / component 欄位，必須先確認是否破壞既有 JSON report contract；破壞相容性時要記錄 migration。
- 參考依據：pytest 官方文件提供 `tmp_path` fixture，可在測試中複製 fixture 到臨時目錄避免污染原始 fixture。

## 新手提示
Fixture 就是小型假專案。它可以參考真實 RAG repo 的架構，但最後要轉寫成我們自己可控的小型樣本。它讓你不用找真實客戶 repo，也能測 scanner 是否抓得到 Docker、dependency、config、code pattern。

## 視覺化說明
```text
┌──────────────────────────────┐
│ Public RAG repos              │
│ examples / frameworks / apps  │
└──────────────┬───────────────┘
               │ reference only
               ↓
┌──────────────────────────────┐
│ Extract scanner signals       │
│ docker / deps / config / code │
└──────────────┬───────────────┘
               │ rewrite as project-owned fixtures
               ↓
┌──────────────────────────────┐
│ tests/fixtures/rag_projects/  │
│ small synthetic RAG projects  │
└───────┬─────────┬────────┬───┘
        │         │        │
        ↓         ↓        ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Provider     │ │ Integration  │ │ Contract     │
│ tests        │ │ tests        │ │ baseline     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴──────┬─────────┘
                                ↓
┌──────────────────────────────┐
│ Stable scanner behavior       │
└──────────────────────────────┘
```
