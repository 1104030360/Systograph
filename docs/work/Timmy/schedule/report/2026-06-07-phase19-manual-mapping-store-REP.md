# 2026-06-07 Phase 19 Manual Mapping Store Report

## 實作邏輯
Phase 19 的核心是保存 project-level manual mapping decision，不直接修改 `ai_system_map.json`，也不把一次 confirmation 推廣成新的 canonical template。

本次實作採用以下資料流：

```text
unmapped component
  -> POST /api/mappings
  -> ManualMappingService validation
  -> ManualMappingRepository
  -> next /api/scans with same project_id
  -> ComponentDetectionService manual hook
  -> normalized ai_system_map.json
```

Route 只呼叫 `ManualMappingService`，不直接讀寫 artifact、DB row 或被掃描 repo。Confirmed mapping 只有在下一次 scan / normalize，且 source evidence 仍存在時，才會影響 canonical map。

## 實作步驟
1. 建立 `ManualMapping` domain model，支援 `confirmed`、`rejected`、`skip_for_now`、`not_applicable`。
2. 建立 `ManualMappingService`，負責 validation、digest、create/update/list，以及把 confirmed decision 套回 `ComponentDetectionResult`。
3. 建立 repository protocol 與 in-memory implementation，並在 `src/kai_mind/storage/repositories.py` 暴露 storage boundary。
4. 建立 `/api/mappings` list/create/patch routes。
5. 修改 `create_app()`，讓 local API 持有同一個 `ManualMappingService`。
6. 修改 `/api/scans` 與 `MapBuildService.build()`，使用同一個 `project_id` 重新 scan 時套用 confirmed mappings。
7. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補上 mapping routes 與下次 scan 生效規則。
8. 更新 Task 19 plan，記錄目前完成範圍與 Task 27 PostgreSQL storage 邊界。

## 測試方式
新增測試：

- `tests/unit/core/test_manual_mapping_service.py`
  - confirmed mapping persistence / digest。
  - invalid slot rejection。
  - reject / skip / not_applicable audit-only decision。
  - unmasked secret-like payload rejection。
  - dangling extension edge rejection。
  - project isolation。
- `tests/integration/test_manual_mapping_component_detection.py`
  - confirmed mapping 把 unmapped evidence 套入 existing slot。
  - rejected mapping 不改 canonical component result。
- `tests/web/test_mapping_routes.py`
  - `/api/mappings` create/list/patch。
  - invalid slot 422。
  - route 不 mutate current `/api/map` payload。
  - confirmed mapping 在同一 project 下一次 `/api/scans` 生效。

## 遇到的問題與解法
- 問題：一開始測試用 `reranker` evidence，現有 detection 會先產生 extension candidate，不會進 `unmapped_components`。
  - 解法：改用 dependency-only Chroma signal，符合現有 weak dependency -> unmapped behavior。
- 問題：`/api/mappings` 可以保存 decision，但一開始 `/api/scans` 沒有把 project-level mapping service 接進 build pipeline。
  - 解法：讓 `MapBuildService.build()` 接受 optional `project_id`，並在 detection 階段使用同 repository 的 project-scoped manual mapping hook。
- 問題：Task 19 plan 已更新為 PostgreSQL-backed storage 方向，但 Task 27 concrete storage 尚未落地。
  - 解法：本次建立 repository boundary 與可注入 implementation；具體 PostgreSQL repository、Alembic migration、DB URL 設定保留給 Task 27。

## 測試結果
```bash
.venv/bin/pytest tests/unit/core/test_manual_mapping_service.py tests/integration/test_manual_mapping_component_detection.py tests/web/test_mapping_routes.py -q
# 15 passed

.venv/bin/ruff check src tests
# All checks passed

.venv/bin/mypy src tests
# Success: no issues found

.venv/bin/pytest -q
# 308 passed
```

## 驗收狀態
- Confirmed mapping 不寫入 project root：已完成。
- Invalid mapping 不進 canonical JSON：已完成。
- Rerun scan 可重現 confirmed mapping：已完成。
- Reject / skip / not_applicable 不會產生 slot、extension 或 flow edge：已完成。
- Web route 不直接 mutate 既有 artifact：已完成。
- API guide 已同步：已完成。
- PostgreSQL concrete repository：未在 Phase 19 直接完成，交由 Task 27 storage layer 落地。
