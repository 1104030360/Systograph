# 2026-05-31 Phase4 Fixtures Contract TODO

## 目標

依照 `04-build-test-fixtures-and-contract-baseline.md` 實作 Epic 1 scanner 測試用 sample projects 與 contract baseline。

## 實作邏輯

- 先用 TDD 寫測試，定義 fixtures 應該長什麼樣子。
- fixtures 只提供 static scanner signals，不需要真的啟動 Docker、Ollama、OpenAI、Postgres 或 vector DB。
- 不 vendoring 外部 repo，只參考公開 repo pattern 後轉寫成 project-owned minimal fixtures。
- 每個 fixture 都要有 README 記錄 reference source、scanner signals、safety notes。
- 測試要保護 secret masking、project-relative POSIX path、fixture size、provider variation coverage。

## 階段拆分

### 階段 1：紅燈測試

- 建立 fixture helper 測試。
- 建立 fixture contract 測試。
- 測試 fixtures 必須存在、README 必須完整、不可含真 secret、不可 vendoring 大型 repo。

### 階段 2：建立 fixtures

- 建立 `tests/fixtures/rag_projects/`。
- 建立 canonical happy path：`basic_qdrant_ollama_rag/`。
- 建立 provider variation fixtures：
  - `openai_external_provider_rag/`
  - `pgvector_openai_rag/`
  - `faiss_sentence_transformers_rag/`
  - `lancedb_or_chroma_local_rag/`
- 建立 behavior / contract fixtures：
  - `malformed_config_rag/`
  - `missing_slots_rag/`
  - `custom_router_rag/`
  - `reranker_extension_rag/`
  - `graph_rag_extension_rag/`
  - `healthcare_rag_minimal/`

### 階段 3：helper 與 contract baseline

- 建立 `tests/helpers/fixtures.py`。
- 讓測試透過 helper 取得 fixture path，避免 hard-coded absolute path。
- 建立 provider coverage matrix 測試。

### 階段 4：驗證

- 執行 pytest。
- 若可用，執行 ruff / mypy 或 project standard checks。
- 記錄測試結果與未完成風險。

## 目前決策

- 第一個 fixture 以 `basic_qdrant_ollama_rag/` 為 canonical happy path。
- 主參考：`AllAboutAI-YT/easy-local-rag` 的小型 local RAG shape。
- 輔助參考：`qdrant/examples` 的 Qdrant scanner signals。
- 概念參考：`Mintplex-Labs/anything-llm` 的 local/private RAG app boundary。
- GraphRAG fixture 納入本階段追加範圍，作為 graph store / graph retriever / knowledge graph extension sample。
- Healthcare fixture 納入本階段追加範圍，作為 synthetic medical data / citation / guardrail / PHI policy sample。

## 注意事項

- 不加入真 API key、token、password、private key。
- 不加入大型 dataset、model weights、binary artifacts。
- 不讓 tests 依賴網路或外部 runtime。
- 不改 `AGENTS.md`，因為本次不是長期開發規則變更。
