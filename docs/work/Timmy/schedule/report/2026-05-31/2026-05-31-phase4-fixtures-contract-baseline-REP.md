# 2026-05-31 Phase4 Fixtures Contract Baseline Report

## 實作摘要

本階段依照 `04-build-test-fixtures-and-contract-baseline.md` 建立 Epic 1 scanner 測試用 RAG sample project fixtures 與 contract baseline。

本次重點不是建立可執行 RAG app，而是建立可被 scanner 靜態掃描的 deterministic signals：

- Docker / Compose signals
- dependency manifest signals
- config / env signals
- code pattern signals
- malformed config behavior
- missing slots behavior
- extension / unmapped behavior

## 實作邏輯

依照 TDD + BDD 方式執行：

1. 先建立紅燈測試，定義 fixtures 的 contract。
2. 再建立 project-owned synthetic fixtures。
3. 補上 BDD-style behavior tests。
4. 跑完整測試、lint、type check。

核心設計決策：

- `basic_qdrant_ollama_rag/` 是 canonical happy path。
- provider variation 不只測 Qdrant + Ollama，也覆蓋 pgvector、FAISS、LanceDB、OpenAI embedding、sentence-transformers。
- custom router / reranker 不硬塞進 standard slot，作為 extension / unmapped scanner signal。
- GraphRAG 使用 `graph_rag_extension_rag/` 覆蓋 graph store / knowledge graph / graph retriever extension signal。
- Healthcare 使用 `healthcare_rag_minimal/` 覆蓋 synthetic patient data、citation required、no diagnosis、emergency escalation、PHI policy readiness signal。
- fixture source 是被 scanner 掃的 sample code，不是本專案 runtime code，因此 mypy 排除 `tests/fixtures/rag_projects/`。

## 實作步驟

### 1. 建立 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-05-31-phase4-fixtures-contract-TODO.md`

內容包含：

- 實作邏輯
- 階段拆分
- fixture 決策
- 安全注意事項

### 2. 建立 fixture helper

新增：

- `tests/helpers/__init__.py`
- `tests/helpers/fixtures.py`

提供：

- `RAG_PROJECT_FIXTURE_NAMES`
- `rag_project_fixtures_root()`
- `rag_project_fixture_path()`
- `fixture_file_text()`

### 3. 建立 RAG project fixtures

新增：

- `tests/fixtures/rag_projects/basic_qdrant_ollama_rag/`
- `tests/fixtures/rag_projects/openai_external_provider_rag/`
- `tests/fixtures/rag_projects/pgvector_openai_rag/`
- `tests/fixtures/rag_projects/faiss_sentence_transformers_rag/`
- `tests/fixtures/rag_projects/lancedb_or_chroma_local_rag/`
- `tests/fixtures/rag_projects/malformed_config_rag/`
- `tests/fixtures/rag_projects/missing_slots_rag/`
- `tests/fixtures/rag_projects/custom_router_rag/`
- `tests/fixtures/rag_projects/reranker_extension_rag/`
- `tests/fixtures/rag_projects/graph_rag_extension_rag/`
- `tests/fixtures/rag_projects/healthcare_rag_minimal/`

每個 fixture 都有 `README.md`，記錄：

- Reference sources
- Scanner signals
- Safety notes

### 4. 建立測試

新增：

- `tests/unit/test_rag_project_fixtures_contract.py`
- `tests/integration/test_phase4_rag_fixture_behaviors.py`
- `tests/__init__.py`
- `tests/conftest.py`

測試覆蓋：

- fixture 名稱完整
- fixture root 與 path helper 正常
- 每個 fixture 有 README 與至少一個 scanner signal file
- README 記錄 reference / signal / safety
- fixtures 不含真 secret-like values
- fixtures 小型，不 vendoring 外部 repo
- provider coverage matrix 覆蓋 Qdrant、pgvector、FAISS、LanceDB、Ollama、OpenAI、sentence-transformers、custom router、reranker、GraphRAG / Neo4j / knowledge graph、healthcare safety signals
- malformed config 作為 isolated parse error fixture
- custom router / reranker 保留為 extension / unmapped 訊號

### 5. 型別與 lint 設定

更新：

- `pyproject.toml`

新增 mypy exclude：

```toml
exclude = ["tests/fixtures/rag_projects/"]
```

原因：

- fixture Python 檔是 scanner sample code。
- 它們故意引用未安裝的 RAG provider packages，例如 `qdrant_client`、`openai`、`faiss`、`lancedb`。
- 它們不應被視為本專案 runtime code 進行 type check。

## 測試方式

執行：

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 測試結果

```text
pytest: 69 passed
ruff: All checks passed
mypy: Success, no issues found in 21 source files
```

## 遇到的問題與解法

### 問題 1：沙盒環境無法建立 pytest temp file

現象：

- pytest 在 sandbox 中無法使用系統 temp directory。

解法：

- 使用已核准的 escalated command 在正常環境執行 pytest。

### 問題 2：新增 tests helper 後 pytest import path 不穩

現象：

- `tests.helpers.fixtures` 在 pytest collection 階段無法穩定匯入。

解法：

- 增加 `tests/conftest.py`，把 repo root 放進 `sys.path`。
- 保留 `tests/__init__.py`，讓 `tests.helpers` 是明確 package。

### 問題 3：mypy 掃到 fixture sample code

現象：

- mypy 檢查 `tests/fixtures/rag_projects/**/src/*.py` 時，因 sample code 引用未安裝 provider packages 而失敗。

解法：

- 在 `pyproject.toml` 中排除 `tests/fixtures/rag_projects/`。
- 這些檔案是 scanner input，不是 production / test helper runtime code。

## Task 4 複查

| 項目 | 結果 |
|---|---:|
| 建立 `tests/fixtures/rag_projects/` | 完成 |
| 建立 basic Qdrant/Ollama fixture | 完成 |
| 建立 OpenAI external provider fixture | 完成 |
| 建立 pgvector + OpenAI fixture | 完成 |
| 建立 FAISS + sentence-transformers fixture | 完成 |
| 建立 LanceDB local fixture | 完成 |
| 建立 malformed config fixture | 完成 |
| 建立 missing slots fixture | 完成 |
| 建立 custom router fixture | 完成 |
| 建立 reranker extension fixture | 完成 |
| 建立 graph RAG extension fixture | 完成 |
| 建立 healthcare RAG minimal fixture | 完成 |
| 建立 fixture path helper | 完成 |
| 建立 contract tests | 完成 |
| README 記錄 reference / safety notes | 完成 |
| 不直接 vendoring 外部 GitHub repo | 完成 |
| 不放真 secrets | 完成 |
| 不需要 network / Docker / runtime | 完成 |
## 最終結果

Phase4 範圍已完成，包含追加的 GraphRAG fixture 與 healthcare fixture。測試、lint、type check 均通過。
