# 2026-06-11 Phase24 Scan Boundary Review TODO

## 實作邏輯
- Task 24 只保留 scan boundary review，不實作 template import。
- Scan boundary review 改為 `POST /api/scans` 的 same-run gate。
- 每次正式 scan 前先檢查 suspicious file；若有 `.env`、secret-like config、vector persistence path 等 target，先回 `requires_boundary_decision`。
- 使用者只選本次 scan 要不要掃：`scan_this_run` 或 `skip_this_run`。
- Decision 必須 match `target_path + fingerprint`，不保存成歷史偏好，也不支援永遠跳過。
- `POST /api/map/build` viewer demo flow 不走 project-scoped boundary gate。

## 步驟
1. 已完成：先寫 web regression，固定 `/api/scans` 遇到 `.env` 時回 `requires_boundary_decision`，且不更新 `/api/map`。
2. 已完成：先寫 unit regression，固定 stateless proposal / decision overlay 行為。
3. 已完成：移除舊 `always_skip`、`metadata_only`、`masked_summary_only`、`scan_normally` action。
4. 已完成：移除 scan boundary repository / persisted decision lifecycle。
5. 已完成：將 `ScanBoundaryReviewService` 改為 stateless helper：產生本次 proposals、套用本次 decisions、輸出 one-run inventory policy。
6. 已完成：把 `/api/scans` 改成 preflight gate；有未決 proposal 時不呼叫 `MapBuildService.build()`。
7. 已完成：讓 `MapBuildService` 只接受上層傳入的 `inventory_policy`，不直接依賴 scan boundary service。
8. 已完成：移除舊 `/api/scan-boundary-proposals` route 與 create/list/decision trace scripts。
9. 已完成：更新 API guide、local API guide、Task24 plan/report。
10. 已完成：跑 targeted tests、full pytest、ruff、mypy、`git diff --check` 與 trace script。

## 驗證重點
- `requires_boundary_decision` response 不含 raw secret、本機絕對路徑或 raw file contents。
- 未決 scan 不寫 map artifact、不更新 latest `/api/map`。
- `scan_this_run` 只影響本次 scan，下一次仍需重新決策。
- `skip_this_run` 只影響本次 scan，不保存為永久跳過。
- stale fingerprint decision 不會放行新內容。
- 不影響 `/api/map/build`、manual mapping、mapping proposal、detail scan、query trace。
