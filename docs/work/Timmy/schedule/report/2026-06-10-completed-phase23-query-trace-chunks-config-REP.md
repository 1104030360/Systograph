# 2026-06-10 Completed Phase 23 Query Trace Chunks Config Report

## 實作邏輯

- 查證 Python 官方 packaging spec / PEP 518 / PEP 621 後，確認工具自訂設定應放在 `pyproject.toml` 的 `[tool.<name>]` namespace；Python 3.11+ 可用標準庫 `tomllib` 讀取 TOML。
- `QueryTraceService._retrieved_chunks()` 原本只讀 `retrieved_chunks`、`chunks`、`documents`，因此自訂 RAG API 回傳 `docs`、`retrieved_docs` 或 `context` 時會漏掉 retrieved chunks。
- 新增 `QueryTraceConfigLoader`，從被掃描專案根目錄的 `pyproject.toml` 讀取 `[tool.systograph.trace] retrieved_chunks_keys`。缺檔或缺設定時保留原本 fallback；設定存在但格式錯誤時 fail fast。
- `QueryTraceService` 改成支援 constructor / per-call `retrieved_chunks_keys` 注入，預設 key 不變，retrieved chunks 仍走既有 masking / summary path。
- `POST /api/trace` 由 project session 的 `project_path` 載入 pyproject 設定，再注入 service；map build / scan / viewer 路徑仍不呼叫 runtime endpoint。
- `systograph trace` 新增 `--project-root`，讓 CLI 在需要 project pyproject 設定時有明確來源，不從 map artifact 猜測專案位置。

## 步驟

1. 先補 RED tests：service 注入 `docs` key、config loader 讀 pyproject、web route 套用 project pyproject、CLI invalid config handling。
2. 實作 `src/systograph/core/services/query_trace_config_loader.py`。
3. 重構 `src/systograph/core/services/query_trace_service.py`，把 chunks key 清單從硬編碼改為可注入。
4. 更新 `src/systograph/web/routes/trace_routes.py`，在 trace 前讀 project config，格式錯誤回 HTTP 400 `invalid_trace_config`。
5. 更新 `src/systograph/cli/trace_command.py`，加入 `--project-root` 並復用相同 config loader。
6. 更新 `docs/API-GUIDE.md`、`docs/work/Timmy/design/epic1-local-api-guide.md` 與本階段 TODO。

## 測試方式

- `.venv/bin/pytest tests/unit/core/test_query_trace_service.py tests/unit/core/test_query_trace_config_loader.py tests/web/test_trace_routes.py tests/cli/test_trace_command.py`
- `.venv/bin/mypy src tests`
- `.venv/bin/pytest`
- `.venv/bin/ruff check .`

## 遇到的問題與解法

- 第一次全套 pytest 在 sandbox 中有 2 個 `test_filesystem_provider.py` 測試失敗，原因是測試內 `git init` 建立 `.git/hooks/` 時被 sandbox 擋下 `Operation not permitted`。解除 sandbox 後重跑全套 pytest 通過，確認不是本次 query trace config 改動造成。
- CLI 原本只有 map JSON path，沒有安全方式知道被掃描專案根目錄；解法是新增顯式 `--project-root`，維持 thin adapter 且讓行為可重現。

## 測試結果

- Focused Query Trace config tests：15 passed。
- mypy：Success，129 source files 無 issue。
- 全套 pytest：398 passed（解除 sandbox 後）。
- ruff：All checks passed。
