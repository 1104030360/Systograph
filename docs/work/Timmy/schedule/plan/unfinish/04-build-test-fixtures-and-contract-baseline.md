# Task 4: Build Test Fixtures and Contract Baseline

## 目標
建立 Epic 1 scanner 測試用 sample projects 與 contract test baseline。這些 fixtures 會支撐後續每個 provider、service、CLI、viewer projection 的驗收。

## 為什麼要先做這個
AGENTS.md 明確指出 scanner 行為缺少測試時視為 P1。設計文件也要求 scanner tests 使用 sample projects / fixtures；先建立 fixtures 可以讓新手每完成一個 provider 就有具體測試場景。

## 前置需求
- Task 1 已完成測試框架。
- Task 2 已完成 schema 與 core models。
- Task 3 已完成 `rag-core-v1` template。

## 實作範圍
- 建立 `tests/fixtures/rag_projects/`。
- 建立 basic Qdrant/Ollama fixture。
- 建立 malformed config/compose fixture。
- 建立 OpenAI external provider fixture，值必須是 fake secret。
- 建立 missing slots fixture。
- 建立 custom router / reranker extension fixture。
- 建立 contract test helpers。

## 不包含範圍
- 不需要所有 provider 一次通過完整 map。
- 不建立大型真實 repo。
- 不放入任何真實 secret。
- 不建立 GUI 測試。

## 建議實作步驟
1. 建立 `tests/fixtures/rag_projects/basic_qdrant_ollama_rag/`。
2. 加入小型 `docker-compose.yml`、`requirements.txt`、`src/app.py`、`README.md`。
3. 建立 `malformed_config_rag/`，放一個故意壞掉的 YAML 或 Compose。
4. 建立 `openai_external_provider_rag/`，使用 fake `OPENAI_API_KEY=sk-test-...`。
5. 建立 `custom_router_rag/` 與 `reranker_extension_rag/`。
6. 建立 `tests/helpers/fixtures.py` 提供 fixture path helper。
7. 建立初始 contract tests，只檢查 fixtures 存在且沒有真實 secret pattern。

## 預期輸出
- `tests/fixtures/rag_projects/basic_qdrant_ollama_rag/`
- `tests/fixtures/rag_projects/openai_external_provider_rag/`
- `tests/fixtures/rag_projects/malformed_config_rag/`
- `tests/fixtures/rag_projects/missing_slots_rag/`
- `tests/fixtures/rag_projects/custom_router_rag/`
- `tests/fixtures/rag_projects/reranker_extension_rag/`
- `tests/helpers/fixtures.py`

## 驗收標準
- pytest 可找到所有 fixtures。
- fixtures 小型、可讀、跨平台，不依賴 absolute path。
- fake secret 不會被誤認為真實 credential。
- 後續 tasks 可直接引用 fixture path helper。

## 可能風險與注意事項
- 不要把本機 `.env` 或真實 API key 複製進 fixtures。
- 測試 fixture 應該足夠小，不要引入真實依賴安裝。
- 參考依據：pytest 官方文件提供 `tmp_path` fixture，可在測試中複製 fixture 到臨時目錄避免污染原始 fixture。

## 新手提示
Fixture 就是小型假專案。它讓你不用找真實客戶 repo，也能測 scanner 是否抓得到 Docker、dependency、config、code pattern。

## 視覺化說明
```text
┌──────────────────────────┐
│ tests/fixtures/rag_projects │
│ small sample RAG repos       │
└───────┬─────────┬────────┬──┘
        │         │        │
        ↓         ↓        ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Provider     │ │ Integration  │ │ Contract     │
│ tests        │ │ tests        │ │ snapshots    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴──────┬─────────┘
                                ↓
┌──────────────────────────┐
│ Stable scanner behavior   │
└──────────────────────────┘
```
