# 2026-06-11 Phase24 Scan Boundary Review REP

## 實作邏輯
- Task 24 已移除 Template Import，實作重心為 scan boundary review。
- Scan boundary review 已從「替下一次 scan 做 policy overlay」改為 `POST /api/scans` 的 same-run gate。
- 每次正式 project scan 前，先用 deterministic inventory 檢查 `.env`、secret-like config、vector persistence path 等 suspicious target。
- 若有未決 target，`POST /api/scans` 回 `requires_boundary_decision`，`build_result = null`，不寫 artifact、不更新 `/api/map`。
- 使用者只選本次 scan 要不要掃：
  - `scan_this_run`
  - `skip_this_run`
- Decision 必須 match `target_path + fingerprint`；內容或 metadata 改變時，舊 decision 不得放行新內容。
- Decision 不保存成歷史偏好，不支援 `always_skip`、`metadata_only`、`masked_summary_only`、`scan_normally`。
- Response 僅包含 project-relative path、fingerprint、masked/bounded evidence packet，不包含 raw file contents、full secret 或本機絕對路徑。
- GitHub Issue #46 與 PR #119 已同步 scope，移除 Template Import / Scan Profile Catalog，避免 PR 關閉未完成或已降 scope 的需求。

## 步驟
1. 依 TDD 先新增 failing web tests，固定 `/api/scans` 遇到 `.env` 時回 `requires_boundary_decision`，且不更新 latest `/api/map`。
2. 依 TDD 補 unit tests，固定 stateless proposal、same-run `scan_this_run` / `skip_this_run` overlay、stale fingerprint 重新 pending、hard-skipped target 不產生 user proposal。
3. 移除舊 5-action policy engine，只保留 `scan_this_run` / `skip_this_run`。
4. 移除 scan boundary repository / persisted decision lifecycle；`ScanBoundaryReviewService` 改為 stateless helper。
5. `MapBuildService` 改為只接受上層傳入的 optional `inventory_policy`，不直接依賴 scan boundary service。
6. `POST /api/scans` 加入 boundary preflight：有 unresolved proposal 時直接回 `requires_boundary_decision`；沒有 unresolved 時才呼叫 `MapBuildService.build()`。
7. 移除舊 `/api/scan-boundary-proposals` route 與 create/list/decision trace scripts。
8. 更新 `scripts/trace_scan_boundary_policy_overlay.sh`，驗證 same-run gate。
9. 更新 `docs/API-GUIDE.md`、`docs/work/Timmy/design/epic1-local-api-guide.md`、Task24 plan/TODO。
10. 保留先前安全修正：decision reason / evidence packet 仍會遮蔽 secret 與本機絕對路徑，`path_safety_service` 已支援 macOS `/private/var/...` tmp path redaction。
11. 依 `/review` subagent feedback 收斂：移除 local API guide 中「decision 保存於 repository」的舊描述，並縮窄 vector persistence 判斷，避免 `src/vector_store.py` 這類原始碼被誤攔。

## 測試方式
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_scan_boundary_review_service.py tests/web/test_scan_boundary_routes.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_scan_boundary_review_service.py tests/unit/core/test_project_scan_service.py tests/web/test_scan_boundary_routes.py tests/web/test_project_scan_routes.py tests/web/test_mapping_routes.py tests/web/test_mapping_proposal_routes.py tests/web/test_detail_scan_routes.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider`
- `.venv/bin/ruff check src tests`
- `.venv/bin/ruff format --check src tests`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src tests`
- `git diff --check`
- `scripts/trace_scan_boundary_policy_overlay.sh --start-server`

## 遇到的問題與解法
- 原始 Task24 report 採 next-run overlay，但產品語意應是「這次正式掃描前先決定掃不掃」。解法：將 boundary review 移入 `POST /api/scans` same-run gate。
- 舊 `always_skip` / `metadata_only` / `masked_summary_only` 會引入長期 policy 與額外 audit state。解法：刪除這些 action，保留兩個使用者能理解的本次選項。
- 舊 `/api/scan-boundary-proposals` create/list/decision route 會讓使用者誤以為要先建立 proposal、再影響下次掃描。解法：移除 route，改由 `/api/scans` 回 pending proposals。
- `MapBuildService` 若直接依賴 scan boundary service，會把 boundary gate 混進 map build pipeline。解法：`MapBuildService` 只接受 optional `inventory_policy`，由 scan route 決定何時傳入。
- Canonical `ai_system_map.scan_summary` 不保存 skipped file 明細，只保存 count。Web tests 改以 public API behavior 驗證 files count、status 與 secret 不外洩，不擴張 canonical schema。
- Review 發現 local API guide 仍殘留「decision 保存於 repository」舊語意。解法：改成 decision 只存在於本次 `POST /api/scans` request。
- Review 發現 vector path heuristic 若用任意字串包含，會把 `src/vector_store.py` 誤判成 persistence target。解法：加入 regression test，並改成只有非 source/doc 類檔案且 path/suffix 顯示為 vector persistence artifact 時才 gate。

## 測試結果
- Targeted scan boundary unit/web tests：12 passed。
- Broader affected suite：39 passed。
- Full pytest：435 passed。
- Ruff lint：All checks passed。
- Ruff format check：154 files already formatted。
- Mypy：Success，140 source files no issues。
- Diff whitespace check：`git diff --check` passed。
- Trace：`scripts/trace_scan_boundary_policy_overlay.sh --start-server` passed，確認第一次回 `requires_boundary_decision`、第二次帶 `scan_this_run` 完成、第三次不記憶 decision。
- `/review` subagent：Standards / Spec 實質 findings 已修正；剩餘「origin/main...HEAD diff 為空」是因為當時尚未 commit，後續由本 branch commit 解決。

## 最終狀態
- Task24 scan boundary review 已改為 same-run gate。
- Template Import 已明確從 Task24 移除，不再作為本任務工項。
- Project upload / GitHub URL ingestion 仍不屬於 Task24，維持 Task25 或後續獨立任務範圍。
