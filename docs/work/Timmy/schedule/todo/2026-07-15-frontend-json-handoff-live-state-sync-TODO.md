# Frontend JSON Handoff Live-State Sync TODO

## 目標

以 2026-07-15 live backend、frontend consumer、Plan 13、Plan 19／20、API 與 model
contracts 為依據，更新 `docs/work/Timmy/design/EPIC1/frontend-json-handoff/`，讓每份文件與
sample 明確區分 current runtime、current backend model 與 planned target。

## 本次完成項目

- [x] 讀取並遵守 repo `AGENTS.md`；本次沒有專案結構或長期規則變更，因此不修改它。
- [x] 對照 `src/`、`frontend/src/`、`docs/spec/`、`API-GUIDE.md`、
  `MODEL-CONTRACT.md`、Plan 13 與已完成 Plan 05～09 reports。
- [x] 修正 Step 3：current Phase A 是 KAI deterministic providers，UA-primary 是 future
  Phase B。
- [x] 修正 Step 4 sample，使其通過 current `AiSystemMapV2`，並標明 public runtime 仍是
  v1、Plan 13 仍 blocked。
- [x] 修正 Step 6／7 文件：richer backend graph、52 reference nodes、profile overlays 與
  6 lenses 已實作；ArtifactRef 仍是 future target。
- [x] 修正 Step 7 graph sample，使其通過 current `GraphViewModel`。
- [x] 以 current `/api/viewer/load` response 收斂 Step 8 `ViewerPayload` sample，移除不存在的
  top-level aggregation 欄位，並明示 graph fixture 截短邊界。
- [x] 修正 Step 9：backend non-baseline candidate 已存在，frontend 仍是 legacy enum；
  Plan 13 尚未退役 normal extension write surface。
- [x] 保留並校正 Step 2 Plan 20 planned samples，補上 current frontend parser／modal 差距。
- [x] 分開 current `/api/trace` 與 deferred richer safe-linkage sample。
- [x] 完成 JSON、Pydantic、frontend parser／build、backend focused tests、trace script、link、
  secret/path 與 `git diff --check` 驗證。
- [x] 完成單代理逐檔 review、三個 runtime 假設與最終格式清理。
- [x] 建立對應 implementation report，記錄實際測試結果與未完成 integration gaps。

## 後續 owner（不代表本次文件同步未完成）

- Plan 13：完成 00A Task 4／5 gates、v2 normal cutover、legacy mapping migration 與 normal
  `new_extension_component` write retirement。
- Plan 19／20：實作 inventory rules catalog、preflight／one-run selection、正式
  Pydantic／Zod／OpenAPI contracts 與 E2E safety gates。
- Frontend：切 project-scoped latest build、保留 rich graph fields／lenses／details、支援
  non-baseline capability candidate，並修正 pending response 無 `scan_id`。
- API design：若要導入 safe `ArtifactRef` lazy load，先凍結受控 fetch route、scope check 與
  schema tests，不得直接暴露 server-local path。
