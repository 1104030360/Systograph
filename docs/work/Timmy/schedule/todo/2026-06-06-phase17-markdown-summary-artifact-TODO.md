# 2026-06-06 Phase 17 Markdown Summary Artifact TODO

## 目標

完成 Task 17：從 validated `RagSystemMap` 產生 `ai_system_map.md`，並讓 local API 可以安全檢視 / 下載最新 Markdown report。

## 實作邏輯

- `ai_system_map.json` 仍是唯一 canonical truth。
- `MarkdownSummaryService` 只接收 validated `RagSystemMap`，只回傳 Markdown `str`。
- `MarkdownSummaryService` 不接收 `project_path`，不讀 raw project files，不寫檔。
- `OutputArtifactProvider` 負責寫出 `ai_system_map.md`。
- `MapBuildService` 在成功產生 JSON artifact 後，使用同一份 validated map 產生 Markdown artifact。
- Local API report endpoint 只讀 session latest build result 指向的受控 Markdown artifact，不接受任意 filesystem path。
- 不新增 Jinja2 dependency，先用 deterministic Python renderer。

## 階段規劃

### Phase A：Markdown renderer

1. 先寫 `tests/unit/core/test_markdown_summary_service.py`。
2. 驗證固定 sections 存在。
3. 驗證 slot coverage table 來自 `components_by_slot`。
4. 驗證 detected / missing slots、flows、endpoints、risk hints、recommended next checks 皆由 canonical map render。
5. 驗證 Markdown 不含 fake full secret。
6. 實作 `src/systograph/core/services/markdown_summary_service.py`。

### Phase B：Artifact writer 與 MapBuildService 串接

1. 先補 `OutputArtifactProvider.write_markdown()` 測試。
2. 先補 `MapBuildService` 整合測試，確認 `map_markdown_path` 存在且檔案寫出。
3. 更新 `MapBuildResult`，加入 `map_markdown_path`。
4. 更新 CLI output，成功時同時列出 JSON 與 Markdown artifact path。
5. 確認 precondition error 只產生 `map-error.md`，不產生 normal Markdown。

### Phase C：Local API report endpoint

1. 先補 `tests/web/test_map_routes.py`。
2. 驗證 build 後 `GET /api/map/report` 回傳 `text/markdown`。
3. 驗證 `GET /api/map/report?download=true` 回傳 attachment header。
4. 驗證未 build 前回傳 404。
5. 驗證 endpoint 不接受任意 path query。
6. 實作 route，從 session latest build result 讀受控 artifact。

### Phase D：文件、驗證、收尾

1. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
2. 更新 Task 17 plan 狀態或補充實作落點。
3. 執行相關測試，再執行完整測試。
4. 執行 ruff / mypy。
5. 撰寫 Phase 17 report。
6. 確認 Task 17 plan 驗收標準全部落地。

## 測試方式

- RED：每個 behavior 先寫測試並確認失敗。
- GREEN：用最小功能碼通過測試。
- REFACTOR：保持測試綠燈後再整理 helper 與命名。
- 最終驗證：
  - `.venv/bin/pytest`
  - `.venv/bin/ruff check .`
  - `.venv/bin/mypy`

## 注意事項

- 不重新掃描 project files。
- 不把 Markdown 當 schema source。
- 不在 Markdown renderer 重新實作 secret detector。
- 不增加任意 path file read API。
- 不破壞既有 `GET /api/map` viewer payload contract。
