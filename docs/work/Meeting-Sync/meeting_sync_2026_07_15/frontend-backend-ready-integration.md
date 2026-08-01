# 前端工作：串接目前已完成的 Backend 功能

Status: backend ready；frontend `main` 尚未完整串接

Last updated: 2026-07-20（依 current backend code、frontend `main` 與 GitHub PR 狀態重查）

## 目的

目前 frontend `main` 已能匯入專案、開始基本 scan、顯示 SSE progress，並載入基本 Viewer。
但 Detail Scan、Mapping Proposal、Apply、Query Trace、build-scoped Viewer 與 report 等 backend
功能仍未完整接上。

這份文件只整理 **backend 已經可以提供、frontend 還要做的工作**。尚未有安全 public API 的
artifact 不會被寫成 frontend 現在就能完成的功能。

## 已完成的 Frontend 基線

7/3 文件記錄的穩定性工作已合併進 `main`，後續改動必須保留：

| 已完成項目 | Frontend 必須維持的行為 |
| --- | --- |
| #221 Scan state reset | cancel、import error、scan error 都會停止 progress 與 SSE |
| #222 Request cancellation | 切換來源或 unmount 時取消舊 request；cancel 不顯示成 timeout |
| #223 Sample indicator | Sample mode 一直清楚標示為範例；API mode 不顯示 |
| #224 Mock honesty | 尚未串 API 的畫面必須標示 Sample，無作用按鈕必須停用 |
| #225 API base URL fallback | 空的 `VITE_API_BASE_URL` 使用 `http://127.0.0.1:8000` |
| #226 SSE reconnect | 單次瞬斷先交給 EventSource 重連，不在第一次 error 就永久降級 |
| #232 Test foundation | Vitest、RTL、jsdom 與 frontend CI 已存在；新串接必須補 regression tests |

## 尚未完成的工作總表

| 工作 | Backend 狀態 | Frontend `main` 狀態 |
| --- | --- | --- |
| Project / build-scoped Viewer | latest、history、指定 build API 已完成 | 仍使用 process-wide `/api/map` |
| Apply confirmed mappings | `POST /api/map-builds/{base_build_id}/apply` 已完成 | 沒有 Apply flow |
| Detail Scan | `POST /api/detail-scans` 與 child build 已完成 | 仍以 sample detail 為主 |
| Mapping Proposal / Mapping | list、create、decision、mapping CRUD 已完成 | Scan Template / Proposal 仍由 mock seam 驅動 |
| Query Trace | `POST /api/trace` 已完成 | 只 replay sample event，沒有送出 trace request |
| Report | session-level `GET /api/map/report` 已完成 | 可做 demo action；project / build-scoped action 待安全 API |
| Profile / readiness / rich graph | build-scoped response 已 inline 回傳 | Zod / UI 只保留舊 graph 子集合 |
| Static execution /其他 artifacts | 磁碟已 atomic publish 10 siblings | 尚無 safe `artifact_refs` / public fetch API，先不串 |

Scan Inventory 與 v2 / legacy extension 有獨立工作文件：

- [Scan Inventory Review](./frontend-inventory-selection-review.md)
- [ai-system-map/v2 與 Legacy Extension 退役](./frontend-ai-system-map-v2-cutover.md)

## 1. 改用 Project / Build-scoped Viewer

### 要做什麼

- Scan 完成後保存 response 的 `project_id`、`scan_id` 與 `build_id`。
- Interactive project flow 維持 Import → Preflight → Scan；不要改呼叫沒有 `project_id` 的 demo
  endpoint `POST /api/map/build`。
- 使用 `GET /api/projects/{project_id}/map-builds/latest` 載入目前專案，而不是依賴
  process-wide `/api/map`。
- 重新開啟已知 project 時，可用 `GET /api/projects/{project_id}` 取得基本資訊；map 仍從 latest
  build endpoint 取得。
- 需要歷史時使用 `GET /api/projects/{project_id}/map-builds`；指定結果使用
  `GET /api/map-builds/{build_id}`。
- project、build 或 data source 改變時，取消舊 request，並清除不屬於新 build 的 detail / trace
  state。

### 為什麼

`/api/map` 只代表目前 process session 的最新 demo map。多專案或 Apply / Detail Scan 產生 child
build 後，frontend 必須用 project / build identity 才不會顯示錯的結果。

## 2. 串接 Apply Confirmed Mappings

### 要做什麼

- 從 `/api/mappings?project_id=...` 取得已確認且可套用的 mapping。
- 呼叫 `POST /api/map-builds/{base_build_id}/apply`，只送 non-empty、unique、同 project 的
  confirmed mapping ids。
- 成功後直接切到 response 的新 `build_id` 與 `viewer_load_result`。
- 409 `base_build_not_latest` 時重新載入 latest，不能在舊 base 上自動重試。

### 為什麼

Apply 會重用同一份 snapshot，建立新的 child build；它不是 Rescan，也不會重新讀 repo。
Frontend 如果把 Apply 當成 Scan，會失去正確的 `scan_id` / `build_id` lineage。

## 3. 串接 Detail Scan

對應舊 PR [#198](https://github.com/1104030360/Systograph/pull/198)。此 PR 仍為 OPEN，
目前與 `main` 有衝突，不能直接視為已完成。

### 要做什麼

- 從目前 graph selection 建立 `project_id`、optional `build_id`、`target_type`、`target` 與
  `scan_depth` request。
- 呼叫 `POST /api/detail-scans`；需要回讀單筆時使用
  `GET /api/detail-scans/{detail_scan_id}`。
- 成功時使用 response 的 child `build_id` 與 `viewer_load_result`，不要只重新讀 process-wide
  `/api/map`。
- 顯示 backend 回傳的 bounded detail、evidence、warnings 與 code-path hops，不顯示 raw secret。
- 處理 `base_build_not_latest`、`scan_snapshot_stale`、`profile_sidecar_unavailable` 與
  `target_not_found`。

### 為什麼

Detail Scan 會補充局部證據，並建立 child build。Frontend 要切到 backend 回傳的新 build，才能
保留 parent history，也避免把新 detail 接到錯的 graph。

### PR 處理方式

重新 rebase 或重建 frontend-only PR。舊 PR 內的 backend service / test 修改不要直接帶進新的
frontend PR；若仍有 backend gap，另外交由 backend owner 判定。

## 4. 串接 Mapping Proposal、Manual Mapping 與 Apply

對應舊 draft PR [#199](https://github.com/1104030360/Systograph/pull/199)。它仍疊在
#198 上，而且使用舊的 extension contract，不能直接合併。

### 要做什麼

- 使用 `GET /api/mapping-proposals?project_id=...` 顯示 proposal lifecycle。
- 使用 `POST /api/mapping-proposals` 為 unmapped item 建立 proposal。
- 使用 `POST /api/mapping-proposals/{proposal_id}/decision` 支援 accept、edit、reject、
  `skip_for_now`；畫面只顯示該 proposal `available_actions` 允許的操作。
- 同時讀 `GET /api/mappings?project_id=...`；proposal state 與 persisted mapping state 是兩份資料，
  frontend 必須合併顯示。
- 若產品保留「直接新增 Manual Mapping」，使用 `POST /api/mappings`；修改既有 mapping 使用
  `PATCH /api/mappings/{mapping_id}`。沒有這個明確入口時，正常流程應從 proposal decision 建立。
- Candidate type 與 legacy 移除規則依
  [v2 cutover 工作](./frontend-ai-system-map-v2-cutover.md)。
- Decision 會儲存可稽核的 manual mapping，但不會改寫目前 map；使用者按 Apply 後才建立新 build。

### 為什麼

Proposal 是建議，Manual Mapping 是已儲存的使用者決策，Apply 才真正產生新的 Viewer build。
把三者混成一次 request，會讓畫面誤以為 accept 已直接改寫 canonical map。

## 5. 串接 Query Trace

對應舊 draft PR [#218](https://github.com/1104030360/Systograph/pull/218)。Backend
endpoint 仍可用，但 PR 需要依 current v2 / build-scoped contract 更新。

### 要做什麼

- 只有使用者明確按下 Run 才呼叫 `POST /api/trace`。
- Request 使用 `project_id`、optional `build_id`、v2 `endpoint_id`、query 與 1–120 秒 timeout。
- 顯示 `events[]`、warnings、partial / error 狀態與 `source_build_id`；不要把 trace 寫回 map。
- 切換 project / build / source 時清除舊 runtime trace。
- Query、retrieved chunk 或 provider output 只顯示 backend 已 masking 的安全欄位。

### 為什麼

Static execution path 與真實 runtime trace 是不同資料。Frontend 不能拿 static path 假裝這次
query 真的經過該節點，也不能因 trace 失敗破壞 base graph。

## 6. Report 與其他 Artifacts

對應舊 PR [#227](https://github.com/1104030360/Systograph/pull/227)。Report action 仍可用，
但「由使用者輸入 server-local map path」不應成為正常 project flow。

### 現在可以做

- 只在畫面清楚標示「latest session / demo」時，使用 `GET /api/map/report` 以純文字 preview。
- 使用 `GET /api/map/report?download=true` 下載 report。
- Report 不以 HTML 注入畫面，也不自行解析出新的 canonical facts。

### 現在不要做

- 不把 `POST /api/viewer/load` 的 `map_json_path` 暴露成一般使用者的檔案輸入流程；它是
  server-local compatibility endpoint。
- 不把 session-level report 說成目前選取 project / build 的 report。
- 不直接讀 backend 回傳的 `*_path`。
- 不為 static execution、evidence table 或 Mermaid 檔案自行拼 server URL。

目前 build-scoped response 尚無 safe `artifact_refs` / public artifact fetch API。正常 project flow
的 report 與其他 artifact，要等 backend 提供 stable id 與受控 endpoint；不能靠 session latest 猜測。

### 為什麼

Session-level endpoint 沒有 project / build identity。若直接放進正常 project flow，使用者可能會
下載到另一個 session 的最新報告；server-local path 也不應暴露給 browser。

## 7. 顯示 Rich Graph、Profile 與 Readiness

### 要做什麼

- 擴充 Zod schema，保留 backend `graph_view_model` 的 rich node identity、relationship、status、
  activation、profile / reference details 與 filters / lenses。
- 顯示 `build_result.profile_inference_result` 與 `build_result.readiness_report`。
- 主圖只 render backend projection；不要從 topology、檔名或 count 重算五態、activation、
  Mapping Completeness 或 readiness verdict。
- `profile_signals_missing_or_invalid` 或 `readiness_report_missing_or_invalid` 時顯示 degraded warning，
  base graph 仍可開啟。

### 為什麼

Backend 已經用同一個 build 的 evidence 產生 projection、profile 與 readiness。Frontend 若再推論
一次，會形成第二套真相，且可能與 report 不一致。

## 舊 PR 的處理結論

| PR | 2026-07-20 狀態 | 接下來 |
| --- | --- | --- |
| #198 Detail Scan | OPEN、merge state DIRTY | 依 current child-build response 重建 / rebase；移除 frontend PR 內 backend mutation |
| #199 Mapping Proposal | OPEN draft、stacked on #198 | 拆成獨立 PR；更新四種 candidate、manual mapping 與 Apply flow |
| #218 Query Trace | OPEN draft | rebase；增加 optional build identity、warnings 與 v2 endpoint handling |
| #227 Artifact Actions | OPEN | 保留 safe report；移除一般 UI 的 server-local path loader；artifact refs 延後 |
| #231 API tests | OPEN issue | Contract 更新後補 API-facing tests、mocks 與 fixtures |

## 建議實作順序

每個階段使用獨立 PR，不把所有功能塞在同一 branch：

1. v2 type / sample + project / build-scoped Viewer + API-facing tests。
2. Scan Inventory preflight 與 one-run selection。
3. Detail Scan child-build flow。
4. Mapping Proposal / Manual Mapping / Apply。
5. Query Trace。
6. Report action與 rich profile / readiness panels。

## 驗收清單

- [ ] `frontend/API_CONTRACT.md` 不再把已存在的 API 寫成 future endpoint。
- [ ] API mode 不再以 process-wide `/api/map` 作 project workflow 的唯一來源。
- [ ] Scan、Apply、Detail Scan 都保存並切換正確的 `scan_id` / `build_id`。
- [ ] Proposal 與 Manual Mapping 分開讀取；Accept 不直接改 graph，Apply 才切 child build。
- [ ] Query Trace 必須 opt-in，且不污染 canonical graph / static execution state。
- [ ] Report 以純文字安全顯示；frontend 不接收或拼接 server-local artifact path。
- [ ] Profile / readiness 缺失只顯示 degraded warning，不讓 base graph 崩潰。
- [ ] Sample / mock 畫面維持明確標示，沒有可點但無作用的假按鈕。
- [ ] Request cancellation、SSE reconnect、scan reset 等 7/3 baseline 沒有 regression。
- [ ] 每個功能都有 Vitest / RTL service、hook、component 測試，再通過 lint、build 與 API mode QA。

## Source of truth

- [API Guide](../../../API-GUIDE.md)
- [Model Contract](../../../MODEL-CONTRACT.md)
- [Plan 13](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md)

若本文件與 current backend code、API Guide 或 Model Contract 衝突，以 current backend code 與
canonical contract 文件為準。

## 不屬於目前 Frontend 工作

- 自行解析 backend filesystem、TOML 或 raw artifact directory。
- 在 browser 實作 v1-to-v2、legacy mapping 或 persisted data migration。
- 在 frontend 重跑 component detection、profile inference、readiness 或 graph projection。
- 在 safe artifact API 尚未存在前自行讀取 static execution / evidence / Mermaid 檔案。
- 修改 backend operator rollback、migration command 或 canonical artifact publisher。
