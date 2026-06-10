# 2026-06-10 Phase 23 Query Trace Chunks Config TODO

## 實作邏輯

- 先確認 `QueryTraceService._retrieved_chunks()` 目前只讀 `retrieved_chunks` / `chunks` / `documents`，因此自訂 RAG API 回傳 `docs` 或 `retrieved_docs` 時會漏掉 retrieved chunks。
- 採用 Python 官方建議的 `pyproject.toml` `[tool.<name>]` 工具設定區，從被掃描專案根目錄讀取 `[tool.kai-mind.trace] retrieved_chunks_keys`。
- Core trace service 保持可測試的 dependency injection：預設 key 不變，但允許由外部注入 per-project chunk key 清單。
- Web trace route 使用 project session 中保存的 `project_path` 讀設定；map build / scan / viewer 仍維持 static read-only，不因設定讀取而呼叫 runtime endpoint。
- 所有 retrieved chunks 仍必須走既有 masking / summary path，不保存 raw chunks。

## 步驟

1. [x] 先補 RED tests：service 可接受 `docs` key、config loader 可讀 pyproject、web route 可套用 project pyproject 設定。
2. [x] 實作 `QueryTraceConfigLoader`，讀取缺檔 fallback、合法 list、錯誤 list 的明確錯誤。
3. [x] 重構 `QueryTraceService`，把 retrieved chunks keys 從硬編碼 tuple 改成可注入設定。
4. [x] 串接 `POST /api/trace`，從 project root 的 `pyproject.toml` 載入設定後傳給 service。
5. [x] 更新 API/design docs，加入 `[tool.kai-mind.trace] retrieved_chunks_keys` 範例與 fallback 規則。
6. [x] 跑 focused tests、lint/mypy，再記錄 report。
