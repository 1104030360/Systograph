# Step 2 — Scan Inventory Boundary Gate

Last updated: 2026-07-15（Plan 19 baseline + Plan 20 per-run selection target）

## 狀態與閱讀方式

本資料夾描述 **Plan 20 完成後的 planned frontend handoff target**，不是 2026-07-15 已上線的
runtime contract。Plan 20 Task 9 尚未完成前，正式 API 仍以 `docs/API-GUIDE.md`、
`docs/MODEL-CONTRACT.md` 與 current schemas 為準。

Current runtime 已有 `POST /api/scans` 與 sensitive boundary proposal，但還沒有
`POST /api/projects/{project_id}/scan-preflights`、`selection_context` 或 directory scope。

Current frontend 也尚未實作本 target：`projectScanApi.ts` 只有 import／scan，
`scanCreateResponseSchema` 仍要求所有 response 都有 `scan_id`，而
`decisionsForBoundary()` 對缺少的 choice 仍 fallback 成 `skip_this_run`。Plan 20 必須先讓
pending response 可省略 `scan_id`，並禁止 required decision 被 fallback 自動補值。

本資料夾的目的是讓 backend、frontend 與 QA 先對同一組 target JSON 開發；實作時仍要用
Pydantic、Zod、API contract tests 與 E2E tests 凍結正式 schema。

## Source of truth 與前提

1. [Plan 19：Inventory Selection Policy Catalog](../../../../schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory/19-add-scan-inventory-rules-toml.md)
   擁有 TOML schema、loader、matching、policy digest、baseline audit 與 fail-closed error。
2. [Plan 20：User-controlled Scan Inventory Selection](../../../../schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory-review/20-add-user-controlled-scan-inventory-selection.md)
   擁有 metadata-only preflight、one-run decision、directory scope、stale validation 與 lifecycle。
3. [Frontend Meeting-Sync handoff](../../../../../Meeting-Sync/meeting_sync_2026_07_15/frontend-inventory-selection-review.md)
   擁有畫面分區、state machine、copy、accessibility 與 frontend task checklist。

前提固定為：KAI-Mind 先提供已驗證、可獨立運作的 TOML product baseline，使用者只在這份
推薦基礎上調整「這一次」要掃或略過的 exact file／bounded recursive directory。

Plan 20 不是空白 file explorer，也不能在 catalog missing／invalid 時要求使用者自行重建
inventory。Frontend 不讀 TOML、不重算規則，也不保存永久偏好。

## Ownership 與安全邊界

| 項目 | 唯一 owner | Frontend 可以做的事 |
| --- | --- | --- |
| TOML baseline 與 policy digest | Backend / Plan 19 | 顯示版本與安全訊息，不解析 TOML |
| Candidate enumeration 與 ignore semantics | Backend | 呼叫 preflight，不碰 local filesystem |
| Hard safety | Backend | 顯示原因，不提供 override control |
| One-run selection | Backend 驗證；Frontend 收集 | 送 explicit delta + required decision |
| Final `FileInventory` | Backend | 不自行合成或保存第二份 inventory |
| Snapshot / build / viewer publish | Backend | completed 後重新載入 viewer |
| UA integration | Plan 16 future work | Plan 20 不呼叫、不顯示、不等待 UA |

固定 precedence：

```text
hard filesystem/content safety
  > explicit per-run user decision
  > project ignore + validated TOML default outcome
```

`scan_this_run` 只能重新納入 `soft_excluded` path；symlink、special file、`.git/**`、越界 path、
resource limit 與 post-decision unsupported content 仍不可覆寫。

## End-to-end JSON handoff

```text
+-------------------------- BACKEND ---------------------------+
| Plan 19 packaged scan_inventory_rules.toml                  |
|   -> load + validate schema                                 |
|   -> unavailable/invalid: typed error, fail closed          |
|   -> valid: schema version + policy digest                  |
+-------------------------------+------------------------------+
                                |
                                v
+-------------------------- FRONTEND --------------------------+
| Import project                                                |
|   -> POST /api/projects/{project_id}/scan-preflights          |
|      requested_paths[] + excluded-page cursor                 |
+-------------------------------+------------------------------+
                                |
                                v
+-------------------------- BACKEND ---------------------------+
| Metadata-only preflight                                      |
|   enumerate -> project ignore -> pre-content safety -> TOML  |
|   -> default included / soft excluded / hard blocked         |
|   -> exact file or bounded recursive directory proposals     |
|   -> preflight_request_id + fingerprints + summaries         |
|   X no candidate content read                                |
|   X no scan_id / snapshot / build                            |
+-------------------------------+------------------------------+
                                | InventoryPreflightResponse
                                v
+-------------------------- FRONTEND --------------------------+
| Review scan scope                                            |
|   Needs your decision                                        |
|   Excluded by default + pagination                           |
|   Add exact file or folder path                              |
|   Cannot be scanned / missing / over-limit                   |
|   -> keep state only for this run                            |
|   -> POST /api/scans                                         |
|      preflight_request_id + scoped boundary_decisions[]      |
+-------------------------------+------------------------------+
                                |
                                v
+-------------------------- BACKEND ---------------------------+
| Re-enumerate + authorize + validate fingerprint/scope        |
|   -> stale/missing/changed: typed error, no scan_id           |
|   -> required decision missing: pending, no scan_id           |
|   -> apply in-memory overlay                                 |
|   -> post-decision content/resource safety                   |
|   -> one final FileInventory + audit + run digest            |
|   -> ScanSnapshot S1 -> current providers -> Build B1        |
|   -> completed response with scan_id + selection summary     |
+-------------------------------+------------------------------+
                                |
                                v
+-------------------------- FRONTEND --------------------------+
| Discard preflight/choices -> refresh latest viewer payload   |
+--------------------------------------------------------------+

Apply confirmed mappings: reuse Snapshot S1; no preflight/repo read.
Rescan: create P2 + new decisions D2; never reuse D1 automatically.
Plan 20 stops here. UA request / files[] / sidecar / parity are deferred.
```

## Sample 索引

| Sample | 用途 |
| --- | --- |
| [`frontend-inventory-preflight-request-sample.json`](frontend-inventory-preflight-request-sample.json) | Import 後或 exact-path lookup 的 request |
| [`frontend-inventory-preflight-response-sample.json`](frontend-inventory-preflight-response-sample.json) | Baseline、proposal、pagination、directory summary 與 missing result |
| [`frontend-scan-selection-request-sample.json`](frontend-scan-selection-request-sample.json) | 使用者決策送回 `POST /api/scans` |
| [`frontend-scan-pending-response-sample.json`](frontend-scan-pending-response-sample.json) | Required decision 未完成；刻意沒有 `scan_id` |
| [`frontend-scan-completed-response-sample.json`](frontend-scan-completed-response-sample.json) | Final inventory 成功後的 additive summary |
| [`frontend-inventory-preflight-stale-error-sample.json`](frontend-inventory-preflight-stale-error-sample.json) | Preflight／fingerprint 過期，要求重新 review |
| [`frontend-inventory-rules-unavailable-error-sample.json`](frontend-inventory-rules-unavailable-error-sample.json) | Plan 19 catalog 不可用，fail closed |
| [`frontend-inventory-rules-invalid-error-sample.json`](frontend-inventory-rules-invalid-error-sample.json) | Plan 19 catalog 無效，fail closed |

所有 sample 都是假的 project id、path、digest 與時間。不得放入 absolute path、原始檔內容、
secret value、raw Git stderr 或未遮蔽 exception。

## 1. Preflight request

Endpoint：

```http
POST /api/projects/{project_id}/scan-preflights
```

Request 只帶掃描深度、要查的 project-relative exact paths 與 soft-excluded pagination。

- `requested_paths` 預設 `[]`，最多 100 筆。
- Project root 唯一合法值是 `.`。
- Path 使用 POSIX separator；不可為 absolute、traversal、blank 或 glob。
- Backend 用 `lstat` 判斷 file／directory；Frontend 不從尾端 `/` 猜 scope。
- 一個 preflight 最多 20 個 directory scopes。
- Cursor 是 opaque token，Frontend 不解析或自行產生。

輸入 directory 代表要求 backend 完整建立 bounded manifest，再回一筆
`selection_scope="recursive_directory"` proposal。Frontend 不會拿到 descendant manifest。

Directory hard bounds：每個 scope 與 aggregate 都受 5,000 unique files、500,000,000 selectable
bytes、64 depth 限制。超限時 fail closed，不可默默只處理前 N 筆。

## 2. Preflight response

成功 response 的 baseline identity：

```text
source_mode
inventory_policy_schema_version
inventory_policy_digest
candidate_set_digest
filesystem_safety_version
preflight_request_id
```

Frontend 不可用空 array 或 count `0` 猜 catalog 是否健康。只有成功 response 代表 baseline 可用；
catalog 問題必須以 `inventory_rules_unavailable`／`inventory_rules_invalid` 回傳。

### Proposal 分區

| JSON path | 語意 | Decision |
| --- | --- | --- |
| `required_boundary_proposals[]` | 預設會掃、但敏感而必須確認 | 必答 scan／skip |
| `reviewable_excluded_page.items[]` | `.gitignore`／catalog soft exclusion | 預設 skip；只送變更 |
| `requested_target_results[]` | exact file／directory 查詢結果 | 只有 `reviewable` 可決策 |
| `blocked_summaries[]` | hard block 或未展開 directory summary | 唯讀；不得送 decision |
| `warnings[]` | Stable warning code | 不從 copy 反推規則 |

同一 proposal 可能同時出現在 required、page 與 requested result。Frontend 必須以
`proposal_id` 去重，不能顯示或提交兩次。

### `selection_context`

Frontend 只 render backend 回傳的 enum：

```text
base_outcome: included | soft_excluded | mixed
review_kind: required_confirmation | optional_override
default_decision: scan_this_run | skip_this_run | null
decision_required: boolean
override_allowed: boolean
exclusion_sources[]
matched_inventory_policy_ids[]
target_kind: file | directory
selection_scope: exact_file | recursive_directory
directory_summary: null | bounded counts
```

`reason` 是顯示文字，不是 machine-readable enum。Frontend 不依 extension、reason、counts 或
source copy 自行判斷 hard／soft，也不自行重算 directory `base_outcome`。

Preflight 尚未取得內容授權，因此 `evidence_packet.masked_evidence_values` 與
`masked_snippets` 必須固定為空 array。

### Directory summary

Frontend 只會拿到 counts 與 manifest fingerprint：

```text
observed_regular_file_count
selectable_file_count
default_included_count
soft_excluded_count
sensitive_file_count
pre_content_hard_blocked_count
selectable_bytes
observed_max_relative_depth
blocked_reason_counts
```

`DirectorySelectionManifest.entries[]` 是 backend internal model，永遠不進 API payload。

## 3. Frontend state 與畫面

Frontend 只在記憶體保存：

```text
projectSession
preflightResponse
latestPreflightRequestId
decisionByProposalId
requestedExactPaths
directoryScopeSummaryByProposalId
reviewableExcludedPages
flowStatus
inlineError
```

畫面沿用既有 `BoundaryDecisionModal`，使用者可見標題改為 `Review scan scope`。不要新增第二套
file picker modal，也不要重用 Step 9 Manual Mapping store。

建議畫面分區：

```text
+------------------------------------------------------------------+
| Review scan scope                                                |
| KAI-Mind prepared a recommended baseline for this project.       |
| Adjustments apply once; project rules are not modified.          |
+------------------------------------------------------------------+
| Summary: included | excluded | blocked | missing                 |
+------------------------------------------------------------------+
| Needs your decision                                              |
| Excluded by default                                  [Load more] |
| Add exact file or folder path                         [Check]     |
| Cannot be scanned / not found                                   |
+------------------------------------------------------------------+
| [Cancel]                                           [Continue]    |
+------------------------------------------------------------------+
```

Required row 不預選；soft-excluded 預設 skip；exact included file 預設 scan。Reviewable directory
不預選，必須選「掃描全部可掃描檔案」或「略過全部可掃描檔案」，或移除該 requested path。

Frontend 不建立整庫 checkbox tree。Default included 一般檔只顯示 summary count；只有 backend
主動提出、soft-excluded 分頁或使用者 exact-path 查詢的 target 才進 review rows。

## 4. Decision 回傳與 one-run 覆寫

Frontend 完成 review 後呼叫：

```http
POST /api/scans
```

每筆 decision 只傳：

```text
target_path
fingerprint
decision: scan_this_run | skip_this_run
selection_scope: exact_file | recursive_directory
optional bounded reason
```

Frontend 不 echo base outcome、source、policy id、counts、size 或完整 candidate list。Backend 不信任
client facts，會重新 enumeration、授權、比對 digest／fingerprint，並重算 directory aggregate。

Decision array 固定為「required decisions + explicit deltas」：

| Case | 沒送 decision 時 | 何時要送 |
| --- | --- | --- |
| Sensitive included file | pending | 一定要 scan／skip |
| Soft-excluded file | 保持 skip | 使用者改成 scan |
| Exact requested included file | 保持 scan | 使用者改成 skip |
| Reviewable directory | 未完成 review | 一定要 scan／skip |
| Hard／missing／empty／over-limit | 不可決策 | 永遠不送 |

Directory decision 是一筆 `recursive_directory` scope，不是由 browser 展開成數千筆 file decisions。
Backend 會把有效 decision 套到 manifest descendants，並在 audit 中記錄共同的 target path/scope。

這裡的「覆寫」只存在於本次 scan 的 backend in-memory overlay。它不寫回 TOML、`.gitignore`、
target repo、Manual Mapping 或 durable user preference。

## 5. Response lifecycle

### Pending

Required decision 不完整時回 `status="requires_boundary_decision"`。Response 可以帶 proposal 與
`preflight_request_id`，但 **不得有 `scan_id`、snapshot、build 或 artifact**。

Frontend 保持 dialog 開啟，補完 required decisions 後再送一次；不能把 missing required decision
自動序列化成 `skip_this_run`。

### Stale／missing／changed

Preflight、policy、candidate、file metadata 或 directory manifest 改變時，backend 回 typed error，
且不建立 `scan_id`。

Frontend 重新 preflight，只保留 `target_path + selection_scope + fingerprint` 完全相同的 choice。
任何一項改變都清除 choice；不得自動重送舊 decision。

### Completed

Backend 先完成 post-decision safety，再建立唯一 final `FileInventory`、snapshot 與 build。Completed
response 才能帶真實 `scan_id`、`build_result` 與 additive `inventory_selection_summary`。

Frontend 不從 preflight 或 decision 自行算完成結果。它丟棄 one-run state，再走既有 latest-build
／viewer refresh；summary 只用來解釋實際納入與阻擋數量。

## 6. Apply、Rescan 與 downstream

```text
New scan / Rescan
  Preflight P1 -> Decisions D1 -> Final inventory R1
  -> Snapshot S1 -> Initial Build B1 -> current Step 3 providers -> Viewer

Apply confirmed mappings
  Snapshot S1 -> Build B2 -> Step 4...7 replay
  X no preflight, no repo read, no new selection

Next Rescan
  Preflight P2 -> Decisions D2 -> Final inventory R2 -> Snapshot S2
  X D1 does not become a default
```

Snapshot 保存 policy、candidate、decision 與 final inventory digests，以及 per-file selection audit。
Preflight response 本身不是 durable project resource，也不建立 `/api/inventory-decisions`。

Plan 20 到 current scanner providers、snapshot 與 build pipeline 為止。**不建立 UA request、不傳
`files[]`、不呼叫 sidecar、不新增 parity test，也不新增任何 UA frontend 欄位。**

## 7. Stable error surface

| HTTP | `detail.code` | Frontend action |
| ---: | --- | --- |
| 404 | `project_not_found` | 回 project import error |
| 422 | `inventory_selection_path_invalid` | exact-path inline error |
| 422 | `inventory_selection_scope_invalid` | 重新 preflight，不猜 scope |
| 422 | `inventory_selection_duplicate_decision` | 阻止 submit，保留 review state |
| 422 | `inventory_selection_conflicting_decision` | 阻止 submit，保留 review state |
| 422 | `inventory_selection_override_not_allowed` | 顯示不可覆寫原因 |
| 422 | `inventory_selection_directory_limit_exceeded` | 顯示 limit/at-least，要求較小 scope |
| 422 | `inventory_selection_directory_no_scannable_files` | 顯示 blocked summary，不建立 scan |
| 422 | `inventory_preflight_review_limit_exceeded` | 中止並縮小 project scope |
| 409 | `inventory_preflight_stale` | 重新 preflight 與 review |
| 409 | `inventory_selection_target_missing` | 標記 missing，重新 preflight |
| 409 | `inventory_selection_target_changed` | 清除 choice，重新 review |
| 422 | `inventory_selection_post_decision_blocked` | 顯示 hard block，不建立 scan |
| 500/422 | `inventory_rules_unavailable` | `baseline_error`；不顯示 review controls |
| 500/422 | `inventory_rules_invalid` | `baseline_error`；不顯示 review controls |

Error body 固定有 `detail.code`、安全的 `message`、`retryable` 與 optional bounded `context`。
UI 不顯示 TOML content、package path、absolute local path、raw exception 或 secret。

Catalog error 的最終 HTTP status 要在 Plan 20 Task 9 同步到三份 canonical contract 後凍結；在此之前
Frontend 必須以 stable `detail.code` 分流，不可依自由文字猜測。

## 8. Frontend invariants

- Preflight 成功前不能進 review；baseline error 不得 fallback 成 blank picker。
- Pending／stale／pre-snapshot error 不得接受或合成 `scan_id`。
- `proposal_id` 去重；`(target_path, selection_scope)` 不可送 duplicate/conflicting decision。
- Directory 只送一筆 scoped decision，不解析 cursor，也不在 browser enumerate descendants。
- `observed_at_least` 是下限，不顯示成精確總數。
- Cancel、completed 與 project change 都清除 preflight／one-run decisions。
- Apply 不重開 review；Rescan 必須重新 preflight。
- Frontend 不從 reason、extension 或 counts 推導 policy outcome。
- Selection state 不進 Manual Mapping，也不新增 UA state。

## 9. 實作與驗證 gate

Plan 20 的 **backend contract freeze gate**（不等待 frontend 實作）：

1. Backend Pydantic request／response／OpenAPI tests。
2. API E2E 驗證 target repo tree／Git status 前後不變。
3. API E2E 驗證 hard-blocked descendant 從未被讀取，summary 與 snapshot audit counts 一致。
4. `docs/API-GUIDE.md`、`docs/MODEL-CONTRACT.md`、`frontend/API_CONTRACT.md` 同步完成。

Meeting-Sync frontend work 啟用新 flow 前另需通過：

1. Zod parse tests，特別是 pending response 沒有 `scan_id`。
2. State-machine、stale refresh、directory scope、baseline-error 與 accessibility tests。
3. Frontend test／lint／build 與 browser E2E。

Frontend gates 不阻擋 Plan 20 backend DoD；在它們完成前，這些 samples 仍不可當成 current UI
behavior。

本資料夾的靜態檢查：

```bash
find docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate \
  -name '*.json' -print0 | xargs -0 -n1 jq empty

git diff --check -- \
  docs/work/Timmy/design/EPIC1/frontend-json-handoff
```
