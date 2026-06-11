# 2026-06-11 Phase24 Scan Boundary Review TODO

## 實作邏輯
- Task 24 現在只保留 scan boundary review，不再實作 template import。
- 目標是建立 pending-only proposal lifecycle，讓使用者針對可疑掃描邊界做決策。
- 決策不能回頭修改目前的 `FileInventory` 或 `ai_system_map.json`，只能在下一次 scan 透過 policy overlay 生效。
- Overlay 必須使用 path + fingerprint；若同一路徑內容或 metadata 改變，既有決策不得無腦套用。
- 未決 suspicious file 不能第一次就交給 provider 深入讀取；project session scan 必須先把它 hold 在 `pending_boundary_review`。
- `scan_normally` 不是永久授權，只在 path + fingerprint 仍相同時讓 target 交回一般 scanner/provider 規則。
- API 必須走 project session：`POST /api/projects/import` -> `POST /api/scans` -> scan boundary proposal。

## 步驟
1. 已完成：先寫 unit tests，覆蓋 proposal 產生、fingerprint、decision lifecycle、policy overlay。
2. 已完成：寫 web route tests，覆蓋 create/list/decision、unknown project、map not loaded、canonical map 不被 mutation。
3. 已完成：確認 RED，測試因缺少 `scan_boundary` model/service 失敗。
4. 已完成：實作 `scan_boundary.py` models。
5. 已完成：實作 `ScanBoundaryReviewService`、in-memory repository、policy overlay。
6. 已完成：將 overlay 接到 `ProjectScanService` / `MapBuildService` / scan route。
7. 已完成：建立 FastAPI routes 與 schemas，並註冊到 app。
8. 已完成：更新 `docs/API-GUIDE.md`、`epic1-local-api-guide.md`、Task 24 plan。
9. 已完成：新增 `scripts/trace_scan_boundary_proposals_create.sh`、`scripts/trace_scan_boundary_proposals_list.sh`、`scripts/trace_scan_boundary_proposals_decision.sh`，並串進 `scripts/trace_all.sh`。
10. 已完成：執行相關測試、全量 pytest、ruff、mypy 與新增 API trace scripts。
11. 已完成：補 TDD regression，確認 `.env` 第一次 project scan 會先 `pending_boundary_review`，不交給 config parser；`scan_normally` decision 後下一次才正常掃描。
12. 已完成：新增 `scripts/trace_scan_boundary_policy_overlay.sh`，用 shell 端到端驗證第一次 hold、proposal、`scan_normally`、第二次 scan 放行。

## 驗證重點
- 已驗證：Proposal response 不含 raw secret 或本機絕對路徑。
- 已驗證：Decision 只保存於 KAI-Mind-managed repository，不寫入被掃描 repo。
- 已驗證：`always_skip` / `metadata_only` / `masked_summary_only` 只在 fingerprint match 時生效。
- 已驗證：未決 suspicious file 會先 hold，fingerprint 變更或 `skip_this_run` 用完後會回到 `pending_boundary_review`，不會直接正常掃描。
- 已驗證：`POST /api/map/build` 不會建立 project-scoped boundary proposal。
