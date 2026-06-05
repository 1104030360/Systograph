# 2026-06-06 Phase 17 Markdown Summary Artifact REP

## 完成範圍

本階段完成 Task 17：從 validated `RagSystemMap` 產生 `ai_system_map.md`，並讓 CLI / local API 可以取得同一批 map artifacts。

已完成：

- 建立 `MarkdownSummaryService`。
- 從 canonical `RagSystemMap` render human-readable Markdown。
- Markdown 包含固定 sections：
  - System Overview
  - Slot Coverage
  - Detected And Missing Slots
  - Indexing Flow
  - Query Answer Flow
  - External Endpoints
  - Network Exposure
  - Recommended Next Checks
- `recommended_next_checks` 以 GFM task list `- [ ]` 呈現。
- `OutputArtifactProvider.write_markdown()` 寫出 `ai_system_map.md`。
- `MapBuildService` 在同一個 output run directory 寫出 `ai_system_map.json` 與 `ai_system_map.md`。
- `MapBuildResult` 增加 `map_markdown_path`。
- CLI `kai-mind map` 成功時同時輸出 JSON 與 Markdown artifact path。
- Local API 新增 `GET /api/map/report`，讓前端可以檢視 latest Markdown report。
- `GET /api/map/report?download=true` 支援 attachment download。
- API guide 已更新 Markdown report contract。
- Task 17 plan 已從 `plan/unfinish` 移至 `plan/finish`。

## 實作邏輯

### Renderer 邊界

`MarkdownSummaryService` 是 pure renderer：

- input：validated `RagSystemMap`
- output：Markdown `str`
- 不接收 `project_path`
- 不讀 raw project files
- 不寫檔
- 不新增 Jinja2 dependency

這讓 Markdown artifact 保持 report view，不會變成第二份 source of truth。

### Artifact 邊界

寫檔仍集中在 `OutputArtifactProvider`：

- `write_json()` 寫 `ai_system_map.json`
- `write_markdown()` 寫 `ai_system_map.md`
- precondition error 仍只寫 `map-error.md`

`OutputRun.map_markdown_path` 已存在，本階段直接使用既有資料結構，沒有再發明 artifact path model。

### API 邊界

`GET /api/map/report` 只從 `InMemorySessionStore.latest_build_result()` 取得 `map_markdown_path`。

它不接受任意 `path` query，不把 request input 交給 `FileResponse` 或本機檔案讀取，因此不會變成本機任意檔案讀取 API。

## 步驟紀錄

1. 先建立 Phase 17 TODO。
2. 讀取 `AGENTS.md`、phase17 dev-prompt、Task 17 plan、既有 `MapBuildService` / `OutputArtifactProvider` / API route。
3. 先寫 `tests/unit/core/test_markdown_summary_service.py`，確認 RED。
4. 實作 `MarkdownSummaryService`，讓 renderer 測試 GREEN。
5. 先補 artifact writer 與 `MapBuildService` 整合測試，確認 RED。
6. 實作 `map_markdown_path`、`write_markdown()` 與 `MapBuildService` 串接，讓測試 GREEN。
7. 先補 CLI 測試，確認 stdout 缺 Markdown path。
8. 更新 CLI 輸出 JSON / Markdown path。
9. 先補 web route 測試，確認 `/api/map/report` 尚不存在。
10. 實作 report view / download endpoint。
11. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
12. 執行完整測試與品質檢查。

## 測試方式

### RED / GREEN 驗證

- `tests/unit/core/test_markdown_summary_service.py`
- `tests/unit/core/test_output_artifact_provider.py`
- `tests/integration/test_map_build_service.py`
- `tests/cli/test_map_command.py`
- `tests/web/test_map_routes.py`

### 最終驗證

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 測試結果

- `.venv/bin/pytest`：282 passed
- `.venv/bin/ruff check .`：All checks passed
- `.venv/bin/mypy`：Success, no issues found in 85 source files

## 遇到的問題與處理

### Markdown secret masking 測試資料未進入輸出路徑

一開始把 fake secret 加在 evidence value，但 MVP Markdown 不輸出 evidence values，因此測試沒有真正驗證 renderer masking。

處理方式：

- 改把 fake secret 放進會被 render 的 risk rationale。
- 測試確認 full secret 不出現在 Markdown。
- renderer 仍使用 `SecretMaskingService.mask_text()` 處理自由文字。

### Markdown 不一定會出現 masking marker

整合測試原本要求 Markdown 也要出現 `[MASKED]` 或 `...`。但若 Markdown 沒有輸出 secret-bearing field，沒有 marker 是合理結果。

處理方式：

- JSON artifact 保留 masking marker 測試。
- Markdown artifact 驗證重點改為不含 `sk-test` full fake secret。

### ruff 格式問題

新增 renderer 後 ruff 發現一行超過 79 字元，以及 import block 需格式化。

處理方式：

- 拆行。
- 使用 ruff 自動修正 import block。

## 驗收對照

- Local web API map build result 同時指向 `ai_system_map.json` 與 `ai_system_map.md`：已完成。
- CLI 後續接上時應重用同一個 artifact generation service：已完成，CLI thin adapter 仍只呼叫 `MapBuildService`。
- Markdown 包含設計文件指定 sections：已完成並有單元測試。
- Markdown 不包含 full fake secret：已完成並有單元 / 整合測試。
- Markdown content 只依賴 validated map：已完成，renderer API 不接收 `project_path`。
- `MarkdownSummaryService.render(validated_map)` 回傳 `str`：已完成。
- `recommended_next_checks` 以 `- [ ]` 呈現：已完成並有單元測試。
- `pyproject.toml` 不新增 Jinja2：已遵守。
- `MapBuildResult` / API artifact metadata 包含 Markdown path：已完成。
- Frontend 可透過 local API 取得 Markdown report content：已完成。
- Route 不接受任意 local path：已完成並有 route 測試。
- 下載模式使用受控 latest artifact 並加 `Content-Disposition`：已完成。

## 後續注意

- 若未來 Markdown sections 顯著變複雜，可再評估 template engine，但 template 不可承擔 secret masking 或 schema decision logic。
- 若 Task 26 導入 persistent session/history，`GET /api/map/report` 可擴充成受控 artifact id，但仍不可接受 raw local path。
