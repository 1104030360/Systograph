# Phase 2 前端同步總覽（2026-07-07）

Last updated: 2026-07-08（10+1 計數、state vs build、ViewerLoadResult、render 用途）

> **2026-07-06 superseding taxonomy:** 固定 reference catalog 改為 10 planes /
> 52 nodes；plane/node ids 以 `docs/MODEL-CONTRACT.md` 與 Plan `01A` 為準。

## 單一真相來源（Source Of Truth）

本同步包以以下文件為準：

- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/dynamic-trace-plan/00-implement-static-call-graph-and-execution-path-mvp.md`
- `docs/MODEL-CONTRACT.md`
- `docs/API-GUIDE.md`（HTTP 端點、`ViewerLoadResult` 聚合與 lazy-load 契約）

若本資料夾內的 sync 文件與上述計畫衝突，執行 stage / gate 以
`static-trace-plan/README.md` 為準，Step 1～9 pipeline 與同日修訂的 Step 6 邊界以
`00-phase2-pipeline-ascii-map.md` 為準；欄位語意、五態、activation、artifact lifecycle 與
`GraphViewModel` 邊界以 `MODEL-CONTRACT.md` 為準；API 載入策略以 `API-GUIDE.md` §
`ViewerLoadResult` 為準。

## 產品方向（Product Direction）

Phase2 的前端同步不再以「RAG 類型分類」為中心。新的產品語意是：

```text
Input AI system repo / workflow artifacts
  -> Step 3 staged rollout
     Phase A：Systograph scan TOML providers primary，UA sidecar 可為 null
     Phase B：UA structural primary + TOML parity
     Phase C：UA only
     + reserved nullable semantic sidecar slot（Phase2 active path 不產生、不消費）
  -> Step 4 backend Python bridge 產生 evidence-backed system map
  -> Step 6 ProfileInferenceService（純 Python）直接定案 capability overlays / 五態 / readiness findings
     Plan 17 AssessmentOrchestrator / AI semantic candidate flow deferred
  -> Step 7 backend projection 產生 reference map + repo overlay / static inferred execution map
  -> frontend render results and optional review queue
```

前端不需要判斷 repo 是哪一種 RAG，也不需要從 evidence 自行推論 profile。Backend
會輸出可渲染的 map、sidecar、readiness 與 static execution artifacts；frontend
負責 contract parsing、顯示、互動、warning 與使用者 review decision。

**2026-07-07 UA 整合決策：** 這是 backend scanner / assessment 內部架構調整；
frontend contract、sample JSON schema 與 public artifact 欄位 **零變更**。Frontend 唯一可能感知
的是 Phase B/C 的 UA fail-closed 時，build API 以既有 error contract 回報失敗；Phase A
的 `ua_analysis_result=null` 仍必須可完成 build / Apply。Frontend contract 不會新增
`signal_origin`、`confidence` 或 candidate 欄位。

## 首次 Scan 使用者體驗（First Scan UX）

第一次 scan 必須先產生可用結果。使用者不需要先完成「檢查 scanner 建議」
流程才能看到報告。

```text
Auto scan
  -> show system map / readiness / profile overlays / static execution artifacts
  -> show a small review queue for high-impact ambiguous evidence
  -> user may accept / edit / reject / skip
  -> Apply（同一 snapshot）或 explicit rescan 套用 confirmed decision
```

詳細差異見 [`rescan-vs-apply.md`](rescan-vs-apply.md)。

UI 不要寫成：

```text
Scanner 無法判斷，請你手動分類後才能看結果。
```

應寫成：

```text
Scanner 已產生報告。有少數項目建議 review，可讓後續 scan 更精準。
```

## 必要產出物認知（Required Output Awareness）

Frontend 要知道 Phase2 P0 會有多個 **independent sibling artifacts**（磁碟上 **10 個 public
檔**），不是一個 aggregate JSON。另加 **1 個 ephemeral API projection**（`graph_view_model`，
**不**列為 atomic-publish 磁碟 sibling 檔）：

```text
JSON（7）
  ai_system_map.json
  profile_signals.json
  readiness_report.json
  call_graph.json
  dataflow_hints.json
  execution_paths.json
  evidence_table.json

Render（3）
  ai_system_map.md
  system_map.mmd
  execution_map.mmd

Ephemeral（API only，非 sibling 磁碟檔）
  graph_view_model  ← Step 7 GraphProjectionService 投影；隨 ViewerLoadResult inline
```

JSON artifacts 之後可各自映射成 database table 或 table group。Frontend 不要假設全部都
被塞在 `ai_system_map.json`。

`ua-analysis-result` / `ScanSnapshot.ua_analysis_result` 是 **snapshot-internal reserved
slot**，不是 public artifact；frontend contract **不得** fetch 或解析。

### 不算進 7 JSON 的 persistence（Frontend 必知）

以下 JSON 存在 **project state store**，不是 `output/{build_id}/` 的 build siblings：

| 儲存 | Step | 與 Viewer 關係 |
|------|------|----------------|
| `scans/{scan_id}/snapshot.json` | 3 | build **輸入**；Apply 重用同一 scan |
| `mappings/{mapping_id}.json` | 9 | 使用者 decision；經 `/api/mappings`，非 `artifact_refs` |
| `project.json`、build manifest | 1 / 7 | metadata only |

Rescan → 新 `scan_id` + 新 snapshot + 新 build。Apply → 同 snapshot、新 `build_id`、
新 10 siblings。見 [`rescan-vs-apply.md`](rescan-vs-apply.md)。

### Render 三檔（export，非主畫布）

| 檔案 | 用途 |
|------|------|
| `ai_system_map.md` | Epic 1 人類可讀報告（`GET /api/map/report`） |
| `system_map.mmd` | 架構 Mermaid export（Plan 06） |
| `execution_map.mmd` | static execution Mermaid export（dynamic 00） |

三者不參與 scoring；Phase2 target 為 **`artifact_refs` lazy**；主 canvas 仍用 inline
`graph_view_model`。

## ViewerLoadResult 載入策略（Phase2 target）

Build 在磁碟上仍 publish 上述 sibling 檔；**`ViewerLoadResult`** 是 Viewer **首次載入用的
API 聚合**，不是把多份 JSON merge 成單一 bundle 檔。詳細 sample 見
`docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-08-viewer/README.md`。

| 來源 | 磁碟 artifact / 投影 | `ViewerLoadResult` 欄位 | 載入方式 |
|------|----------------------|-------------------------|----------|
| Step 4 | `ai_system_map.json` | `ai_system_map` | **inline** |
| Step 6-1 Profile Inference | `profile_signals.json` | `profile_inference_result` | **inline**（≡ 同 schema；欄位名不同） |
| Step 6-2 Readiness | `readiness_report.json` | `readiness_report` | **inline** |
| Step 7 投影 | （無獨立 sibling 檔） | `graph_view_model` | **inline**（ephemeral；非磁碟檔） |
| Step 6-3～5 static execution | `call_graph.json` / `dataflow_hints.json` / `execution_paths.json` | — | **`artifact_refs[]` only**（lazy load） |
| Step 6-6 | `evidence_table.json` | — | **`artifact_refs[]` only**（lazy load） |
| Step 7 render | `*.md` / `*.mmd` | — | **`artifact_refs[]` only**（lazy load） |

重點：

- **主畫布 ≠ merge 六份 Step 6 JSON。** Viewer load 時 **不得**把 `profile_signals.json`、
  `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、`readiness_report.json`、
  `evidence_table.json` 拼成單一 graph JSON。
- **只有 6-1 Profile Inference 結果**（經 Step 7 `GraphProjectionService`）進 **主 canvas**
  （52 格 reference overlay、repo overlay、`profile_attachment` 等）。`readiness_report` 供
  report 面板；static execution 三件套與 `evidence_table` 供 Inspector / debug **lazy surface**。
- Frontend 消費 **`graph_view_model`**（canvas）與 **`profile_inference_result`**
 （panel / 詳情）；API mode **不**直接讀 server-local sidecar path。
- Sidecar 缺失或 invalid → **degraded load + warnings**（例如 `profile_signals_missing`），
  **不** blocking canonical `ai_system_map` / base graph。
- Lazy load 必須以 `project_id` + `build_id` scope 呼叫 **受控 artifact API**；`artifact_refs`
  不含 absolute path。

命名對照（禁止混用）：

| 層級 | 名稱 |
|------|------|
| 流程 / 服務 | **Profile Inference** / `ProfileInferenceService`（Step 6-1） |
| 磁碟 sibling | `profile_signals.json`（`profile-signals/v1`） |
| API 欄位 | `profile_inference_result: ProfileInferenceResult \| null` |

## Backend / Frontend 職責切分

| 領域 | Backend 負責 | Frontend 負責 |
|---|---|---|
| Canonical map | `ai_system_map.json`、schema、evidence refs | 解析並渲染目前 payload |
| Evidence table | `evidence_table.json` writer 與 stable ids | evidence detail / table UI（若對外暴露） |
| Profile overlays | `profile_signals.json`、status、related refs | 唯讀 profile 呈現 |
| Readiness | `readiness_report.json`、findings | report cards、warnings、導覽 |
| Static execution | `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` | payload 存在時顯示 static-only execution map |
| Graph Studio | reference map、repo overlay、five-state/activation、Mapping Completeness、lens/evidence projection | 組合 backend projection、lenses、Evidence Inspector 與完整 UI states；不做 inference |
| Review scanner suggestions | proposal candidates、validation、confirmed decision persistence | review queue UX 與 decision mutation |
| Runtime trace | dynamic `01`、opt-in `/api/trace` | 僅在 backend contract 就緒後做 transient focus |

### Pipeline bridge boundary（Frontend 必讀）

完整 Step 1～9 見 `00-phase2-pipeline-ascii-map.md`。下表為 **frontend 視角** bridge 邊界
（Step 5 / 8 未列於舊版表，但 Viewer 仍會消費其產物）：

| Step | Backend 意義 | Frontend 可做 | Frontend 不可做 |
|---|---|---|---|
| Step 3 staged scan | Phase A 以 Systograph scan TOML providers 為 primary；Phase B 改為 UA structural primary + TOML parity；Phase C 為 UA only。Semantic sidecar 是 reserved nullable slot，Phase2 active path 不產生、不消費 | 不直接消費；只理解 Phase B/C build error 可能來自 fail-closed structural scan | 依賴 `ua-analysis-result.json`、新增 schema 欄位或讀 internal sidecar |
| Step 4 Bridge 1 | `rule_id + evidence` → repo component / unmapped / candidate input | 顯示 backend 已投影的 component、unmapped、review queue | 從 rule id、dependency、檔名自行建立 component |
| Step 5 Index | read-only lookup；不寫檔、不 infer | （無直接 UI） | 依賴 index 或自行 rebuild topology |
| Step 6 Bridge 2 | `ProfileInferenceService` 以純 Python 對 validated map ↔ 10 planes / 52 reference nodes 定五態 / profiles / completeness；Plan 17 AI flow deferred | 顯示 backend status、reason、related refs（經 `profile_inference_result`） | 自己把 repo node 對到 reference node、推五態或信任 internal semantic sidecar |
| Step 7 Projection | fixed reference map + repo overlay → **`graph_view_model`** | render backend projection、lens、legend、Evidence Inspector | 從 layout、顏色或缺欄位重算 completeness；merge sibling JSON 建 graph |
| Step 8 Viewer | 聚合 `ViewerLoadResult`（inline + `artifact_refs`） | 解析 contract、render、warning、optional review 入口 | load-time 重算 profile inference 或 assessment |
| Step 9 Review | **post-build** optional：對 unmapped 建 proposal，存 confirmed decision | accept/edit/reject/skip decision mutation | 讓 proposal 直接改 JSON 或 profile status |

## 計畫影響摘要（Plan Impact Summary）

| Backend plan | Frontend 影響 |
|---|---|
| `00A` | 準備 v1/v2 compatibility migration；active cutover 稍後進行。 |
| `01` | 以 ambiguous evidence review 取代 extension-confirmation UX。 |
| `01B` | Step 4 Python component bridge registry；frontend 不消費 scan TOML，也不自行做 component mapping。 |
| `01A` | 定義可由 TOML 維護的固定 10 Plane／52 reference node catalog 與 stable ids。 |
| `02` | 渲染 stackable capability overlays；不在 frontend 分類 profile。 |
| `03` | 將 profile/readiness sidecar 視為 independent artifacts，missing 時 degraded warning。 |
| `03A` | Rescan vs Apply、`scan_id`/`build_id` lineage；Apply 重用 snapshot、不重掃 repo。見 [`rescan-vs-apply.md`](rescan-vs-apply.md)。 |
| `04` | Profile inference 維持唯讀，與 mapping proposal lifecycle 分離。 |
| `05`–`09` | 預期 backend projection/index 收斂；frontend 消費 projection，不重建 topology。 |
| `10`–`11` | Profile labels/metadata 來自 backend payload；frontend 不得 hard-code registry metadata。 |
| `12` | Runtime trace 僅 deferred boundary；static plan 不啟動實作 task。 |
| `13` | Active v2 cutover 在 compatibility gate 通過後退役 legacy extension output。 |
| `14` | 以真實 AI system repo 與 fixtures 驗證 UA-primary / parity gate、sample/API mode；不依賴 Plan 17。 |
| `15` | 僅在 `00A`、`13`、`14` 通過後完成 legacy v1 退役。 |
| `16` | Gate-1 後導入 UA structural primary、snapshot internal sidecar 與 TOML parity harness。 |
| `17` | `AssessmentOrchestrator` / AI semantic candidate flow deferred；不是 Plan 14 前置，frontend 不得依賴。 |
| `18` | Plan 14 parity gate 通過後才退役 Systograph scan TOML providers 主掃描路徑。 |
| `19` | Step 2 inventory include / ignore metadata；不改變 Step 6 ownership。 |
| dynamic `00` | 新增 static call graph、dataflow hints、execution paths、evidence table 認知。 |

## Graph Studio Work Item

Graph Studio 本次新增與調整的 frontend contract 統一記錄在
`frontend-graph-studio.md`。這是提供 Hardy 實作與同步的交接文件；本次決策不得直接回寫或
修改 `docs/work/Hardy/` 底下的既有 plan。若後續規格再變更，仍更新本 Meeting Sync，
由 Hardy 自行決定如何整合進其執行計畫。

它依賴：

- Hardy Task `5` 的正式 Viewer API/session payload；
- Timmy Plan `00A` 的 v2 compatibility contract；
- Timmy Plan `01B` 的 Step 4 bridge boundary；
- Timmy Plan `01A` 的 reference catalog、plane/node identity 與 metadata contract；
- Timmy Plan `06` 的 backend `GraphViewModel` / projection contract；
- Timmy Plan `14` 的 sample/API、真實專案與 degraded-state 驗證；
- Timmy Plan `15` compatibility gates 通過後的 legacy v1 retirement。

Graph Studio 在同一張固定 reference map 上，以按鈕切換 repo overlay，並呈現 backend 提供的
`detected`、`partial`、`undetermined`、`not_detected`、`conflicted`、獨立 activation、
Mapping Completeness、六種 lenses 與 Evidence Inspector。`DeepResearch` 僅作視覺／
互動參考，不是可複製的 frontend implementation 或資料 contract。

Mapping Completeness 的固定權重為 `detected=1`、`not_detected=1`、`partial=0.5`、
`undetermined=0`、`conflicted=0`；denominator 是全部固定 reference nodes，activation 不納入。

Graph Studio 不重做已完成的 Hardy Task `2` React Flow/ELK graph engine，也不重做 Task `4`
node/edge detail 與 replay interaction。Validation Simulator 與 runtime trace 不在本工作項目。

## DeepResearch Icon 搬移工作事項

`DeepResearch` 示意頁中的 icon 需整理並搬到正式 `frontend`，詳細 inventory、實作邊界與
驗收標準見 [`frontend-deepresearch-icon-migration.md`](frontend-deepresearch-icon-migration.md)。
此工作只搬移 icon 與必要呈現樣式，不搬移示意頁的資料、schema、inference 或互動邏輯。

## 2026-07-03 Frontend Stability Baseline

原本的 `frontend_sync_2026_07_03.md` 已在 2026-07-20 完整合併到
[7/15 前端同步總覽](../meeting_sync_2026_07_15/frontend-sync-overview.md)，因此不再保留獨立檔案。

- #221～#226 與 #232 已合併，作為不得回歸的 frontend stability / test baseline。
- 尚未完成的 #198、#199、#218、#227 與 #231 已依 current backend contract 改寫到
  [Backend-ready integration](../meeting_sync_2026_07_15/frontend-backend-ready-integration.md)。
- Current 驗證與交付順序以 7/15 同步包為準，不再沿用 7/3 的舊 contract freeze 假設。

## Frontend 執行順序

1. Review scanner suggestions UX 與 proposal decision flow。
2. Profile overlay / attachment rendering。
3. Artifact output 與 evidence table 認知。
4. Readiness findings panel 與 Evidence Inspector。
5. Graph Studio：reference map/repo overlay、五態/activation、Mapping Completeness、
   lenses、Evidence Inspector 與完整 UI states。
6. Static execution map display contract 維持既有獨立 surface，且不宣稱 runtime；不列入
   Graph Studio 六個固定 lenses。
7. v2 compatibility 與 legacy extension retirement。
8. Runtime trace deferred boundary 認知（僅文件層級，不納入 Graph Studio）。
9. 搬移 `DeepResearch` 全部 icon 到正式 frontend，並完成 accessibility、theme、responsive
   與 regression 驗證。

## 禁止事項（Do Not Do）

- 不要在 frontend infer profile、component bridge 或 reference-node mapping。
- 不要要求 Review scanner suggestions 完成後才顯示首次 scan 結果。
- 不要建立 frontend-only extension nodes。
- 不要把 static execution paths 當 runtime proof。
- 不要 write back 到 `ai_system_map.json`、`profile_signals.json` 或 execution artifacts。
- 不要依賴 active v2 payload 的 top-level `extensions`。
- 不要 hard-code profile labels、axes 或 implementation depth 文案。
- 不要在 Graph Studio 計算 Mapping Completeness、activation、five-state 或 lens membership。
- 不要直接複製 `DeepResearch` 網頁的 HTML、CSS、JavaScript 或 hard-coded data。
- 不要把 Validation Simulator 或 runtime trace 放入 Graph Studio work item。

## 同步完成檢查清單（Sync Completion Checklist）

- [ ] Frontend 已讀完本資料夾每一個檔案（含 [`rescan-vs-apply.md`](rescan-vs-apply.md)）。
- [ ] 對外 artifact 計數：**10 public siblings + 1 ephemeral `graph_view_model`**；不寫「11 sibling JSON」。
- [ ] 不把 `snapshot.json` 或 `mappings/*.json` 算進 build 7 JSON。
- [ ] `ViewerLoadResult` inline vs `artifact_refs` lazy load 已對齊上表；主畫布只消費
      `graph_view_model`，不 merge Step 6 sibling JSON。
- [ ] Sample mode 與 API mode 已用同一 active contract 測試。
- [ ] Review scanner suggestions queue 為 optional，不阻擋 report rendering。
- [ ] Active payload parsing 不要求 `extensions`。
- [ ] Frontend 能在 sidecar missing 時以 warning 降級，而非 hard failure。
- [ ] Static execution UI 將所有 path 標為 static inferred / not runtime verified。
- [ ] Runtime trace 維持 opt-in，且在 static map flow 之外。
- [ ] Hardy／Frontend 已讀完 `frontend-graph-studio.md`，並以本 Meeting Sync 接收本次新增規格。
- [ ] Hardy／Frontend 已讀完 `frontend-deepresearch-icon-migration.md`，並完成全部 icon 的
      source-to-target inventory。
- [ ] Graph Studio 使用 backend projection，未建立 frontend-only graph/inference contract。
- [ ] Graph Studio 的 loading、empty、error、degraded、accessibility 與 responsive states 已納入驗收。
- [ ] 0703 frontend stability baseline 仍有效：sample/API mode 標示、request cancellation、
      SSE reconnect tolerance、API base URL fallback 與 frontend test gate 沒有 regression。
