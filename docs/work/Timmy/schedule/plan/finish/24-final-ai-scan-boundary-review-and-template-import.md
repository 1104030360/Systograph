# Task 24: Final Epic 1 Scan Boundary Review

## 目標
完成 Epic 1 最後一段「正式掃描前的人工邊界確認」能力：`POST /api/scans` 在 provider collection 前先檢查 suspicious file，若需要使用者決定，先回 `requires_boundary_decision`，不產生 map、不寫 artifact、不更新 `/api/map`。

白話流程：

```text
POST /api/projects/import
  -> POST /api/scans
  -> deterministic FileInventory
  -> ScanBoundaryReviewService preflight
  -> if unresolved suspicious target:
       status = requires_boundary_decision
       boundary_proposals[]
       build_result = null
     else:
       apply same-run boundary_decisions
       run provider collection
       build ai_system_map artifacts
```

使用者只需要回答本次 scan 要不要掃：

- `scan_this_run`
- `skip_this_run`

不提供 `always_skip`、`metadata_only`、`masked_summary_only`、`scan_normally`，也不保存使用者過去選擇。

## 重要決策：移除 Template Import 工項（2026-06-11）
`Local Template Import / Scan Profile Catalog` 已從 Task 24 移除，不再作為本任務實作項目。

移除原因：

- 一般使用者真正期待的是「匯入 GitHub repo / 本機資料夾 -> 掃描 -> confirm component」，不是自行準備 `systograph-template.yaml`。
- 目前已完成的 `ManualMappingService` / `MappingProposalService` 更符合一般使用者的客製化流程。
- Epic 1 目前 canonical template selection 仍固定 `rag-core-v1`，即使匯入 scan profile 也不能立即套用，容易讓使用者困惑。
- `Template Import` 容易被誤解成 project import、RAG framework import、GitHub template import，和實際產品主流程衝突。
- 若未來真的需要，應另開 P3/admin feature，例如 `Scan Profile Catalog`，並等到多個內建 scan profiles 與 template activation policy 清楚後再做。

因此 Task 24 不再做：

- `TemplateImportService`
- `POST /api/templates/import`
- `GET /api/templates`
- `systograph-template.yaml` import
- archive / folder template package validation
- template quarantine / digest / provenance catalog

## 外部查證結論（2026-06-11）
外部工具經驗仍支持「fingerprint、防止污染被掃描 repo、策略與 scanner 分離」方向，但產品層不再提供長期 suppression / policy store。

已查證來源：

- Gitleaks 官方 README：支援 `--baseline-path`、`.gitleaksignore` 與 finding `Fingerprint`。來源：https://github.com/gitleaks/gitleaks
- Semgrep 官方文件：`semgrep scan --config` 可使用 registry rules、local YAML-defined rules、multiple config。來源：https://docs.semgrep.dev/running-rules
- Trivy 官方文件：misconfiguration scan 支援以 Rego 撰寫 custom checks。來源：https://trivy.dev/docs/latest/tutorials/misconfiguration/custom-checks/
- TruffleHog 官方 README：結果可區分 `verified` / `unknown` / `unverified`，並支援 JSON output。來源：https://github.com/trufflesecurity/trufflehog

對 Task 24 的落地影響：

- Boundary decision 只跟本次 `POST /api/scans` request 一起送入，不寫入被掃描 repo，也不保存成 Systograph 長期偏好。
- Decision 必須依 `target_path + fingerprint` 套用；同一路徑內容或 metadata 改變時，舊 decision 不得放行新內容。
- Response 只提供 project-relative path、fingerprint、masked/bounded packet，不提供 raw file content、raw secret 或本機絕對路徑。

## 已完成、必須承接但不要重做
- Task 16 已完成 local API shell，但 `POST /api/map/build` 仍是 viewer demo 捷徑，不建立 `project_id`。
- Task 18 已完成 `ViewerSessionService` / viewer payload 路線，web route 採獨立 `routes/*.py` + `web/schemas.py`。
- Task 19 已完成 `ManualMappingService`、repository protocol / in-memory implementation、`/api/mappings` routes。
- Task 20 已完成 pending-only `MappingProposalService`、`MappingEvidencePacketBuilder`、`/api/mapping-proposals` lifecycle。
- Task 21 已完成 target-scoped detail scan。
- Task 22 已完成 opt-in query trace。
- Task 23 已完成 local API hardening、path safety、snapshot safety、stable masked error 與 `docs/API-GUIDE.md` 更新。
- Task 25 已明確把 project upload ingestion 拆走；archive scan input 不屬於本任務。

## Task 24 最新實作狀態（2026-06-11）

目前 scan boundary review 已改為 same-run gate，backend/core/API 落地。

已實作檔案：

- `src/systograph/core/models/scan_boundary.py`
- `src/systograph/core/services/scan_boundary_review_service.py`
- `src/systograph/core/services/project_scan_service.py`
- `src/systograph/core/services/map_build_service.py`
- `src/systograph/web/routes/scan_routes.py`
- `src/systograph/web/app.py`
- `src/systograph/web/schemas.py`
- `tests/unit/core/test_scan_boundary_review_service.py`
- `tests/web/test_scan_boundary_routes.py`
- `docs/API-GUIDE.md`
- `docs/work/Timmy/design/epic1-local-api-guide.md`
- `scripts/trace_scan_boundary_policy_overlay.sh`

### A. Scan boundary review models
- 已完成：建立 `ScanBoundaryEvidencePacket`。
- 已完成：建立 `ScanBoundaryProposal`。
- 已完成：建立 `ScanBoundaryDecisionRequest`，作為本次 scan request 的 per-target decision。
- 已完成：型別沒有重用 `mapping.py`；scan boundary decision 和 component mapping decision 是不同 domain。

### B. ScanBoundaryReviewService
- 已完成：改為 stateless helper，不保存 proposal / decision history。
- 已完成：根據 `FileInventory` 產生 bounded review packet。
- 已完成：suspicious target 只涵蓋原本可掃、但需要使用者確認的 path，例如 secret-like config / vector persistence path。
- 已完成：已由 deterministic scanner hard-skip 的 model/log/dependency/cache target 不產生使用者 decision proposal。
- 已完成：proposal response masked / bounded / traceable，不包含 raw secret 或本機絕對路徑。

### C. User decisions
user decision 只支援：

- `scan_this_run`
- `skip_this_run`

已完成：

- `scan_this_run` 只讓 matching target 在本次 scan 進入 provider collection。
- `skip_this_run` 只讓 matching target 在本次 scan 移到 skipped，reason 為 `skipped_by_policy_overlay`。
- Decision 必須 match `target_path + fingerprint`。
- Decision 不 retroactively 修改已產生 artifact，不保存成長期 policy。

### D. Local API
已完成：

- `POST /api/scans` 回傳 `status = "requires_boundary_decision"` 時，`build_result = null` 且包含 `boundary_proposals[]`。
- `POST /api/scans` 帶完整 `boundary_decisions[]` 後才正式建立 map。
- `POST /api/map/build` 不走 project-scoped boundary gate。
- 舊 `/api/scan-boundary-proposals` create/list/decision route 已移除。

## 不包含範圍
- 不讓 AI / rule helper 自動修改 canonical inventory。
- 不把 boundary review decision 寫進被掃描 repo。
- 不保存使用者過去的 scan boundary 選擇。
- 不做 project upload / multipart ingestion；那是 Task 25。
- 不做 GitHub URL project ingestion。
- 不做 local template import / scan profile catalog。
- 不做 frontend modal / review queue UI；本任務只提供 backend/API contract。

## 實作步驟對照
1. 已完成：建立 scan boundary core models，不重用 `mapping.py`。
2. 已完成：實作 stateless `ScanBoundaryReviewService` deterministic proposal / one-run decision overlay。
3. 已完成：更新 `ProjectScanService` inventory policy extension。
4. 已完成：更新 `MapBuildService`，只接受上層傳入的 optional `inventory_policy`，不直接依賴 scan boundary service。
5. 已完成：更新 `POST /api/scans` same-run gate。
6. 已完成：移除舊 scan boundary repository 與 `/api/scan-boundary-proposals` route。
7. 已完成：更新 `docs/work/Timmy/design/epic1-local-api-guide.md` 與 `docs/API-GUIDE.md`。
8. 已完成：寫 unit / web tests，驗證 same-run gate、masking、no absolute local path、no canonical mutation、project-session-only。

## 驗收標準狀態
- 已驗證：unresolved suspicious file 會讓 `POST /api/scans` 回 `requires_boundary_decision`，不會第一次就交給 provider 完整深讀。
- 已驗證：`requires_boundary_decision` 不寫 artifact、不更新 `/api/map`。
- 已驗證：`scan_this_run` 後同一個 request 才進正式 scanner/provider。
- 已驗證：`skip_this_run` 只影響本次 scan。
- 已驗證：下一次 scan 不會記住前一次 decision。
- 已驗證：decision payload / response 不顯示 full secret 或本機絕對路徑。
- 已驗證：`POST /api/map/build` 不會偷偷觸發 boundary review。
- 已驗證：unknown `project_id` 回 404 typed error。

## 可能風險與注意事項
- 不要把 Task 24 做成第二套 scanner pipeline。
- 不要把 boundary review proposal 跟 manual mapping proposal 混成同一個 model；兩者生命週期相似，但目標與安全邊界不同。
- 任何 AI/provider 輸出都只能是 proposal，不是 source of truth。
- 這個任務的價值是補正式 scan 前的 boundary safety，不是新增 project import，也不是新增 template system。

## 視覺化說明
```text
project session
  -> deterministic inventory
  -> ScanBoundaryReviewService preflight
  -> unresolved suspicious files?
       yes -> requires_boundary_decision, no map artifact
       no  -> apply one-run decisions and build map

important:
  proposal does not mutate current FileInventory
  proposal does not mutate current ai_system_map.json
  decision does not write to scanned repo
  decision is not remembered after this request
```
